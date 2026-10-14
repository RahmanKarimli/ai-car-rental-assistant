"""Allowlisted table catalogue and field help shared by all admin screens."""
from sqlalchemy import Boolean, Integer, Numeric, DateTime, Date
from sqlalchemy.dialects.postgresql import JSONB, DATERANGE, TSTZRANGE
from app import models as m
from app.schemas.catalog import (
    AdminInput, BranchInput, VehicleInput, ExtraInput, RateInput, RuleInput,
    PhotoInput, DocumentInput,
)

TABLES = {
    'branches': (m.Branch, 'Branches', 'Pickup offices, their addresses, hours and availability.'),
    'vehicles': (m.Vehicle, 'Vehicles', 'Individual cars in the fleet, linked to a branch and pricing plan. Each car can have its own daily AZN price override.'),
    'extras': (m.Extra, 'Extras', 'Optional equipment and insurance with bilingual copy, prices and stock.'),
    'vehicle_photos': (m.VehiclePhoto, 'Vehicle photos', 'Images and bilingual descriptions displayed on vehicle cards.'),
    'rate_plans': (m.RatePlan, 'Rate plans', 'Versioned daily rates, deposits and taxes used by the pricing engine.'),
    'pricing_rules': (m.PricingRule, 'Pricing rules', 'Seasonal daily overrides and fixed fees attached to a rate plan.'),
    'rental_policies': (m.RentalPolicy, 'Operational policies', 'Published, versioned age limits, rental limits and change fees.'),
    'policy_documents': (m.PolicyDocument, 'Policy documents', 'Reviewed Azerbaijani and English source documents for policy answers.'),
    'policy_chunks': (m.PolicyChunk, 'Policy search chunks', 'Searchable excerpts and embeddings generated when policies are published.'),
    'admin_users': (m.AdminUser, 'Admin users', 'Operator accounts and their administrator or support permissions.'),
    'reservations': (m.Reservation, 'Reservations', 'Current booking details; changes and cancellation use an itemized draft and confirmation.'),
    'reservation_versions': (m.ReservationVersion, 'Reservation history', 'Permanent snapshots of every confirmed creation, modification and cancellation.'),
    'booking_drafts': (m.BookingDraft, 'Booking drafts', 'Proposed booking actions awaiting confirmation, with expiring holds.'),
    'quotes': (m.Quote, 'Signed quotes', 'Immutable, signed price quotes produced by the deterministic pricing engine.'),
    'quote_items': (m.QuoteItem, 'Quote line items', 'The individual rental charges, extras, fees and taxes inside a signed quote.'),
    'vehicle_allocations': (m.VehicleAllocation, 'Vehicle allocations', 'Time windows reserved by holds and confirmed bookings to prevent double booking.'),
    'extra_allocations': (m.ExtraAllocation, 'Extra allocations', 'Quantities of equipment reserved for each hold or booking time window.'),
    'conversations': (m.Conversation, 'Conversations', 'Customer contact details, language, conversation state and manual retention deadlines.'),
    'chat_logs': (m.ChatLog, 'Chat history', 'Full, unredacted customer, assistant and operator messages in their original order.'),
    'agent_runs': (m.AgentRun, 'Agent runs', 'Processing status, token usage and recovery information for each conversation event.'),
    'escalation_cases': (m.EscalationCase, 'Escalation cases', 'Requests needing human review, their assigned operator and resolution.'),
    'approved_adjustments': (m.ApprovedAdjustment, 'Approved adjustments', 'Time-limited administrator-approved discounts applied through the pricing engine.'),
    'audit_events': (m.AuditEvent, 'Audit trail', 'Permanent records of who performed booking and administration actions.'),
    'conversion_events': (m.ConversionEvent, 'Conversion events', 'Booking funnel events used to understand search, draft and completion activity.'),
    'fx_rates': (m.FxRate, 'Exchange rates', 'CBAR exchange rates used only for informational USD display; contracts remain in AZN.'),
    'sessions': (m.WebSession, 'Sessions', 'Customer and staff browser sessions, their expiry and revocation state.'),
    'booking_access_grants': (m.BookingAccessGrant, 'Booking access', 'Session-bound permission to read, modify or cancel a reservation.'),
    'idempotency_records': (m.IdempotencyRecord, 'Request receipts', 'Recorded operation results that prevent retries from creating duplicate bookings.'),
}
INPUTS = {
    'branches': BranchInput, 'vehicles': VehicleInput, 'extras': ExtraInput,
    'rate_plans': RateInput, 'pricing_rules': RuleInput, 'vehicle_photos': PhotoInput,
    'admin_users': AdminInput, 'policy_documents': DocumentInput,
}
EDITABLE = {'branches', 'vehicles', 'extras', 'vehicle_photos', 'admin_users', 'policy_documents'}
DELETABLE = EDITABLE
HIDDEN = {'password_hash', 'token_hash', 'embedding', 'search_vector'}
HELP = {
    'id': 'Automatically generated unique record ID.',
    'created_at': 'Time this record was created; assigned by the database.',
    'name_az': 'Customer-facing name in Azerbaijani.', 'name_en': 'Customer-facing name in English.',
    'city': 'City where this pickup office is located.', 'address': 'Full street address shown to renters.',
    'country_code': 'Two-letter country code; launch branches must be in Azerbaijan (AZ).',
    'opening_hours': 'Opening hours as a JSON object, for example {"mon": "09:00–18:00"}.',
    'active': 'Whether this office, extra or staff account is available for use.',
    'registration_number': 'Unique registration plate identifying this physical vehicle.',
    'make': 'Vehicle manufacturer, such as Toyota.', 'model': 'Vehicle model, such as Corolla.',
    'model_year': 'Manufacturing model year, entered as a whole number.',
    'vehicle_type': 'Body style used when filtering vehicle searches.',
    'class_code': 'Rental class, such as ECONOMY or STANDARD; also used for extra compatibility.',
    'seats': 'Maximum passenger capacity, including the driver.',
    'fuel_type': 'Fuel or power source used in search filters.',
    'transmission': 'Automatic or manual gearbox.',
    'branch_id': 'Linked branch ID; on a policy, empty means the policy applies to all branches.',
    'rate_plan_id': 'Linked pricing plan defining daily rate, deposit, tax and rental policy.',
    'daily_rate_qepik': 'Optional price for this specific physical car in AZN qəpiks; when set, it overrides the linked plan daily rate. Empty uses the plan default.',
    'status': 'Current lifecycle or availability state of this record.',
    'features': 'List of vehicle amenities as JSON, for example ["Bluetooth", "Air conditioning"].',
    'vehicle_id': 'ID of the physical vehicle this record concerns.',
    'extra_id': 'ID of the optional equipment or insurance product allocated to this booking.',
    'asset_key': 'Local image path generated during upload; changing the image requires a new upload.',
    'alt_az': 'Short Azerbaijani image description for accessibility.',
    'alt_en': 'Short English image description for accessibility.',
    'sort_order': 'Display position; smaller values appear first.',
    'code': 'Operator-defined code identifying this product or pricing plan.',
    'kind': 'Category that determines how the system handles this record.',
    'description_az': 'Consultative description in Azerbaijani explaining when this extra helps.',
    'description_en': 'Consultative description in English explaining when this extra helps.',
    'price_qepik': 'Price in whole AZN qəpiks; 100 qəpiks = 1 AZN.',
    'billing_unit': 'Charge for each rental day or once per rental.',
    'stock_total': 'Total equipment stock; empty means unlimited availability, zero means unavailable.',
    'eligibility_rules': 'Optional JSON rules: minimum_trip_days, months (1–12), destinations, vehicle_classes.',
    'period': 'Reserved time range: pickup included, return excluded.',
    'purpose': 'Whether the vehicle window is a temporary hold or a confirmed reservation.',
    'draft_id': 'Booking draft responsible for this temporary hold.',
    'reservation_id': 'Reservation linked to this record.',
    'expires_at': 'Time the temporary authorization, session or hold expires.',
    'quantity': 'Whole number of units reserved or charged.',
    'version': 'Version number; historical published versions remain available for audit.',
    'rules': 'Operational age, rental duration, modification and cancellation rules as JSON.',
    'policy_bundle_key': 'Key linking operational rules to their reviewed bilingual policy documents.',
    'published_by': 'Administrator ID that published these operational rules.',
    'published_at': 'Time these operational rules were approved for use.',
    'daily_rate_qepik': 'Base daily rental price in AZN qəpiks; 100 = 1 AZN.',
    'deposit_qepik': 'Security deposit in AZN qəpiks, shown separately from rental charges.',
    'tax_basis_points': 'Tax percentage in basis points: 100 = 1%, 1800 = 18%.',
    'tax_mode': 'INCLUSIVE means tax is included; EXCLUSIVE adds configured tax to the subtotal.',
    'rental_policy_id': 'Published operational policy used to enforce limits and change fees.',
    'created_by': 'Administrator ID that created this pricing plan.',
    'amount_qepik': 'Whole AZN qəpiks; an approved negative adjustment reduces the quote.',
    'effective_dates': 'Seasonal date range as [start, end]; the end date is excluded. Fixed fees leave this empty.',
    'conditions': 'Reserved JSON configuration; currently only an empty object is supported.',
    'currency_code': 'Currency being converted for informational display, currently USD.',
    'effective_date': 'CBAR date to which this exchange rate applies.',
    'azn_per_unit': 'AZN value of one unit of the foreign currency.',
    'source_url': 'CBAR source URL from which the rate was fetched.',
    'fetched_at': 'Time the system retrieved this exchange rate.',
    'escalation_case_id': 'Human review case authorizing this adjustment.',
    'conversation_id': 'Conversation associated with this record.',
    'reason': 'Recorded explanation for the action or approval.',
    'approved_by': 'Administrator ID that authorized the price adjustment.',
    'consumed_by_version_id': 'Confirmed booking version that used this adjustment; empty means unused.',
    'document_key': 'Shared policy bundle key; English and Azerbaijani versions must match.',
    'topic': 'Policy subject, such as GENERAL, MILEAGE or INSURANCE.',
    'language': 'Language code: az for Azerbaijani or en for English.',
    'source_asset_key': 'Generated local path to the stored Markdown source.',
    'full_text': 'Complete policy text in Markdown; only reviewed published documents answer customer questions.',
    'content_hash': 'System-generated fingerprint identifying the exact text version.',
    'effective_from': 'Timezone-aware date and time when the policy becomes effective.',
    'effective_until': 'Optional timezone-aware end date; empty means no scheduled end.',
    'reviewed_by': 'Administrator ID that reviewed and published this policy.',
    'reviewed_at': 'Time this policy passed administrator review.',
    'document_id': 'Source policy document from which this excerpt was generated.',
    'chunk_index': 'Excerpt position within its source document, starting at zero.',
    'content': 'Policy excerpt retrieved to support a cited answer.',
    'section_reference': 'Section label displayed in policy citations.',
    'search_vector': 'System-generated keyword search index; its internal value is omitted from this console.',
    'embedding': 'Generated 1536-dimensional search vector; its internal value is omitted from this console.',
    'embedding_model': 'OpenAI model used to embed this excerpt.',
    'email': 'Unique operator sign-in email address.',
    'password_hash': 'Argon2 password hash; never returned or displayed by the console.',
    'password': 'New sign-in password, at least 12 characters; leave empty during editing to keep it.',
    'role': 'Speaker or account role; ADMIN manages data, SUPPORT handles assigned conversations.',
    'token_hash': 'Hashed session credential; never returned or displayed by the console.',
    'actor_type': 'Whether the actor is a customer, administrator or system process.',
    'admin_user_id': 'Operator account attached to this session, if any.',
    'revoked_at': 'Revocation time; empty means this session or permission has not been revoked.',
    'session_id': 'Browser session owning this conversation, request or access grant.',
    'key': 'Caller-supplied retry key identifying one intended operation.',
    'operation': 'Booking operation recorded by this retry receipt.',
    'request_hash': 'Fingerprint detecting reuse of a retry key with different input.',
    'result_reference': 'Stored operation result returned for safe retries.',
    'action_kind': 'Booking action: CREATE, MODIFY or CANCEL.',
    'inputs_snapshot': 'Frozen trip and adjustment inputs used to calculate the quote.',
    'policy_snapshot': 'Frozen operational policy used when the quote was calculated.',
    'fx_rate_id': 'Exchange rate used for the quote’s informational USD display.',
    'total_qepik': 'Final rental charge in AZN qəpiks, calculated only by the pricing engine.',
    'delta_qepik': 'Change in rental charge compared with the existing booking, in AZN qəpiks.',
    'signature': 'Integrity signature covering the quote and line items; generated by the pricing engine.',
    'valid_until': 'Deadline for accepting this exact signed quote.',
    'operation_key': 'Internal unique key ensuring the same booking operation is created once.',
    'quote_id': 'Signed quote associated with this record.',
    'label_az': 'Azerbaijani label shown on the itemized quote.',
    'label_en': 'English label shown on the itemized quote.',
    'unit_amount_qepik': 'Price per charge unit in AZN qəpiks.',
    'line_total_qepik': 'Quantity multiplied by unit amount, calculated in AZN qəpiks.',
    'rule_reference': 'IDs of the deterministic pricing rules responsible for this charge.',
    'base_reservation_version': 'Booking version on which this draft is based; prevents conflicting modifications.',
    'proposal': 'Proposed trip, contact and action awaiting explicit confirmation.',
    'committed_version_id': 'Reservation history entry created after this draft was confirmed.',
    'public_reference': 'Customer-facing booking reference; it does not grant access by itself.',
    'pickup_branch_id': 'Branch where the renter collects the vehicle.',
    'return_branch_id': 'Branch where the renter returns the vehicle.',
    'pickup_at': 'Timezone-aware pickup date and time.',
    'return_at': 'Timezone-aware return date and time.',
    'current_version': 'Latest confirmed booking version; increments after each confirmed change.',
    'renter_contact': 'Unredacted contractual renter contact details stored as JSON.',
    'payment_method': 'Payment arrangement; launch reservations use PAY_AT_PICKUP.',
    'updated_at': 'Time the reservation was last changed through a confirmed action.',
    'snapshot': 'Permanent booking details captured at this reservation version.',
    'actor_id': 'ID of the customer session or operator that performed the action.',
    'permissions': 'Actions granted to this session, such as READ, MODIFY and CANCEL.',
    'contact_name': 'Customer’s full name, stored without redaction.',
    'contact_email': 'Customer’s email address, stored without redaction.',
    'contact_phone': 'Customer’s phone number, stored without redaction.',
    'session_state': 'Saved conversation preferences and current workflow context as JSON.',
    'state_version': 'Conversation state revision used to track workflow changes.',
    'active_draft_id': 'Current draft awaiting confirmation, if any.',
    'last_activity_at': 'Most recent customer or operator activity time.',
    'retention_due_at': 'Manual retention review deadline, normally 12 months after the latest activity.',
    'sequence': 'Message position within a conversation.',
    'client_event_id': 'Client-generated event ID used to recognize retries.',
    'raw_content': 'Full original message text; stored without PII redaction.',
    'payload': 'Original structured message data, including visual cards and event details.',
    'agent_run_id': 'Processing run associated with this message.',
    'input_log_id': 'Chat history record containing the input event.',
    'event_kind': 'Type of customer event processed by this run.',
    'checkpoint_id': 'LangGraph recovery checkpoint identifier.',
    'response_log_id': 'Chat history record containing the completed response.',
    'input_tokens': 'Number of input tokens reported for this processing run.',
    'output_tokens': 'Number of output tokens reported for this processing run.',
    'error_code': 'Failure category recorded if processing did not complete.',
    'started_at': 'Time processing began.', 'finished_at': 'Time processing ended, if completed.',
    'reason_code': 'Escalation category, such as MANUAL_DISCOUNT or PAYMENT_EXCEPTION.',
    'summary': 'Context explaining why an operator needs to review this request.',
    'source_log_ids': 'Chat message IDs supporting this escalation.',
    'assigned_admin_id': 'Operator responsible for the human review case.',
    'resolution': 'Recorded review decision, justification and any approved discount.',
    'opened_at': 'Time the human review case was opened.',
    'resolved_at': 'Time the review case was resolved, if closed.',
    'action': 'Name of the audited operation.',
    'entity_type': 'Table containing the record affected by this audit event.',
    'entity_id': 'ID of the record affected by the audited action.',
    'request_id': 'Identifier linking the audit entry to the initiating request.',
    'before_snapshot': 'Record values before the audited change, excluding credentials.',
    'after_snapshot': 'Record values after the audited change, excluding credentials.',
    'event_name': 'Booking funnel milestone, such as SEARCH or DRAFT_CREATED.',
    'attributes': 'Additional structured context for this conversion event.',
}
NOTES = {
    'branches': 'Delete unused branches. Referenced branches must be retained; turn off Active to hide them.',
    'vehicles': 'Vehicle details cannot change while it has an active hold or future booking. Referenced cars cannot be deleted; set Inactive to remove them from search.',
    'extras': 'Stock reductions must respect current allocations. Referenced extras cannot be deleted; turn off Active to hide them.',
    'vehicle_photos': 'Upload a photo, edit its captions or order, or delete it from vehicle cards.',
    'admin_users': 'Passwords are write-only. Your own account cannot be disabled, demoted or deleted. Referenced accounts can be deactivated instead.',
    'policy_documents': 'Edit or delete unpublished drafts. Published and retired documents are retained; duplicate into a new version, then approve the bilingual pair on Policies.',
    'rate_plans': 'Publish a new version to change prices. Existing versions are permanent so signed quotes and booking history remain verifiable. Assign the new version to a vehicle on Fleet.',
    'pricing_rules': 'Rules are permanent. To change or remove a rule, create a new rate-plan version and add only the desired rules before assigning vehicles.',
    'rental_policies': 'Publish a new operational policy version on Policies after reviewing the matching bilingual documents.',
    'reservations': 'Use Manage booking to modify or cancel through an itemized draft and explicit confirmation; bookings are never deleted.',
    'conversations': 'Open Conversations for human handoff. Delete eligible history manually on Privacy after its retention deadline.',
    'chat_logs': 'Messages preserve the original history. Manual deletion is available only through the conversation retention review on Privacy.',
}
DEFAULT_NOTE = 'Managed by the application workflow. Direct editing and deletion are disabled to preserve booking integrity and history.'


