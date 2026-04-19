# UltimateDesk CNC Pro - Product Requirements Document

## Original Problem Statement
AI-powered CNC desk designer for Kiwi DIY gamers/builders. Generate unlimited gaming/studio/office desks from NZ 18mm plywood (2400x1200mm sheets). AI chat, 2D/3D preview, CNC file generation with nesting, scale-based transparent pricing, Stripe payments.

## Architecture
- **Frontend**: React 19 + Tailwind + Shadcn/UI + Framer Motion
- **Backend**: FastAPI + Motor (async MongoDB)
- **AI**: Gemini 3 Flash via Emergent LLM Key
- **Payments**: Stripe test mode (dynamic pricing via engine)
- **Auth**: JWT in httpOnly cookies

## Pricing Model (v3 — Final, Feb 2026)
**Engine:** `/app/backend/pricing.py` — pure, 13 pytest unit tests, 33 tests total.

| Component | Amount |
|---|---|
| Base fee | **$15** |
| Per sheet | **$6** |
| Per extra part (> 6) | $0.50 |
| Joint: finger / box / dovetail | $0 / $2 / $4 |
| Per premium feature | $2 |
| Bundle multiplier: dxf / +svg / +gcode / full | 1.0 / 1.15 / 1.35 / 1.50 |
| Commercial-use license | **+$29** flat |
| Material (informational) | ~$80 × sheets (plywood bought separately) |

**Live price ranges hit:**
- Small desk 1 sheet simple → **$22–28** ✓
- Medium 2 sheets cable/monitor → **$35–45** ✓
- Gaming/studio 3+ sheets premium → **$55–75** ✓
- +Commercial license: +$29

## Implemented Features (v1→v3)
### v1 MVP (Apr 2026)
Auth, Chat Designer (Gemini), 2D isometric preview, nesting, G-code preview, save/load, Stripe skeleton.

### v2 Scale-based Pricing (Feb 2026)
- Pricing engine, `/api/pricing/{bundles,quote}`
- Dynamic Stripe checkout using server-priced params
- Bundle-aware exports (DXF / +SVG / +G-code / Full Pack)
- ExportDialog rewrite: live quote + breakdown + bundle selector + commercial toggle
- Live-price pill in Designer header
- Copy protection: email-watermark overlay + rounded dims for non-Pro

### v3 Pricing Refinement + Sharing (Feb 2026)
- Constants bumped: base $15, sheet $6, commercial $29
- Material estimate + note added to every quote (`material_cost_estimate`, `material_note`)
- **Shareable quote links**: `POST /api/pricing/share` → slug; `GET /api/pricing/shared/{slug}` + `/pdf`
- **`/quote/:slug` public page** (SharedQuote.jsx) with design summary, line items, total, material note, Save-as-PDF button, Design-your-own CTA
- ExportDialog: Share this quote button + copy-to-clipboard + PDF download
- Pricing page updated with new range copy

## Backend Endpoints
- `/api/auth/*`, `/api/designs/*`, `/api/chat/design`, `/api/cnc/*`
- `/api/pricing/bundles`, `/api/pricing/quote`
- `/api/pricing/share`, `/api/pricing/shared/{slug}`, `/api/pricing/shared/{slug}/pdf`
- `/api/exports/check-access`, `/api/exports/purchase-single`, `/api/exports/purchase-pro`, `/api/exports/generate`, `/api/exports/download/{id}/{type}`
- `/api/payments/*`, `/api/webhook/stripe`

## Test Coverage
- 13 unit tests in `test_pricing.py`
- 11 integration tests in `test_pricing_api.py`
- 9 share/PDF integration tests in `test_share_quote.py`
- **33/33 pass**
- Frontend flows (iteration_3.json): 100 % pass including regressions

## Prioritized Backlog

### P1 — High
- [ ] Industrial bin-packing nesting (<10 % waste target)
- [ ] No-signup landing-page material cost estimator
- [ ] Credit packs (5-pack 15 % off etc.)

### P2 — Medium
- [ ] Subscription Pro via Stripe Billing
- [ ] True interactive Three.js 3D preview
- [ ] Design sharing / public gallery
- [ ] PWA installable

### P3 — Nice to have
- [ ] Split `server.py` (1700 lines) → modules (pricing_router, exports_router, cnc_router)
- [ ] Shared-quotes TTL cleanup job
- [ ] Design version history

## Test Credentials
See `/app/memory/test_credentials.md` (admin is Pro for testing unlimited exports).
