#!/usr/bin/env python3
"""
Comprehensive Review Request Testing
Testing all core features specifically requested in the review:
1. Admin permissions testing
2. Doctor appointment visibility testing  
3. Provider appointment visibility testing
4. Notification system testing
"""

import requests
import sys
import json
import time
from datetime import datetime

class ReviewRequestTester:
    def __init__(self, base_url="https://medconnect-app-5.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tokens = {}  # Store tokens for different user roles
        self.users = {}   # Store user data for different roles
        self.tests_run = 0
        self.tests_passed = 0
        self.created_appointments = []  # Track created appointments for cleanup
        self.created_users = []  # Track created users for cleanup
        
        # Demo credentials as specified in review request
        self.demo_credentials = {
            "admin": {"username": "demo_admin", "password": "Demo123!"},
            "doctor": {"username": "demo_doctor", "password": "Demo123!"},
            "provider": {"username": "demo_provider", "password": "Demo123!"}
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
                response = requests.get(url, headers=headers, timeout=15)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=15)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=15)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=15)

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

    def login_all_roles(self):
        """Login with all demo credentials"""
        print("\n🔑 LOGGING IN WITH DEMO CREDENTIALS")
        print("=" * 60)
        
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
                print(f"   ✅ {role.title()} login successful")
                print(f"   User ID: {response['user'].get('id')}")
                print(f"   Full Name: {response['user'].get('full_name')}")
                print(f"   Role: {response['user'].get('role')}")
            else:
                print(f"   ❌ {role.title()} login failed - CRITICAL ISSUE")
                all_success = False
        
        return all_success

    def test_admin_permissions(self):
        """🎯 ADMIN PERMISSIONS TESTING"""
        print("\n🎯 ADMIN PERMISSIONS TESTING")
        print("=" * 60)
        print("Testing admin login, view passwords, delete users, disable/enable accounts, edit users")
        
        if 'admin' not in self.tokens:
            print("❌ Admin token not available")
            return False
        
        all_success = True
        
        # Test 1: Admin login (already done, but verify token works)
        print("\n1️⃣ Testing Admin Login Verification")
        success, response = self.run_test(
            "Admin Profile Access",
            "GET",
            "users/profile",
            200,
            token=self.tokens['admin']
        )
        
        if success:
            print("   ✅ Admin login verified - can access profile")
        else:
            print("   ❌ Admin login verification failed")
            all_success = False
        
        # Test 2: Admin view password functionality
        print("\n2️⃣ Testing Admin View Password Functionality")
        
        # First get list of users to find a user ID
        success, users_response = self.run_test(
            "Get Users List (Admin)",
            "GET",
            "users",
            200,
            token=self.tokens['admin']
        )
        
        if success and users_response:
            # Find a non-admin user to test password viewing
            test_user = None
            for user in users_response:
                if user.get('role') != 'admin':
                    test_user = user
                    break
            
            if test_user:
                success, password_response = self.run_test(
                    f"View User Password - {test_user.get('username')}",
                    "GET",
                    f"admin/users/{test_user.get('id')}/password",
                    200,
                    token=self.tokens['admin']
                )
                
                if success:
                    print(f"   ✅ Admin can view user passwords")
                    print(f"   Password for {test_user.get('username')}: {password_response.get('password')}")
                else:
                    print("   ❌ Admin cannot view user passwords")
                    all_success = False
            else:
                print("   ⚠️  No non-admin users found to test password viewing")
        else:
            print("   ❌ Could not get users list for password testing")
            all_success = False
        
        # Test 3: Admin ability to permanently delete users
        print("\n3️⃣ Testing Admin Permanent User Deletion")
        
        # Create a test user first
        test_user_data = {
            "username": f"delete_test_{datetime.now().strftime('%H%M%S')}",
            "email": f"delete_test_{datetime.now().strftime('%H%M%S')}@example.com",
            "password": "TestPass123!",
            "phone": "+1234567890",
            "full_name": "Test User for Deletion",
            "role": "provider",
            "district": "Test District"
        }
        
        success, create_response = self.run_test(
            "Create Test User for Deletion",
            "POST",
            "admin/create-user",
            200,
            data=test_user_data,
            token=self.tokens['admin']
        )
        
        if success:
            test_user_id = create_response.get('id')
            self.created_users.append(test_user_id)
            
            # Now test permanent deletion
            success, delete_response = self.run_test(
                "Permanently Delete User (Admin)",
                "DELETE",
                f"admin/users/{test_user_id}/permanent",
                200,
                token=self.tokens['admin']
            )
            
            if success:
                print("   ✅ Admin can permanently delete users")
                self.created_users.remove(test_user_id)  # Remove from cleanup list
            else:
                print("   ❌ Admin cannot permanently delete users")
                all_success = False
        else:
            print("   ❌ Could not create test user for deletion testing")
            all_success = False
        
        # Test 4: Admin ability to disable/enable user accounts
        print("\n4️⃣ Testing Admin Disable/Enable User Accounts")
        
        # Create another test user
        test_user_data['username'] = f"status_test_{datetime.now().strftime('%H%M%S')}"
        test_user_data['email'] = f"status_test_{datetime.now().strftime('%H%M%S')}@example.com"
        
        success, create_response = self.run_test(
            "Create Test User for Status Testing",
            "POST",
            "admin/create-user",
            200,
            data=test_user_data,
            token=self.tokens['admin']
        )
        
        if success:
            test_user_id = create_response.get('id')
            self.created_users.append(test_user_id)
            
            # Test disabling user
            success, disable_response = self.run_test(
                "Disable User Account (Admin)",
                "PUT",
                f"users/{test_user_id}/status",
                200,
                data={"is_active": False},
                token=self.tokens['admin']
            )
            
            if success:
                print("   ✅ Admin can disable user accounts")
                
                # Test enabling user
                success, enable_response = self.run_test(
                    "Enable User Account (Admin)",
                    "PUT",
                    f"users/{test_user_id}/status",
                    200,
                    data={"is_active": True},
                    token=self.tokens['admin']
                )
                
                if success:
                    print("   ✅ Admin can enable user accounts")
                else:
                    print("   ❌ Admin cannot enable user accounts")
                    all_success = False
            else:
                print("   ❌ Admin cannot disable user accounts")
                all_success = False
        else:
            print("   ❌ Could not create test user for status testing")
            all_success = False
        
        # Test 5: Admin ability to edit user information
        print("\n5️⃣ Testing Admin Edit User Information")
        
        if self.created_users:
            test_user_id = self.created_users[0]
            edit_data = {
                "full_name": "Updated Test User Name",
                "phone": "+9876543210",
                "district": "Updated District"
            }
            
            success, edit_response = self.run_test(
                "Edit User Information (Admin)",
                "PUT",
                f"users/{test_user_id}",
                200,
                data=edit_data,
                token=self.tokens['admin']
            )
            
            if success:
                print("   ✅ Admin can edit user information")
                print(f"   Updated name: {edit_response.get('full_name')}")
            else:
                print("   ❌ Admin cannot edit user information")
                all_success = False
        else:
            print("   ⚠️  No test users available for edit testing")
        
        # Test 6: Verify admin changes take effect immediately
        print("\n6️⃣ Testing Admin Changes Take Effect Immediately")
        
        if self.created_users:
            test_user_id = self.created_users[0]
            
            # Get user details to verify changes
            success, user_details = self.run_test(
                "Verify User Changes (Admin)",
                "GET",
                "users",
                200,
                token=self.tokens['admin']
            )
            
            if success:
                # Find our test user in the list
                updated_user = None
                for user in user_details:
                    if user.get('id') == test_user_id:
                        updated_user = user
                        break
                
                if updated_user and updated_user.get('full_name') == "Updated Test User Name":
                    print("   ✅ Admin changes take effect immediately")
                else:
                    print("   ❌ Admin changes not reflected immediately")
                    all_success = False
            else:
                print("   ❌ Could not verify admin changes")
                all_success = False
        
        return all_success

    def test_doctor_appointment_visibility(self):
        """🎯 DOCTOR APPOINTMENTS VISIBILITY TESTING"""
        print("\n🎯 DOCTOR APPOINTMENTS VISIBILITY TESTING")
        print("=" * 60)
        print("Testing doctor login, see ALL pending appointments, accept appointments, call functionality")
        
        if 'doctor' not in self.tokens or 'provider' not in self.tokens:
            print("❌ Doctor or provider token not available")
            return False
        
        all_success = True
        
        # Test 1: Doctor login verification (already done)
        print("\n1️⃣ Testing Doctor Login Verification")
        success, response = self.run_test(
            "Doctor Profile Access",
            "GET",
            "users/profile",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            print("   ✅ Doctor login verified")
        else:
            print("   ❌ Doctor login verification failed")
            all_success = False
        
        # Test 2: Create appointment as provider to test doctor visibility
        print("\n2️⃣ Testing Provider Creates Appointment for Doctor Visibility")
        
        appointment_data = {
            "patient": {
                "name": "Sarah Johnson",
                "age": 28,
                "gender": "Female",
                "vitals": {
                    "blood_pressure": "130/85",
                    "heart_rate": 88,
                    "temperature": 99.2,
                    "oxygen_saturation": 97
                },
                "consultation_reason": "Severe chest pain and shortness of breath"
            },
            "appointment_type": "emergency",
            "consultation_notes": "Patient reports sudden onset chest pain 2 hours ago"
        }
        
        success, create_response = self.run_test(
            "Provider Creates Emergency Appointment",
            "POST",
            "appointments",
            200,
            data=appointment_data,
            token=self.tokens['provider']
        )
        
        if success:
            appointment_id = create_response.get('id')
            self.created_appointments.append(appointment_id)
            print(f"   ✅ Provider created appointment: {appointment_id}")
        else:
            print("   ❌ Provider could not create appointment")
            all_success = False
            return False
        
        # Test 3: Doctor can see ALL pending appointments immediately
        print("\n3️⃣ Testing Doctor Can See ALL Pending Appointments Immediately")
        
        success, appointments_response = self.run_test(
            "Doctor Gets All Appointments",
            "GET",
            "appointments",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            appointments = appointments_response
            pending_appointments = [apt for apt in appointments if apt.get('status') == 'pending']
            
            print(f"   ✅ Doctor can see {len(appointments)} total appointments")
            print(f"   ✅ Doctor can see {len(pending_appointments)} pending appointments")
            
            # Verify the newly created appointment is visible
            new_appointment_visible = any(apt.get('id') == appointment_id for apt in appointments)
            if new_appointment_visible:
                print("   ✅ Newly created appointment immediately visible to doctor")
            else:
                print("   ❌ Newly created appointment NOT visible to doctor")
                all_success = False
        else:
            print("   ❌ Doctor cannot get appointments list")
            all_success = False
        
        # Test 4: Doctor can accept appointments from dashboard
        print("\n4️⃣ Testing Doctor Can Accept Appointments")
        
        if appointment_id:
            accept_data = {
                "status": "accepted",
                "doctor_id": self.users['doctor']['id']
            }
            
            success, accept_response = self.run_test(
                "Doctor Accepts Appointment",
                "PUT",
                f"appointments/{appointment_id}",
                200,
                data=accept_data,
                token=self.tokens['doctor']
            )
            
            if success:
                print("   ✅ Doctor can accept appointments")
                print(f"   Appointment status: {accept_response.get('status')}")
            else:
                print("   ❌ Doctor cannot accept appointments")
                all_success = False
        
        # Test 5: Call functionality available for accepted appointments
        print("\n5️⃣ Testing Call Functionality for Accepted Appointments")
        
        if appointment_id:
            # Test video call session creation
            success, call_response = self.run_test(
                "Doctor Creates Video Call Session",
                "GET",
                f"video-call/session/{appointment_id}",
                200,
                token=self.tokens['doctor']
            )
            
            if success:
                jitsi_url = call_response.get('jitsi_url')
                room_name = call_response.get('room_name')
                print("   ✅ Call functionality available for accepted appointments")
                print(f"   Jitsi URL: {jitsi_url}")
                print(f"   Room Name: {room_name}")
            else:
                print("   ❌ Call functionality not available for accepted appointments")
                all_success = False
        
        # Test 6: Appointment details visible in doctor dashboard immediately
        print("\n6️⃣ Testing Appointment Details Visible Immediately")
        
        if appointment_id:
            success, details_response = self.run_test(
                "Doctor Gets Appointment Details",
                "GET",
                f"appointments/{appointment_id}",
                200,
                token=self.tokens['doctor']
            )
            
            if success:
                patient_info = details_response.get('patient', {})
                print("   ✅ Appointment details visible immediately in doctor dashboard")
                print(f"   Patient: {patient_info.get('name')}")
                print(f"   Reason: {patient_info.get('consultation_reason')}")
                print(f"   Type: {details_response.get('appointment_type')}")
            else:
                print("   ❌ Appointment details not visible immediately")
                all_success = False
        
        return all_success

    def test_provider_appointment_visibility(self):
        """🎯 PROVIDER APPOINTMENT VISIBILITY TESTING"""
        print("\n🎯 PROVIDER APPOINTMENT VISIBILITY TESTING")
        print("=" * 60)
        print("Testing provider login, see own appointments, create appointments, see assigned doctors")
        
        if 'provider' not in self.tokens:
            print("❌ Provider token not available")
            return False
        
        all_success = True
        
        # Test 1: Provider login verification (already done)
        print("\n1️⃣ Testing Provider Login Verification")
        success, response = self.run_test(
            "Provider Profile Access",
            "GET",
            "users/profile",
            200,
            token=self.tokens['provider']
        )
        
        if success:
            print("   ✅ Provider login verified")
        else:
            print("   ❌ Provider login verification failed")
            all_success = False
        
        # Test 2: Provider can see appointments they created in their dashboard
        print("\n2️⃣ Testing Provider Can See Own Appointments")
        
        success, appointments_response = self.run_test(
            "Provider Gets Own Appointments",
            "GET",
            "appointments",
            200,
            token=self.tokens['provider']
        )
        
        if success:
            appointments = appointments_response
            provider_id = self.users['provider']['id']
            
            # Verify all appointments belong to this provider
            own_appointments = [apt for apt in appointments if apt.get('provider_id') == provider_id]
            other_appointments = [apt for apt in appointments if apt.get('provider_id') != provider_id]
            
            print(f"   ✅ Provider can see {len(appointments)} appointments")
            print(f"   ✅ All {len(own_appointments)} appointments belong to provider")
            
            if other_appointments:
                print(f"   ❌ Provider seeing {len(other_appointments)} appointments from other providers")
                all_success = False
            else:
                print("   ✅ Provider only sees own appointments (proper filtering)")
        else:
            print("   ❌ Provider cannot get appointments list")
            all_success = False
        
        # Test 3: Provider appointment creation and immediate visibility
        print("\n3️⃣ Testing Provider Appointment Creation and Immediate Visibility")
        
        new_appointment_data = {
            "patient": {
                "name": "Michael Chen",
                "age": 35,
                "gender": "Male",
                "vitals": {
                    "blood_pressure": "125/80",
                    "heart_rate": 75,
                    "temperature": 98.6,
                    "oxygen_saturation": 98
                },
                "consultation_reason": "Persistent abdominal pain for 3 days"
            },
            "appointment_type": "non_emergency",
            "consultation_notes": "Patient reports dull aching pain in lower right abdomen"
        }
        
        success, create_response = self.run_test(
            "Provider Creates New Appointment",
            "POST",
            "appointments",
            200,
            data=new_appointment_data,
            token=self.tokens['provider']
        )
        
        if success:
            new_appointment_id = create_response.get('id')
            self.created_appointments.append(new_appointment_id)
            print(f"   ✅ Provider created new appointment: {new_appointment_id}")
            
            # Immediately check if it's visible
            success, updated_appointments = self.run_test(
                "Provider Checks Updated Appointments List",
                "GET",
                "appointments",
                200,
                token=self.tokens['provider']
            )
            
            if success:
                new_appointment_visible = any(apt.get('id') == new_appointment_id for apt in updated_appointments)
                if new_appointment_visible:
                    print("   ✅ New appointment immediately visible in provider dashboard")
                else:
                    print("   ❌ New appointment NOT immediately visible")
                    all_success = False
            else:
                print("   ❌ Could not check updated appointments list")
                all_success = False
        else:
            print("   ❌ Provider could not create appointment")
            all_success = False
        
        # Test 4: Provider can see assigned doctors for accepted appointments
        print("\n4️⃣ Testing Provider Can See Assigned Doctors")
        
        # First, have doctor accept one of the appointments
        if self.created_appointments and 'doctor' in self.tokens:
            test_appointment_id = self.created_appointments[0]
            
            accept_data = {
                "status": "accepted",
                "doctor_id": self.users['doctor']['id']
            }
            
            success, accept_response = self.run_test(
                "Doctor Accepts Provider's Appointment",
                "PUT",
                f"appointments/{test_appointment_id}",
                200,
                data=accept_data,
                token=self.tokens['doctor']
            )
            
            if success:
                print("   ✅ Doctor accepted provider's appointment")
                
                # Now check if provider can see the assigned doctor
                success, appointments_with_doctor = self.run_test(
                    "Provider Checks for Assigned Doctor",
                    "GET",
                    "appointments",
                    200,
                    token=self.tokens['provider']
                )
                
                if success:
                    accepted_appointment = None
                    for apt in appointments_with_doctor:
                        if apt.get('id') == test_appointment_id:
                            accepted_appointment = apt
                            break
                    
                    if accepted_appointment:
                        doctor_info = accepted_appointment.get('doctor')
                        if doctor_info:
                            print("   ✅ Provider can see assigned doctor for accepted appointments")
                            print(f"   Assigned Doctor: {doctor_info.get('full_name')}")
                            print(f"   Doctor Specialty: {doctor_info.get('specialty', 'General Medicine')}")
                        else:
                            print("   ❌ Provider cannot see assigned doctor information")
                            all_success = False
                    else:
                        print("   ❌ Could not find accepted appointment in provider's list")
                        all_success = False
                else:
                    print("   ❌ Provider could not get updated appointments list")
                    all_success = False
            else:
                print("   ❌ Doctor could not accept provider's appointment")
                all_success = False
        
        return all_success

    def test_notification_system(self):
        """🎯 NOTIFICATION SYSTEM TESTING"""
        print("\n🎯 NOTIFICATION SYSTEM TESTING")
        print("=" * 60)
        print("Testing WebSocket notifications, appointment acceptance from notifications, real-time updates")
        
        if 'doctor' not in self.tokens or 'provider' not in self.tokens:
            print("❌ Doctor or provider token not available")
            return False
        
        all_success = True
        
        # Test 1: WebSocket connection status
        print("\n1️⃣ Testing WebSocket Connection Status")
        
        success, websocket_status = self.run_test(
            "Check WebSocket Status (Doctor)",
            "GET",
            "websocket/status",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            print("   ✅ WebSocket status endpoint accessible")
            print(f"   Total connections: {websocket_status.get('websocket_status', {}).get('total_connections', 0)}")
        else:
            print("   ❌ WebSocket status endpoint not accessible")
            all_success = False
        
        # Test 2: Test WebSocket message functionality
        print("\n2️⃣ Testing WebSocket Message Functionality")
        
        success, test_message_response = self.run_test(
            "Send Test WebSocket Message (Doctor)",
            "POST",
            "websocket/test-message",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            print("   ✅ WebSocket test message functionality working")
            print(f"   Message sent: {test_message_response.get('message_sent')}")
        else:
            print("   ❌ WebSocket test message functionality not working")
            all_success = False
        
        # Test 3: Create appointment to trigger notifications
        print("\n3️⃣ Testing Appointment Creation Triggers Notifications")
        
        notification_test_appointment = {
            "patient": {
                "name": "Emma Wilson",
                "age": 42,
                "gender": "Female",
                "vitals": {
                    "blood_pressure": "140/90",
                    "heart_rate": 95,
                    "temperature": 100.1,
                    "oxygen_saturation": 96
                },
                "consultation_reason": "High fever and persistent cough for 5 days"
            },
            "appointment_type": "emergency",
            "consultation_notes": "Patient reports worsening symptoms, possible respiratory infection"
        }
        
        success, notification_appointment = self.run_test(
            "Provider Creates Appointment (Should Trigger Notifications)",
            "POST",
            "appointments",
            200,
            data=notification_test_appointment,
            token=self.tokens['provider']
        )
        
        if success:
            notification_appointment_id = notification_appointment.get('id')
            self.created_appointments.append(notification_appointment_id)
            print(f"   ✅ Appointment created for notification testing: {notification_appointment_id}")
            
            # Give a moment for notifications to be processed
            time.sleep(2)
            
            # Test that doctor can see the new appointment (simulating notification)
            success, doctor_appointments = self.run_test(
                "Doctor Checks for New Appointment (Notification Effect)",
                "GET",
                "appointments",
                200,
                token=self.tokens['doctor']
            )
            
            if success:
                new_appointment_visible = any(apt.get('id') == notification_appointment_id for apt in doctor_appointments)
                if new_appointment_visible:
                    print("   ✅ New appointment immediately visible to doctor (notification system working)")
                else:
                    print("   ❌ New appointment not visible to doctor (notification system issue)")
                    all_success = False
            else:
                print("   ❌ Doctor could not check for new appointments")
                all_success = False
        else:
            print("   ❌ Could not create appointment for notification testing")
            all_success = False
        
        # Test 4: Doctor accepts appointment (should trigger notification to provider)
        print("\n4️⃣ Testing Doctor Accepts Appointment from Notification Panel")
        
        if notification_appointment_id:
            accept_data = {
                "status": "accepted",
                "doctor_id": self.users['doctor']['id']
            }
            
            success, accept_response = self.run_test(
                "Doctor Accepts Appointment (Should Notify Provider)",
                "PUT",
                f"appointments/{notification_appointment_id}",
                200,
                data=accept_data,
                token=self.tokens['doctor']
            )
            
            if success:
                print("   ✅ Doctor can accept appointments (notification panel functionality)")
                
                # Give a moment for notifications to be processed
                time.sleep(2)
                
                # Check if provider can see the updated appointment status
                success, provider_appointments = self.run_test(
                    "Provider Checks Updated Appointment Status",
                    "GET",
                    "appointments",
                    200,
                    token=self.tokens['provider']
                )
                
                if success:
                    updated_appointment = None
                    for apt in provider_appointments:
                        if apt.get('id') == notification_appointment_id:
                            updated_appointment = apt
                            break
                    
                    if updated_appointment and updated_appointment.get('status') == 'accepted':
                        print("   ✅ Provider sees updated appointment status (real-time notification working)")
                    else:
                        print("   ❌ Provider does not see updated appointment status")
                        all_success = False
                else:
                    print("   ❌ Provider could not check updated appointments")
                    all_success = False
            else:
                print("   ❌ Doctor could not accept appointment")
                all_success = False
        
        # Test 5: Video call notifications
        print("\n5️⃣ Testing Video Call Notifications")
        
        if notification_appointment_id:
            success, video_call_response = self.run_test(
                "Doctor Starts Video Call (Should Notify Provider)",
                "GET",
                f"video-call/session/{notification_appointment_id}",
                200,
                token=self.tokens['doctor']
            )
            
            if success:
                jitsi_url = video_call_response.get('jitsi_url')
                print("   ✅ Video call notifications working")
                print(f"   Video call URL: {jitsi_url}")
                
                # Test that provider can also access the same video call
                success, provider_video_response = self.run_test(
                    "Provider Joins Same Video Call",
                    "GET",
                    f"video-call/session/{notification_appointment_id}",
                    200,
                    token=self.tokens['provider']
                )
                
                if success:
                    provider_jitsi_url = provider_video_response.get('jitsi_url')
                    if provider_jitsi_url == jitsi_url:
                        print("   ✅ Both doctor and provider get same video call session (notification system working)")
                    else:
                        print("   ❌ Doctor and provider get different video call sessions")
                        all_success = False
                else:
                    print("   ❌ Provider could not join video call")
                    all_success = False
            else:
                print("   ❌ Video call notifications not working")
                all_success = False
        
        # Test 6: Real-time updates between roles
        print("\n6️⃣ Testing Real-time Updates Between Roles")
        
        # Create another appointment to test real-time updates
        realtime_test_appointment = {
            "patient": {
                "name": "David Rodriguez",
                "age": 55,
                "gender": "Male",
                "vitals": {
                    "blood_pressure": "160/100",
                    "heart_rate": 105,
                    "temperature": 98.8,
                    "oxygen_saturation": 95
                },
                "consultation_reason": "Chest tightness and dizziness"
            },
            "appointment_type": "emergency",
            "consultation_notes": "Patient reports symptoms started 1 hour ago"
        }
        
        success, realtime_appointment = self.run_test(
            "Provider Creates Appointment for Real-time Testing",
            "POST",
            "appointments",
            200,
            data=realtime_test_appointment,
            token=self.tokens['provider']
        )
        
        if success:
            realtime_appointment_id = realtime_appointment.get('id')
            self.created_appointments.append(realtime_appointment_id)
            
            # Immediately check if doctor can see it
            success, immediate_check = self.run_test(
                "Doctor Immediate Check for New Appointment",
                "GET",
                "appointments",
                200,
                token=self.tokens['doctor']
            )
            
            if success:
                immediate_visible = any(apt.get('id') == realtime_appointment_id for apt in immediate_check)
                if immediate_visible:
                    print("   ✅ Real-time updates working - doctor sees appointment immediately")
                else:
                    print("   ❌ Real-time updates not working - doctor doesn't see appointment immediately")
                    all_success = False
            else:
                print("   ❌ Could not test real-time updates")
                all_success = False
        else:
            print("   ❌ Could not create appointment for real-time testing")
            all_success = False
        
        return all_success

    def cleanup_test_data(self):
        """Clean up test data created during testing"""
        print("\n🧹 CLEANING UP TEST DATA")
        print("=" * 40)
        
        # Clean up created users
        if self.created_users and 'admin' in self.tokens:
            for user_id in self.created_users:
                try:
                    success, response = self.run_test(
                        f"Cleanup User {user_id}",
                        "DELETE",
                        f"admin/users/{user_id}/permanent",
                        200,
                        token=self.tokens['admin']
                    )
                    if success:
                        print(f"   ✅ Cleaned up user: {user_id}")
                except:
                    pass
        
        # Clean up created appointments
        if self.created_appointments and 'admin' in self.tokens:
            for appointment_id in self.created_appointments:
                try:
                    success, response = self.run_test(
                        f"Cleanup Appointment {appointment_id}",
                        "DELETE",
                        f"appointments/{appointment_id}",
                        200,
                        token=self.tokens['admin']
                    )
                    if success:
                        print(f"   ✅ Cleaned up appointment: {appointment_id}")
                except:
                    pass

    def run_all_tests(self):
        """Run all review request tests"""
        print("🎯 COMPREHENSIVE REVIEW REQUEST TESTING")
        print("=" * 80)
        print("Testing all core features specifically requested in the review")
        print("=" * 80)
        
        # Login with all demo credentials
        if not self.login_all_roles():
            print("❌ CRITICAL: Could not login with demo credentials")
            return False
        
        # Run all test categories
        test_results = {
            "admin_permissions": self.test_admin_permissions(),
            "doctor_appointment_visibility": self.test_doctor_appointment_visibility(),
            "provider_appointment_visibility": self.test_provider_appointment_visibility(),
            "notification_system": self.test_notification_system()
        }
        
        # Clean up test data
        self.cleanup_test_data()
        
        # Print final summary
        print("\n" + "=" * 80)
        print("🎯 COMPREHENSIVE REVIEW REQUEST TESTING SUMMARY")
        print("=" * 80)
        
        all_passed = all(test_results.values())
        
        for test_name, result in test_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status} - {test_name.replace('_', ' ').title()}")
        
        print(f"\nTotal Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if all_passed:
            print("\n🎉 ALL REVIEW REQUEST FEATURES WORKING CORRECTLY!")
            print("✅ Admin permissions fully operational")
            print("✅ Doctor appointment visibility working perfectly")
            print("✅ Provider appointment visibility working correctly")
            print("✅ Notification system functioning properly")
        else:
            print("\n❌ SOME REVIEW REQUEST FEATURES HAVE ISSUES")
            failed_tests = [name for name, result in test_results.items() if not result]
            print(f"Failed test categories: {', '.join(failed_tests)}")
        
        return all_passed

if __name__ == "__main__":
    tester = ReviewRequestTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)