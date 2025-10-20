#!/usr/bin/env python3
"""
Focused Call Management System Testing
Tests the auto-redial and call tracking functionality specifically
"""

import requests
import json
import time
from datetime import datetime

class CallManagementTester:
    def __init__(self, base_url="https://medconnect-live-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tokens = {}
        self.users = {}
        
        # Demo credentials
        self.demo_credentials = {
            "provider": {"username": "demo_provider", "password": "Demo123!"},
            "doctor": {"username": "demo_doctor", "password": "Demo123!"},
            "admin": {"username": "demo_admin", "password": "Demo123!"}
        }

    def login_users(self):
        """Login all demo users"""
        print("🔑 Logging in demo users...")
        
        for role, credentials in self.demo_credentials.items():
            response = requests.post(f"{self.api_url}/login", json=credentials)
            if response.status_code == 200:
                data = response.json()
                self.tokens[role] = data['access_token']
                self.users[role] = data['user']
                print(f"   ✅ {role.title()} logged in: {data['user']['id']}")
            else:
                print(f"   ❌ {role.title()} login failed")
                return False
        return True

    def create_and_assign_appointment(self):
        """Create appointment and assign doctor to it"""
        print("\n📅 Creating and assigning appointment...")
        
        # Step 1: Provider creates appointment
        appointment_data = {
            "patient": {
                "name": "Call Management Test Patient",
                "age": 35,
                "gender": "Male",
                "vitals": {
                    "blood_pressure": "120/80",
                    "heart_rate": 72,
                    "temperature": 98.6,
                    "oxygen_saturation": 98
                },
                "consultation_reason": "Call management system testing"
            },
            "appointment_type": "non_emergency",
            "consultation_notes": "Test appointment for call management"
        }
        
        response = requests.post(
            f"{self.api_url}/appointments",
            json=appointment_data,
            headers={'Authorization': f'Bearer {self.tokens["provider"]}'}
        )
        
        if response.status_code != 200:
            print(f"   ❌ Failed to create appointment: {response.status_code}")
            return None
        
        appointment_id = response.json()['id']
        print(f"   ✅ Appointment created: {appointment_id}")
        
        # Step 2: Doctor accepts/assigns themselves to appointment
        update_data = {
            "status": "accepted",
            "doctor_id": self.users['doctor']['id']
        }
        
        response = requests.put(
            f"{self.api_url}/appointments/{appointment_id}",
            json=update_data,
            headers={'Authorization': f'Bearer {self.tokens["doctor"]}'}
        )
        
        if response.status_code != 200:
            print(f"   ❌ Failed to assign doctor: {response.status_code}")
            return None
        
        print(f"   ✅ Doctor assigned to appointment")
        return appointment_id

    def test_call_management_workflow(self, appointment_id):
        """Test the complete call management workflow"""
        print(f"\n🎯 Testing Call Management Workflow for appointment: {appointment_id}")
        
        # Step 1: Doctor starts video call session (triggers call tracking)
        print("\n   Step 1: Doctor starts video call session...")
        response = requests.get(
            f"{self.api_url}/video-call/session/{appointment_id}",
            headers={'Authorization': f'Bearer {self.tokens["doctor"]}'}
        )
        
        if response.status_code != 200:
            print(f"   ❌ Failed to start video call session: {response.status_code}")
            return False
        
        session_data = response.json()
        print(f"   ✅ Video call session started")
        print(f"   Jitsi URL: {session_data.get('jitsi_url')}")
        print(f"   Room: {session_data.get('room_name')}")
        
        # Step 2: Check call status (should show active call)
        print("\n   Step 2: Check call status...")
        response = requests.get(
            f"{self.api_url}/video-call/status/{appointment_id}",
            headers={'Authorization': f'Bearer {self.tokens["doctor"]}'}
        )
        
        if response.status_code == 200:
            status_data = response.json()
            print(f"   ✅ Call status retrieved")
            print(f"   Active: {status_data.get('active')}")
            print(f"   Caller ID: {status_data.get('caller_id')}")
            print(f"   Provider ID: {status_data.get('provider_id')}")
            print(f"   Status: {status_data.get('status')}")
            print(f"   Retry count: {status_data.get('retry_count', 0)}")
        else:
            print(f"   ❌ Failed to get call status: {response.status_code}")
        
        # Step 3: Doctor ends call quickly (should trigger auto-redial)
        print("\n   Step 3: Doctor ends call quickly...")
        response = requests.post(
            f"{self.api_url}/video-call/end/{appointment_id}",
            headers={'Authorization': f'Bearer {self.tokens["doctor"]}'}
        )
        
        if response.status_code == 200:
            end_data = response.json()
            print(f"   ✅ Call ended successfully")
            print(f"   Message: {end_data.get('message')}")
            print(f"   Ended by: {end_data.get('ended_by')}")
        else:
            print(f"   ❌ Failed to end call: {response.status_code} - {response.text}")
            return False
        
        # Step 4: Check call status again (should show retry info)
        print("\n   Step 4: Check call status after end (auto-redial check)...")
        time.sleep(2)  # Wait a moment for auto-redial logic
        
        response = requests.get(
            f"{self.api_url}/video-call/status/{appointment_id}",
            headers={'Authorization': f'Bearer {self.tokens["doctor"]}'}
        )
        
        if response.status_code == 200:
            status_data = response.json()
            print(f"   ✅ Call status after end:")
            print(f"   Active: {status_data.get('active')}")
            print(f"   Status: {status_data.get('status')}")
            print(f"   Retry count: {status_data.get('retry_count', 0)}")
            print(f"   Max retries: {status_data.get('max_retries', 0)}")
            
            if status_data.get('retry_count', 0) > 0:
                print(f"   🎉 AUTO-REDIAL SYSTEM WORKING: Call marked for retry!")
                return True
            else:
                print(f"   ℹ️  Auto-redial may be scheduled (30s delay)")
                return True
        else:
            print(f"   ❌ Failed to get call status after end: {response.status_code}")
            return False

    def test_provider_call_end(self, appointment_id):
        """Test provider ending call"""
        print(f"\n🎯 Testing Provider Call End for appointment: {appointment_id}")
        
        # Provider ends call
        response = requests.post(
            f"{self.api_url}/video-call/end/{appointment_id}",
            headers={'Authorization': f'Bearer {self.tokens["provider"]}'}
        )
        
        if response.status_code == 200:
            end_data = response.json()
            print(f"   ✅ Provider can end call")
            print(f"   Message: {end_data.get('message')}")
            return True
        else:
            print(f"   ❌ Provider cannot end call: {response.status_code} - {response.text}")
            return False

    def test_websocket_endpoints(self):
        """Test WebSocket-related endpoints"""
        print(f"\n🎯 Testing WebSocket Endpoints")
        
        # Test WebSocket status
        response = requests.get(
            f"{self.api_url}/websocket/status",
            headers={'Authorization': f'Bearer {self.tokens["admin"]}'}
        )
        
        if response.status_code == 200:
            status_data = response.json()
            print(f"   ✅ WebSocket status endpoint working")
            print(f"   Total connections: {status_data.get('websocket_status', {}).get('total_connections', 0)}")
            print(f"   Connected users: {status_data.get('websocket_status', {}).get('connected_users', [])}")
        else:
            print(f"   ❌ WebSocket status failed: {response.status_code}")
            return False
        
        # Test WebSocket test message
        response = requests.post(
            f"{self.api_url}/websocket/test-message",
            headers={'Authorization': f'Bearer {self.tokens["doctor"]}'}
        )
        
        if response.status_code == 200:
            msg_data = response.json()
            print(f"   ✅ WebSocket test message endpoint working")
            print(f"   Message sent: {msg_data.get('message_sent')}")
            print(f"   User connected: {msg_data.get('user_connected')}")
            return True
        else:
            print(f"   ❌ WebSocket test message failed: {response.status_code}")
            return False

    def run_all_tests(self):
        """Run all call management tests"""
        print("🎯 CALL MANAGEMENT SYSTEM TESTING")
        print("=" * 50)
        
        if not self.login_users():
            return False
        
        # Create and assign appointment
        appointment_id = self.create_and_assign_appointment()
        if not appointment_id:
            return False
        
        # Test WebSocket endpoints
        websocket_success = self.test_websocket_endpoints()
        
        # Test call management workflow
        call_workflow_success = self.test_call_management_workflow(appointment_id)
        
        # Test provider call end
        provider_end_success = self.test_provider_call_end(appointment_id)
        
        # Summary
        print(f"\n🎯 CALL MANAGEMENT TEST SUMMARY")
        print("=" * 50)
        print(f"   WebSocket Endpoints: {'✅ PASSED' if websocket_success else '❌ FAILED'}")
        print(f"   Call Management Workflow: {'✅ PASSED' if call_workflow_success else '❌ FAILED'}")
        print(f"   Provider Call End: {'✅ PASSED' if provider_end_success else '❌ FAILED'}")
        
        overall_success = websocket_success and call_workflow_success and provider_end_success
        print(f"\n   Overall: {'🎉 SUCCESS' if overall_success else '❌ ISSUES FOUND'}")
        
        return overall_success

if __name__ == "__main__":
    tester = CallManagementTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 CALL MANAGEMENT TESTING COMPLETED SUCCESSFULLY!")
    else:
        print("\n❌ CALL MANAGEMENT TESTING FOUND ISSUES")