def field_type(column):
    if isinstance(column.type, Boolean): return 'boolean'
    if isinstance(column.type, JSONB): return 'json'
    if isinstance(column.type, DATERANGE): return 'date_range'
    if isinstance(column.type, TSTZRANGE): return 'range'
    if isinstance(column.type, Integer): return 'integer'
    if isinstance(column.type, Numeric): return 'decimal'
    if isinstance(column.type, DateTime): return 'datetime'
    if isinstance(column.type, Date): return 'date'
    return 'text'


def metadata(table):
    model, title, description = TABLES[table]
    schema = INPUTS[table].model_json_schema() if table in INPUTS else {}
    properties = schema.get('properties', {})
    fields = []
    for column in model.__table__.columns:
        name = column.name
        prop = properties.get(name, {})
        description = HELP[name]
        label = name.replace('_', ' ').capitalize()
        if table == 'vehicles' and name == 'daily_rate_qepik':
            description = 'Price for this individual car in AZN per day. Enter AZN to two decimal places. This overrides the linked rate plan; leave empty to use the plan price.'
            label = 'Individual daily price (AZN)'
        field = {
            'name': name, 'label': label,
            'description': description, 'type': field_type(column), 'nullable': column.nullable,
            'editable': table in EDITABLE and name in properties,
            'create': name in properties, 'required': name in schema.get('required', []),
            'hidden': name in HIDDEN, 'reference': next((fk.column.table.name for fk in column.foreign_keys), None),
        }
        variants = [prop] + prop.get('anyOf', [])
        for variant in variants:
            for key in ['enum', 'default', 'minimum', 'maximum', 'minLength', 'maxLength']:
                if key in variant: field[key] = variant[key]
        if table == 'vehicles' and name == 'daily_rate_qepik':
            field['type'] = 'money'
        if name == 'full_text': field['type'] = 'multiline'
        fields.append(field)
    if table == 'admin_users':
        fields.append({'name': 'password', 'label': 'Password', 'description': HELP['password'],
                       'type': 'password', 'editable': True, 'create': True, 'required': True, 'nullable': False, 'hidden': False,
                       'minLength': 12, 'maxLength': 128})
    if table == 'vehicle_photos':
        next(f for f in fields if f['name'] == 'vehicle_id')['create'] = True
        next(f for f in fields if f['name'] == 'vehicle_id')['required'] = True
    return {'name': table, 'title': title, 'description': description, 'fields': fields,
            'can_create': table in INPUTS, 'can_edit': table in EDITABLE, 'can_delete': table in DELETABLE,
            'create_mode': 'upload' if table == 'vehicle_photos' else 'form',
            'note': NOTES.get(table, DEFAULT_NOTE)}
