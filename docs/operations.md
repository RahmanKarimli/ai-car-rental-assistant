# Local operations

## Lifecycle

Start: `docker compose up -d --build`.
Stop while preserving storage: `docker compose stop`.
Inspect services: `docker compose ps`.
Inspect application startup: `docker compose logs --tail=100 api web`.
Bootstrap admin: `docker compose exec api python scripts/bootstrap_admin.py`.

Do not remove the PostgreSQL volume unless you intend to permanently erase application data. There are no backups or archives.

Compose dependency health checks are startup controls, not test suites. The API exposes `/health/live` and `/health/ready` inside its network. Readiness requires PostgreSQL; OpenAI configuration status is reported separately. Redis failures disable coordinated AI calls while database-backed booking forms remain available.

## Key and credentials

Keep `.env` and `.secrets` out of Git. Set the OpenAI key locally in `.secrets/openai_api_key` and restart API. LangSmith tracing is optional: put its key in `.secrets/langsmith_api_key`, set `LANGSMITH_TRACING=true` in `.env`, and recreate the API container. Traces use the configured `LANGSMITH_PROJECT`; `LANGSMITH_HIDE_INPUTS` and `LANGSMITH_HIDE_OUTPUTS` default to `true` so raw prompts, customer details and replies are not copied to the tracing service. Changing a database password file does not change an already-initialized PostgreSQL role: rotate the role password through a privileged session and update the corresponding secret together.

## Interrupted work

The browser retains the current failed event ID for Retry. Reusing it returns a recorded result or replays idempotent nodes. Raw events are committed before processing. A successful database booking commit remains committed if response/checkpoint delivery later fails. Reservation state and the original quote are authoritative.

## Support and retention

The **Database tables** admin screen lists all application tables with a short description and a complete field guide. Editable catalog records, draft policies and operator accounts have create, detail, edit and explicit delete controls. Deletion rejects relational and signed-quote references instead of cascading. Use Active/Status to retire used catalog records. The current administrator cannot disable, demote or delete their own account. Changed passwords, roles and deactivation revoke other sessions for that operator.

Pricing plans/rules and published operational policies remain permanent. Create a new rate-plan version, add its desired rules while it is unused, then change vehicle assignments. Published policy sources are copied into a new version and reviewed in both languages. Original versions, signed quotes and reservation history remain readable. Table browsing and mutations are recorded in the audit trail; credential hashes and internal vectors are omitted from API responses.

An admin claims a support case, reviews its full audited transcript and sends messages while takeover is active. Resolution returns the conversation to automation. Manual discounts are explicit approved engine inputs, not model-generated prices. Drop-off/payment exceptions remain manual operator decisions; resolving a case does not bypass ordinary booking rules.

The privacy dashboard lists histories due twelve months after their last activity. An admin explicitly purges or records an extension reason. Contractual and accounting retention must be separately approved by the operator. There is no scheduled deletion, checkpoint sweeper, export, backup or archive worker.

## Portability

Use external database/Redis URLs and an HTTPS origin/cookie setting when changing deployment. PostgreSQL needs vector and btree_gist; initialize the graph schema before serving traffic. All API instances share PostgreSQL locks, Redis quota counters and asset storage. A filesystem adapter can use a shared mounted volume; alternative adapters implement the same interfaces. API limits and hardware determine practical capacity.
