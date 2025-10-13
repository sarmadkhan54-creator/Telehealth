#!/usr/bin/env python3
"""
Enhanced Features Testing for Review Request
Testing the enhanced functionality implemented:
1. Enhanced Admin Permissions Testing
2. Doctor Appointment Visibility Testing  
3. Provider Appointment Visibility Testing
4. Role-Based Access Verification
"""

import requests
import sys
import json
from datetime import datetime

class EnhancedFeaturesAPITester:
    def __init__(self, base_url="https://healthlink-app-6.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tokens = {}  # Store tokens for different user roles
        self.users = {}   # Store user data for different roles
        self.tests_run = 0
        self.tests_passed = 0
        
        # Test credentials from review request
        self.demo_credentials = {
            "provider": {"username": "demo_provider", "password": "Demo123!"},
            "doctor": {"username": "demo_doctor", "password": "Demo123!"},
            "admin": {"username": "demo_admin", "password": "Demo123!"}
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

    def test_login_all_roles(self):
        """Test login for all user roles"""
        print("\n🔑 Testing Login for All Roles")
        print("-" * 50)
        
        all_success = True
        for role, credentials in self.demo_credentials.items():
            success, response = self.run_test(
                f"Login {role.title()}",
                "POST", 
                "login",
                200,
                data=credentials
            )
            
            if success and 'access_token' in response:
                self.tokens[role] = response['access_token']
                self.users[role] = response['user']
                print(f"   ✅ {role.title()} login successful - Token obtained")
                print(f"   User ID: {response['user'].get('id')}")
                print(f"   Full Name: {response['user'].get('full_name')}")
                print(f"   Role: {response['user'].get('role')}")
            else:
                print(f"   ❌ {role.title()} login failed")
                all_success = False
        
        return all_success

    def test_enhanced_admin_permissions(self):
        """🎯 ENHANCED ADMIN PERMISSIONS TESTING - Review Request Feature"""
        print("\n🎯 ENHANCED ADMIN PERMISSIONS TESTING")
        print("=" * 70)
        
        if 'admin' not in self.tokens:
            print("❌ No admin token available")
            return False
        
        all_success = True
        
        # Create a test user for testing enhanced admin features
        test_user_data = {
            "username": f"admin_test_{datetime.now().strftime('%H%M%S')}",
            "email": f"admin_test_{datetime.now().strftime('%H%M%S')}@example.com",
            "password": "TestPass123!",
            "phone": "+1234567890",
            "full_name": "Admin Test User",
            "role": "provider",
            "district": "Test District"
        }
        
        success, response = self.run_test(
            "Create Test User for Admin Testing",
            "POST",
            "admin/create-user",
            200,
            data=test_user_data,
            token=self.tokens['admin']
        )
        
        if not success:
            print("❌ Could not create test user for admin testing")
            return False
        
        test_user_id = response.get('id')
        print(f"   ✅ Created test user ID: {test_user_id}")
        
        # Test 1: GET /api/admin/users/{user_id}/password endpoint for password viewing
        print("\n1️⃣ Testing Admin Password Viewing Endpoint")
        print("-" * 50)
        
        success, response = self.run_test(
            "Get User Password (Admin Only)",
            "GET",
            f"admin/users/{test_user_id}/password",
            200,
            token=self.tokens['admin']
        )
        
        if success:
            print("   ✅ Admin can view user passwords")
            if 'password' in response and 'username' in response:
                print(f"   Password: {response['password']}")
                print(f"   Username: {response['username']}")
            else:
                print("   ❌ Password response missing required fields")
                all_success = False
        else:
            print("   ❌ Admin cannot view user passwords")
            all_success = False
        
        # Test non-admin access to password endpoint (should fail)
        if 'provider' in self.tokens:
            success, response = self.run_test(
                "Get User Password (Provider - Should Fail)",
                "GET",
                f"admin/users/{test_user_id}/password",
                403,
                token=self.tokens['provider']
            )
            
            if success:
                print("   ✅ Provider correctly denied password access")
            else:
                print("   ❌ Provider unexpectedly allowed password access")
                all_success = False
        
        # Test 2: Updated DELETE /api/users/{user_id} endpoint for soft deletion
        print("\n2️⃣ Testing Soft Deletion (Mark Inactive)")
        print("-" * 50)
        
        success, response = self.run_test(
            "Soft Delete User (Admin)",
            "DELETE",
            f"users/{test_user_id}",
            200,
            token=self.tokens['admin']
        )
        
        if success:
            print("   ✅ Admin can soft delete users")
            print(f"   Response: {response.get('message', 'No message')}")
            
            # Verify user is marked as inactive, not permanently deleted
            success, users_response = self.run_test(
                "Verify User Still Exists (Soft Deleted)",
                "GET",
                "users",
                200,
                token=self.tokens['admin']
            )
            
            if success:
                # Check if user still exists but is inactive
                user_found = False
                for user in users_response:
                    if user.get('id') == test_user_id:
                        user_found = True
                        if user.get('is_active') == False:
                            print("   ✅ User marked as inactive (soft deleted)")
                        else:
                            print("   ❌ User not marked as inactive")
                            all_success = False
                        break
                
                if not user_found:
                    print("   ❌ User completely removed (should be soft deleted)")
                    all_success = False
            else:
                print("   ❌ Could not verify soft deletion")
                all_success = False
        else:
            print("   ❌ Admin cannot soft delete users")
            all_success = False
        
        # Test 3: New DELETE /api/admin/users/{user_id}/permanent endpoint
        print("\n3️⃣ Testing Permanent Deletion Endpoint")
        print("-" * 50)
        
        # Create another test user for permanent deletion
        test_user_data2 = {
            "username": f"perm_test_{datetime.now().strftime('%H%M%S')}",
            "email": f"perm_test_{datetime.now().strftime('%H%M%S')}@example.com",
            "password": "TestPass123!",
            "phone": "+1234567890",
            "full_name": "Permanent Delete Test User",
            "role": "provider",
            "district": "Test District"
        }
        
        success, response = self.run_test(
            "Create User for Permanent Deletion Test",
            "POST",
            "admin/create-user",
            200,
            data=test_user_data2,
            token=self.tokens['admin']
        )
        
        if success:
            perm_test_user_id = response.get('id')
            
            # Test permanent deletion
            success, response = self.run_test(
                "Permanent Delete User (Admin Only)",
                "DELETE",
                f"admin/users/{perm_test_user_id}/permanent",
                200,
                token=self.tokens['admin']
            )
            
            if success:
                print("   ✅ Admin can permanently delete users")
                print(f"   Response: {response.get('message', 'No message')}")
                
                # Verify user is completely removed
                success, users_response = self.run_test(
                    "Verify User Permanently Deleted",
                    "GET",
                    "users",
                    200,
                    token=self.tokens['admin']
                )
                
                if success:
                    user_found = any(user.get('id') == perm_test_user_id for user in users_response)
                    if not user_found:
                        print("   ✅ User permanently deleted (not found in database)")
                    else:
                        print("   ❌ User still exists after permanent deletion")
                        all_success = False
            else:
                print("   ❌ Admin cannot permanently delete users")
                all_success = False
        
        # Test non-admin access to permanent deletion (should fail)
        if 'doctor' in self.tokens:
            success, response = self.run_test(
                "Permanent Delete (Doctor - Should Fail)",
                "DELETE",
                f"admin/users/{test_user_id}/permanent",
                403,
                token=self.tokens['doctor']
            )
            
            if success:
                print("   ✅ Doctor correctly denied permanent deletion access")
            else:
                print("   ❌ Doctor unexpectedly allowed permanent deletion access")
                all_success = False
        
        # Test 4: Verify proper admin-only access control
        print("\n4️⃣ Testing Admin-Only Access Control")
        print("-" * 50)
        
        # Test all new endpoints with non-admin users
        non_admin_tests = [
            ("provider", "Provider"),
            ("doctor", "Doctor")
        ]
        
        for role, role_name in non_admin_tests:
            if role in self.tokens:
                # Test password viewing
                success, response = self.run_test(
                    f"Password Access ({role_name} - Should Fail)",
                    "GET",
                    f"admin/users/{test_user_id}/password",
                    403,
                    token=self.tokens[role]
                )
                
                if success:
                    print(f"   ✅ {role_name} correctly denied password access")
                else:
                    print(f"   ❌ {role_name} unexpectedly allowed password access")
                    all_success = False
                
                # Test permanent deletion
                success, response = self.run_test(
                    f"Permanent Delete ({role_name} - Should Fail)",
                    "DELETE",
                    f"admin/users/{test_user_id}/permanent",
                    403,
                    token=self.tokens[role]
                )
                
                if success:
                    print(f"   ✅ {role_name} correctly denied permanent deletion access")
                else:
                    print(f"   ❌ {role_name} unexpectedly allowed permanent deletion access")
                    all_success = False
        
        return all_success

    def test_doctor_appointment_visibility(self):
        """🎯 DOCTOR APPOINTMENT VISIBILITY TESTING - Review Request Feature"""
        print("\n🎯 DOCTOR APPOINTMENT VISIBILITY TESTING")
        print("=" * 70)
        
        if 'doctor' not in self.tokens or 'provider' not in self.tokens:
            print("❌ Missing doctor or provider tokens")
            return False
        
        all_success = True
        
        # Test 1: Doctor can see ALL appointments (including pending ones)
        print("\n1️⃣ Testing Doctor Can See ALL Appointments")
        print("-" * 50)
        
        success, response = self.run_test(
            "Get All Appointments (Doctor)",
            "GET",
            "appointments",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            doctor_appointments = response
            print(f"   ✅ Doctor can see {len(doctor_appointments)} total appointments")
            
            # Count pending appointments
            pending_count = sum(1 for apt in doctor_appointments if apt.get('status') == 'pending')
            accepted_count = sum(1 for apt in doctor_appointments if apt.get('status') == 'accepted')
            other_count = len(doctor_appointments) - pending_count - accepted_count
            
            print(f"   📊 Appointment breakdown:")
            print(f"      - Pending: {pending_count}")
            print(f"      - Accepted: {accepted_count}")
            print(f"      - Other statuses: {other_count}")
            
            if pending_count > 0:
                print("   ✅ Doctor can see pending appointments")
            else:
                print("   ⚠️  No pending appointments found (may be expected)")
        else:
            print("   ❌ Doctor cannot see appointments")
            all_success = False
        
        # Test 2: Create a new appointment and verify doctor sees it immediately
        print("\n2️⃣ Testing Immediate Visibility of New Appointments")
        print("-" * 50)
        
        # Create appointment as provider
        appointment_data = {
            "patient": {
                "name": "Dr Visibility Test Patient",
                "age": 42,
                "gender": "Female",
                "vitals": {
                    "blood_pressure": "130/85",
                    "heart_rate": 78,
                    "temperature": 99.1,
                    "oxygen_saturation": 98
                },
                "consultation_reason": "Testing doctor visibility of new appointments"
            },
            "appointment_type": "emergency",
            "consultation_notes": "Created to test doctor appointment visibility"
        }
        
        success, response = self.run_test(
            "Create Test Appointment (Provider)",
            "POST",
            "appointments",
            200,
            data=appointment_data,
            token=self.tokens['provider']
        )
        
        if success:
            new_appointment_id = response.get('id')
            print(f"   ✅ Created test appointment ID: {new_appointment_id}")
            
            # Immediately check if doctor can see the new appointment
            success, response = self.run_test(
                "Doctor Sees New Appointment Immediately",
                "GET",
                "appointments",
                200,
                token=self.tokens['doctor']
            )
            
            if success:
                doctor_appointments = response
                new_appointment_found = any(apt.get('id') == new_appointment_id for apt in doctor_appointments)
                
                if new_appointment_found:
                    print("   ✅ Doctor can see new appointment immediately")
                else:
                    print("   ❌ Doctor cannot see new appointment immediately")
                    all_success = False
            else:
                print("   ❌ Doctor cannot retrieve appointments")
                all_success = False
        else:
            print("   ❌ Could not create test appointment")
            all_success = False
        
        # Test 3: Test appointment acceptance workflow
        print("\n3️⃣ Testing Appointment Acceptance Workflow")
        print("-" * 50)
        
        if 'new_appointment_id' in locals():
            # Doctor accepts the appointment
            update_data = {
                "status": "accepted",
                "doctor_id": self.users['doctor']['id'],
                "doctor_notes": "Appointment accepted by doctor for testing"
            }
            
            success, response = self.run_test(
                "Doctor Accepts Appointment",
                "PUT",
                f"appointments/{new_appointment_id}",
                200,
                data=update_data,
                token=self.tokens['doctor']
            )
            
            if success:
                print("   ✅ Doctor can accept appointments")
                
                # Verify status changed to accepted
                success, response = self.run_test(
                    "Verify Appointment Status Changed",
                    "GET",
                    f"appointments/{new_appointment_id}",
                    200,
                    token=self.tokens['doctor']
                )
                
                if success:
                    appointment_status = response.get('status')
                    assigned_doctor_id = response.get('doctor_id')
                    
                    if appointment_status == 'accepted':
                        print("   ✅ Appointment status changed to accepted")
                    else:
                        print(f"   ❌ Appointment status not changed (current: {appointment_status})")
                        all_success = False
                    
                    if assigned_doctor_id == self.users['doctor']['id']:
                        print("   ✅ Doctor correctly assigned to appointment")
                    else:
                        print("   ❌ Doctor not correctly assigned to appointment")
                        all_success = False
                else:
                    print("   ❌ Could not verify appointment status")
                    all_success = False
            else:
                print("   ❌ Doctor cannot accept appointments")
                all_success = False
        
        # Test 4: Verify call initiation is available after acceptance
        print("\n4️⃣ Testing Call Initiation After Acceptance")
        print("-" * 50)
        
        if 'new_appointment_id' in locals():
            # Test video call session creation for accepted appointment
            success, response = self.run_test(
                "Create Video Call Session (Accepted Appointment)",
                "GET",
                f"video-call/session/{new_appointment_id}",
                200,
                token=self.tokens['doctor']
            )
            
            if success:
                jitsi_url = response.get('jitsi_url')
                room_name = response.get('room_name')
                
                if jitsi_url and room_name:
                    print("   ✅ Video call session available after acceptance")
                    print(f"   Jitsi Room: {room_name}")
                    print(f"   Jitsi URL: {jitsi_url}")
                else:
                    print("   ❌ Video call session missing required fields")
                    all_success = False
            else:
                print("   ❌ Video call session not available after acceptance")
                all_success = False
        
        return all_success

    def test_provider_appointment_visibility(self):
        """🎯 PROVIDER APPOINTMENT VISIBILITY TESTING - Review Request Feature"""
        print("\n🎯 PROVIDER APPOINTMENT VISIBILITY TESTING")
        print("=" * 70)
        
        if 'provider' not in self.tokens:
            print("❌ No provider token available")
            return False
        
        all_success = True
        
        # Test 1: Provider can see ONLY their own created appointments
        print("\n1️⃣ Testing Provider Sees Only Own Appointments")
        print("-" * 50)
        
        success, response = self.run_test(
            "Get Appointments (Provider - Own Only)",
            "GET",
            "appointments",
            200,
            token=self.tokens['provider']
        )
        
        if success:
            provider_appointments = response
            provider_id = self.users['provider']['id']
            
            print(f"   ✅ Provider can see {len(provider_appointments)} appointments")
            
            # Verify all appointments belong to this provider (provider_id filtering)
            all_own_appointments = True
            for apt in provider_appointments:
                if apt.get('provider_id') != provider_id:
                    print(f"   ❌ Provider seeing appointment not owned by them: {apt.get('id')}")
                    print(f"      Appointment provider_id: {apt.get('provider_id')}")
                    print(f"      Current provider_id: {provider_id}")
                    all_own_appointments = False
                    all_success = False
            
            if all_own_appointments:
                print("   ✅ Provider only sees own appointments (provider_id filtering working)")
            
        else:
            print("   ❌ Provider cannot see appointments")
            all_success = False
        
        # Test 2: Test appointment creation by provider
        print("\n2️⃣ Testing Appointment Creation by Provider")
        print("-" * 50)
        
        appointment_data = {
            "patient": {
                "name": "Provider Visibility Test Patient",
                "age": 38,
                "gender": "Male",
                "vitals": {
                    "blood_pressure": "125/80",
                    "heart_rate": 75,
                    "temperature": 98.8,
                    "oxygen_saturation": 99
                },
                "consultation_reason": "Testing provider appointment creation and visibility"
            },
            "appointment_type": "non_emergency",
            "consultation_notes": "Created to test provider appointment visibility"
        }
        
        success, response = self.run_test(
            "Create Appointment (Provider)",
            "POST",
            "appointments",
            200,
            data=appointment_data,
            token=self.tokens['provider']
        )
        
        if success:
            new_provider_appointment_id = response.get('id')
            print(f"   ✅ Provider created appointment ID: {new_provider_appointment_id}")
            
            # Verify the appointment has correct provider_id
            if response.get('provider_id') == self.users['provider']['id']:
                print("   ✅ Appointment correctly assigned to provider")
            else:
                print("   ❌ Appointment not correctly assigned to provider")
                all_success = False
        else:
            print("   ❌ Provider cannot create appointments")
            all_success = False
        
        # Test 3: Verify new appointments appear immediately in provider dashboard
        print("\n3️⃣ Testing Immediate Visibility in Provider Dashboard")
        print("-" * 50)
        
        if 'new_provider_appointment_id' in locals():
            success, response = self.run_test(
                "Provider Sees New Appointment Immediately",
                "GET",
                "appointments",
                200,
                token=self.tokens['provider']
            )
            
            if success:
                provider_appointments = response
                new_appointment_found = any(apt.get('id') == new_provider_appointment_id for apt in provider_appointments)
                
                if new_appointment_found:
                    print("   ✅ New appointment appears immediately in provider dashboard")
                else:
                    print("   ❌ New appointment not immediately visible in provider dashboard")
                    all_success = False
            else:
                print("   ❌ Provider cannot retrieve appointments")
                all_success = False
        
        # Test 4: Confirm proper role-based filtering is working
        print("\n4️⃣ Testing Role-Based Filtering")
        print("-" * 50)
        
        # Compare provider appointments vs doctor appointments vs admin appointments
        provider_count = 0
        doctor_count = 0
        admin_count = 0
        
        # Get provider appointment count
        success, response = self.run_test(
            "Count Provider Appointments",
            "GET",
            "appointments",
            200,
            token=self.tokens['provider']
        )
        
        if success:
            provider_count = len(response)
            print(f"   Provider sees: {provider_count} appointments")
        
        # Get doctor appointment count
        if 'doctor' in self.tokens:
            success, response = self.run_test(
                "Count Doctor Appointments",
                "GET",
                "appointments",
                200,
                token=self.tokens['doctor']
            )
            
            if success:
                doctor_count = len(response)
                print(f"   Doctor sees: {doctor_count} appointments")
        
        # Get admin appointment count
        if 'admin' in self.tokens:
            success, response = self.run_test(
                "Count Admin Appointments",
                "GET",
                "appointments",
                200,
                token=self.tokens['admin']
            )
            
            if success:
                admin_count = len(response)
                print(f"   Admin sees: {admin_count} appointments")
        
        # Verify filtering logic
        if doctor_count >= provider_count and admin_count >= provider_count:
            print("   ✅ Role-based filtering working correctly:")
            print("      - Provider sees only own appointments (filtered)")
            print("      - Doctor sees all appointments (no filtering)")
            print("      - Admin sees all appointments (no filtering)")
        else:
            print("   ❌ Role-based filtering may not be working correctly")
            print(f"      Provider: {provider_count}, Doctor: {doctor_count}, Admin: {admin_count}")
            all_success = False
        
        return all_success

    def test_role_based_access_verification(self):
        """🎯 ROLE-BASED ACCESS VERIFICATION - Review Request Feature"""
        print("\n🎯 ROLE-BASED ACCESS VERIFICATION")
        print("=" * 70)
        
        all_success = True
        
        # Test 1: Confirm doctors see ALL appointments (no filtering)
        print("\n1️⃣ Testing Doctor Access - ALL Appointments")
        print("-" * 50)
        
        if 'doctor' in self.tokens:
            success, response = self.run_test(
                "Doctor Gets All Appointments",
                "GET",
                "appointments",
                200,
                token=self.tokens['doctor']
            )
            
            if success:
                doctor_appointments = response
                print(f"   ✅ Doctor can access {len(doctor_appointments)} appointments")
                
                # Check if doctor sees appointments from different providers
                provider_ids = set()
                for apt in doctor_appointments:
                    if apt.get('provider_id'):
                        provider_ids.add(apt.get('provider_id'))
                
                if len(provider_ids) > 1:
                    print(f"   ✅ Doctor sees appointments from {len(provider_ids)} different providers")
                    print("   ✅ No filtering applied for doctors")
                elif len(provider_ids) == 1:
                    print("   ⚠️  Doctor sees appointments from only 1 provider (may be expected)")
                else:
                    print("   ⚠️  No appointments with provider_id found")
            else:
                print("   ❌ Doctor cannot access appointments")
                all_success = False
        
        # Test 2: Confirm providers see only own appointments (provider_id filtering)
        print("\n2️⃣ Testing Provider Access - Own Appointments Only")
        print("-" * 50)
        
        if 'provider' in self.tokens:
            success, response = self.run_test(
                "Provider Gets Own Appointments",
                "GET",
                "appointments",
                200,
                token=self.tokens['provider']
            )
            
            if success:
                provider_appointments = response
                provider_id = self.users['provider']['id']
                
                print(f"   ✅ Provider can access {len(provider_appointments)} appointments")
                
                # Verify all appointments belong to this provider
                all_own = True
                for apt in provider_appointments:
                    if apt.get('provider_id') != provider_id:
                        all_own = False
                        break
                
                if all_own:
                    print("   ✅ Provider sees only own appointments (provider_id filtering working)")
                else:
                    print("   ❌ Provider sees appointments from other providers")
                    all_success = False
            else:
                print("   ❌ Provider cannot access appointments")
                all_success = False
        
        # Test 3: Confirm admins see ALL appointments
        print("\n3️⃣ Testing Admin Access - ALL Appointments")
        print("-" * 50)
        
        if 'admin' in self.tokens:
            success, response = self.run_test(
                "Admin Gets All Appointments",
                "GET",
                "appointments",
                200,
                token=self.tokens['admin']
            )
            
            if success:
                admin_appointments = response
                print(f"   ✅ Admin can access {len(admin_appointments)} appointments")
                
                # Check if admin sees appointments from different providers
                provider_ids = set()
                for apt in admin_appointments:
                    if apt.get('provider_id'):
                        provider_ids.add(apt.get('provider_id'))
                
                if len(provider_ids) > 1:
                    print(f"   ✅ Admin sees appointments from {len(provider_ids)} different providers")
                    print("   ✅ No filtering applied for admins")
                elif len(provider_ids) == 1:
                    print("   ⚠️  Admin sees appointments from only 1 provider (may be expected)")
                else:
                    print("   ⚠️  No appointments with provider_id found")
            else:
                print("   ❌ Admin cannot access appointments")
                all_success = False
        
        # Test 4: Test unauthorized access to admin-only endpoints
        print("\n4️⃣ Testing Unauthorized Access to Admin-Only Endpoints")
        print("-" * 50)
        
        # Create a test user for admin endpoint testing
        if 'admin' in self.tokens:
            test_user_data = {
                "username": f"access_test_{datetime.now().strftime('%H%M%S')}",
                "email": f"access_test_{datetime.now().strftime('%H%M%S')}@example.com",
                "password": "TestPass123!",
                "phone": "+1234567890",
                "full_name": "Access Test User",
                "role": "provider",
                "district": "Test District"
            }
            
            success, response = self.run_test(
                "Create Test User for Access Testing",
                "POST",
                "admin/create-user",
                200,
                data=test_user_data,
                token=self.tokens['admin']
            )
            
            if success:
                access_test_user_id = response.get('id')
                
                # Test unauthorized access to admin endpoints
                unauthorized_tests = [
                    ("provider", "Provider", "users", "GET"),
                    ("doctor", "Doctor", "users", "GET"),
                    ("provider", "Provider", f"admin/users/{access_test_user_id}/password", "GET"),
                    ("doctor", "Doctor", f"admin/users/{access_test_user_id}/password", "GET"),
                    ("provider", "Provider", f"admin/users/{access_test_user_id}/permanent", "DELETE"),
                    ("doctor", "Doctor", f"admin/users/{access_test_user_id}/permanent", "DELETE"),
                ]
                
                for role, role_name, endpoint, method in unauthorized_tests:
                    if role in self.tokens:
                        success, response = self.run_test(
                            f"Unauthorized {method} {endpoint} ({role_name} - Should Fail)",
                            method,
                            endpoint,
                            403,
                            token=self.tokens[role]
                        )
                        
                        if success:
                            print(f"   ✅ {role_name} correctly denied access to {endpoint}")
                        else:
                            print(f"   ❌ {role_name} unexpectedly allowed access to {endpoint}")
                            all_success = False
                
                # Cleanup test user
                self.run_test(
                    "Cleanup Access Test User",
                    "DELETE",
                    f"admin/users/{access_test_user_id}/permanent",
                    200,
                    token=self.tokens['admin']
                )
        
        return all_success

    def run_enhanced_features_tests(self):
        """Run all enhanced features tests as requested in review"""
        print("🎯 ENHANCED FEATURES TESTING - REVIEW REQUEST")
        print("=" * 80)
        print("Testing enhanced functionality as requested:")
        print("1. Enhanced Admin Permissions Testing")
        print("2. Doctor Appointment Visibility Testing")
        print("3. Provider Appointment Visibility Testing")
        print("4. Role-Based Access Verification")
        print("=" * 80)
        
        # First login to get tokens
        if not self.test_login_all_roles():
            print("❌ Login failed - aborting tests")
            return False
        
        # Run all enhanced feature tests
        results = []
        
        print("\n" + "🎯" * 20 + " ENHANCED FEATURES TESTING " + "🎯" * 20)
        
        results.append(self.test_enhanced_admin_permissions())
        results.append(self.test_doctor_appointment_visibility())
        results.append(self.test_provider_appointment_visibility())
        results.append(self.test_role_based_access_verification())
        
        # Final summary
        print("\n" + "=" * 80)
        print("🎯 ENHANCED FEATURES TESTING SUMMARY")
        print("=" * 80)
        print(f"Total Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        all_passed = all(results)
        
        if all_passed:
            print("🎉 ALL ENHANCED FEATURES TESTS PASSED!")
            print("✅ Enhanced Admin Permissions working correctly")
            print("✅ Doctor Appointment Visibility working correctly")
            print("✅ Provider Appointment Visibility working correctly")
            print("✅ Role-Based Access Verification working correctly")
        else:
            print("❌ SOME ENHANCED FEATURES TESTS FAILED!")
            print("⚠️  Review the detailed test results above")
        
        return all_passed

if __name__ == "__main__":
    # Run the enhanced features test as requested in review
    tester = EnhancedFeaturesAPITester()
    
    result = tester.run_enhanced_features_tests()
    
    if result:
        print("\n🎉 ENHANCED FEATURES TESTING COMPLETED SUCCESSFULLY!")
        print("✅ All enhanced functionality working as expected")
        sys.exit(0)
    else:
        print("\n❌ ENHANCED FEATURES TESTING FAILED!")
        print("⚠️  Some enhanced functionality needs attention")
        sys.exit(1)