# Yol — local rental assistant

Azerbaijani/English customer chat and operator console, with deterministic AZN pricing, temporary fleet holds, confirmed booking actions, policy RAG, and full PostgreSQL conversation histories.

## Start locally

Prerequisites: Docker Desktop / Docker Engine with Compose, and Python 3.11+ for the setup command.

```sh
python3 scripts/setup_local.py
docker compose up -d --build
```

Open **http://localhost:3000**. The only published port is bound to the local host. API documentation is generated in `backend/openapi.json`.

Set your OpenAI key directly in `.secrets/openai_api_key` using a local editor; do not put it in chat, source control, or the frontend. Restart the API after changing it:

```sh
docker compose restart api
```

With an empty key, structured inventory/booking controls work; natural-language interpretation and policy embedding remain unavailable. No OpenAI requests are made during startup. `.secrets` is a private host directory; individual secret files are readable inside only the containers to which Compose mounts them.

## First operator and real catalog

```sh
docker compose exec api python scripts/bootstrap_admin.py
```

The command prompts privately for a password of at least 12 characters. Sign in at **http://localhost:3000/admin**.

Setup order:

1. Upload the actual complete rental policy as two Markdown documents: Azerbaijani and English, with the same bundle key and version. Cover mileage, age, insurance, deposits, modification and cancellation.
2. Approve and publish the bilingual pair. This embeds reviewed policy content using `text-embedding-3-small`; an OpenAI key is required.
3. Publish matching operational rules. The operator must ensure these match the documents.
4. Create a rate plan referencing the published operational policy ID. Amounts are whole AZN qəpiks: `12500` means `125.00 AZN`. Add seasonal/fixed rules before assigning vehicles. Create a new rate-plan version to change prices or remove a rule.
5. Create pickup branches, then real vehicles referencing branch and rate-plan IDs; upload their photos.
6. Add bilingual extras, correct stock quantities, and eligibility rules as needed.

The default startup does not seed any catalog records. The catalog examples remain empty templates. For local exploration, the repository includes a small explicit demo dataset:

```sh
docker compose exec api python scripts/bootstrap_admin.py
docker compose exec api python scripts/seed_demo.py
```

This reconciles duplicate demo locations into structured Baku city, airport, and Sumqayit branches, then creates 52 individually numbered vehicles using Azerbaijani-style plates such as `10-AA-001`, `90-BB-001`, and `12-EE-010`. Each physical vehicle receives its own varied daily AZN price override, so cars in the same class can have different rates based on age, condition, and equipment. The fleet covers economy, standard, family SUV, premium, van, hybrid, petrol, diesel, manual, automatic, and electric scenarios. It also creates five rate plans, seasonal and fixed pricing rules, three extras, bilingual published policy records, and a USD display rate. It is idempotent and uses stable plates and codes. Add `--embed` when an OpenAI key is configured to create the policy RAG vectors. The demo policy is clearly labeled and should be replaced before real customer use. The optional importer accepts the same administrator catalog payloads:

### LangSmith tracing

LangGraph tracing can be enabled for local development by setting `LANGSMITH_TRACING=true` in `.env` and putting the LangSmith key in `.secrets/langsmith_api_key`, then running `docker compose up -d --build api`. Runs are sent to the configured `LANGSMITH_PROJECT`. Inputs and outputs are hidden by default so customer prompts, contact details, and assistant replies remain in PostgreSQL rather than being copied into external traces. Traces still show workflow runs and timing. Keep `LANGSMITH_TRACING=false` to disable tracing.

```sh
docker compose exec api python scripts/import_catalog.py /data/catalog/fleet.example.json
```

## Admin record management

**Fleet**, **Pricing**, **Policies**, and **Database tables** use field-based forms with short explanations below each input. The database browser describes all 28 application tables and every column, supports paginated browsing and individual record details, and links related records by ID.

- Create, edit and delete branches, vehicles, extras, photo records, unused operator accounts and unpublished policy drafts. Passwords are write-only. Photo creation uploads a local image; captions and display order can be edited afterwards.
- Deletion requires explicit confirmation and is refused when another record references the item. Deactivate used branches, vehicles, extras or operator accounts instead. Vehicle details cannot change while active holds or future bookings depend on them; allocated stock cannot be reduced.
- Prices and reviewed operational policies retain permanent versions. Use **Copy to new version** for rate plans and policy documents; add desired pricing rules to the new plan before assigning vehicles. Use **Create translation** to prepare the matching document in the second language, then approve the reviewed pair.
- Reservations use **Manage booking** for confirmed modification/cancellation. Logs, allocations, signed quotes, history, request receipts and audits are read through the browser and changed only through their established workflows. Eligible conversation histories are deleted manually on **Privacy**.
- All new data mutations and table/record reads are audited. Session credentials, password hashes and internal search vectors are never exposed; raw customer histories and contact details remain unredacted.

No database migration is added for these controls. Rebuild the API and web images when applying code updates to an existing Compose installation.

## Important behavior

- The LLM interprets preferences and answers approved policies. It has no price or database-commit tool.
- Quotes are itemized, signed and immutable. AZN is binding; USD equivalents use the CBAR feed and are informational.
- Create, modify and cancel all require a displayed draft followed by the customer pressing **Confirm**. Text such as “yes” cannot commit.
- Drafts/holds last ten minutes. PostgreSQL transactions, row locks and exclusion constraints protect physical-car and extra availability.
- Changes preserve the original reservation until confirmation. Immutable versions and booking audits remain.
- Customers access their own bookings using session grants; a public reference does not authorize edits. Keep the same browser session, or use administrator-assisted recovery.
- Manual discounts, different-location/cross-border drop-offs, and payment exceptions enter the administrator queue. Automated actions pause during takeover.
- Full raw messages, contact details, actions and cards are stored unredacted. Admin history access is audited.
- Retention is twelve months after last activity. Due histories appear in the manual privacy dashboard. There is no automated deletion.
- OpenAI receives bounded relevant conversation context, which can contain personal details typed in chat. Stored contact-profile fields are excluded. Responses use `store:false`; OpenAI abuse-monitoring retention may still apply.
- No backups, archive tasks, S3, audit exports, test code, unit tests or load-testing tooling are included.

## Configuration and deployment

`.env.example` lists non-secret settings; `.secrets` supplies credentials through Compose secrets. `DATABASE_URL`, `CHECKPOINT_DATABASE_URL`, `REDIS_URL`, `OPENAI_BASE_URL`, and the storage/provider interfaces separate deployment from business behavior. The two database URLs use asyncpg and psycopg respectively.

The API maintains the CBAR refresh loop in-process under a PostgreSQL leadership lock. Policy embedding is an administrator-triggered operation. Redis carries quota counters and identifiers, not raw transcripts.

See [architecture](docs/architecture.md), [execution record](docs/execution-plan.md), and [operations](docs/operations.md).

Local storage is the sole durable copy. Launch capacity is bounded by hardware, PostgreSQL resources and configured OpenAI quotas. Validate the operator's retention policy and cross-border AI processing arrangements before real customer use.
