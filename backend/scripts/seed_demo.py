"""Create a small connected Azerbaijan catalog for local manual exploration.

The operation is idempotent: stable branch addresses, plate numbers, product
codes, policy bundle and rate-plan versions are reused on later runs.
"""
import argparse
import asyncio
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, update, func

from app.core.config import settings
from app.core.security import digest
from app.db.session import Session, engine
from app.models import (
    AdminUser, Branch, Extra, FxRate, PolicyDocument, PricingRule,
    RatePlan, RentalPolicy, Vehicle, Reservation, VehicleAllocation,
)
from app.services.policies import ingest
from app.services.audit import now


POLICY_KEY = "demo-azerbaijan-rental"


POLICIES = {
    "en": """# Demo Azerbaijan rental policy

## Driver age
The minimum driver age is 21 years. The renter must present a valid driving licence and passport or identity document at pickup.

## Mileage and fuel
The daily allowance is 250 kilometres. Additional kilometres are charged according to the current rate plan. The vehicle is supplied with the recorded fuel level and should be returned at the same level.

## Insurance and deposit
Basic insurance is included in the rental price. The security deposit is collected at pickup and is released after the vehicle is returned and inspected.

## Changes and cancellation
Changes are subject to availability and the published modification fee. Cancellation is free until 24 hours before pickup; later cancellation may incur the published cancellation fee.
""",
    "az": """# Azərbaycan demo icarə siyasəti

## Sürücü yaşı
Minimum sürücü yaşı 21-dir. İcarəçi avtomobili götürərkən etibarlı sürücülük vəsiqəsi və pasport və ya şəxsiyyət sənədi təqdim etməlidir.

## Yürüş və yanacaq
Gündəlik limit 250 kilometrdir. Əlavə kilometrlər cari tarif planına əsasən hesablanır. Avtomobil qeyd olunmuş yanacaq səviyyəsi ilə verilir və eyni səviyyədə qaytarılmalıdır.

## Sığorta və depozit
Əsas sığorta icarə qiymətinə daxildir. Təhlükəsizlik depoziti avtomobil götürülərkən alınır və avtomobil qaytarılıb yoxlanıldıqdan sonra sərbəst buraxılır.

## Dəyişiklik və ləğv
Dəyişikliklər mövcudluq və dərc olunmuş dəyişiklik haqqından asılıdır. Götürmə vaxtına 24 saat qalmışadək ləğv pulsuzdur; daha gec ləğv üçün dərc olunmuş ləğv haqqı tətbiq oluna bilər.
""",
}


BRANCHES = [
    {"key": "city", "name_az": "Bakı mərkəz ofisi", "name_en": "Baku city office", "city": "Baku", "address": "12 Nizami Street, Baku, AZ1000", "opening_hours": {"mon-sun": "09:00-21:00"}},
    {"key": "airport", "name_az": "Hava limanı ofisi", "name_en": "Airport office", "city": "Baku", "address": "Terminal 1, Heydar Aliyev International Airport, Baku", "opening_hours": {"mon-sun": "00:00-23:59"}},
    {"key": "sumqayit", "name_az": "Sumqayıt regional ofisi", "name_en": "Sumqayit regional office", "city": "Sumqayit", "address": "25 Sülh Street, Sumqayit, AZ5000", "opening_hours": {"mon-sun": "09:00-19:00"}},
]


def branch_key(branch):
    value = f"{branch.name_en} {branch.city} {branch.address}".lower()
    if "airport" in value or "hava limanı" in value or "hey dar aliyev" in value:
        return "airport"
    if "sumq" in value or "sumgay" in value:
        return "sumqayit"
    if branch.city.lower() == "baku" or "baki" in value or "baku" in value:
        return "city"
    return None


