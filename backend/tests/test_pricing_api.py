"""Pricing & Exports API integration tests.

Exercises:
- GET  /api/pricing/bundles
- POST /api/pricing/quote  (unauthenticated)
- POST /api/exports/check-access
- POST /api/exports/purchase-single  (auth, Stripe test mode)
- POST /api/exports/generate          (Pro)
- GET  /api/exports/download/{id}/{type} (bundle-gating)
"""
import os
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://desk-ai-designer.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@ultimatedesk.com"
ADMIN_PASSWORD = "Admin123!"


# ---------- fixtures ----------
# Auth is cookie-based — login sets an httpOnly cookie on the session.

@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    # verify /me works
    me = s.get(f"{API}/auth/me", timeout=30)
    assert me.status_code == 200, f"/me failed: {me.status_code} {me.text}"
    return s


@pytest.fixture(scope="module")
def fresh_user_session():
    s = requests.Session()
    email = f"TEST_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(
        f"{API}/auth/register",
        json={"email": email, "password": "Passw0rd!", "name": "Test User"},
        timeout=30,
    )
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    me = s.get(f"{API}/auth/me", timeout=30)
    if me.status_code != 200:
        s.post(f"{API}/auth/login", json={"email": email, "password": "Passw0rd!"}, timeout=30)
    return s


SMALL_OFFICE = {
    "width": 1400, "depth": 700, "height": 750,
    "desk_type": "office", "joint_type": "finger",
    "style": "minimal",
}
LARGE_STUDIO = {
    "width": 2200, "depth": 900, "height": 750,
    "desk_type": "studio", "joint_type": "box",
    "style": "industrial",
    "has_mixer_tray": True, "has_pedal_tilt": True,
    "has_cable_management": True, "has_vesa_mount": True,
}


# ---------- pricing endpoints ----------

class TestPricingEndpoints:
    def test_bundles_returns_four_with_constants(self):
        r = requests.get(f"{API}/pricing/bundles", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data["currency"] == "nzd"
        keys = {b["key"] for b in data["bundles"]}
        assert keys == {"dxf", "dxf_svg", "dxf_gcode", "full_pack"}
        # Each bundle has multiplier + files
        for b in data["bundles"]:
            assert "multiplier" in b and "files" in b
            assert isinstance(b["files"], list) and len(b["files"]) >= 1
        c = data["constants"]
        for k in ("base_fee", "sheet_fee", "feature_fee_each", "commercial_license_fee", "joint_fees"):
            assert k in c

    def test_quote_small_office_dxf(self):
        r = requests.post(
            f"{API}/pricing/quote",
            json={"params": SMALL_OFFICE, "bundle": "dxf", "commercial_license": False},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        q = r.json()
        assert q["bundle_key"] == "dxf"
        assert 14 <= q["total"] <= 22, f"unexpected total {q['total']}"
        assert "$" in q["headline"] and "NZD" in q["headline"]
        assert q["sheets_required"] >= 1
        assert len(q["line_items"]) >= 2

    def test_quote_large_studio_full_pack(self):
        r = requests.post(
            f"{API}/pricing/quote",
            json={"params": LARGE_STUDIO, "bundle": "full_pack", "commercial_license": True},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        q = r.json()
        assert q["bundle_key"] == "full_pack"
        assert q["commercial_license"] is True
        assert q["commercial_fee"] == 19.0
        assert q["total"] > 30
        labels = " ".join(li["label"] for li in q["line_items"])
        assert "Commercial" in labels or "commercial" in labels.lower()
        assert "Bundle upgrade" in labels
        assert q["bundle_files"] == ["dxf", "svg", "gcode", "pdf"]

    def test_quote_headline_contains_size_desk_sheets(self):
        r = requests.post(
            f"{API}/pricing/quote",
            json={"params": LARGE_STUDIO, "bundle": "dxf", "commercial_license": False},
            timeout=30,
        )
        q = r.json()
        h = q["headline"]
        assert "Large" in h and "studio" in h and "NZD" in h
        assert f"{q['sheets_required']} sheet" in h


# ---------- exports access ----------

class TestExportsAccess:
    def test_check_access_unauth_returns_not_authenticated(self):
        r = requests.post(f"{API}/exports/check-access", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["has_access"] is False
        assert d["reason"] == "not_authenticated"

    def test_check_access_admin_is_pro(self, admin_session):
        r = admin_session.post(f"{API}/exports/check-access", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["has_access"] is True
        assert d.get("plan") == "pro_unlimited"

    def test_check_access_fresh_user_no_credits(self, fresh_user_session):
        r = fresh_user_session.post(f"{API}/exports/check-access", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["has_access"] is False
        assert d["reason"] == "no_credits"


# ---------- purchase-single ----------

class TestPurchaseSingle:
    def test_purchase_single_requires_auth(self):
        r = requests.post(
            f"{API}/exports/purchase-single",
            json={"origin_url": "https://example.com", "params": SMALL_OFFICE, "bundle": "dxf"},
            timeout=30,
        )
        assert r.status_code in (401, 403)

    def test_purchase_single_creates_stripe_session(self, fresh_user_session):
        r = fresh_user_session.post(
            f"{API}/exports/purchase-single",
            json={
                "origin_url": "https://example.com",
                "params": LARGE_STUDIO,
                "bundle": "full_pack",
                "commercial_license": True,
                "design_name": "TEST_large_studio",
            },
            timeout=45,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert "stripe.com" in d["url"]
        assert d["session_id"]
        assert d["amount"] > 30  # server priced
        assert d["bundle"] == "full_pack"


# ---------- generate + download ----------

class TestGenerateAndDownload:
    def test_generate_full_pack_returns_four_files(self, admin_session):
        r = admin_session.post(
            f"{API}/exports/generate",
            json={"params": SMALL_OFFICE, "design_name": "TEST_fullpack", "bundle": "full_pack"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["success"] is True
        assert d["bundle"] == "full_pack"
        files = d["files"]
        assert set(files.keys()) == {"dxf", "svg", "gcode", "pdf"}

        export_id = d["export_id"]
        for ft in ("dxf", "svg", "gcode", "pdf"):
            rr = admin_session.get(f"{API}/exports/download/{export_id}/{ft}", timeout=30)
            assert rr.status_code == 200, f"download {ft} failed: {rr.status_code} {rr.text[:200]}"
            assert len(rr.content) > 0

    def test_generate_dxf_only_excludes_svg(self, admin_session):
        r = admin_session.post(
            f"{API}/exports/generate",
            json={"params": SMALL_OFFICE, "design_name": "TEST_dxfonly", "bundle": "dxf"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["bundle"] == "dxf"
        assert list(d["files"].keys()) == ["dxf"]

        export_id = d["export_id"]
        rr_ok = admin_session.get(f"{API}/exports/download/{export_id}/dxf", timeout=30)
        assert rr_ok.status_code == 200
        rr_svg = admin_session.get(f"{API}/exports/download/{export_id}/svg", timeout=30)
        assert rr_svg.status_code == 404, f"svg on dxf-only should 404, got {rr_svg.status_code}"
