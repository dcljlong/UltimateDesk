from pathlib import Path
import importlib.util
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
SERVER_PATH = BACKEND / "server.py"
OUT_DIR = ROOT / "tmp_smoke_outputs"

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "ultimatedesk_smoke_tests")
os.environ.setdefault("JWT_SECRET", "local-smoke-test-secret")
os.environ.setdefault("SECRET_KEY", "local-smoke-test-secret")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

sys.path.insert(0, str(BACKEND.resolve()))

spec = importlib.util.spec_from_file_location("server", SERVER_PATH.resolve())
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)

OUT_DIR.mkdir(exist_ok=True)

CASES = [
    {
        "name": "standard_basic",
        "min_bytes": 32000,
        "params": dict(
            width=1800,
            depth=800,
            height=750,
            has_cable_management=True,
            has_mixer_tray=False,
            has_vesa_mount=False,
            has_headset_hook=False,
        ),
    },
    {
        "name": "full_accessory_pack",
        "min_bytes": 39000,
        "params": dict(
            width=1800,
            depth=800,
            height=750,
            has_cable_management=True,
            has_mixer_tray=True,
            mixer_tray_width=610,
            has_vesa_mount=True,
            has_headset_hook=True,
        ),
    },
    {
        "name": "oversize_split_top",
        "min_bytes": 32000,
        "params": dict(
            width=2600,
            depth=900,
            height=750,
            has_cable_management=True,
            has_mixer_tray=True,
            mixer_tray_width=610,
            has_vesa_mount=True,
            has_headset_hook=True,
            is_oversize=True,
            desktop_split_count=2,
            requires_centre_support=True,
        ),
    },
]

SOURCE_MARKERS = [
    "Calculated hardware quantities",
    "Approval / Release Sign-Off",
    "Required review sign-offs",
    "Exploded Assembly View",
    "Joint Detail Diagrams",
    "Part Marking / Orientation",
    "Cut Part Labels",
    "Assembly Details",
    "Hardware / Fastener Schedule",
    "draw_approval_signoff_page()",
    "draw_exploded_assembly_page()",
    "draw_joint_detail_diagrams_page()",
    "draw_part_marking_page()",
    "draw_cut_part_labels_page()",
]

def check_source_markers():
    raw = SERVER_PATH.read_text(encoding="utf-8-sig")
    missing = [marker for marker in SOURCE_MARKERS if marker not in raw]
    if missing:
        raise RuntimeError("Missing source markers: " + ", ".join(missing))

def run_case(case):
    params = server.DesignParams(**case["params"])
    pdf = server.generate_review_drawing_pdf_bytes(
        params,
        f"Smoke Test - {case['name']}",
    )

    out_path = OUT_DIR / f"manufacturing_pack_{case['name']}.pdf"
    out_path.write_bytes(pdf)

    size = len(pdf)
    if size < case["min_bytes"]:
        raise RuntimeError(
            f"{case['name']} PDF too small: {size} bytes, expected >= {case['min_bytes']}"
        )

    print(f"PASS {case['name']}: {size} bytes -> {out_path}")

def main():
    print("=== UltimateDesk Manufacturing Pack Smoke Test ===")
    print(f"Server: {SERVER_PATH}")

    check_source_markers()

    for case in CASES:
        run_case(case)

    print("")
    print("PASS - manufacturing pack smoke tests completed")

if __name__ == "__main__":
    main()
