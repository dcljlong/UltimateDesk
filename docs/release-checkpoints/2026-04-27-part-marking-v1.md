# UltimateDesk Part Marking V1 Checkpoint

Date: 2026-04-27

Stable commit:
- c058e68 add part marking labels to review drawings

Based on:
- CNC Export V1 tag: cnc-export-v1
- Review Drawings V2 tag: review-drawings-v2
- Assembly Details V1 tag: assembly-details-v1

Confirmed working:
- Backend /api/review-drawings/pdf endpoint live
- Export dialog Review Drawings download still works
- Review Drawing PDF now includes part marking and orientation instruction pages
- Part Marking / Orientation page added
- Cut Part Labels page added
- P01/P02-style part IDs added
- Front / Back / Left / Right marking guidance added
- Shop-floor cut part label guide added

Live proof:
- Live Part Marking V1 PDF size: 31,179 bytes
- Previous Assembly Details V1 PDF size was approximately 19,530 bytes
- Test used 1800W x 800D x 750H, 18mm material
- Test included cable management, mixer tray, VESA mount, and headset hook

CNC impact:
- No CNC geometry change
- No DXF/NC/SVG/nesting/G-code logic change
- This is PDF/manufacturing instruction only

Known remaining work:
- Add exploded assembly page
- Add per-joint detail diagrams
- Add actual hardware quantity calculations from hole groups
- Add revision / drawing ID / sheet numbering
- Add customer/manufacturer sign-off block
- Add automated PDF text/content smoke test

Commercial caution:
- Part marking/orientation labels are shop-floor guidance.
- Final part handedness and hardware position must still be verified before manufacture.
