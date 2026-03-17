"""
Telehealth API Backend Tests
Tests for authentication, appointments, video calls, and WebSocket functionality
"""
import pytest
import requests
import os
import time
import json
from datetime import datetime

# Get backend URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://docstream-sync.preview.emergentagent.com').rstrip('/')
API_URL = f"{BASE_URL}/api"

# Test credentials from review request
TEST_PROVIDER = {"username": "testprovider", "password": "test123"}
TEST_DOCTOR = {"username": "testdoctor", "password": "test123"}
ADMIN_USER = {"username": "sarmad", "password": "sarmad"}


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_health_check(self):
        """Test /health endpoint"""
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✅ Health check passed: {data}")
    
    def test_api_health_check(self):
        """Test /api/health endpoint"""
        response = requests.get(f"{API_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        print(f"✅ API health check passed: {data}")
    
    def test_ready_endpoint(self):
        """Test /ready endpoint"""
        response = requests.get(f"{BASE_URL}/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["ready"] == True
        print(f"✅ Ready check passed: {data}")


class TestAuthentication:
    """Test authentication endpoints"""
    
    def test_login_provider(self):
        """Test provider login"""
        response = requests.post(f"{API_URL}/login", json=TEST_PROVIDER)
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert "user" in data
            assert data["user"]["role"] == "provider"
            print(f"✅ Provider login successful: {data['user']['full_name']}")
        elif response.status_code == 401:
            print(f"⚠️ Provider login failed - user may not exist: {response.json()}")
            pytest.skip("Test provider user not found")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    def test_login_doctor(self):
        """Test doctor login"""
        response = requests.post(f"{API_URL}/login", json=TEST_DOCTOR)
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert "user" in data
            assert data["user"]["role"] == "doctor"
            print(f"✅ Doctor login successful: {data['user']['full_name']}")
        elif response.status_code == 401:
            print(f"⚠️ Doctor login failed - user may not exist: {response.json()}")
            pytest.skip("Test doctor user not found")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    def test_login_admin(self):
        """Test admin login"""
        response = requests.post(f"{API_URL}/login", json=ADMIN_USER)
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert "user" in data
            print(f"✅ Admin login successful: {data['user']['full_name']}")
        elif response.status_code == 401:
            print(f"⚠️ Admin login failed - user may not exist: {response.json()}")
            pytest.skip("Admin user not found")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{API_URL}/login", json={
            "username": "invalid_user",
            "password": "wrong_password"
        })
        assert response.status_code == 401
        print("✅ Invalid login correctly rejected")


