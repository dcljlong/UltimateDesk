# UltimateDesk Design Review Drawings V2 Checkpoint

Date: 2026-04-27

Stable commit:
- c1ec087 add isometric assembly page to review drawings

Based on:
- CNC Export V1 tag: cnc-export-v1
- Review Drawings V1 tag: review-drawings-v1

Confirmed working:
- Backend /api/review-drawings/pdf endpoint live
- Export dialog Review Drawings download still works
- Live Review Drawings PDF generates successfully
- PDF includes Plan / Top View
- PDF includes Front Elevation
- PDF includes Side Elevation
- PDF includes Isometric Assembly View
- PDF includes Review Schedule
- Isometric view includes schematic desktop, legs, rails, cable tray, mixer tray, VESA/headset zones where enabled
- Live V2 endpoint returned larger PDF after Render deployment

Live proof:
- Live Review Drawings V2 PDF size: 13,376 bytes
- Previous V1 PDF size was approximately 10,081 bytes
- V2 proof used 1800W x 800D x 750H, 18mm material
- Test included cable management, mixer tray, VESA mount, and headset hook

Known remaining work:
- Improve title block and sheet numbering
- Add revision / drawing ID
- Add customer approval/sign-off block
- Add hardware/fastener schedule
- Add exploded assembly page
- Add more accurate joinery/hardware-specific dimensions
- Add automated PDF text/content smoke test
- Revisit CNC safety confirmation gate later as an isolated component, not inside the current ExportDialog state/useMemo flow

Commercial caution:
- These are Design Review Drawings / Approval Drawings / Manufacturing Review Pack outputs.
- They are not architectural consent drawings or certified engineering documents.