async def reconcile_branches(db):
    """Merge known duplicate demo locations while preserving referenced rows."""
    existing = (await db.scalars(select(Branch).order_by(Branch.created_at, Branch.id))).all()
    result = {}
    for definition in BRANCHES:
        candidates = [row for row in existing if branch_key(row) == definition["key"]]
        keeper = next((row for row in candidates if row.address == definition["address"]), candidates[0] if candidates else None)
        if not keeper:
            values = {key: value for key, value in definition.items() if key != "key"}
            keeper = Branch(country_code="AZ", active=True, **values)
            db.add(keeper)
            await db.flush()
        else:
            for key, value in definition.items():
                if key != "key": setattr(keeper, key, value)
            keeper.country_code = "AZ"
            keeper.active = True
        result[definition["key"]] = keeper
        for duplicate in candidates:
            if duplicate.id == keeper.id:
                continue
            await db.execute(update(Vehicle).where(Vehicle.branch_id == duplicate.id).values(branch_id=keeper.id))
            await db.execute(update(Reservation).where(Reservation.pickup_branch_id == duplicate.id).values(pickup_branch_id=keeper.id))
            await db.execute(update(Reservation).where(Reservation.return_branch_id == duplicate.id).values(return_branch_id=keeper.id))
            await db.execute(update(PolicyDocument).where(PolicyDocument.branch_id == duplicate.id).values(branch_id=keeper.id))
            references = await db.scalar(select(func.count()).select_from(VehicleAllocation).join(Vehicle, VehicleAllocation.vehicle_id == Vehicle.id).where(Vehicle.branch_id == duplicate.id))
            if not references:
                await db.delete(duplicate)
    return result