class TestAppointments:
    """Test appointment endpoints"""
    
    @pytest.fixture
    def provider_token(self):
        """Get provider auth token"""
        response = requests.post(f"{API_URL}/login", json=TEST_PROVIDER)
        if response.status_code != 200:
            pytest.skip("Provider login failed")
        return response.json()["access_token"]
    
    @pytest.fixture
    def doctor_token(self):
        """Get doctor auth token"""
        response = requests.post(f"{API_URL}/login", json=TEST_DOCTOR)
        if response.status_code != 200:
            pytest.skip("Doctor login failed")
        return response.json()["access_token"]
    
    def test_get_appointments_as_provider(self, provider_token):
        """Test getting appointments as provider"""
        headers = {"Authorization": f"Bearer {provider_token}"}
        response = requests.get(f"{API_URL}/appointments", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Provider can fetch appointments: {len(data)} found")
    
    def test_get_appointments_as_doctor(self, doctor_token):
        """Test getting appointments as doctor"""
        headers = {"Authorization": f"Bearer {doctor_token}"}
        response = requests.get(f"{API_URL}/appointments", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Doctor can fetch appointments: {len(data)} found")
    
    def test_create_emergency_appointment(self, provider_token):
        """Test creating an emergency appointment"""
        headers = {"Authorization": f"Bearer {provider_token}"}
        appointment_data = {
            "patient": {
                "name": "TEST_Emergency_Patient",
                "age": 45,
                "gender": "male",
                "vitals": {
                    "blood_pressure": "140/90",
                    "heart_rate": 95,
                    "temperature": 38.5,
                    "oxygen_saturation": 96
                },
                "history": "Chest pain, shortness of breath",
                "area_of_consultation": "Cardiology"
            },
            "appointment_type": "emergency",
            "consultation_notes": "Urgent cardiac evaluation needed"
        }
        
        response = requests.post(f"{API_URL}/appointments", json=appointment_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["appointment_type"] == "emergency"
        assert data["status"] == "pending"
        print(f"✅ Emergency appointment created: {data['id']}")
        
        # Store for cleanup
        return data["id"]
    
    def test_create_non_emergency_appointment(self, provider_token):
        """Test creating a non-emergency appointment"""
        headers = {"Authorization": f"Bearer {provider_token}"}
        appointment_data = {
            "patient": {
                "name": "TEST_Regular_Patient",
                "age": 30,
                "gender": "female",
                "vitals": {
                    "blood_pressure": "120/80",
                    "heart_rate": 72
                },
                "history": "Routine checkup",
                "area_of_consultation": "General Medicine"
            },
            "appointment_type": "non_emergency",
            "consultation_notes": "Annual health checkup"
        }
        
        response = requests.post(f"{API_URL}/appointments", json=appointment_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["appointment_type"] == "non_emergency"
        print(f"✅ Non-emergency appointment created: {data['id']}")
        
        return data["id"]


class TestVideoCallEndpoints:
    """Test video call related endpoints"""
    
    @pytest.fixture
    def doctor_token(self):
        """Get doctor auth token"""
        response = requests.post(f"{API_URL}/login", json=TEST_DOCTOR)
        if response.status_code != 200:
            pytest.skip("Doctor login failed")
        return response.json()["access_token"]
    
    @pytest.fixture
    def provider_token(self):
        """Get provider auth token"""
        response = requests.post(f"{API_URL}/login", json=TEST_PROVIDER)
        if response.status_code != 200:
            pytest.skip("Provider login failed")
        return response.json()["access_token"]
    
    @pytest.fixture
    def emergency_appointment_id(self, provider_token):
        """Create an emergency appointment for video call testing"""
        headers = {"Authorization": f"Bearer {provider_token}"}
        appointment_data = {
            "patient": {
                "name": "TEST_VideoCall_Patient",
                "age": 50,
                "gender": "male",
                "vitals": {"blood_pressure": "150/95"},
                "history": "Severe headache",
                "area_of_consultation": "Neurology"
            },
            "appointment_type": "emergency",
            "consultation_notes": "Video call test"
        }
        
        response = requests.post(f"{API_URL}/appointments", json=appointment_data, headers=headers)
        if response.status_code != 200:
            pytest.skip("Failed to create test appointment")
        return response.json()["id"]
    
    def test_start_video_call_emergency(self, doctor_token, emergency_appointment_id):
        """Test starting video call for emergency appointment"""
        headers = {"Authorization": f"Bearer {doctor_token}"}
        
        response = requests.post(
            f"{API_URL}/video-call/start/{emergency_appointment_id}",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "jitsi_url" in data
        assert "room_name" in data
        assert "call_id" in data
        assert data["appointment_type"] == "emergency"
        print(f"✅ Video call started successfully:")
        print(f"   Call ID: {data['call_id']}")
        print(f"   Jitsi URL: {data['jitsi_url'][:50]}...")
        print(f"   Provider notified: {data['provider_notified']}")
        
        return data["call_id"]
    
    def test_video_call_not_allowed_for_non_emergency(self, doctor_token, provider_token):
        """Test that video calls are blocked for non-emergency appointments"""
        # First create a non-emergency appointment
        headers_provider = {"Authorization": f"Bearer {provider_token}"}
        appointment_data = {
            "patient": {
                "name": "TEST_NonEmergency_Patient",
                "age": 25,
                "gender": "female",
                "vitals": {},
                "history": "Routine checkup",
                "area_of_consultation": "General Medicine"
            },
            "appointment_type": "non_emergency",
            "consultation_notes": "Regular visit"
        }
        
        create_response = requests.post(f"{API_URL}/appointments", json=appointment_data, headers=headers_provider)
        if create_response.status_code != 200:
            pytest.skip("Failed to create non-emergency appointment")
        
        appointment_id = create_response.json()["id"]
        
        # Try to start video call
        headers_doctor = {"Authorization": f"Bearer {doctor_token}"}
        response = requests.post(
            f"{API_URL}/video-call/start/{appointment_id}",
            headers=headers_doctor
        )
        
        assert response.status_code == 403
        data = response.json()
        assert "non-emergency" in data["detail"].lower() or "not allowed" in data["detail"].lower()
        print("✅ Video call correctly blocked for non-emergency appointment")
    
    def test_cancel_video_call(self, doctor_token, emergency_appointment_id):
        """Test cancelling a video call"""
        headers = {"Authorization": f"Bearer {doctor_token}"}
        
        # First start a call
        start_response = requests.post(
            f"{API_URL}/video-call/start/{emergency_appointment_id}",
            headers=headers
        )
        
        if start_response.status_code != 200:
            pytest.skip("Failed to start video call")
        
        call_id = start_response.json()["call_id"]
        
        # Now cancel it
        cancel_data = {
            "call_id": call_id,
            "reason": "Test cancellation",
            "cancelled_by": "doctor"
        }
        
        cancel_response = requests.post(
            f"{API_URL}/video-call/cancel/{emergency_appointment_id}",
            json=cancel_data,
            headers=headers
        )
        
        assert cancel_response.status_code == 200
        data = cancel_response.json()
        assert data["success"] == True
        assert data["provider_notified"] == True
        print(f"✅ Video call cancelled successfully: {data}")
    
    def test_get_video_call_session(self, doctor_token, emergency_appointment_id):
        """Test getting video call session details"""
        headers = {"Authorization": f"Bearer {doctor_token}"}
        
        # First start a call
        start_response = requests.post(
            f"{API_URL}/video-call/start/{emergency_appointment_id}",
            headers=headers
        )
        
        if start_response.status_code != 200:
            pytest.skip("Failed to start video call")
        
        # Get session details
        response = requests.get(
            f"{API_URL}/video-call/session/{emergency_appointment_id}",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "jitsi_url" in data
        assert "room_name" in data
        assert "session_id" in data
        print(f"✅ Video call session retrieved: {data['session_id']}")


class TestWebSocketStatus:
    """Test WebSocket status endpoints"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token"""
        response = requests.post(f"{API_URL}/login", json=TEST_PROVIDER)
        if response.status_code != 200:
            pytest.skip("Login failed")
        return response.json()["access_token"]
    
    def test_websocket_status_endpoint(self, auth_token):
        """Test WebSocket status endpoint"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{API_URL}/websocket/status", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "websocket_status" in data
        assert "total_connections" in data["websocket_status"]
        print(f"✅ WebSocket status: {data['websocket_status']['total_connections']} connections")


class TestAppointmentNotes:
    """Test appointment notes functionality"""
    
    @pytest.fixture
    def provider_token(self):
        """Get provider auth token"""
        response = requests.post(f"{API_URL}/login", json=TEST_PROVIDER)
        if response.status_code != 200:
            pytest.skip("Provider login failed")
        return response.json()["access_token"]
    
    @pytest.fixture
    def doctor_token(self):
        """Get doctor auth token"""
        response = requests.post(f"{API_URL}/login", json=TEST_DOCTOR)
        if response.status_code != 200:
            pytest.skip("Doctor login failed")
        return response.json()["access_token"]
    
    @pytest.fixture
    def test_appointment_id(self, provider_token):
        """Create a test appointment"""
        headers = {"Authorization": f"Bearer {provider_token}"}
        appointment_data = {
            "patient": {
                "name": "TEST_Notes_Patient",
                "age": 35,
                "gender": "male",
                "vitals": {},
                "history": "Testing notes",
                "area_of_consultation": "General"
            },
            "appointment_type": "emergency",
            "consultation_notes": "Test appointment for notes"
        }
        
        response = requests.post(f"{API_URL}/appointments", json=appointment_data, headers=headers)
        if response.status_code != 200:
            pytest.skip("Failed to create test appointment")
        return response.json()["id"]
    
    def test_add_note_as_provider(self, provider_token, test_appointment_id):
        """Test adding note as provider"""
        headers = {"Authorization": f"Bearer {provider_token}"}
        note_data = {
            "note": "Provider note: Patient vitals stable",
            "sender_role": "provider"
        }
        
        response = requests.post(
            f"{API_URL}/appointments/{test_appointment_id}/notes",
            json=note_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "note_id" in data
        print(f"✅ Provider note added: {data['note_id']}")
    
    def test_get_appointment_notes(self, provider_token, test_appointment_id):
        """Test getting appointment notes"""
        headers = {"Authorization": f"Bearer {provider_token}"}
        
        # First add a note
        note_data = {
            "note": "Test note for retrieval",
            "sender_role": "provider"
        }
        requests.post(
            f"{API_URL}/appointments/{test_appointment_id}/notes",
            json=note_data,
            headers=headers
        )
        
        # Get notes
        response = requests.get(
            f"{API_URL}/appointments/{test_appointment_id}/notes",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Retrieved {len(data)} notes for appointment")


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{API_URL}/login", json=ADMIN_USER)
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json()["access_token"]
    
    def test_cleanup_test_appointments(self, admin_token):
        """Clean up TEST_ prefixed appointments"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get all appointments
        response = requests.get(f"{API_URL}/appointments", headers=headers)
        if response.status_code != 200:
            pytest.skip("Failed to get appointments")
        
        appointments = response.json()
        deleted_count = 0
        
        for apt in appointments:
            patient_name = apt.get("patient", {}).get("name", "")
            if patient_name.startswith("TEST_"):
                delete_response = requests.delete(
                    f"{API_URL}/appointments/{apt['id']}",
                    headers=headers
                )
                if delete_response.status_code == 200:
                    deleted_count += 1
        
        print(f"✅ Cleaned up {deleted_count} test appointments")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
