# Implementation record

1. Created local Compose, secret initialization, backend and frontend lockfiles.
2. Implemented application models, extensions, initial migration, restricted application/graph roles and manual history purge.
3. Implemented session authentication, staff RBAC, booking access grants, raw event persistence and idempotent turn processing.
4. Implemented fleet/extras management, photo upload, availability and deterministic ranking.
5. Implemented integer AZN quote calculations, immutable signed itemization, deposits, modification/cancellation charges and CBAR USD display support.
6. Implemented physical-car/stock holds and transactional confirmed create/modify/cancel with immutable contract versions and audits.
7. Implemented typed customer events, booking APIs and OpenAPI/TypeScript generation.
8. Implemented async OpenAI Structured Outputs and the persistent LangGraph turn workflow.
9. Implemented bilingual administrator-reviewed policy publication, embeddings and cited hybrid RAG.
10. Implemented contextual extra recommendations and administrator escalation/discount approval.
11. Implemented customer chat, cards, structured trip/contact controls, booking management and operator console.
12. Implemented manual due-history review, justified extensions and explicit purging.
13. Implemented provider failure responses, quotas, concurrency limits, advisory locks and idempotent recovery.
14. Added startup instructions and operational documentation. Real keys, fleet and reviewed policies are operator setup inputs.
15. Added field-based admin CRUD, paginated inspection of all 28 tables, descriptions for every column, linked record navigation, write-only account passwords and audited deletion guards. Published pricing/policies and transactional records retain their versioned or confirmed workflows.
16. Separated natural-language car sorting from eligibility filters and explicit requests for other options. Cheapest uses engine trip totals across all eligible cars; capacity uses recorded seats and luggage features. Repeated searches have stable order, and budgets are not automatically relaxed.

No test code or test/load-testing tasks are part of this project.

## Operator execution order

The source implementation is complete. The following setup supplies the operator's real credentials, policies and fleet; it does not create example contracts or prices.

1. Run `python3 scripts/setup_local.py`. This creates the ignored `.env`, a private `.secrets` directory and distinct database, Redis and quote-signing credentials. Existing credentials are preserved.
2. Set `.secrets/openai_api_key` using a local editor. Configure the public origin in `.env`; retain the finalized OpenAI model and embedding settings for launch.
3. Run `docker compose up -d --build`. PostgreSQL initializes extensions and roles. The API applies the frozen Alembic schema, initializes the LangGraph checkpoint schema and starts FastAPI. Web starts after API readiness.
4. Run `docker compose exec api python scripts/bootstrap_admin.py` and create the first operator account. Open `/admin` and sign in.
5. Upload the actual Azerbaijani and English policy documents using one matching bundle key/version. Publish the reviewed pair, which creates pgvector embeddings. Publish operational age, duration, modification and cancellation rules that match those documents.
6. Create versioned rate plans with integer AZN prices, tax and deposit amounts referencing the published operational policy. Add seasonal/fixed rules where appropriate; publish a new rate-plan version for later pricing changes.
7. Create real pickup branches, individual physical vehicles and their photos. Create bilingual extras with genuine stock counts, billing units and eligibility rules. Use returned IDs to connect catalog records.
8. Open the customer page. Customers provide preferences, select a live car and receive a signed itemized draft. Only the explicit confirmation button commits a reservation. Existing reservations link to modification/cancellation drafts with the same confirmation requirement.
9. Operate the escalation inbox: claim cases, read the audited full transcript, message the customer and resolve the case. An approved manual discount is applied by the pricing engine when a fresh draft is prepared.
10. Review the privacy dashboard for histories due after twelve months of inactivity. An administrator explicitly purges due chat data or records a justified extension. Maintain contractual retention independently of chat-history retention.

For local manual exploration, run `docker compose exec api python scripts/seed_demo.py` after the API is ready. This reconciles duplicate demo locations and adds 52 connected vehicles with real-format Azerbaijan-style plates, five rate plans, varied vehicle categories and powertrains, extras, policies and FX data. It is safe to rerun. Add `--embed` when the OpenAI key is configured if you want policy RAG vectors generated for the demo documents.

Do not remove the PostgreSQL volume or secret files during routine restarts. The runtime contains no backup, archival, audit-export or automated deletion service. Local hardware and provider quotas determine capacity; additional deployment instances must share PostgreSQL, Redis and asset storage.

See [the complete directory tree, database schema and workflow](architecture.md) and [restart/recovery operations](operations.md).