VEHICLE_CATALOG = [
    ("10-AA-001", "Toyota", "Yaris", 2023, "HATCHBACK", "ECONOMY", 5, "HYBRID", "AUTOMATIC", "city", "DEMO_ECONOMY", ["Air conditioning", "Bluetooth", "USB"]),
    ("10-AA-002", "Hyundai", "i20", 2022, "HATCHBACK", "ECONOMY", 5, "PETROL", "AUTOMATIC", "city", "DEMO_ECONOMY", ["Air conditioning", "Bluetooth"]),
    ("10-AA-003", "Kia", "Rio", 2023, "SEDAN", "ECONOMY", 5, "PETROL", "AUTOMATIC", "city", "DEMO_ECONOMY", ["Air conditioning", "USB"]),
    ("10-AA-004", "Renault", "Clio", 2022, "HATCHBACK", "ECONOMY", 5, "PETROL", "MANUAL", "city", "DEMO_ECONOMY", ["Air conditioning"]),
    ("10-AA-005", "Volkswagen", "Polo", 2023, "HATCHBACK", "ECONOMY", 5, "PETROL", "AUTOMATIC", "city", "DEMO_ECONOMY", ["Air conditioning", "Bluetooth"]),
    ("10-AA-006", "Skoda", "Fabia", 2024, "HATCHBACK", "ECONOMY", 5, "PETROL", "AUTOMATIC", "city", "DEMO_ECONOMY", ["Air conditioning", "Cruise control"]),
    ("10-AA-007", "Nissan", "Micra", 2022, "HATCHBACK", "ECONOMY", 5, "PETROL", "AUTOMATIC", "city", "DEMO_ECONOMY", ["Air conditioning"]),
    ("10-AA-008", "Honda", "Jazz", 2023, "HATCHBACK", "ECONOMY", 5, "HYBRID", "AUTOMATIC", "city", "DEMO_ECONOMY", ["Air conditioning", "Bluetooth"]),
    ("10-AA-009", "Toyota", "Corolla", 2024, "SEDAN", "STANDARD", 5, "PETROL", "AUTOMATIC", "airport", "DEMO_STANDARD", ["Air conditioning", "Bluetooth", "Cruise control"]),
    ("10-AA-010", "Hyundai", "Elantra", 2024, "SEDAN", "STANDARD", 5, "PETROL", "AUTOMATIC", "airport", "DEMO_STANDARD", ["Air conditioning", "Bluetooth", "USB"]),
    ("10-AA-011", "Kia", "Cerato", 2023, "SEDAN", "STANDARD", 5, "PETROL", "AUTOMATIC", "airport", "DEMO_STANDARD", ["Air conditioning", "Rear camera"]),
    ("10-AA-012", "Mazda", "3", 2024, "SEDAN", "STANDARD", 5, "PETROL", "AUTOMATIC", "airport", "DEMO_STANDARD", ["Air conditioning", "Bluetooth"]),
    ("10-AA-013", "Skoda", "Octavia", 2023, "SEDAN", "STANDARD", 5, "PETROL", "AUTOMATIC", "airport", "DEMO_STANDARD", ["Air conditioning", "Large boot"]),
    ("10-AA-014", "Nissan", "Sentra", 2023, "SEDAN", "STANDARD", 5, "PETROL", "AUTOMATIC", "airport", "DEMO_STANDARD", ["Air conditioning", "Bluetooth"]),
    ("10-AA-015", "Toyota", "Prius", 2022, "SEDAN", "STANDARD", 5, "HYBRID", "AUTOMATIC", "airport", "DEMO_STANDARD", ["Air conditioning", "Low fuel use"]),
    ("10-AA-016", "Hyundai", "Sonata", 2024, "SEDAN", "PREMIUM", 5, "HYBRID", "AUTOMATIC", "airport", "DEMO_PREMIUM", ["Leather interior", "Bluetooth", "Adaptive cruise"]),
    ("10-AA-017", "Toyota", "Camry", 2023, "SEDAN", "PREMIUM", 5, "HYBRID", "AUTOMATIC", "airport", "DEMO_PREMIUM", ["Leather interior", "Rear camera"]),
    ("10-AA-018", "Mercedes-Benz", "C-Class", 2023, "SEDAN", "PREMIUM", 5, "PETROL", "AUTOMATIC", "airport", "DEMO_PREMIUM", ["Leather interior", "Navigation"]),
    ("10-AA-019", "BMW", "3 Series", 2024, "SEDAN", "PREMIUM", 5, "PETROL", "AUTOMATIC", "airport", "DEMO_PREMIUM", ["Leather interior", "Navigation"]),
    ("10-AA-020", "Lexus", "ES", 2022, "SEDAN", "PREMIUM", 5, "HYBRID", "AUTOMATIC", "airport", "DEMO_PREMIUM", ["Leather interior", "Sunroof"]),
    ("90-BB-001", "Kia", "Sportage", 2024, "SUV", "FAMILY", 5, "HYBRID", "AUTOMATIC", "airport", "DEMO_FAMILY", ["Air conditioning", "Large boot", "Rear camera"]),
    ("90-BB-002", "Toyota", "RAV4", 2023, "SUV", "FAMILY", 5, "HYBRID", "AUTOMATIC", "airport", "DEMO_FAMILY", ["Air conditioning", "All wheel drive"]),
    ("90-BB-003", "Hyundai", "Tucson", 2024, "SUV", "FAMILY", 5, "PETROL", "AUTOMATIC", "airport", "DEMO_FAMILY", ["Air conditioning", "Rear camera"]),
    ("90-BB-004", "Nissan", "Qashqai", 2023, "SUV", "FAMILY", 5, "PETROL", "AUTOMATIC", "sumqayit", "DEMO_FAMILY", ["Air conditioning", "Bluetooth"]),
    ("90-BB-005", "Mazda", "CX-5", 2023, "SUV", "FAMILY", 5, "PETROL", "AUTOMATIC", "sumqayit", "DEMO_FAMILY", ["Air conditioning", "Large boot"]),
    ("90-BB-006", "Honda", "CR-V", 2022, "SUV", "FAMILY", 5, "HYBRID", "AUTOMATIC", "sumqayit", "DEMO_FAMILY", ["Air conditioning", "All wheel drive"]),
    ("90-BB-007", "Ford", "Kuga", 2023, "SUV", "FAMILY", 5, "HYBRID", "AUTOMATIC", "sumqayit", "DEMO_FAMILY", ["Air conditioning", "Rear camera"]),
    ("90-BB-008", "Volkswagen", "Tiguan", 2024, "SUV", "FAMILY", 5, "PETROL", "AUTOMATIC", "sumqayit", "DEMO_FAMILY", ["Air conditioning", "Navigation"]),
    ("90-BB-009", "Subaru", "Forester", 2022, "SUV", "FAMILY", 5, "PETROL", "AUTOMATIC", "sumqayit", "DEMO_FAMILY", ["All wheel drive", "Large boot"]),
    ("90-BB-010", "Kia", "Sorento", 2023, "SUV", "FAMILY", 7, "DIESEL", "AUTOMATIC", "sumqayit", "DEMO_FAMILY", ["7 seats", "Large boot"]),
    ("90-BB-011", "Toyota", "Highlander", 2023, "SUV", "FAMILY", 7, "HYBRID", "AUTOMATIC", "sumqayit", "DEMO_FAMILY", ["7 seats", "All wheel drive"]),
    ("90-BB-012", "Hyundai", "Santa Fe", 2024, "SUV", "FAMILY", 7, "HYBRID", "AUTOMATIC", "sumqayit", "DEMO_FAMILY", ["7 seats", "Navigation"]),
    ("99-CC-001", "Toyota", "Sienna", 2023, "MINIVAN", "VAN", 7, "HYBRID", "AUTOMATIC", "city", "DEMO_VAN", ["7 seats", "Sliding doors"]),
    ("99-CC-002", "Kia", "Carnival", 2024, "MINIVAN", "VAN", 8, "DIESEL", "AUTOMATIC", "city", "DEMO_VAN", ["8 seats", "Large boot"]),
    ("99-CC-003", "Ford", "Tourneo Custom", 2022, "VAN", "VAN", 8, "DIESEL", "MANUAL", "city", "DEMO_VAN", ["8 seats", "Large luggage area"]),
    ("99-CC-004", "Renault", "Trafic", 2023, "VAN", "VAN", 8, "DIESEL", "MANUAL", "city", "DEMO_VAN", ["8 seats", "Sliding doors"]),
    ("99-CC-005", "Mercedes-Benz", "Vito", 2023, "VAN", "VAN", 8, "DIESEL", "AUTOMATIC", "city", "DEMO_VAN", ["8 seats", "Navigation"]),
    ("99-CC-006", "Volkswagen", "Caravelle", 2022, "VAN", "VAN", 8, "DIESEL", "AUTOMATIC", "city", "DEMO_VAN", ["8 seats", "Large luggage area"]),
    ("77-DD-001", "Tesla", "Model 3", 2024, "SEDAN", "ELECTRIC", 5, "ELECTRIC", "AUTOMATIC", "city", "DEMO_STANDARD", ["Electric", "Navigation"]),
    ("77-DD-002", "BYD", "Atto 3", 2024, "SUV", "ELECTRIC", 5, "ELECTRIC", "AUTOMATIC", "city", "DEMO_FAMILY", ["Electric", "Rear camera"]),
    ("77-DD-003", "Nissan", "Leaf", 2023, "HATCHBACK", "ELECTRIC", 5, "ELECTRIC", "AUTOMATIC", "city", "DEMO_ECONOMY", ["Electric", "Bluetooth"]),
    ("77-DD-004", "MG", "4", 2024, "HATCHBACK", "ELECTRIC", 5, "ELECTRIC", "AUTOMATIC", "city", "DEMO_STANDARD", ["Electric", "Navigation"]),
    ("12-EE-001", "Toyota", "Yaris", 2023, "HATCHBACK", "ECONOMY", 5, "HYBRID", "AUTOMATIC", "sumqayit", "DEMO_ECONOMY", ["Air conditioning", "Bluetooth"]),
    ("12-EE-002", "Hyundai", "Accent", 2022, "SEDAN", "ECONOMY", 5, "PETROL", "AUTOMATIC", "sumqayit", "DEMO_ECONOMY", ["Air conditioning"]),
    ("12-EE-003", "Kia", "Seltos", 2023, "SUV", "FAMILY", 5, "PETROL", "AUTOMATIC", "sumqayit", "DEMO_FAMILY", ["Air conditioning", "Rear camera"]),
    ("12-EE-004", "Suzuki", "Vitara", 2022, "SUV", "FAMILY", 5, "PETROL", "AUTOMATIC", "sumqayit", "DEMO_FAMILY", ["All wheel drive", "Bluetooth"]),
    ("12-EE-005", "Mitsubishi", "Outlander", 2023, "SUV", "FAMILY", 7, "HYBRID", "AUTOMATIC", "sumqayit", "DEMO_FAMILY", ["7 seats", "Large boot"]),
    ("12-EE-006", "Peugeot", "3008", 2024, "SUV", "FAMILY", 5, "PETROL", "AUTOMATIC", "sumqayit", "DEMO_FAMILY", ["Navigation", "Rear camera"]),
    ("12-EE-007", "Audi", "A4", 2023, "SEDAN", "PREMIUM", 5, "PETROL", "AUTOMATIC", "airport", "DEMO_PREMIUM", ["Leather interior", "Navigation"]),
    ("12-EE-008", "Volvo", "XC40", 2023, "SUV", "PREMIUM", 5, "HYBRID", "AUTOMATIC", "airport", "DEMO_PREMIUM", ["Safety assist", "Navigation"]),
    ("12-EE-009", "Jeep", "Compass", 2022, "SUV", "FAMILY", 5, "PETROL", "AUTOMATIC", "airport", "DEMO_FAMILY", ["All wheel drive", "Rear camera"]),
    ("12-EE-010", "Ford", "Focus", 2023, "HATCHBACK", "STANDARD", 5, "PETROL", "MANUAL", "airport", "DEMO_STANDARD", ["Air conditioning", "Bluetooth"]),
]


