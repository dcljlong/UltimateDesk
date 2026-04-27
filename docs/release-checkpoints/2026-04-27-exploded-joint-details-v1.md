# UltimateDesk Exploded Assembly + Joint Details V1 Checkpoint

Date: 2026-04-27

Stable commit:
- a3adde2 add exploded assembly and joint details to review drawings

Based on:
- CNC Export V1 tag: cnc-export-v1
- Review Drawings V2 tag: review-drawings-v2
- Assembly Details V1 tag: assembly-details-v1
- Part Marking V1 tag: part-marking-v1

Confirmed working:
- Backend /api/review-drawings/pdf endpoint live
- Export dialog Review Drawings download still works
- Exploded Assembly View page added
- Joint Detail Diagrams page added
- J01/J02-style joint detail labels added
- Desktop to frame rail detail added
- Rail end to leg post detail added
- Side rail to leg frame detail added
- Cable tray / accessory fixing detail added
- Live PDF generated successfully after Render deployment

Live proof:
- Live Exploded Assembly + Joint Details V1 PDF size: 38,761 bytes
- Previous Part Marking V1 PDF size was approximately 31,349 bytes
- Test used 1800W x 800D x 750H, 18mm material
- Test included cable management, mixer tray, VESA mount, and headset hook

CNC impact:
- No CNC geometry change
- No DXF/NC/SVG/nesting/G-code logic change
- This is PDF/manufacturing instruction only

Known remaining work:
- Add actual hardware quantity calculations from hole groups
- Add drawing title block / revision / sheet numbering
- Add customer/manufacturer sign-off block
- Add automated PDF text/content smoke test
- Add final full export pack QA tests across multiple desk configurations
- Rebuild CNC safety confirmation gate later as isolated safe component

Commercial caution:
- Exploded assembly and joint details are schematic manufacturing aids.
- Final fixing type, edge distance, hardware load, and supplier hardware must still be verified before production manufacture.
