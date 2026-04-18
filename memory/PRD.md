# UltimateDesk CNC Pro - Product Requirements Document

## Original Problem Statement
AI-powered CNC desk designer for Kiwi DIY gamers/builders. Generate unlimited gaming/PC/studio/home desks from NZ 18mm plywood (2400x1200mm sheets). Features AI chat designer, 3D preview, CNC file generation with nesting optimization, and Stripe payments.

## User Personas
1. **Gamer**: 49" ultrawide, RGB channels, headset arm
2. **Studio**: Mixer tray (610mm), pedal tilt, iso-damp
3. **Office**: Cable management, VESA mount

## Architecture
- **Frontend**: React 19 + Tailwind CSS + Shadcn/UI + Framer Motion
- **Backend**: FastAPI + Motor (MongoDB async driver)
- **Database**: MongoDB (local)
- **AI**: Gemini 3 Flash via Emergent LLM Key
- **Payments**: Stripe (test mode)
- **Auth**: JWT with httpOnly cookies

## Core Requirements (Static)
1. AI Chat Designer - Natural language to desk params
2. Desk Preview - Visual representation
3. CNC Generation - Nesting, G-code, material estimates
4. User Auth - Register, login, JWT tokens
5. Design Library - Save/load user designs
6. Pro Subscription - $4.99 NZD/month via Stripe

## What's Been Implemented (April 2026)

### Phase 1 - MVP Complete ✅
- [x] Landing page with presets (Gaming, Studio, Office)
- [x] User authentication (register, login, logout, JWT)
- [x] AI Chat Designer with Gemini 3 Flash integration
- [x] 2D Desk Preview (canvas-based visualization)
- [x] Configuration Panel (dimensions, features, style)
- [x] CNC Generation engine (nesting algorithm, G-code preview)
- [x] Sheet nesting visualization
- [x] Material cost estimator
- [x] Design save/load functionality
- [x] Dark/Light theme toggle
- [x] Stripe checkout integration (test mode)
- [x] Pricing page
- [x] Payment success page with polling

### Backend Endpoints
- `/api/auth/*` - Authentication
- `/api/designs/*` - Design CRUD
- `/api/designs/presets` - Preset templates
- `/api/chat/design` - AI chat
- `/api/cnc/generate` - CNC file generation
- `/api/cnc/material-estimate` - Quick estimate
- `/api/payments/*` - Stripe integration

## Prioritized Backlog

### P0 - Critical
- [x] Core functionality complete

### P1 - High Priority
- [ ] True 3D preview with Three.js (had compatibility issues)
- [ ] DXF/SVG/PDF file export downloads
- [ ] Full G-code file download for Pro users
- [ ] AR GLB export for mobile

### P2 - Medium Priority
- [ ] Realtime collaboration
- [ ] Design sharing/public gallery
- [ ] PWA installable
- [ ] Improved nesting algorithm (<5% waste target)
- [ ] Finger/dovetail joint visualization

### P3 - Nice to Have
- [ ] 95% Lighthouse score optimization
- [ ] Mobile-responsive 3D preview
- [ ] Design version history
- [ ] Export to PDF cutting sheets

## Test Credentials
- Admin: admin@ultimatedesk.com / Admin123!
- New users can register with any valid email

## Next Action Items
1. Implement proper 3D preview with compatible Three.js setup
2. Add actual file download functionality for Pro users
3. Improve nesting algorithm efficiency
4. Add material cost breakdown by part
