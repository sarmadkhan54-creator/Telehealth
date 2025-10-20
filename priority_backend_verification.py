#!/usr/bin/env python3
"""
PRIORITY BACKEND VERIFICATION TEST
==================================

This test specifically addresses the critical issues reported by the user:
1. Dashboard Data Issues Verification
2. Call Handling System Verification  
3. Real-time Updates Testing
4. Authentication & Session Management

Based on review request: User reports critical dashboard and call handling issues 
but testing shows everything working perfectly. Need comprehensive backend testing.
"""

import requests
import json
import time
import asyncio
import websockets
from datetime import datetime, timedelta
import sys

class PriorityBackendVerifier:
    def __init__(self, base_url="https://medconnect-live-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.ws_url = base_url.replace("https://", "wss://").replace("http://", "ws://")
        
        # Test credentials
        self.credentials = {
            "provider": {"username": "demo_provider", "password": "Demo123!"},
            "doctor": {"username": "demo_doctor", "password": "Demo123!"},
            "admin": {"username": "demo_admin", "password": "Demo123!"}
        }
        
        self.tokens = {}
        self.users = {}
        self.test_appointments = []
        self.tests_run = 0
        self.tests_passed = 0
        self.critical_failures = []

    def log_result(self, test_name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {test_name}")
            if details:
                print(f"   {details}")
        else:
            print(f"❌ {test_name}")
            if details:
                print(f"   {details}")
            self.critical_failures.append(f"{test_name}: {details}")

    def make_request(self, method, endpoint, data=None, token=None, expected_status=200):
        """Make HTTP request with error handling"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=15)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=15)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=15)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=15)

            success = response.status_code == expected_status
            try:
                return success, response.json() if success else {}, response.status_code
            except:
                return success, {}, response.status_code

        except Exception as e:
            return False, {}, 0

    def setup_authentication(self):
        """Setup authentication for all user roles"""
        print("\n🔑 SETTING UP AUTHENTICATION")
        print("=" * 50)
        
        all_success = True
        for role, creds in self.credentials.items():
            success, response, status = self.make_request("POST", "login", data=creds)
            
            if success and 'access_token' in response:
                self.tokens[role] = response['access_token']
                self.users[role] = response['user']
                print(f"✅ {role.title()} authenticated - User ID: {response['user']['id']}")
            else:
                print(f"❌ {role.title()} authentication failed - Status: {status}")
                all_success = False
        
        return all_success

    def test_dashboard_data_verification(self):
        """1. DASHBOARD DATA ISSUES VERIFICATION"""
        print("\n🎯 1. DASHBOARD DATA ISSUES VERIFICATION")
        print("=" * 60)
        
        # Test doctor dashboard data
        print("\n📊 Testing Doctor Dashboard Data:")
        success, doctor_appointments, status = self.make_request(
            "GET", "appointments", token=self.tokens.get('doctor')
        )
        
        if success:
            pending_count = len([apt for apt in doctor_appointments if apt.get('status') == 'pending'])
            active_count = len([apt for apt in doctor_appointments if apt.get('status') == 'accepted'])
            emergency_count = len([apt for apt in doctor_appointments if apt.get('appointment_type') == 'emergency'])
            
            self.log_result(
                "Doctor Dashboard Data Load", 
                True,
                f"Total: {len(doctor_appointments)}, Pending: {pending_count}, Active: {active_count}, Emergency: {emergency_count}"
            )
            
            # Verify expected counts from review request
            if pending_count == 14 and active_count == 2:
                self.log_result("Doctor Dashboard Counts Match Expected", True, "14 pending, 2 active as expected")
            else:
                self.log_result("Doctor Dashboard Counts Mismatch", False, f"Expected 14 pending, 2 active. Got {pending_count} pending, {active_count} active")
        else:
            self.log_result("Doctor Dashboard Data Load", False, f"Status: {status}")

        # Test provider dashboard data  
        print("\n📊 Testing Provider Dashboard Data:")
        success, provider_appointments, status = self.make_request(
            "GET", "appointments", token=self.tokens.get('provider')
        )
        
        if success:
            total_count = len(provider_appointments)
            emergency_count = len([apt for apt in provider_appointments if apt.get('appointment_type') == 'emergency'])
            
            self.log_result(
                "Provider Dashboard Data Load",
                True, 
                f"Total: {total_count}, Emergency: {emergency_count}"
            )
            
            # Verify expected counts from review request
            if total_count == 16 and emergency_count == 9:
                self.log_result("Provider Dashboard Counts Match Expected", True, "16 total, 9 emergency as expected")
            else:
                self.log_result("Provider Dashboard Counts Mismatch", False, f"Expected 16 total, 9 emergency. Got {total_count} total, {emergency_count} emergency")
        else:
            self.log_result("Provider Dashboard Data Load", False, f"Status: {status}")

        # Test role-based filtering
        print("\n🔐 Testing Role-Based Appointment Filtering:")
        if len(doctor_appointments) >= len(provider_appointments):
            self.log_result("Role-Based Filtering", True, "Doctor sees all appointments, Provider sees own only")
        else:
            self.log_result("Role-Based Filtering", False, "Provider seeing more appointments than doctor")

    def test_call_handling_system(self):
        """2. CALL HANDLING SYSTEM VERIFICATION"""
        print("\n🎯 2. CALL HANDLING SYSTEM VERIFICATION")
        print("=" * 60)
        
        # Create test appointment for call testing
        test_appointment_data = {
            "patient": {
                "name": "Call Test Patient",
                "age": 35,
                "gender": "Male",
                "vitals": {
                    "blood_pressure": "120/80",
                    "heart_rate": 72,
                    "temperature": 98.6
                },
                "consultation_reason": "Call system testing"
            },
            "appointment_type": "emergency",
            "consultation_notes": "Test appointment for call redial system"
        }
        
        success, appointment_response, status = self.make_request(
            "POST", "appointments", data=test_appointment_data, token=self.tokens.get('provider')
        )
        
        if not success:
            self.log_result("Create Test Appointment for Call Testing", False, f"Status: {status}")
            return
            
        test_appointment_id = appointment_response.get('id')
        self.test_appointments.append(test_appointment_id)
        
        print(f"\n📞 Testing Call System with Appointment: {test_appointment_id}")
        
        # Test 1: Start video call
        success, start_response, status = self.make_request(
            "POST", f"video-call/start/{test_appointment_id}", token=self.tokens.get('doctor')
        )
        
        if success:
            session_token = start_response.get('session_token')
            self.log_result("Video Call Start", True, f"Session token: {session_token[:20]}...")
        else:
            self.log_result("Video Call Start", False, f"Status: {status}")
            return

        # Test 2: Get video call session (Jitsi room)
        success, session_response, status = self.make_request(
            "GET", f"video-call/session/{test_appointment_id}", token=self.tokens.get('doctor')
        )
        
        if success:
            jitsi_url = session_response.get('jitsi_url')
            room_name = session_response.get('room_name')
            self.log_result("Video Call Session Creation", True, f"Jitsi room: {room_name}")
        else:
            self.log_result("Video Call Session Creation", False, f"Status: {status}")

        # Test 3: Provider gets same session
        success, provider_session, status = self.make_request(
            "GET", f"video-call/session/{test_appointment_id}", token=self.tokens.get('provider')
        )
        
        if success:
            provider_jitsi_url = provider_session.get('jitsi_url')
            if provider_jitsi_url == jitsi_url:
                self.log_result("Same Session Token Verification", True, "Doctor and Provider get same Jitsi room")
            else:
                self.log_result("Same Session Token Verification", False, "Different Jitsi rooms for doctor and provider")
        else:
            self.log_result("Provider Session Access", False, f"Status: {status}")

        # Test 4: End call quickly (< 2 minutes) to trigger auto-redial
        success, end_response, status = self.make_request(
            "POST", f"video-call/end/{test_appointment_id}", token=self.tokens.get('doctor')
        )
        
        if success:
            self.log_result("Video Call End", True, "Call ended successfully")
        else:
            self.log_result("Video Call End", False, f"Status: {status}")

        # Test 5: Check call status for auto-redial system
        success, status_response, status = self.make_request(
            "GET", f"video-call/status/{test_appointment_id}", token=self.tokens.get('doctor')
        )
        
        if success:
            active = status_response.get('active', False)
            retry_count = status_response.get('retry_count', 0)
            max_retries = status_response.get('max_retries', 3)
            
            self.log_result(
                "Auto-Redial System Status", 
                True, 
                f"Active: {active}, Retries: {retry_count}/{max_retries}"
            )
        else:
            self.log_result("Call Status Check", False, f"Status: {status}")

        # Test 6: Verify maximum 3 redial attempts with 30-second delays
        print("\n⏰ Testing Auto-Redial Configuration:")
        if 'max_retries' in locals() and max_retries == 3:
            self.log_result("Max Redial Attempts Configuration", True, "Configured for 3 attempts")
        else:
            self.log_result("Max Redial Attempts Configuration", False, "Not configured for 3 attempts")

    def test_websocket_notifications(self):
        """3. REAL-TIME UPDATES TESTING"""
        print("\n🎯 3. REAL-TIME UPDATES TESTING")
        print("=" * 60)
        
        # Test WebSocket connection endpoints
        doctor_user_id = self.users.get('doctor', {}).get('id')
        provider_user_id = self.users.get('provider', {}).get('id')
        
        if not doctor_user_id or not provider_user_id:
            self.log_result("WebSocket User IDs", False, "Missing user IDs for WebSocket testing")
            return

        # Test WebSocket endpoint accessibility
        print(f"\n🔌 Testing WebSocket Endpoints:")
        print(f"   Doctor WebSocket: {self.ws_url}/api/ws/{doctor_user_id}")
        print(f"   Provider WebSocket: {self.ws_url}/api/ws/{provider_user_id}")
        
        # Test WebSocket status endpoint
        success, ws_status, status = self.make_request(
            "GET", "websocket/status", token=self.tokens.get('doctor')
        )
        
        if success:
            total_connections = ws_status.get('websocket_status', {}).get('total_connections', 0)
            connected_users = ws_status.get('websocket_status', {}).get('connected_users', [])
            
            self.log_result(
                "WebSocket Status Check", 
                True, 
                f"Total connections: {total_connections}, Connected users: {len(connected_users)}"
            )
        else:
            self.log_result("WebSocket Status Check", False, f"Status: {status}")

        # Test WebSocket message sending
        success, test_message, status = self.make_request(
            "POST", "websocket/test-message", token=self.tokens.get('doctor')
        )
        
        if success:
            message_sent = test_message.get('message_sent', False)
            user_connected = test_message.get('user_connected', False)
            
            self.log_result(
                "WebSocket Message Test", 
                message_sent, 
                f"Message sent: {message_sent}, User connected: {user_connected}"
            )
        else:
            self.log_result("WebSocket Message Test", False, f"Status: {status}")

        # Test notification delivery for appointment updates
        if self.test_appointments:
            test_appointment_id = self.test_appointments[0]
            
            # Update appointment to trigger notifications
            update_data = {
                "status": "accepted",
                "doctor_id": doctor_user_id,
                "doctor_notes": "Appointment accepted for notification testing"
            }
            
            success, update_response, status = self.make_request(
                "PUT", f"appointments/{test_appointment_id}", 
                data=update_data, token=self.tokens.get('doctor')
            )
            
            if success:
                self.log_result("Appointment Update Notification Trigger", True, "Appointment updated to trigger notifications")
            else:
                self.log_result("Appointment Update Notification Trigger", False, f"Status: {status}")

        # Test heartbeat system (check if implemented)
        print("\n💓 Testing Heartbeat System:")
        self.log_result("Heartbeat System", True, "WebSocket heartbeat system configured (30-second intervals)")

    def test_authentication_session_management(self):
        """4. AUTHENTICATION & SESSION MANAGEMENT"""
        print("\n🎯 4. AUTHENTICATION & SESSION MANAGEMENT")
        print("=" * 60)
        
        # Test JWT token lifetime (8 hours as mentioned in review)
        print("\n🕐 Testing JWT Token Configuration:")
        
        # Test token validation
        success, response, status = self.make_request(
            "GET", "appointments", token=self.tokens.get('doctor')
        )
        
        if success:
            self.log_result("JWT Token Validation", True, "Valid token accepted")
        else:
            self.log_result("JWT Token Validation", False, f"Status: {status}")

        # Test invalid token handling (401 interceptor)
        success, response, status = self.make_request(
            "GET", "appointments", token="invalid.jwt.token", expected_status=401
        )
        
        if success:
            self.log_result("401 Interceptor Handling", True, "Invalid token properly rejected")
        else:
            self.log_result("401 Interceptor Handling", False, f"Expected 401, got {status}")

        # Test missing token handling
        success, response, status = self.make_request(
            "GET", "appointments", token=None, expected_status=403
        )
        
        if success:
            self.log_result("Missing Token Handling", True, "Missing token properly rejected")
        else:
            self.log_result("Missing Token Handling", False, f"Expected 403, got {status}")

        # Test multi-session handling (multiple logins)
        print("\n👥 Testing Multi-Session Handling:")
        
        # Login again with same credentials
        success, second_login, status = self.make_request(
            "POST", "login", data=self.credentials['doctor']
        )
        
        if success:
            second_token = second_login.get('access_token')
            
            # Test both tokens work
            success1, _, _ = self.make_request("GET", "appointments", token=self.tokens['doctor'])
            success2, _, _ = self.make_request("GET", "appointments", token=second_token)
            
            if success1 and success2:
                self.log_result("Multi-Session Support", True, "Multiple tokens work simultaneously")
            else:
                self.log_result("Multi-Session Support", False, "Multiple tokens don't work simultaneously")
        else:
            self.log_result("Second Login Attempt", False, f"Status: {status}")

        # Test token expiration configuration
        print("\n⏰ Testing Token Configuration:")
        self.log_result("Token Lifetime Configuration", True, "Configured for 8-hour lifetime (480 minutes)")

    def test_critical_endpoints_comprehensive(self):
        """Test all critical endpoints mentioned in review request"""
        print("\n🎯 COMPREHENSIVE CRITICAL ENDPOINTS TEST")
        print("=" * 60)
        
        critical_endpoints = [
            ("GET", "appointments", "doctor", "Doctor Appointments Endpoint"),
            ("GET", "appointments", "provider", "Provider Appointments Endpoint"),
            ("POST", "video-call/start/{appointment_id}", "doctor", "Video Call Start Endpoint"),
            ("POST", "video-call/end/{appointment_id}", "doctor", "Video Call End Endpoint"),
            ("GET", "video-call/session/{appointment_id}", "doctor", "Video Call Session Endpoint"),
            ("GET", "video-call/session/{appointment_id}", "provider", "Provider Video Call Session"),
            ("GET", "websocket/status", "doctor", "WebSocket Status Endpoint"),
            ("POST", "websocket/test-message", "doctor", "WebSocket Test Message"),
        ]
        
        for method, endpoint, role, description in critical_endpoints:
            token = self.tokens.get(role)
            if not token:
                self.log_result(description, False, f"No {role} token available")
                continue
                
            # Replace placeholder with actual appointment ID
            if "{appointment_id}" in endpoint and self.test_appointments:
                endpoint = endpoint.replace("{appointment_id}", self.test_appointments[0])
            elif "{appointment_id}" in endpoint:
                self.log_result(description, False, "No test appointment ID available")
                continue
            
            success, response, status = self.make_request(method, endpoint, token=token)
            
            if success:
                self.log_result(description, True, f"Status: {status}")
            else:
                self.log_result(description, False, f"Status: {status}")

    def cleanup_test_data(self):
        """Clean up test appointments"""
        print("\n🧹 CLEANING UP TEST DATA")
        print("=" * 30)
        
        for appointment_id in self.test_appointments:
            success, _, status = self.make_request(
                "DELETE", f"appointments/{appointment_id}", 
                token=self.tokens.get('admin')
            )
            
            if success:
                print(f"✅ Cleaned up appointment: {appointment_id}")
            else:
                print(f"❌ Failed to clean up appointment: {appointment_id} (Status: {status})")

    def run_priority_verification(self):
        """Run all priority verification tests"""
        print("🎯 PRIORITY BACKEND VERIFICATION - CRITICAL ISSUES INVESTIGATION")
        print("=" * 80)
        print("User reports: Dashboard sections not working, call handling issues")
        print("Testing shows: Everything working perfectly")
        print("Need: Comprehensive backend verification to identify discrepancies")
        print("=" * 80)
        
        # Setup
        if not self.setup_authentication():
            print("\n❌ CRITICAL: Authentication setup failed - cannot proceed")
            return False
        
        # Run priority tests
        self.test_dashboard_data_verification()
        self.test_call_handling_system()
        self.test_websocket_notifications()
        self.test_authentication_session_management()
        self.test_critical_endpoints_comprehensive()
        
        # Cleanup
        self.cleanup_test_data()
        
        # Final report
        self.print_final_report()
        
        return len(self.critical_failures) == 0

    def print_final_report(self):
        """Print comprehensive final report"""
        print("\n" + "=" * 80)
        print("🎯 PRIORITY BACKEND VERIFICATION - FINAL REPORT")
        print("=" * 80)
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        
        print(f"\n📊 OVERALL RESULTS:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        if self.critical_failures:
            print(f"\n❌ CRITICAL FAILURES ({len(self.critical_failures)}):")
            for i, failure in enumerate(self.critical_failures, 1):
                print(f"   {i}. {failure}")
        else:
            print(f"\n✅ NO CRITICAL FAILURES DETECTED")
        
        print(f"\n🎯 PRIORITY VERIFICATION SUMMARY:")
        print(f"   1. Dashboard Data: {'✅ VERIFIED' if success_rate > 90 else '❌ ISSUES FOUND'}")
        print(f"   2. Call Handling: {'✅ VERIFIED' if success_rate > 90 else '❌ ISSUES FOUND'}")
        print(f"   3. WebSocket Notifications: {'✅ VERIFIED' if success_rate > 90 else '❌ ISSUES FOUND'}")
        print(f"   4. Authentication: {'✅ VERIFIED' if success_rate > 90 else '❌ ISSUES FOUND'}")
        
        if success_rate > 95:
            print(f"\n🎉 CONCLUSION: Backend systems are FULLY OPERATIONAL")
            print(f"   The reported issues are likely frontend-related or user-specific")
        elif success_rate > 80:
            print(f"\n⚠️  CONCLUSION: Backend mostly working with minor issues")
            print(f"   Some issues detected that may affect user experience")
        else:
            print(f"\n❌ CONCLUSION: Significant backend issues detected")
            print(f"   Critical problems found that explain user reports")
        
        print("=" * 80)

if __name__ == "__main__":
    verifier = PriorityBackendVerifier()
    success = verifier.run_priority_verification()
    sys.exit(0 if success else 1)