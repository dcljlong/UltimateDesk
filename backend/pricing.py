"""
UltimateDesk CNC Pro - Pricing Engine

Transparent, usage-based pricing for CNC exports.
Price scales with project complexity: sheet count, part count, joint type, and
premium features. Reusable across quote and checkout flows.

Formula:
    base_fee                     = $10 NZD
    + sheets_fee  = $4 per 2400x1200 sheet required
    + parts_fee   = $0.50 per part over the base 6-part threshold (rounded)
    + joint_fee   = finger:$0, box:$2, dovetail:$4
    + features_fee = $2 per premium feature enabled
    subtotal       = sum of the above
    bundle_total  = subtotal * bundle_multiplier
                     (dxf:1.0, dxf_svg:1.15, dxf_gcode:1.35, full_pack:1.50)
    + commercial_license = +$19 flat if requested
    final = round to nearest $1 NZD

Examples (from the product spec):
    Small desk,   1 sheet, simple joints, DXF only  -> ~$14
    Large studio, 3 sheets, premium features, full  -> ~$34
"""
from __future__ import annotations

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


# ---- Constants (single source of truth) ----

BASE_FEE = 10.0
SHEET_FEE = 4.0
PART_FEE_OVER_THRESHOLD = 0.50
PART_THRESHOLD = 6  # first 6 parts included in base

JOINT_FEES = {
    "finger": 0.0,
    "box": 2.0,
    "dovetail": 4.0,
}

PREMIUM_FEATURE_KEYS = [
    ("has_rgb_channels", "RGB channel routing"),
    ("has_headset_hook", "Headset hook"),
    ("has_gpu_tray", "GPU support tray"),
    ("has_mixer_tray", "Mixer tray (studio)"),
    ("has_pedal_tilt", "Pedal tilt (studio)"),
    ("has_vesa_mount", "VESA mount plate"),
    ("has_cable_management", "Cable management tray"),
]
FEATURE_FEE_EACH = 2.0

BUNDLE_OPTIONS = {
    "dxf":       {"label": "DXF only",           "multiplier": 1.00, "files": ["dxf"]},
    "dxf_svg":   {"label": "DXF + SVG",          "multiplier": 1.15, "files": ["dxf", "svg"]},
    "dxf_gcode": {"label": "DXF + G-code",       "multiplier": 1.35, "files": ["dxf", "gcode"]},
    "full_pack": {"label": "Full Pack (DXF + SVG + G-code + PDF cutlist)",
                  "multiplier": 1.50,
                  "files": ["dxf", "svg", "gcode", "pdf"]},
}
DEFAULT_BUNDLE = "dxf"

COMMERCIAL_LICENSE_FEE = 19.0

CURRENCY = "nzd"


# ---- Pydantic models used by API layer ----

class LineItem(BaseModel):
    label: str
    amount: float
    detail: Optional[str] = None


class QuoteBreakdown(BaseModel):
    currency: str = CURRENCY
    subtotal: float
    bundle_key: str
    bundle_label: str
    bundle_multiplier: float
    bundle_total: float        # subtotal * multiplier (pre-license)
    commercial_license: bool = False
    commercial_fee: float = 0.0
    total: float               # final, rounded
    line_items: List[LineItem] # human-readable breakdown
    headline: str              # short human explanation
    sheets_required: int
    part_count: int
    bundle_files: List[str]


class QuoteRequest(BaseModel):
    params: Dict[str, Any]
    bundle: str = DEFAULT_BUNDLE
    commercial_license: bool = False
    # Optional pre-computed nesting summary — if provided we use it,
    # otherwise the API layer computes it from params.
    sheets_required: Optional[int] = None
    part_count: Optional[int] = None


# ---- Core engine ----

def _count_premium_features(params: Dict[str, Any]) -> List[str]:
    active = []
    for key, label in PREMIUM_FEATURE_KEYS:
        if params.get(key):
            active.append(label)
    return active