async def one(db, model, **where):
    return await db.scalar(select(model).filter_by(**where).limit(1))


def demo_vehicle_price(plan_daily, plate, model_year, class_code):
    """Give each demo car a realistic, deterministic condition/position price."""
    # Stable variation makes cars in the same class visibly different while
    # keeping prices close to the linked plan's normal daily rate.
    seed = sum(ord(char) for char in plate)
    variation = ((seed % 11) - 5) * 500
    newer_car_adjustment = max(0, model_year - 2022) * 300
    premium_adjustment = 700 if class_code == "PREMIUM" else 0
    return max(0, plan_daily + variation + newer_car_adjustment + premium_adjustment)


async def main(embed: bool):
    async with Session() as db, db.begin():
        admin = await db.scalar(select(AdminUser).where(AdminUser.active.is_(True), AdminUser.role == "ADMIN").order_by(AdminUser.created_at).limit(1))
        if not admin:
            raise RuntimeError("Create an administrator with scripts/bootstrap_admin.py before seeding demo data.")

        branch_rows = await reconcile_branches(db)

        documents = []
        for language, content in POLICIES.items():
            document = await one(db, PolicyDocument, document_key=POLICY_KEY, language=language, version=1)
            if not document:
                document = PolicyDocument(
                    document_key=POLICY_KEY, topic="GENERAL", language=language, version=1,
                    branch_id=None, full_text=content,
                    source_asset_key=f"policies/{language}/{POLICY_KEY}-v1.md",
                    content_hash=digest(content), effective_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    status="PUBLISHED", reviewed_by=admin.id, reviewed_at=now(),
                )
                db.add(document)
                await db.flush()
                asset = Path(settings().asset_root) / document.source_asset_key
                asset.parent.mkdir(parents=True, exist_ok=True)
                asset.write_text(content, encoding="utf-8")
            documents.append(document)

        policy = await one(db, RentalPolicy, policy_bundle_key=POLICY_KEY, version=1)
        if not policy:
            policy = RentalPolicy(
                version=1, policy_bundle_key=POLICY_KEY,
                rules={"minimum_driver_age": 21, "maximum_rental_days": 30,
                       "modification_fee_qepik": 1500, "cancellation_fee_qepik": 2500,
                       "cancellation_free_hours": 24},
                published_by=admin.id, published_at=now(),
            )
            db.add(policy)
            await db.flush()

        plans = {}
        for code, daily, deposit, tax in [
            ("DEMO_ECONOMY", 6500, 30000, 1800),
            ("DEMO_STANDARD", 8500, 40000, 1800),
            ("DEMO_FAMILY", 10500, 50000, 1800),
            ("DEMO_PREMIUM", 18000, 80000, 1800),
            ("DEMO_VAN", 16000, 70000, 1800),
        ]:
            plan = await one(db, RatePlan, code=code, version=1)
            if not plan:
                plan = RatePlan(code=code, version=1, daily_rate_qepik=daily, deposit_qepik=deposit,
                                tax_basis_points=tax, tax_mode="EXCLUSIVE", rental_policy_id=policy.id,
                                created_by=admin.id)
                db.add(plan)
                await db.flush()
            plans[code] = plan

        rules = [
            (plans["DEMO_ECONOMY"], "FIXED_FEE", 1200, None),
            (plans["DEMO_ECONOMY"], "SEASONAL_DAILY", 8000, (date(2026, 11, 1), date(2027, 1, 1))),
            (plans["DEMO_STANDARD"], "FIXED_FEE", 1500, None),
            (plans["DEMO_STANDARD"], "SEASONAL_DAILY", 10000, (date(2026, 11, 1), date(2027, 1, 1))),
            (plans["DEMO_FAMILY"], "FIXED_FEE", 1800, None),
            (plans["DEMO_FAMILY"], "SEASONAL_DAILY", 12500, (date(2026, 11, 1), date(2027, 1, 1))),
            (plans["DEMO_PREMIUM"], "FIXED_FEE", 2500, None),
            (plans["DEMO_VAN"], "FIXED_FEE", 2500, None),
        ]
        for plan, kind, amount, dates in rules:
            existing = await db.scalar(select(PricingRule.id).where(PricingRule.rate_plan_id == plan.id, PricingRule.kind == kind, PricingRule.amount_qepik == amount).limit(1))
            if not existing:
                from sqlalchemy.dialects.postgresql import Range
                db.add(PricingRule(rate_plan_id=plan.id, kind=kind, amount_qepik=amount,
                                   effective_dates=Range(*dates, bounds="[)") if dates else None, conditions={}))

        # Migrate the original three placeholder plates to real Azerbaijani-style
        # formats before filling the larger catalog.
        legacy_plates = {"10-DEMO-EC": "10-AA-001", "10-DEMO-SD": "10-AA-010", "10-DEMO-SU": "90-BB-001"}
        for old, new in legacy_plates.items():
            vehicle = await one(db, Vehicle, registration_number=old)
            if vehicle and not await one(db, Vehicle, registration_number=new):
                vehicle.registration_number = new

        for plate, make, model, year, kind, class_code, seats, fuel, transmission, branch_key_value, plan_code, features in VEHICLE_CATALOG:
            vehicle = await one(db, Vehicle, registration_number=plate)
            daily_rate = demo_vehicle_price(plans[plan_code].daily_rate_qepik, plate, year, class_code)
            values = dict(registration_number=plate, make=make, model=model, model_year=year,
                          vehicle_type=kind, class_code=class_code, seats=seats, fuel_type=fuel,
                          transmission=transmission, branch_id=branch_rows[branch_key_value].id,
                          rate_plan_id=plans[plan_code].id, daily_rate_qepik=daily_rate,
                          status="ACTIVE", features=features)
            if not vehicle:
                db.add(Vehicle(**values))
            else:
                for key, value in values.items(): setattr(vehicle, key, value)

        extras = [
            ("DEMO_GPS", "GPS", "GPS naviqasiya", "GPS navigation", "Bakı və regionlarda rahat marşrut planlaması.", "Easy route planning around Baku and the regions.", 700, "PER_DAY", 8, {"minimum_trip_days": 1}),
            ("DEMO_CHILD", "CHILD_SEAT", "Uşaq oturacağı", "Child seat", "Kiçik sərnişinlər üçün təhlükəsiz oturacaq.", "A safer seat for young passengers.", 1200, "PER_RENTAL", 4, {}),
            ("DEMO_INSURANCE", "INSURANCE", "Əlavə sığorta", "Additional cover", "Səfər zamanı əlavə rahatlıq üçün.", "Extra peace of mind during the trip.", 1800, "PER_DAY", None, {"minimum_trip_days": 2}),
        ]
        for code, kind, az, en, daz, den, price, unit, stock, eligibility in extras:
            if not await one(db, Extra, code=code):
                db.add(Extra(code=code, kind=kind, name_az=az, name_en=en, description_az=daz,
                             description_en=den, price_qepik=price, billing_unit=unit,
                             stock_total=stock, eligibility_rules=eligibility, active=True))

        fx = await one(db, FxRate, currency_code="USD", effective_date=date(2026, 10, 3))
        if not fx:
            db.add(FxRate(currency_code="USD", effective_date=date(2026, 10, 3), azn_per_unit=Decimal("1.7000"),
                          source_url="demo://cbar-rate", fetched_at=now()))

        await db.flush()
        if embed and settings().api_key:
            for document in documents:
                await ingest(db, document)
        elif embed:
            print("OpenAI key is empty; published demo policy has no vector chunks. Fleet and booking data are still ready.")

    print("Demo data is ready: structured branches, 52 vehicles, 5 rate plans, 8 pricing rules, 3 extras, 2 policies, 1 USD rate.")
    await engine.dispose()


parser = argparse.ArgumentParser(description="Seed a small connected demo catalog")
parser.add_argument("--embed", action="store_true", help="Embed policy documents when an OpenAI key is configured")
args = parser.parse_args()
asyncio.run(main(args.embed))
