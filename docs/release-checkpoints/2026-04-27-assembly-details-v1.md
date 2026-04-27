# UltimateDesk Assembly Details V1 Checkpoint

Date: 2026-04-27

Stable commit:
- 78968a0 add assembly details to review drawings

Based on:
- CNC Export V1 tag: cnc-export-v1
- Review Drawings V2 tag: review-drawings-v2

Confirmed working:
- Backend /api/review-drawings/pdf endpoint live
- Export dialog Review Drawings download still works
- Review Drawing PDF now includes manufacturing instruction pages
- Assembly Details page added
- Hardware / Fastener Schedule page added
- Part-to-part connection map added
- Recommended assembly order added
- Manufacturing checks before cutting / assembly added

Live proof:
- Live Assembly Details V1 PDF size: 19,529 bytes
- Previous V2 PDF size was approximately 13,419 bytes
- Test used 1800W x 800D x 750H, 18mm material
- Test included cable management, mixer tray, VESA mount, and headset hook

CNC impact:
- No CNC geometry change
- No DXF/NC/SVG/nesting/G-code logic change
- This is PDF/manufacturing instruction only

Known remaining work:
- Add exploded assembly page
- Add per-joint detail diagrams
- Add hardware quantity calculations from actual hole groups
- Add front/back/left/right edge orientation labels
- Add part marking labels for assembly
- Add customer/manufacturer sign-off block
- Add drawing revision and sheet numbering improvements

Commercial caution:
- Assembly details are manufacturing instructions and review aids.
- Hardware specifications are indicative until confirmed against final material, fixings, loads, and supplier hardware.
