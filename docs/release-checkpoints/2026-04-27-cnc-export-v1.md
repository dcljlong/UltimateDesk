# UltimateDesk CNC Export V1 Checkpoint

Date: 2026-04-27

Stable commit:
- a746d24 show cnc features in dxf svg and pdf exports

Confirmed working:
- CNC settings visible in export dialog
- cnc_config reaches backend export generation
- DXF + NC export works live
- Full Pack export works live
- Multi-sheet NC output has sheet setup sections and M0 pause
- G-code has drill / pocket / inside / outside operation ordering
- G-code supports GRBL-safe explicit drilling
- G-code supports Mach-style G81 when machine post is selected
- Multi-pass cutting works
- Lead-in / lead-out works
- Holding tabs work
- Stock-margin origin shift works
- Operation audit summary works
- Desk part generator now passes feature metadata through nesting
- NC file now includes real drill and inside profile operations
- DXF/SVG/PDF now visually show CNC features

Live export proof:
- PDF showed 2 sheets
- PDF showed 75 drill features
- PDF showed 3 inside cuts
- PDF showed 0 pockets/rebates for the tested non-mixer design
- PDF showed 15 parts
- Parts list includes Drill / Inside / Pocket columns

Known remaining work:
- Run one live proof using Music Production or mixer tray enabled to confirm pocket/rebate operations live
- Improve accuracy of actual joinery locations against final hardware/spec
- Add machine-specific post processor presets beyond basic GRBL/Mach/LinuxCNC/Fanuc/Haas labels
- Add richer tool library and material presets
- Add automated export smoke tests
- Add customer-facing manufacturing warnings/confirmation workflow
- Clean old backup files only after this checkpoint is confirmed safe

Commercial caution:
- Current outputs are much stronger but must still be verified in CAM/controller before cutting.
- This is a V1 CNC export milestone, not a guarantee for every machine/controller/material combination.
