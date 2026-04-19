# UltimateDesk CNC Pro - Product Requirements Document

## Original Problem Statement
AI-powered CNC desk designer for Kiwi DIY gamers/builders. Generate unlimited gaming/PC/studio/home desks from NZ 18mm plywood (2400x1200mm sheets). Features: AI chat designer, 2D/3D preview, CNC file generation with nesting optimization, transparent scale-based pricing, Stripe payments.

## User Personas
1. **Gamer**: 49" ultrawide, RGB channels, headset arm
2. **Studio**: Mixer tray (610mm), pedal tilt, iso-damp
3. **Office**: Cable management, VESA mount

## Architecture
- **Frontend**: React 19 + Tailwind + Shadcn/UI + Framer Motion
- **Backend**: FastAPI + Motor (async MongoDB)
- **AI**: Gemini 3 Flash via Emergent LLM Key
- **Payments**: Stripe (test mode) — dynamic pricing via pricing engine
- **Auth**: JWT in httpOnly cookies

## Core Requirements
1. AI Chat Designer — natural language → desk params
2. Desk Preview — visual + dim display (watermarked for non-Pro)
3. CNC Generation — nesting, G-code, DXF, SVG, PDF cut-sheet
4. User Auth — register / login / JWT
5. Design Library — save/load user designs
6. **Scale-based pricing** — price scales with sheets × parts × joints × features × bundle
7. **Copy protection** — watermark + rounded dims for free tier

## Pricing Model (Implemented Feb 2026)
**Engine: `/app/backend/pricing.py` — pure, tested, reusable**

- `base_fee` $10
- `+ sheets_fee` $4 × sheets required
- `+ parts_fee` $0.50 × (parts > 6)
- `+ joint_fee` finger $0 / box $2 / dovetail $4
- `+ features_fee` $2 per premium feature (RGB, mixer, hook, GPU, pedal, VESA, cable mgmt)
- `× bundle_multiplier` dxf 1.0 / dxf_svg 1.15 / dxf_gcode 1.35 / full_pack 1.50
- `+ commercial_license` +$19 flat

Examples: Small office 1 sheet simple → **$14**; Medium gaming 2 sheets 3 feats full_pack → ~$37; Large studio 2 sheets premium full_pack + commercial → ~$64.

## What's Been Implemented

### Phase 1 — MVP (Apr 2026)
- Landing, auth, chat designer, 2D isometric preview, nesting, G-code preview, save/load, Stripe skeleton.

### Phase 2 — Pricing Refinement (Feb 2026) ✅
- [x] **Pricing engine** (`/app/backend/pricing.py`) with 12 unit tests
- [x] `GET /api/pricing/bundles` catalog endpoint
- [x] `POST /api/pricing/quote` unauthenticated live-quote endpoint
- [x] `POST /api/exports/purchase-single` uses server-computed price (accepts params + bundle + commercial_license)
- [x] `POST /api/exports/generate` honours bundle (only generates requested files)
- [x] SVG export generator added
- [x] Webhook stores bundle + params_snapshot in export_credits
- [x] Download endpoint returns 404 for files not in the paid bundle
- [x] **ExportDialog** rewritten — bundle selector, commercial-license toggle, live-quote-card with line-item breakdown, checkout/generate dual mode
- [x] **Live-price pill** in Designer header (updates on params change)
- [x] **Copy protection** — diagonal email-watermark overlay on canvas for non-Pro, rounded dim display (`~1800mm`), right-click disabled
- [x] **Pricing page** updated — replaced "$4.99 Single Export" with "Per-Design Export from $14"
- [x] TZ bug fix on download expiry check

### Backend Endpoints
- `/api/auth/*`
- `/api/designs/*` + `/api/designs/presets`
- `/api/chat/design`
- `/api/cnc/generate`, `/api/cnc/material-estimate`
- `/api/pricing/bundles`, `/api/pricing/quote`
- `/api/exports/check-access`, `/api/exports/purchase-single`, `/api/exports/purchase-pro`, `/api/exports/generate`, `/api/exports/download/{id}/{type}`
- `/api/payments/*`, `/api/webhook/stripe`

## Testing
- 12 pytest pricing engine tests (pass)
- 11 integration API tests (pass)
- 7+ frontend E2E UI flows (pass)
- Test report: `/app/test_reports/iteration_2.json` — 100% pass both layers

## Prioritized Backlog
### P1 — High
- [ ] Industrial bin-packing nesting (<10 % waste target)
- [ ] No-signup landing-page material cost estimator
- [ ] Credit packs (e.g. 5-pack at 20 % off)

### P2 — Medium
- [ ] True interactive Three.js 3D preview (prev had lib-compat issues)
- [ ] Subscription plan via Stripe Billing (monthly Pro)
- [ ] Design sharing / public gallery
- [ ] PWA installable

### P3 — Nice to have
- [ ] Split `server.py` (now 1700 lines) into modules (exports, pricing, cnc routers)
- [ ] Finger/dovetail joint visualization
- [ ] Design version history

## Test Credentials
See `/app/memory/test_credentials.md` (admin is Pro for testing unlimited exports).