def calculate_quote(
    params: Dict[str, Any],
    *,
    sheets_required: int,
    part_count: int,
    bundle: str = DEFAULT_BUNDLE,
    commercial_license: bool = False,
) -> QuoteBreakdown:
    """Pure pricing function — no I/O, fully testable."""
    if bundle not in BUNDLE_OPTIONS:
        bundle = DEFAULT_BUNDLE
    bundle_cfg = BUNDLE_OPTIONS[bundle]

    line_items: List[LineItem] = []

    # Base
    line_items.append(LineItem(label="Base export fee", amount=BASE_FEE))

    # Sheets
    sheets_fee = SHEET_FEE * max(1, sheets_required)
    line_items.append(LineItem(
        label=f"Material sheets ({sheets_required} × 2400×1200mm)",
        amount=round(sheets_fee, 2),
        detail=f"${SHEET_FEE:.2f} per sheet",
    ))

    # Parts complexity
    extra_parts = max(0, part_count - PART_THRESHOLD)
    parts_fee = round(extra_parts * PART_FEE_OVER_THRESHOLD, 2)
    if parts_fee > 0:
        line_items.append(LineItem(
            label=f"Part complexity ({extra_parts} parts over base {PART_THRESHOLD})",
            amount=parts_fee,
            detail=f"${PART_FEE_OVER_THRESHOLD:.2f} per extra part",
        ))

    # Joint type
    joint_type = params.get("joint_type", "finger")
    joint_fee = JOINT_FEES.get(joint_type, 0.0)
    if joint_fee > 0:
        line_items.append(LineItem(
            label=f"{joint_type.capitalize()} joints",
            amount=joint_fee,
            detail="Premium joinery",
        ))

    # Premium features
    active_features = _count_premium_features(params)
    features_fee = round(len(active_features) * FEATURE_FEE_EACH, 2)
    if features_fee > 0:
        line_items.append(LineItem(
            label=f"Premium features ({len(active_features)})",
            amount=features_fee,
            detail=", ".join(active_features),
        ))

    subtotal = round(
        BASE_FEE + sheets_fee + parts_fee + joint_fee + features_fee, 2
    )

    # Bundle multiplier
    multiplier = bundle_cfg["multiplier"]
    bundle_total_raw = subtotal * multiplier
    bundle_total = round(bundle_total_raw, 2)
    if multiplier != 1.0:
        diff = round(bundle_total_raw - subtotal, 2)
        line_items.append(LineItem(
            label=f"Bundle upgrade — {bundle_cfg['label']}",
            amount=diff,
            detail=f"×{multiplier:.2f} on subtotal",
        ))

    # Commercial license
    commercial_fee = COMMERCIAL_LICENSE_FEE if commercial_license else 0.0
    if commercial_license:
        line_items.append(LineItem(
            label="Commercial-use license",
            amount=commercial_fee,
            detail="Permits selling desks built from these files",
        ))

    total_raw = bundle_total + commercial_fee
    # Round to nearest whole NZD for UX
    total = float(round(total_raw))

    headline = _build_headline(
        params=params,
        sheets_required=sheets_required,
        feature_count=len(active_features),
        bundle_cfg=bundle_cfg,
        total=total,
    )

    return QuoteBreakdown(
        subtotal=subtotal,
        bundle_key=bundle,
        bundle_label=bundle_cfg["label"],
        bundle_multiplier=multiplier,
        bundle_total=bundle_total,
        commercial_license=commercial_license,
        commercial_fee=commercial_fee,
        total=total,
        line_items=line_items,
        headline=headline,
        sheets_required=sheets_required,
        part_count=part_count,
        bundle_files=bundle_cfg["files"],
    )


def _build_headline(
    *,
    params: Dict[str, Any],
    sheets_required: int,
    feature_count: int,
    bundle_cfg: Dict[str, Any],
    total: float,
) -> str:
    """Human-language summary: "Large studio desk, 3 sheets, premium features: $34"."""
    width = params.get("width", 0)
    if width >= 2000:
        size = "Large"
    elif width >= 1600:
        size = "Medium"
    else:
        size = "Small"

    desk_type = params.get("desk_type", "office")
    sheets_str = f"{sheets_required} sheet" if sheets_required == 1 else f"{sheets_required} sheets"
    joints = params.get("joint_type", "finger")

    parts: List[str] = [f"{size} {desk_type} desk", sheets_str]
    if feature_count == 0:
        parts.append(f"simple {joints} joints")
    elif feature_count <= 2:
        parts.append(f"{feature_count} premium feature{'s' if feature_count != 1 else ''}")
    else:
        parts.append("premium features")

    return f"{', '.join(parts)} — ${int(total)} NZD ({bundle_cfg['label']})"


def get_bundle_catalog() -> List[Dict[str, Any]]:
    """Expose available bundles to the frontend."""
    return [
        {"key": k, "label": v["label"], "multiplier": v["multiplier"], "files": v["files"]}
        for k, v in BUNDLE_OPTIONS.items()
    ]
