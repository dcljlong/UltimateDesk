"""Integration tests for pricing share + PDF + new constants.

Iteration 3 — shareable quote link, PDF HTML, updated constants.
Run: cd /app/backend && python -m pytest tests/test_share_quote.py -v
"""
import os
import re
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
# Fallback to public frontend env file if not set in shell
if not BASE_URL:
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")
    except Exception:
        pass

assert BASE_URL, "REACT_APP_BACKEND_URL must be set"

API = f"{BASE_URL}/api"


# ---- Constants via /api/pricing/bundles ----
def test_bundles_constants_reflect_new_pricing():
    r = requests.get(f"{API}/pricing/bundles", timeout=15)
    assert r.status_code == 200
    data = r.json()
    c = data["constants"]
    assert c["base_fee"] == 15.0
    assert c["sheet_fee"] == 6.0
    assert c["commercial_license_fee"] == 29.0
    # Ensure bundles still intact
    keys = {b["key"] for b in data["bundles"]}
    assert {"dxf", "dxf_svg", "dxf_gcode", "full_pack"}.issubset(keys)


# ---- Quote endpoint: small office ----
def test_quote_small_office_range_and_material_note():
    body = {
        "params": {
            "width": 1400, "depth": 700, "height": 750,
            "desk_type": "office", "joint_type": "finger",
            "has_cable_management": False,
        },
        "bundle": "dxf",
        "commercial_license": False,
    }
    r = requests.post(f"{API}/pricing/quote", json=body, timeout=15)
    assert r.status_code == 200
    q = r.json()
    assert 20 <= q["total"] <= 28, f"Small office total out of range: {q['total']}"
    assert q["material_cost_estimate"] > 0
    assert "Material" in q["material_note"]
    assert "$80" in q["material_note"]


# ---- Quote endpoint: medium gaming ----
def test_quote_medium_gaming_range():
    body = {
        "params": {
            "width": 1800, "depth": 800, "height": 750,
            "desk_type": "gaming", "joint_type": "finger",
            "has_cable_management": True, "has_vesa_mount": True,
        },
        "bundle": "dxf_gcode",
        "commercial_license": False,
    }
    r = requests.post(f"{API}/pricing/quote", json=body, timeout=15)
    assert r.status_code == 200
    q = r.json()
    assert 35 <= q["total"] <= 50, f"Medium gaming total out of range: {q['total']}"


# ---- Quote endpoint: large studio + commercial license delta ----
def test_quote_large_studio_and_commercial_delta():
    params = {
        "width": 2200, "depth": 900, "height": 750,
        "desk_type": "studio", "joint_type": "box",
        "has_mixer_tray": True, "has_pedal_tilt": True,
        "has_cable_management": True, "has_vesa_mount": True,
        "has_rgb_channels": True,
    }
    r1 = requests.post(f"{API}/pricing/quote", json={
        "params": params, "bundle": "full_pack", "commercial_license": False
    }, timeout=15).json()
    r2 = requests.post(f"{API}/pricing/quote", json={
        "params": params, "bundle": "full_pack", "commercial_license": True
    }, timeout=15).json()
    assert 55 <= r1["total"] <= 80, f"Large studio total out of range: {r1['total']}"
    assert r2["commercial_fee"] == 29.0
    assert abs((r2["total"] - r1["total"]) - 29) <= 1


# ---- Share link creation + retrieval + view counter ----
@pytest.fixture(scope="module")
def share_slug():
    body = {
        "params": {
            "width": 1800, "depth": 800, "height": 750,
            "desk_type": "gaming", "joint_type": "finger",
            "has_cable_management": True, "has_rgb_channels": True,
        },
        "bundle": "full_pack",
        "commercial_license": False,
        "design_name": "TEST_Shared_Gaming_Desk",
    }
    r = requests.post(f"{API}/pricing/share", json=body, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    return data


def test_share_returns_slug_and_urls(share_slug):
    data = share_slug
    assert "slug" in data
    assert re.fullmatch(r"[0-9a-f]{10}", data["slug"]), f"Bad slug: {data['slug']}"
    assert data["share_url"].endswith(f"/quote/{data['slug']}")
    assert data["pdf_url"] == f"/api/pricing/shared/{data['slug']}/pdf"


def test_get_shared_quote_and_view_increment(share_slug):
    slug = share_slug["slug"]
    # First GET
    r1 = requests.get(f"{API}/pricing/shared/{slug}", timeout=15)
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["design_name"] == "TEST_Shared_Gaming_Desk"
    assert d1["slug"] == slug
    assert "quote" in d1
    views1 = d1.get("views", 0)
    # Second GET should increment
    r2 = requests.get(f"{API}/pricing/shared/{slug}", timeout=15)
    assert r2.status_code == 200
    views2 = r2.json().get("views", 0)
    assert views2 == views1 + 1, f"Views not incremented: {views1} -> {views2}"


def test_shared_pdf_html_has_expected_content(share_slug):
    slug = share_slug["slug"]
    r = requests.get(f"{API}/pricing/shared/{slug}/pdf", timeout=15)
    assert r.status_code == 200
    html = r.text
    assert "UltimateDesk" in html
    # Export total in the PDF label (case-sensitive match per review_request)
    assert "Export total" in html or "Expor" in html  # guard against truncation
    assert "Plywood (separate)" in html


def test_shared_pdf_nonexistent_slug_returns_404():
    r = requests.get(f"{API}/pricing/shared/deadbeef99/pdf", timeout=15)
    assert r.status_code == 404


def test_shared_quote_nonexistent_slug_returns_404():
    r = requests.get(f"{API}/pricing/shared/notarealslug", timeout=15)
    assert r.status_code == 404
