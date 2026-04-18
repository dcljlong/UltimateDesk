"""
UltimateDesk CNC Pro - Backend API Tests
Tests: Health, Auth, Designs, CNC Generation, Chat
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data prefix for cleanup
TEST_PREFIX = "TEST_"

class TestHealth:
    """Health check endpoint tests"""
    
    def test_health_endpoint(self):
        """Test /api/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        print(f"✓ Health check passed: {data}")

    def test_root_endpoint(self):
        """Test /api/ returns API info"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "UltimateDesk" in data["message"]
        print(f"✓ Root endpoint passed: {data}")


class TestAuth:
    """Authentication endpoint tests"""
    
    def test_login_admin_success(self):
        """Test admin login with correct credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@ultimatedesk.com", "password": "Admin123!"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@ultimatedesk.com"
        assert data["role"] == "admin"
        assert data["is_pro"] == True
        assert "id" in data
        print(f"✓ Admin login passed: {data['email']}, role={data['role']}")
    
    def test_login_invalid_credentials(self):
        """Test login with wrong password"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@ultimatedesk.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        print(f"✓ Invalid credentials rejected: {data['detail']}")
    
    def test_login_nonexistent_user(self):
        """Test login with non-existent email"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "nonexistent@test.com", "password": "anypassword"}
        )
        assert response.status_code == 401
        print("✓ Non-existent user rejected")
    
    def test_register_new_user(self):
        """Test user registration"""
        unique_email = f"{TEST_PREFIX}user_{uuid.uuid4().hex[:8]}@test.com"
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "email": unique_email,
                "password": "TestPass123!",
                "name": "Test User"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == unique_email.lower()
        assert data["name"] == "Test User"
        assert data["role"] == "user"
        assert data["is_pro"] == False
        print(f"✓ User registration passed: {data['email']}")
        return data
    
    def test_register_duplicate_email(self):
        """Test registration with existing email fails"""
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "email": "admin@ultimatedesk.com",
                "password": "TestPass123!",
                "name": "Duplicate User"
            }
        )
        assert response.status_code == 400
        data = response.json()
        assert "already registered" in data["detail"].lower()
        print(f"✓ Duplicate email rejected: {data['detail']}")
    
    def test_me_without_auth(self):
        """Test /me endpoint without authentication"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
        print("✓ Unauthenticated /me request rejected")
    
    def test_me_with_auth(self):
        """Test /me endpoint with valid session"""
        session = requests.Session()
        # Login first
        login_resp = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@ultimatedesk.com", "password": "Admin123!"}
        )
        assert login_resp.status_code == 200
        
        # Check /me
        me_resp = session.get(f"{BASE_URL}/api/auth/me")
        assert me_resp.status_code == 200
        data = me_resp.json()
        assert data["email"] == "admin@ultimatedesk.com"
        print(f"✓ Authenticated /me passed: {data['email']}")
    
    def test_logout(self):
        """Test logout clears session"""
        session = requests.Session()
        # Login
        session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@ultimatedesk.com", "password": "Admin123!"}
        )
        # Logout
        logout_resp = session.post(f"{BASE_URL}/api/auth/logout")
        assert logout_resp.status_code == 200
        
        # Verify session is cleared
        me_resp = session.get(f"{BASE_URL}/api/auth/me")
        assert me_resp.status_code == 401
        print("✓ Logout passed")


class TestDesigns:
    """Design endpoints tests"""
    
    def test_get_presets(self):
        """Test /api/designs/presets returns preset designs"""
        response = requests.get(f"{BASE_URL}/api/designs/presets")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3  # gaming, studio, office
        
        # Verify preset structure
        preset_ids = [p["id"] for p in data]
        assert "gaming" in preset_ids
        assert "studio" in preset_ids
        assert "office" in preset_ids
        
        # Verify params structure
        gaming = next(p for p in data if p["id"] == "gaming")
        assert "params" in gaming
        assert gaming["params"]["width"] == 1800
        assert gaming["params"]["has_rgb_channels"] == True
        print(f"✓ Presets endpoint passed: {len(data)} presets found")
    
    def test_get_designs_requires_auth(self):
        """Test /api/designs requires authentication"""
        response = requests.get(f"{BASE_URL}/api/designs/")
        assert response.status_code == 401
        print("✓ Designs list requires auth")
    
    def test_create_design_requires_auth(self):
        """Test creating design requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/designs/",
            json={
                "name": "Test Design",
                "params": {
                    "width": 1800,
                    "depth": 800,
                    "height": 750,
                    "desk_type": "gaming"
                }
            }
        )
        assert response.status_code == 401
        print("✓ Create design requires auth")
    
    def test_create_and_get_design(self):
        """Test full design CRUD flow"""
        session = requests.Session()
        
        # Login
        login_resp = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@ultimatedesk.com", "password": "Admin123!"}
        )
        assert login_resp.status_code == 200
        
        # Create design
        design_name = f"{TEST_PREFIX}Design_{uuid.uuid4().hex[:8]}"
        create_resp = session.post(
            f"{BASE_URL}/api/designs/",
            json={
                "name": design_name,
                "params": {
                    "width": 2000,
                    "depth": 900,
                    "height": 750,
                    "desk_type": "studio",
                    "monitor_count": 2,
                    "has_rgb_channels": False,
                    "has_cable_management": True,
                    "has_headset_hook": False,
                    "has_gpu_tray": False,
                    "has_mixer_tray": True,
                    "mixer_tray_width": 610,
                    "has_pedal_tilt": False,
                    "has_vesa_mount": False,
                    "leg_style": "solid",
                    "joint_type": "finger",
                    "material_thickness": 18,
                    "custom_features": []
                }
            }
        )
        assert create_resp.status_code == 200
        created = create_resp.json()
        assert created["name"] == design_name
        assert created["params"]["width"] == 2000
        assert "id" in created
        design_id = created["id"]
        print(f"✓ Design created: {design_id}")
        
        # Get design by ID
        get_resp = session.get(f"{BASE_URL}/api/designs/{design_id}")
        assert get_resp.status_code == 200
        fetched = get_resp.json()
        assert fetched["id"] == design_id
        assert fetched["name"] == design_name
        print(f"✓ Design fetched: {fetched['name']}")
        
        # Update design
        update_resp = session.put(
            f"{BASE_URL}/api/designs/{design_id}",
            json={
                "name": f"{design_name}_Updated",
                "params": {
                    "width": 2200,
                    "depth": 900,
                    "height": 750,
                    "desk_type": "studio",
                    "monitor_count": 2,
                    "has_rgb_channels": False,
                    "has_cable_management": True,
                    "has_headset_hook": False,
                    "has_gpu_tray": False,
                    "has_mixer_tray": True,
                    "mixer_tray_width": 610,
                    "has_pedal_tilt": False,
                    "has_vesa_mount": False,
                    "leg_style": "solid",
                    "joint_type": "finger",
                    "material_thickness": 18,
                    "custom_features": []
                }
            }
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["params"]["width"] == 2200
        print(f"✓ Design updated: width={updated['params']['width']}")
        
        # Delete design
        delete_resp = session.delete(f"{BASE_URL}/api/designs/{design_id}")
        assert delete_resp.status_code == 200
        print(f"✓ Design deleted: {design_id}")
        
        # Verify deletion
        verify_resp = session.get(f"{BASE_URL}/api/designs/{design_id}")
        assert verify_resp.status_code == 404
        print("✓ Design deletion verified")


class TestCNC:
    """CNC generation endpoint tests"""
    
    def test_generate_cnc_basic(self):
        """Test basic CNC generation"""
        response = requests.post(
            f"{BASE_URL}/api/cnc/generate",
            json={
                "width": 1800,
                "depth": 800,
                "height": 750,
                "desk_type": "gaming",
                "monitor_count": 1,
                "has_rgb_channels": False,
                "has_cable_management": True,
                "has_headset_hook": False,
                "has_gpu_tray": False,
                "has_mixer_tray": False,
                "mixer_tray_width": 610,
                "has_pedal_tilt": False,
                "has_vesa_mount": False,
                "leg_style": "standard",
                "joint_type": "finger",
                "material_thickness": 18,
                "custom_features": []
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify nesting output
        assert "nesting" in data
        assert data["nesting"]["sheets_required"] >= 1
        assert "waste_percentage" in data["nesting"]
        assert "parts" in data["nesting"]
        assert len(data["nesting"]["parts"]) > 0
        
        # Verify estimates
        assert "estimated_cut_time_minutes" in data
        assert data["estimated_cut_time_minutes"] > 0
        assert "material_cost_nzd" in data
        assert data["material_cost_nzd"] > 0
        
        # Verify G-code preview
        assert "gcode_preview" in data
        assert "G21" in data["gcode_preview"]  # mm units
        assert "M3" in data["gcode_preview"]   # spindle on
        print(f"✓ CNC generation passed: {data['nesting']['sheets_required']} sheets, {data['estimated_cut_time_minutes']}min")
    
    def test_generate_cnc_with_features(self):
        """Test CNC generation with all features enabled"""
        response = requests.post(
            f"{BASE_URL}/api/cnc/generate",
            json={
                "width": 2000,
                "depth": 900,
                "height": 750,
                "desk_type": "studio",
                "monitor_count": 3,
                "has_rgb_channels": True,
                "has_cable_management": True,
                "has_headset_hook": True,
                "has_gpu_tray": True,
                "has_mixer_tray": True,
                "mixer_tray_width": 610,
                "has_pedal_tilt": True,
                "has_vesa_mount": True,
                "leg_style": "solid",
                "joint_type": "dovetail",
                "material_thickness": 18,
                "custom_features": []
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # More parts = more sheets
        assert data["nesting"]["sheets_required"] >= 2
        
        # Verify all feature parts are included
        part_names = [p["name"] for p in data["nesting"]["parts"]]
        assert "Desktop" in part_names
        assert "Cable Tray" in part_names
        assert "Headset Hook" in part_names
        assert "GPU Support Tray" in part_names
        assert "Mixer Tray" in part_names
        assert "VESA Mount Plate" in part_names
        print(f"✓ CNC with features passed: {len(part_names)} parts generated")
    
    def test_material_estimate(self):
        """Test quick material estimate endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/cnc/material-estimate",
            params={"width": 1800, "depth": 800, "height": 750}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "sheets_required" in data
        assert "waste_percentage" in data
        assert "estimated_cost_nzd" in data
        assert "part_count" in data
        print(f"✓ Material estimate passed: {data['sheets_required']} sheets, ${data['estimated_cost_nzd']} NZD")


class TestChat:
    """AI Chat Designer endpoint tests"""
    
    def test_chat_design_basic(self):
        """Test basic chat design request"""
        response = requests.post(
            f"{BASE_URL}/api/chat/design",
            json={
                "message": "I want a gaming desk with RGB lighting",
                "current_params": {
                    "width": 1800,
                    "depth": 800,
                    "height": 750,
                    "desk_type": "gaming",
                    "monitor_count": 1,
                    "has_rgb_channels": False,
                    "has_cable_management": True,
                    "has_headset_hook": False,
                    "has_gpu_tray": False,
                    "has_mixer_tray": False,
                    "mixer_tray_width": 610,
                    "has_pedal_tilt": False,
                    "has_vesa_mount": False,
                    "leg_style": "standard",
                    "joint_type": "finger",
                    "material_thickness": 18,
                    "custom_features": []
                }
            },
            timeout=30  # AI responses can take time
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "response" in data
        assert "updated_params" in data
        assert "session_id" in data
        assert len(data["response"]) > 0
        print(f"✓ Chat design passed: session={data['session_id'][:8]}...")
        print(f"  Response preview: {data['response'][:100]}...")
    
    def test_chat_design_session_continuity(self):
        """Test chat maintains session context"""
        # First message
        resp1 = requests.post(
            f"{BASE_URL}/api/chat/design",
            json={
                "message": "Make it 2 meters wide",
                "current_params": {
                    "width": 1800,
                    "depth": 800,
                    "height": 750,
                    "desk_type": "gaming",
                    "monitor_count": 1,
                    "has_rgb_channels": False,
                    "has_cable_management": True,
                    "has_headset_hook": False,
                    "has_gpu_tray": False,
                    "has_mixer_tray": False,
                    "mixer_tray_width": 610,
                    "has_pedal_tilt": False,
                    "has_vesa_mount": False,
                    "leg_style": "standard",
                    "joint_type": "finger",
                    "material_thickness": 18,
                    "custom_features": []
                }
            },
            timeout=30
        )
        assert resp1.status_code == 200
        session_id = resp1.json()["session_id"]
        
        # Second message with same session
        resp2 = requests.post(
            f"{BASE_URL}/api/chat/design",
            json={
                "message": "Now add a headset hook",
                "current_params": resp1.json()["updated_params"],
                "session_id": session_id
            },
            timeout=30
        )
        assert resp2.status_code == 200
        assert resp2.json()["session_id"] == session_id
        print(f"✓ Chat session continuity passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
