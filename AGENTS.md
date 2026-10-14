Whenever you can perform an action yourself (running terminal commands, starting the dev server, inspecting local outputs), do so autonomously without asking for confirmation.

# Project guidance

## Context

This is a white-label car rental SaaS platform with an AI customer concierge. The backend, database, AI workflow, and existing customer and operator interfaces are implemented. The current work is a frontend redesign. Read `docs/architecture.md`, `docs/execution-plan.md`, and `docs/operations.md` before changing behavior or deployment assumptions.

## System boundaries

- `frontend/` is the Next.js customer and operator interface. Its same-origin API proxy is the route to the FastAPI backend. Preserve the existing API contracts and generated TypeScript types when changing UI code.
- FastAPI validates sessions, ownership, staff permissions, CSRF, Origin, and inputs. Domain services own inventory, prices, quotes, holds, bookings, and audits. Do not move these decisions into the browser or derive authoritative prices from displayed data.
- Free-form chat can collect preferences and explain options, but booking create, modify, and cancel actions require structured events and an explicit confirmation of the displayed quote. Keep that distinction clear in the UI.
- Quotes are signed, itemized snapshots in integer AZN qəpiks. Availability and eligibility are checked again at confirmation. Show server-returned prices, status, errors, and reservation versions accurately.
- Customer-facing content is bilingual Azerbaijani and English. Preserve localization, accessible controls, and escaped rendering of untrusted chat or policy text.
- Operator workflows include catalog management, policy and rate publication, support takeover, audit visibility, and manual retention review. Respect protected records and versioned publication flows.

## Frontend design workflow

- For every upcoming visual design or frontend task, load and apply the relevant guidance installed from `Leonxlnx/taste-skill` in `.agents/skills/` before planning or editing. Start with `.agents/skills/design-taste-frontend/SKILL.md`; load a focused skill from the same installation when the task calls for it, such as `redesign-existing-projects` for a redesign. Apply the guidance that fits the product UI and its constraints.
- `design.md` is the strict visual identity source for all frontend UI. Read and follow it for typography, colors, spacing, layout, and surfaces. These project tokens take precedence over conflicting aesthetic suggestions from other design guidance.
- Use the Bento Quiet system's declared colors, Plus Jakarta Sans for display and body text, JetBrains Mono for metadata, 1280px centered content, 12-column desktop grid, 80px section spacing, and its specified radius and CTA recipes. Use one shared module treatment; use the restrained interaction shadows now declared in `design.md`, added at the user’s request. Keep resting cards flat; reserve shadows for hover feedback and side panels. Use its single-column mobile layout where applicable. Do not invent visual tokens.
- If examples later in `design.md` conflict with its frontmatter tokens or explicit design recipes, follow the frontmatter and explicit recipes; do not copy conflicting sample values.
- Use Phosphor Icons (`@phosphor-icons/react`) as the standard and only icon set throughout customer and operator UI, including vehicle specs, AI concierge badges, and controls. Do not substitute emoji or another icon library.
- Never use the default `/site` design skill for styling or layouts.
- Customer rentals use whole days: return time must match pickup time, with no editable return clock. Make all pickup branches’ inventory available on the landing page through server pagination (12 cars per page) and offer an All cars action after a filtered search. AI chat opens in a sidebar on the current page. Use the shared styled `Select` control for dropdowns with keyboard navigation and explicit EN/AZ selection. Support persisted Light/Dark/System appearance using `design.md` dark tokens. Support AZN and informational USD display from stored CBAR rates; signed quotes and payments remain AZN.
- Customer pages use a search-first car-rental layout inspired by the supplied KAYAK references, with filters, real inventory cards, and an AI concierge companion panel. Preserve the Yol identity and `design.md` tokens. Do not add people’s faces, customer review sections, marketplace comparison claims, or unsupported price predictions.

## UI assets

- Store all custom UI illustrations, exported icon graphics, and branding images in `frontend/public/assets/`; Next.js serves them at `/assets/<filename>`. Interface icons continue to use Phosphor Icons.
- Keep `docs/visual-asset-catalog.md` current whenever an asset is added or changed. Record its purpose, dimensions, format, transparency, file size, and generated status. Use optimized WebP images and preserve transparent alpha where needed.
- Category car illustrations represent rental categories; they are not actual fleet photographs. The concierge emblem is a custom brand illustration. Testimonial portraits are synthetic placeholders and do not establish a real customer identity or endorsement.

## Local operation and safety

- Use the documented Compose lifecycle in `docs/operations.md` when local services are needed. Inspect existing service status and logs before changing runtime state.
- Keep `.env`, `.secrets/`, credentials, and customer data out of Git and tool output. Do not remove the PostgreSQL volume during routine work; the project has no backup or archive service.
- Treat PostgreSQL as authoritative for conversations and reservations; Redis is disposable coordination state. A failed browser response does not imply that a booking transaction failed, so use the existing idempotent retry flow.
- The implementation record says there is no test code or test/load-testing task in the project. Verify changes with appropriate available checks and direct inspection without assuming a test suite exists.
