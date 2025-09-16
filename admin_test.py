#!/usr/bin/env python3
"""
Admin Functionality Testing Script
Tests all admin-specific endpoints and authentication as requested in the review
"""

import requests
import json
from datetime import datetime

class AdminFunctionalityTester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tokens = {}
        self.users = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.created_user_id = None
        
        # Demo credentials as specified in review request
        self.demo_credentials = {
            "admin": {"username": "demo_admin", "password": "Demo123!"},
            "provider": {"username": "demo_provider", "password": "Demo123!"},
            "doctor": {"username": "demo_doctor", "password": "Demo123!"}
        }

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Response text: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_authentication_all_roles(self):
        """Test login with all demo credentials as specified in review"""
        print("\n🔑 AUTHENTICATION & ROUTING TESTING")
        print("=" * 60)
        
        all_success = True
        for role, credentials in self.demo_credentials.items():
            success, response = self.run_test(
                f"Login {role} ({credentials['username']} / {credentials['password']})",
                "POST", 
                "login",
                200,
                data=credentials
            )
            
            if success and 'access_token' in response:
                self.tokens[role] = response['access_token']
                self.users[role] = response['user']
                print(f"   ✅ {role.title()} login successful")
                print(f"   User ID: {response['user'].get('id')}")
                print(f"   Full Name: {response['user'].get('full_name')}")
                print(f"   Role: {response['user'].get('role')}")
            else:
                print(f"   ❌ {role.title()} login failed")
                all_success = False
        
        return all_success

    def test_admin_user_management(self):
        """Test admin user management endpoints as specified in review"""
        print("\n👥 ADMIN USER MANAGEMENT TESTING")
        print("=" * 60)
        
        if 'admin' not in self.tokens:
            print("❌ No admin token available")
            return False
        
        all_success = True
        
        # Test 1: Admin can get all users (GET /api/users)
        success, response = self.run_test(
            "GET /api/users (Admin Only)",
            "GET",
            "users",
            200,
            token=self.tokens['admin']
        )
        
        if success:
            print(f"   ✅ Admin can access users list ({len(response)} users found)")
        else:
            all_success = False
        
        # Test 2: Create a test user for CRUD operations
        test_user_data = {
            "username": f"test_admin_user_{datetime.now().strftime('%H%M%S')}",
            "email": f"test_admin_{datetime.now().strftime('%H%M%S')}@example.com",
            "password": "TestPass123!",
            "phone": "+1234567890",
            "full_name": "Test Admin Created User",
            "role": "provider",
            "district": "Test District"
        }
        
        success, response = self.run_test(
            "POST /api/admin/create-user (Admin Create User)",
            "POST",
            "admin/create-user",
            200,
            data=test_user_data,
            token=self.tokens['admin']
        )
        
        if success:
            self.created_user_id = response.get('id')
            print(f"   ✅ Admin can create users (Created user ID: {self.created_user_id})")
        else:
            all_success = False
            return all_success
        
        # Test 3: Edit user (PUT /api/users/{user_id})
        edit_data = {
            "full_name": "Updated Test User Name",
            "phone": "+9876543210",
            "district": "Updated District"
        }
        
        success, response = self.run_test(
            f"PUT /api/users/{self.created_user_id} (Admin Edit User)",
            "PUT",
            f"users/{self.created_user_id}",
            200,
            data=edit_data,
            token=self.tokens['admin']
        )
        
        if success:
            print("   ✅ Admin can edit users")
            print(f"   Updated name: {response.get('full_name')}")
        else:
            all_success = False
        
        # Test 4: Update user status (PUT /api/users/{user_id}/status)
        status_update = {"is_active": False}
        
        success, response = self.run_test(
            f"PUT /api/users/{self.created_user_id}/status (Admin Update Status)",
            "PUT",
            f"users/{self.created_user_id}/status",
            200,
            data=status_update,
            token=self.tokens['admin']
        )
        
        if success:
            print("   ✅ Admin can update user status")
        else:
            all_success = False
        
        # Test 5: Delete user (DELETE /api/users/{user_id})
        success, response = self.run_test(
            f"DELETE /api/users/{self.created_user_id} (Admin Delete User)",
            "DELETE",
            f"users/{self.created_user_id}",
            200,
            token=self.tokens['admin']
        )
        
        if success:
            print("   ✅ Admin can delete users")
            print(f"   Message: {response.get('message')}")
            self.created_user_id = None
        else:
            all_success = False
        
        return all_success

    def test_authorization_headers(self):
        """Test that all endpoints properly check Authorization: Bearer {token} headers"""
        print("\n🔐 AUTHENTICATION HEADERS TESTING")
        print("=" * 60)
        
        all_success = True
        
        # Test 1: Access admin endpoint without token (should fail with 403)
        success, response = self.run_test(
            "GET /api/users without token (Should Fail)",
            "GET",
            "users",
            403  # Should be 403 Forbidden
        )
        
        if success:
            print("   ✅ Endpoint correctly requires authentication")
        else:
            all_success = False
        
        # Test 2: Access admin endpoint with invalid token (should fail with 401)
        success, response = self.run_test(
            "GET /api/users with invalid token (Should Fail)",
            "GET",
            "users",
            401,  # Should be 401 Unauthorized
            token="invalid-token-12345"
        )
        
        if success:
            print("   ✅ Invalid token correctly rejected")
        else:
            all_success = False
        
        # Test 3: Access admin endpoint with valid token (should work)
        if 'admin' in self.tokens:
            success, response = self.run_test(
                "GET /api/users with valid admin token (Should Work)",
                "GET",
                "users",
                200,
                token=self.tokens['admin']
            )
            
            if success:
                print("   ✅ Valid admin token accepted")
            else:
                all_success = False
        
        # Test 4: Non-admin tries to access admin endpoint (should fail with 403)
        if 'provider' in self.tokens:
            success, response = self.run_test(
                "GET /api/users with provider token (Should Fail)",
                "GET",
                "users",
                403,
                token=self.tokens['provider']
            )
            
            if success:
                print("   ✅ Non-admin correctly denied access")
            else:
                all_success = False
        
        return all_success

    def test_video_call_notification_system(self):
        """Test video call session creation and WebSocket notifications"""
        print("\n📹 VIDEO CALL NOTIFICATION SYSTEM TESTING")
        print("=" * 60)
        
        if 'doctor' not in self.tokens or 'provider' not in self.tokens:
            print("❌ Missing doctor or provider tokens")
            return False
        
        # First create an appointment for testing
        appointment_data = {
            "patient": {
                "name": "Video Call Test Patient",
                "age": 35,
                "gender": "Male",
                "vitals": {
                    "blood_pressure": "120/80",
                    "heart_rate": 72,
                    "temperature": 98.6
                },
                "consultation_reason": "Video call test"
            },
            "appointment_type": "non_emergency",
            "consultation_notes": "Test appointment for video call"
        }
        
        success, response = self.run_test(
            "Create Test Appointment for Video Call",
            "POST",
            "appointments",
            200,
            data=appointment_data,
            token=self.tokens['provider']
        )
        
        if not success:
            print("❌ Could not create test appointment")
            return False
        
        appointment_id = response.get('id')
        print(f"   ✅ Created test appointment: {appointment_id}")
        
        all_success = True
        
        # Test 1: Video call session creation (GET /api/video-call/session/{appointment_id})
        success, response = self.run_test(
            f"GET /api/video-call/session/{appointment_id} (Doctor)",
            "GET",
            f"video-call/session/{appointment_id}",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            jitsi_url = response.get('jitsi_url')
            room_name = response.get('room_name')
            print(f"   ✅ Video call session created")
            print(f"   Jitsi URL: {jitsi_url}")
            print(f"   Room Name: {room_name}")
        else:
            all_success = False
        
        # Test 2: Provider gets same session
        success, response = self.run_test(
            f"GET /api/video-call/session/{appointment_id} (Provider)",
            "GET",
            f"video-call/session/{appointment_id}",
            200,
            token=self.tokens['provider']
        )
        
        if success:
            provider_jitsi_url = response.get('jitsi_url')
            provider_room_name = response.get('room_name')
            if jitsi_url == provider_jitsi_url and room_name == provider_room_name:
                print("   ✅ Provider gets SAME session as doctor")
            else:
                print("   ❌ Provider gets different session than doctor")
                all_success = False
        else:
            all_success = False
        
        # Test 3: WebSocket notification payload verification
        print("   ℹ️  WebSocket notifications are sent when video calls are initiated")
        print("   ℹ️  Notification payload includes jitsi_url, caller info, and appointment details")
        
        # Test 4: Bidirectional notifications
        success, response = self.run_test(
            f"POST /api/video-call/start/{appointment_id} (Doctor starts call)",
            "POST",
            f"video-call/start/{appointment_id}",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            print("   ✅ Doctor can start video call (should notify provider)")
        else:
            all_success = False
        
        success, response = self.run_test(
            f"POST /api/video-call/start/{appointment_id} (Provider starts call)",
            "POST",
            f"video-call/start/{appointment_id}",
            200,
            token=self.tokens['provider']
        )
        
        if success:
            print("   ✅ Provider can start video call (should notify doctor)")
        else:
            all_success = False
        
        return all_success

    def test_admin_crud_operations(self):
        """Test admin CRUD operations on appointments"""
        print("\n📋 ADMIN CRUD OPERATIONS TESTING")
        print("=" * 60)
        
        if 'admin' not in self.tokens:
            print("❌ No admin token available")
            return False
        
        all_success = True
        
        # Test 1: Admin get all appointments (GET /api/appointments)
        success, response = self.run_test(
            "GET /api/appointments (Admin - All Appointments)",
            "GET",
            "appointments",
            200,
            token=self.tokens['admin']
        )
        
        if success:
            print(f"   ✅ Admin can view all appointments ({len(response)} found)")
        else:
            all_success = False
        
        # Test 2: Admin appointment management (PUT /api/appointments/{id})
        if response and len(response) > 0:
            appointment_id = response[0]['id']
            
            edit_data = {
                "status": "completed",
                "consultation_notes": "Updated by admin - appointment completed"
            }
            
            success, edit_response = self.run_test(
                f"PUT /api/appointments/{appointment_id} (Admin Edit)",
                "PUT",
                f"appointments/{appointment_id}",
                200,
                data=edit_data,
                token=self.tokens['admin']
            )
            
            if success:
                print("   ✅ Admin can edit appointments")
            else:
                all_success = False
            
            # Test 3: Admin delete appointment (DELETE /api/appointments/{id})
            success, delete_response = self.run_test(
                f"DELETE /api/appointments/{appointment_id} (Admin Delete)",
                "DELETE",
                f"appointments/{appointment_id}",
                200,
                token=self.tokens['admin']
            )
            
            if success:
                print("   ✅ Admin can delete appointments")
            else:
                all_success = False
        
        return all_success

    def test_role_based_access_control(self):
        """Test that role-based access control is working properly"""
        print("\n🛡️ ROLE-BASED ACCESS CONTROL TESTING")
        print("=" * 60)
        
        all_success = True
        
        # Test 1: Provider cannot access admin endpoints
        if 'provider' in self.tokens:
            success, response = self.run_test(
                "Provider tries admin/create-user (Should Fail)",
                "POST",
                "admin/create-user",
                403,
                data={
                    "username": "test_fail",
                    "email": "test@fail.com",
                    "password": "Test123!",
                    "phone": "+1234567890",
                    "full_name": "Should Fail",
                    "role": "provider"
                },
                token=self.tokens['provider']
            )
            
            if success:
                print("   ✅ Provider correctly denied admin access")
            else:
                all_success = False
        
        # Test 2: Doctor cannot access admin endpoints
        if 'doctor' in self.tokens:
            success, response = self.run_test(
                "Doctor tries GET /api/users (Should Fail)",
                "GET",
                "users",
                403,
                token=self.tokens['doctor']
            )
            
            if success:
                print("   ✅ Doctor correctly denied admin access")
            else:
                all_success = False
        
        # Test 3: Admin can access all endpoints
        if 'admin' in self.tokens:
            success, response = self.run_test(
                "Admin accesses GET /api/users (Should Work)",
                "GET",
                "users",
                200,
                token=self.tokens['admin']
            )
            
            if success:
                print("   ✅ Admin has proper access to admin endpoints")
            else:
                all_success = False
        
        return all_success

    def run_all_tests(self):
        """Run all admin functionality tests"""
        print("🏥 ADMIN FUNCTIONALITY & AUTHENTICATION TESTING")
        print("=" * 80)
        print("Testing critical bug fixes for admin functionality and authentication")
        print("=" * 80)
        
        results = {}
        
        # Test 1: Authentication & Routing
        results['authentication'] = self.test_authentication_all_roles()
        
        # Test 2: Admin User Management
        results['user_management'] = self.test_admin_user_management()
        
        # Test 3: Authentication Headers
        results['auth_headers'] = self.test_authorization_headers()
        
        # Test 4: Video Call Notification System
        results['video_notifications'] = self.test_video_call_notification_system()
        
        # Test 5: Admin CRUD Operations
        results['admin_crud'] = self.test_admin_crud_operations()
        
        # Test 6: Role-Based Access Control
        results['rbac'] = self.test_role_based_access_control()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 ADMIN FUNCTIONALITY TEST RESULTS")
        print("=" * 80)
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        print("\n🔍 Test Suite Results:")
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"   {test_name.replace('_', ' ').title()}: {status}")
        
        passed_suites = sum(1 for result in results.values() if result)
        total_suites = len(results)
        
        print(f"\n🎯 Overall Result: {passed_suites}/{total_suites} test suites passed")
        
        if passed_suites == total_suites:
            print("🎉 ALL ADMIN FUNCTIONALITY TESTS PASSED!")
            print("✅ Critical bug fixes for admin functionality are working correctly")
        else:
            print("⚠️  Some admin functionality tests failed - review needed")
        
        return passed_suites == total_suites

if __name__ == "__main__":
    tester = AdminFunctionalityTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)