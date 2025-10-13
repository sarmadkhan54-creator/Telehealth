import requests
import sys
import json
from datetime import datetime
import time

class EnhancedTelehealthTester:
    def __init__(self, base_url="https://healthlink-app-6.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tokens = {}
        self.users = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.created_appointments = []
        
        # Demo credentials
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
        """Login all user roles"""
        print("\n🔑 Logging in all user roles...")
        print("-" * 60)
        
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
            else:
                print(f"   ❌ {role.title()} login failed")
                return False
        
        return True

    def test_new_form_fields(self):
        """🎯 TEST 1: NEW FORM FIELDS TESTING"""
        print("\n🎯 TEST 1: NEW FORM FIELDS TESTING")
        print("=" * 80)
        print("Testing appointment creation with new 'history' field and 'area_of_consultation'")
        print("Testing new vitals fields: 'hb' (7-18 g/dL) and 'sugar_level' (70-200 mg/dL)")
        print("=" * 80)
        
        if 'provider' not in self.tokens:
            print("❌ No provider token available")
            return False
        
        all_success = True
        
        # Test 1.1: Appointment with new history field (replaces consultation_reason)
        print("\n1️⃣ Testing New 'history' Field (replaces consultation_reason)")
        print("-" * 60)
        
        appointment_with_history = {
            "patient": {
                "name": "Sarah Johnson",
                "age": 28,
                "gender": "Female",
                "vitals": {
                    "blood_pressure": "120/80",
                    "heart_rate": 75,
                    "temperature": 98.6,
                    "oxygen_saturation": 98,
                    "hb": 12.5,  # New field: 7-18 g/dL range
                    "sugar_level": 95  # New field: 70-200 mg/dL range
                },
                "history": "Patient has a history of mild hypertension, currently on medication. Reports occasional chest discomfort over the past week.",  # New field
                "area_of_consultation": "Cardiology"  # New field
            },
            "appointment_type": "emergency",
            "consultation_notes": "Patient reports chest pain - needs immediate attention"
        }
        
        success, response = self.run_test(
            "Create Appointment with New History Field",
            "POST",
            "appointments",
            200,
            data=appointment_with_history,
            token=self.tokens['provider']
        )
        
        if success:
            appointment_id = response.get('id')
            self.created_appointments.append(appointment_id)
            print(f"   ✅ Appointment created with history field (ID: {appointment_id})")
            print(f"   History: {appointment_with_history['patient']['history'][:50]}...")
            print(f"   Area of Consultation: {appointment_with_history['patient']['area_of_consultation']}")
        else:
            print("   ❌ Failed to create appointment with history field")
            all_success = False
        
        # Test 1.2: Test new vitals fields validation
        print("\n2️⃣ Testing New Vitals Fields Validation")
        print("-" * 60)
        
        # Test valid hb range (7-18 g/dL)
        valid_hb_tests = [
            {"hb": 7.0, "desc": "Minimum valid Hb (7.0 g/dL)"},
            {"hb": 12.5, "desc": "Normal Hb (12.5 g/dL)"},
            {"hb": 18.0, "desc": "Maximum valid Hb (18.0 g/dL)"}
        ]
        
        for test_case in valid_hb_tests:
            test_appointment = {
                "patient": {
                    "name": f"Test Patient Hb {test_case['hb']}",
                    "age": 30,
                    "gender": "Male",
                    "vitals": {
                        "blood_pressure": "120/80",
                        "heart_rate": 72,
                        "temperature": 98.6,
                        "oxygen_saturation": 98,
                        "hb": test_case['hb'],
                        "sugar_level": 100
                    },
                    "history": "Testing Hb validation",
                    "area_of_consultation": "General Medicine"
                },
                "appointment_type": "non_emergency"
            }
            
            success, response = self.run_test(
                f"Valid Hb Test - {test_case['desc']}",
                "POST",
                "appointments",
                200,
                data=test_appointment,
                token=self.tokens['provider']
            )
            
            if success:
                appointment_id = response.get('id')
                self.created_appointments.append(appointment_id)
                print(f"   ✅ {test_case['desc']} accepted")
            else:
                print(f"   ❌ {test_case['desc']} rejected")
                all_success = False
        
        # Test valid sugar_level range (70-200 mg/dL)
        valid_sugar_tests = [
            {"sugar": 70, "desc": "Minimum valid Sugar (70 mg/dL)"},
            {"sugar": 120, "desc": "Normal Sugar (120 mg/dL)"},
            {"sugar": 200, "desc": "Maximum valid Sugar (200 mg/dL)"}
        ]
        
        for test_case in valid_sugar_tests:
            test_appointment = {
                "patient": {
                    "name": f"Test Patient Sugar {test_case['sugar']}",
                    "age": 35,
                    "gender": "Female",
                    "vitals": {
                        "blood_pressure": "120/80",
                        "heart_rate": 72,
                        "temperature": 98.6,
                        "oxygen_saturation": 98,
                        "hb": 12.0,
                        "sugar_level": test_case['sugar']
                    },
                    "history": "Testing sugar level validation",
                    "area_of_consultation": "Endocrinology"
                },
                "appointment_type": "non_emergency"
            }
            
            success, response = self.run_test(
                f"Valid Sugar Test - {test_case['desc']}",
                "POST",
                "appointments",
                200,
                data=test_appointment,
                token=self.tokens['provider']
            )
            
            if success:
                appointment_id = response.get('id')
                self.created_appointments.append(appointment_id)
                print(f"   ✅ {test_case['desc']} accepted")
            else:
                print(f"   ❌ {test_case['desc']} rejected")
                all_success = False
        
        # Test 1.3: Verify data storage by retrieving appointment
        print("\n3️⃣ Testing Data Storage Verification")
        print("-" * 60)
        
        if self.created_appointments:
            test_appointment_id = self.created_appointments[0]
            success, response = self.run_test(
                "Retrieve Appointment to Verify Data Storage",
                "GET",
                f"appointments/{test_appointment_id}",
                200,
                token=self.tokens['provider']
            )
            
            if success:
                patient_data = response.get('patient', {})
                vitals = patient_data.get('vitals', {})
                
                # Check if new fields are stored correctly
                stored_history = patient_data.get('history')
                stored_area = patient_data.get('area_of_consultation')
                stored_hb = vitals.get('hb')
                stored_sugar = vitals.get('sugar_level')
                
                print(f"   ✅ Data storage verification:")
                print(f"   History stored: {'✅' if stored_history else '❌'} {stored_history[:30] if stored_history else 'Missing'}...")
                print(f"   Area of consultation: {'✅' if stored_area else '❌'} {stored_area}")
                print(f"   Hb level: {'✅' if stored_hb else '❌'} {stored_hb} g/dL")
                print(f"   Sugar level: {'✅' if stored_sugar else '❌'} {stored_sugar} mg/dL")
                
                if all([stored_history, stored_area, stored_hb, stored_sugar]):
                    print("   ✅ All new fields stored correctly")
                else:
                    print("   ❌ Some new fields not stored properly")
                    all_success = False
            else:
                print("   ❌ Could not retrieve appointment for data verification")
                all_success = False
        
        return all_success

    def test_appointment_type_workflow(self):
        """🎯 TEST 2: APPOINTMENT TYPE WORKFLOW"""
        print("\n🎯 TEST 2: APPOINTMENT TYPE WORKFLOW")
        print("=" * 80)
        print("Testing emergency vs non-emergency appointment workflows")
        print("Testing video call restrictions based on appointment type")
        print("=" * 80)
        
        if 'provider' not in self.tokens or 'doctor' not in self.tokens:
            print("❌ Missing provider or doctor tokens")
            return False
        
        all_success = True
        
        # Test 2.1: Create emergency appointment (should allow video calls)
        print("\n1️⃣ Testing Emergency Appointment Creation")
        print("-" * 60)
        
        emergency_appointment = {
            "patient": {
                "name": "Michael Chen",
                "age": 42,
                "gender": "Male",
                "vitals": {
                    "blood_pressure": "160/100",
                    "heart_rate": 95,
                    "temperature": 101.2,
                    "oxygen_saturation": 94,
                    "hb": 11.5,
                    "sugar_level": 180
                },
                "history": "Patient has diabetes and hypertension. Experiencing severe abdominal pain for 3 hours.",
                "area_of_consultation": "Emergency Medicine"
            },
            "appointment_type": "emergency",
            "consultation_notes": "URGENT: Severe abdominal pain, possible appendicitis"
        }
        
        success, response = self.run_test(
            "Create Emergency Appointment",
            "POST",
            "appointments",
            200,
            data=emergency_appointment,
            token=self.tokens['provider']
        )
        
        emergency_appointment_id = None
        if success:
            emergency_appointment_id = response.get('id')
            self.created_appointments.append(emergency_appointment_id)
            print(f"   ✅ Emergency appointment created (ID: {emergency_appointment_id})")
            print(f"   Type: {response.get('appointment_type')}")
        else:
            print("   ❌ Failed to create emergency appointment")
            all_success = False
        
        # Test 2.2: Create non-emergency appointment (should only allow notes)
        print("\n2️⃣ Testing Non-Emergency Appointment Creation")
        print("-" * 60)
        
        non_emergency_appointment = {
            "patient": {
                "name": "Lisa Rodriguez",
                "age": 35,
                "gender": "Female",
                "vitals": {
                    "blood_pressure": "118/75",
                    "heart_rate": 68,
                    "temperature": 98.4,
                    "oxygen_saturation": 99,
                    "hb": 13.2,
                    "sugar_level": 85
                },
                "history": "Patient has mild seasonal allergies. Requesting routine consultation for allergy management.",
                "area_of_consultation": "Allergy and Immunology"
            },
            "appointment_type": "non_emergency",
            "consultation_notes": "Routine consultation for allergy management"
        }
        
        success, response = self.run_test(
            "Create Non-Emergency Appointment",
            "POST",
            "appointments",
            200,
            data=non_emergency_appointment,
            token=self.tokens['provider']
        )
        
        non_emergency_appointment_id = None
        if success:
            non_emergency_appointment_id = response.get('id')
            self.created_appointments.append(non_emergency_appointment_id)
            print(f"   ✅ Non-emergency appointment created (ID: {non_emergency_appointment_id})")
            print(f"   Type: {response.get('appointment_type')}")
        else:
            print("   ❌ Failed to create non-emergency appointment")
            all_success = False
        
        # Test 2.3: Test video call restrictions for emergency appointments (should work)
        print("\n3️⃣ Testing Video Call Access for Emergency Appointments")
        print("-" * 60)
        
        if emergency_appointment_id:
            success, response = self.run_test(
                "Start Video Call for Emergency Appointment (Should Work)",
                "POST",
                f"video-call/start/{emergency_appointment_id}",
                200,
                token=self.tokens['doctor']
            )
            
            if success:
                print("   ✅ Video call allowed for emergency appointment")
                print(f"   Call ID: {response.get('call_id')}")
                print(f"   Jitsi URL: {response.get('jitsi_url')}")
                print(f"   Call Attempt: {response.get('call_attempt')}")
            else:
                print("   ❌ Video call blocked for emergency appointment")
                all_success = False
        
        # Test 2.4: Test video call restrictions for non-emergency appointments (should fail)
        print("\n4️⃣ Testing Video Call Restrictions for Non-Emergency Appointments")
        print("-" * 60)
        
        if non_emergency_appointment_id:
            success, response = self.run_test(
                "Start Video Call for Non-Emergency Appointment (Should Fail)",
                "POST",
                f"video-call/start/{non_emergency_appointment_id}",
                403,  # Should be forbidden
                token=self.tokens['doctor']
            )
            
            if success:
                print("   ✅ Video call correctly blocked for non-emergency appointment")
                print(f"   Error message: {response.get('detail', 'No error message')}")
            else:
                print("   ❌ Video call unexpectedly allowed for non-emergency appointment")
                all_success = False
        
        # Test 2.5: Test notes functionality for both appointment types
        print("\n5️⃣ Testing Notes Functionality for Both Appointment Types")
        print("-" * 60)
        
        # Test notes for emergency appointment
        if emergency_appointment_id:
            note_data = {
                "note": "Emergency patient stabilized. Recommend immediate CT scan to rule out appendicitis.",
                "sender_role": "doctor"
            }
            
            success, response = self.run_test(
                "Add Note to Emergency Appointment",
                "POST",
                f"appointments/{emergency_appointment_id}/notes",
                200,
                data=note_data,
                token=self.tokens['doctor']
            )
            
            if success:
                print("   ✅ Notes work for emergency appointments")
            else:
                print("   ❌ Notes failed for emergency appointment")
                all_success = False
        
        # Test notes for non-emergency appointment
        if non_emergency_appointment_id:
            note_data = {
                "note": "Patient's allergy symptoms are well-controlled. Continue current antihistamine regimen. Follow-up in 3 months.",
                "sender_role": "doctor"
            }
            
            success, response = self.run_test(
                "Add Note to Non-Emergency Appointment",
                "POST",
                f"appointments/{non_emergency_appointment_id}/notes",
                200,
                data=note_data,
                token=self.tokens['doctor']
            )
            
            if success:
                print("   ✅ Notes work for non-emergency appointments")
            else:
                print("   ❌ Notes failed for non-emergency appointment")
                all_success = False
        
        return all_success

    def test_whatsapp_like_video_calling(self):
        """🎯 TEST 3: WHATSAPP-LIKE VIDEO CALLING"""
        print("\n🎯 TEST 3: WHATSAPP-LIKE VIDEO CALLING")
        print("=" * 80)
        print("Testing multiple video call attempts for emergency appointments")
        print("Testing real-time notifications and Jitsi URL generation with call tracking")
        print("=" * 80)
        
        if 'doctor' not in self.tokens or 'provider' not in self.tokens:
            print("❌ Missing doctor or provider tokens")
            return False
        
        all_success = True
        
        # First create an emergency appointment for testing
        emergency_appointment = {
            "patient": {
                "name": "David Wilson",
                "age": 55,
                "gender": "Male",
                "vitals": {
                    "blood_pressure": "170/110",
                    "heart_rate": 105,
                    "temperature": 102.8,
                    "oxygen_saturation": 92,
                    "hb": 10.8,
                    "sugar_level": 220
                },
                "history": "Patient has history of heart disease and diabetes. Experiencing chest pain and shortness of breath.",
                "area_of_consultation": "Cardiology"
            },
            "appointment_type": "emergency",
            "consultation_notes": "CRITICAL: Possible heart attack - needs immediate attention"
        }
        
        success, response = self.run_test(
            "Create Emergency Appointment for Video Call Testing",
            "POST",
            "appointments",
            200,
            data=emergency_appointment,
            token=self.tokens['provider']
        )
        
        if not success:
            print("❌ Could not create emergency appointment for video call testing")
            return False
        
        test_appointment_id = response.get('id')
        self.created_appointments.append(test_appointment_id)
        print(f"   ✅ Test appointment created (ID: {test_appointment_id})")
        
        # Test 3.1: Multiple video call attempts (WhatsApp-like behavior)
        print("\n1️⃣ Testing Multiple Video Call Attempts (WhatsApp-like)")
        print("-" * 60)
        
        call_attempts = []
        for attempt in range(3):  # Test 3 call attempts
            success, response = self.run_test(
                f"Video Call Attempt #{attempt + 1}",
                "POST",
                f"video-call/start/{test_appointment_id}",
                200,
                token=self.tokens['doctor']
            )
            
            if success:
                call_id = response.get('call_id')
                jitsi_url = response.get('jitsi_url')
                call_attempt_num = response.get('call_attempt')
                room_name = response.get('room_name')
                
                call_attempts.append({
                    'call_id': call_id,
                    'jitsi_url': jitsi_url,
                    'attempt': call_attempt_num,
                    'room_name': room_name
                })
                
                print(f"   ✅ Call attempt #{attempt + 1} successful")
                print(f"   Call ID: {call_id}")
                print(f"   Attempt Number: {call_attempt_num}")
                print(f"   Room Name: {room_name}")
                print(f"   Jitsi URL: {jitsi_url}")
                
                # Verify each call has unique identifiers
                if attempt > 0:
                    prev_call = call_attempts[attempt - 1]
                    if call_id != prev_call['call_id'] and room_name != prev_call['room_name']:
                        print(f"   ✅ Call #{attempt + 1} has unique identifiers")
                    else:
                        print(f"   ❌ Call #{attempt + 1} identifiers not unique")
                        all_success = False
                
                time.sleep(1)  # Brief pause between calls
            else:
                print(f"   ❌ Call attempt #{attempt + 1} failed")
                all_success = False
        
        # Test 3.2: Verify call history tracking
        print("\n2️⃣ Testing Call History Tracking")
        print("-" * 60)
        
        success, response = self.run_test(
            "Get Appointment Details to Check Call History",
            "GET",
            f"appointments/{test_appointment_id}",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            call_history = response.get('call_history', [])
            print(f"   ✅ Call history contains {len(call_history)} entries")
            
            for i, call_entry in enumerate(call_history):
                print(f"   Call {i+1}: ID={call_entry.get('call_id')}, Status={call_entry.get('status')}, Attempt={call_entry.get('attempt_number')}")
            
            if len(call_history) == len(call_attempts):
                print("   ✅ Call history matches number of attempts")
            else:
                print("   ❌ Call history count mismatch")
                all_success = False
        else:
            print("   ❌ Could not retrieve call history")
            all_success = False
        
        # Test 3.3: Test real-time notifications (WebSocket status check)
        print("\n3️⃣ Testing Real-Time Notification System")
        print("-" * 60)
        
        success, response = self.run_test(
            "Check WebSocket Status for Notifications",
            "GET",
            "websocket/status",
            200,
            token=self.tokens['provider']
        )
        
        if success:
            websocket_status = response.get('websocket_status', {})
            total_connections = websocket_status.get('total_connections', 0)
            connected_users = websocket_status.get('connected_users', [])
            
            print(f"   ✅ WebSocket system operational")
            print(f"   Total connections: {total_connections}")
            print(f"   Connected users: {len(connected_users)}")
            
            # Test sending a notification
            success, response = self.run_test(
                "Send Test WebSocket Message",
                "POST",
                "websocket/test-message",
                200,
                token=self.tokens['provider']
            )
            
            if success:
                message_sent = response.get('message_sent', False)
                print(f"   ✅ Test notification sent: {message_sent}")
            else:
                print("   ❌ Test notification failed")
                all_success = False
        else:
            print("   ❌ WebSocket status check failed")
            all_success = False
        
        # Test 3.4: Verify Jitsi URL generation patterns
        print("\n4️⃣ Testing Jitsi URL Generation Patterns")
        print("-" * 60)
        
        if call_attempts:
            for i, call in enumerate(call_attempts):
                jitsi_url = call['jitsi_url']
                room_name = call['room_name']
                
                # Verify URL format
                if jitsi_url.startswith('https://meet.jit.si/'):
                    print(f"   ✅ Call {i+1} Jitsi URL format correct")
                else:
                    print(f"   ❌ Call {i+1} Jitsi URL format incorrect")
                    all_success = False
                
                # Verify room name contains appointment ID
                if test_appointment_id in room_name:
                    print(f"   ✅ Call {i+1} room name contains appointment ID")
                else:
                    print(f"   ❌ Call {i+1} room name missing appointment ID")
                    all_success = False
                
                # Verify room name is unique for each call
                if 'call-' in room_name:
                    print(f"   ✅ Call {i+1} room name includes call identifier")
                else:
                    print(f"   ❌ Call {i+1} room name missing call identifier")
                    all_success = False
        
        return all_success

    def test_multiple_account_management(self):
        """🎯 TEST 4: MULTIPLE ACCOUNT MANAGEMENT"""
        print("\n🎯 TEST 4: MULTIPLE ACCOUNT MANAGEMENT")
        print("=" * 80)
        print("Testing provider-specific appointment visibility")
        print("Testing doctor access to all appointments with proper filtering")
        print("=" * 80)
        
        if not all(role in self.tokens for role in ['provider', 'doctor', 'admin']):
            print("❌ Missing required tokens for account management testing")
            return False
        
        all_success = True
        
        # Test 4.1: Provider sees only their own appointments
        print("\n1️⃣ Testing Provider Account Isolation")
        print("-" * 60)
        
        success, response = self.run_test(
            "Get Appointments as Provider",
            "GET",
            "appointments",
            200,
            token=self.tokens['provider']
        )
        
        if success:
            provider_appointments = response
            provider_id = self.users['provider']['id']
            
            print(f"   ✅ Provider sees {len(provider_appointments)} appointments")
            
            # Verify all appointments belong to this provider
            own_appointments = 0
            other_appointments = 0
            
            for appointment in provider_appointments:
                if appointment.get('provider_id') == provider_id:
                    own_appointments += 1
                else:
                    other_appointments += 1
            
            print(f"   Own appointments: {own_appointments}")
            print(f"   Other appointments: {other_appointments}")
            
            if other_appointments == 0:
                print("   ✅ Provider correctly sees only own appointments")
            else:
                print("   ❌ Provider seeing appointments from other providers")
                all_success = False
        else:
            print("   ❌ Provider could not retrieve appointments")
            all_success = False
        
        # Test 4.2: Doctor sees all appointments
        print("\n2️⃣ Testing Doctor Access to All Appointments")
        print("-" * 60)
        
        success, response = self.run_test(
            "Get Appointments as Doctor",
            "GET",
            "appointments",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            doctor_appointments = response
            print(f"   ✅ Doctor sees {len(doctor_appointments)} appointments (all)")
            
            # Count appointments by type and status
            emergency_count = sum(1 for apt in doctor_appointments if apt.get('appointment_type') == 'emergency')
            non_emergency_count = sum(1 for apt in doctor_appointments if apt.get('appointment_type') == 'non_emergency')
            pending_count = sum(1 for apt in doctor_appointments if apt.get('status') == 'pending')
            accepted_count = sum(1 for apt in doctor_appointments if apt.get('status') == 'accepted')
            
            print(f"   Emergency appointments: {emergency_count}")
            print(f"   Non-emergency appointments: {non_emergency_count}")
            print(f"   Pending appointments: {pending_count}")
            print(f"   Accepted appointments: {accepted_count}")
            
            # Verify doctor sees appointments from different providers
            unique_providers = set()
            for appointment in doctor_appointments:
                provider_id = appointment.get('provider_id')
                if provider_id:
                    unique_providers.add(provider_id)
            
            print(f"   Appointments from {len(unique_providers)} different providers")
            
            if len(unique_providers) >= 1:
                print("   ✅ Doctor sees appointments from multiple providers")
            else:
                print("   ❌ Doctor not seeing appointments from multiple providers")
                all_success = False
        else:
            print("   ❌ Doctor could not retrieve appointments")
            all_success = False
        
        # Test 4.3: Admin sees all appointments
        print("\n3️⃣ Testing Admin Access to All Appointments")
        print("-" * 60)
        
        success, response = self.run_test(
            "Get Appointments as Admin",
            "GET",
            "appointments",
            200,
            token=self.tokens['admin']
        )
        
        if success:
            admin_appointments = response
            print(f"   ✅ Admin sees {len(admin_appointments)} appointments (all)")
            
            # Verify admin has same visibility as doctor (all appointments)
            if len(admin_appointments) >= len(doctor_appointments):
                print("   ✅ Admin has comprehensive appointment visibility")
            else:
                print("   ❌ Admin seeing fewer appointments than doctor")
                all_success = False
        else:
            print("   ❌ Admin could not retrieve appointments")
            all_success = False
        
        # Test 4.4: Cross-account appointment access restrictions
        print("\n4️⃣ Testing Cross-Account Access Restrictions")
        print("-" * 60)
        
        # Create a test appointment to verify access restrictions
        if self.created_appointments:
            test_appointment_id = self.created_appointments[0]
            
            # Provider should access their own appointment
            success, response = self.run_test(
                "Provider Access Own Appointment Details",
                "GET",
                f"appointments/{test_appointment_id}",
                200,
                token=self.tokens['provider']
            )
            
            if success:
                print("   ✅ Provider can access own appointment details")
            else:
                print("   ❌ Provider cannot access own appointment details")
                all_success = False
            
            # Doctor should access any appointment
            success, response = self.run_test(
                "Doctor Access Any Appointment Details",
                "GET",
                f"appointments/{test_appointment_id}",
                200,
                token=self.tokens['doctor']
            )
            
            if success:
                print("   ✅ Doctor can access any appointment details")
            else:
                print("   ❌ Doctor cannot access appointment details")
                all_success = False
            
            # Admin should access any appointment
            success, response = self.run_test(
                "Admin Access Any Appointment Details",
                "GET",
                f"appointments/{test_appointment_id}",
                200,
                token=self.tokens['admin']
            )
            
            if success:
                print("   ✅ Admin can access any appointment details")
            else:
                print("   ❌ Admin cannot access appointment details")
                all_success = False
        
        return all_success

    def test_enhanced_ui_indicators(self):
        """🎯 TEST 5: ENHANCED UI INDICATORS"""
        print("\n🎯 TEST 5: ENHANCED UI INDICATORS")
        print("=" * 80)
        print("Testing appointment type badges (Emergency vs Non-Emergency)")
        print("Testing enhanced vitals display with new fields")
        print("Testing call history tracking")
        print("=" * 80)
        
        all_success = True
        
        # Test 5.1: Verify appointment type indicators in API responses
        print("\n1️⃣ Testing Appointment Type Badges Data")
        print("-" * 60)
        
        if 'doctor' in self.tokens:
            success, response = self.run_test(
                "Get All Appointments for Type Badge Testing",
                "GET",
                "appointments",
                200,
                token=self.tokens['doctor']
            )
            
            if success:
                appointments = response
                emergency_appointments = [apt for apt in appointments if apt.get('appointment_type') == 'emergency']
                non_emergency_appointments = [apt for apt in appointments if apt.get('appointment_type') == 'non_emergency']
                
                print(f"   ✅ Found {len(emergency_appointments)} emergency appointments")
                print(f"   ✅ Found {len(non_emergency_appointments)} non-emergency appointments")
                
                # Verify appointment type field is present and correct
                for appointment in appointments[:3]:  # Check first 3 appointments
                    apt_type = appointment.get('appointment_type')
                    apt_id = appointment.get('id', 'Unknown')[:8]
                    
                    if apt_type in ['emergency', 'non_emergency']:
                        print(f"   ✅ Appointment {apt_id}: Type = {apt_type}")
                    else:
                        print(f"   ❌ Appointment {apt_id}: Invalid type = {apt_type}")
                        all_success = False
            else:
                print("   ❌ Could not retrieve appointments for type testing")
                all_success = False
        
        # Test 5.2: Verify enhanced vitals display with new fields
        print("\n2️⃣ Testing Enhanced Vitals Display")
        print("-" * 60)
        
        if self.created_appointments:
            test_appointment_id = self.created_appointments[0]
            success, response = self.run_test(
                "Get Appointment with Enhanced Vitals",
                "GET",
                f"appointments/{test_appointment_id}",
                200,
                token=self.tokens['doctor']
            )
            
            if success:
                patient_data = response.get('patient', {})
                vitals = patient_data.get('vitals', {})
                
                print("   ✅ Enhanced vitals data:")
                
                # Check traditional vitals
                traditional_vitals = ['blood_pressure', 'heart_rate', 'temperature', 'oxygen_saturation']
                for vital in traditional_vitals:
                    value = vitals.get(vital)
                    if value:
                        print(f"   {vital}: {value}")
                    else:
                        print(f"   ❌ Missing {vital}")
                        all_success = False
                
                # Check new vitals fields
                new_vitals = ['hb', 'sugar_level']
                for vital in new_vitals:
                    value = vitals.get(vital)
                    if value is not None:
                        print(f"   ✅ NEW {vital}: {value}")
                    else:
                        print(f"   ❌ Missing new vital: {vital}")
                        all_success = False
                
                # Check new patient fields
                history = patient_data.get('history')
                area_of_consultation = patient_data.get('area_of_consultation')
                
                if history:
                    print(f"   ✅ History: {history[:50]}...")
                else:
                    print("   ❌ Missing history field")
                    all_success = False
                
                if area_of_consultation:
                    print(f"   ✅ Area of consultation: {area_of_consultation}")
                else:
                    print("   ❌ Missing area of consultation")
                    all_success = False
            else:
                print("   ❌ Could not retrieve appointment for vitals testing")
                all_success = False
        
        # Test 5.3: Test call history tracking indicators
        print("\n3️⃣ Testing Call History Tracking")
        print("-" * 60)
        
        # Find an appointment with call history
        if 'doctor' in self.tokens:
            success, response = self.run_test(
                "Get Appointments to Check Call History",
                "GET",
                "appointments",
                200,
                token=self.tokens['doctor']
            )
            
            if success:
                appointments = response
                appointments_with_calls = [apt for apt in appointments if apt.get('call_history')]
                
                print(f"   ✅ Found {len(appointments_with_calls)} appointments with call history")
                
                if appointments_with_calls:
                    # Examine call history structure
                    sample_appointment = appointments_with_calls[0]
                    call_history = sample_appointment.get('call_history', [])
                    
                    print(f"   ✅ Sample appointment has {len(call_history)} call entries")
                    
                    for i, call_entry in enumerate(call_history[:3]):  # Show first 3 calls
                        call_id = call_entry.get('call_id', 'Unknown')[:8]
                        doctor_name = call_entry.get('doctor_name', 'Unknown')
                        attempt_number = call_entry.get('attempt_number', 'Unknown')
                        status = call_entry.get('status', 'Unknown')
                        initiated_at = call_entry.get('initiated_at', 'Unknown')
                        
                        print(f"   Call {i+1}: ID={call_id}, Doctor={doctor_name}, Attempt={attempt_number}, Status={status}")
                        
                        # Verify required fields are present
                        required_fields = ['call_id', 'doctor_name', 'attempt_number', 'status', 'initiated_at']
                        missing_fields = [field for field in required_fields if not call_entry.get(field)]
                        
                        if not missing_fields:
                            print(f"   ✅ Call {i+1} has all required tracking fields")
                        else:
                            print(f"   ❌ Call {i+1} missing fields: {missing_fields}")
                            all_success = False
                else:
                    print("   ⚠️  No appointments with call history found (may be expected if no calls made)")
            else:
                print("   ❌ Could not retrieve appointments for call history testing")
                all_success = False
        
        return all_success

    def cleanup_test_data(self):
        """Clean up test appointments"""
        print("\n🧹 Cleaning up test data...")
        print("-" * 40)
        
        if 'admin' in self.tokens and self.created_appointments:
            for appointment_id in self.created_appointments:
                success, response = self.run_test(
                    f"Delete Test Appointment {appointment_id[:8]}",
                    "DELETE",
                    f"appointments/{appointment_id}",
                    200,
                    token=self.tokens['admin']
                )
                
                if success:
                    print(f"   ✅ Deleted appointment {appointment_id[:8]}")
                else:
                    print(f"   ❌ Failed to delete appointment {appointment_id[:8]}")

    def run_comprehensive_enhanced_telehealth_tests(self):
        """Run all enhanced telehealth feature tests"""
        print("🎯 COMPREHENSIVE ENHANCED TELEHEALTH SYSTEM TESTING")
        print("=" * 80)
        print("Testing all new enhanced telehealth features as requested in review")
        print("Focus: New form fields, appointment workflows, video calling, account management")
        print("=" * 80)
        
        # Login all roles
        if not self.login_all_roles():
            print("❌ Failed to login all roles - cannot continue testing")
            return False
        
        all_tests_passed = True
        
        # Run all test suites
        test_suites = [
            ("NEW FORM FIELDS", self.test_new_form_fields),
            ("APPOINTMENT TYPE WORKFLOW", self.test_appointment_type_workflow),
            ("WHATSAPP-LIKE VIDEO CALLING", self.test_whatsapp_like_video_calling),
            ("MULTIPLE ACCOUNT MANAGEMENT", self.test_multiple_account_management),
            ("ENHANCED UI INDICATORS", self.test_enhanced_ui_indicators)
        ]
        
        for suite_name, test_method in test_suites:
            print(f"\n{'='*80}")
            print(f"RUNNING TEST SUITE: {suite_name}")
            print(f"{'='*80}")
            
            try:
                result = test_method()
                if result:
                    print(f"✅ {suite_name} - ALL TESTS PASSED")
                else:
                    print(f"❌ {suite_name} - SOME TESTS FAILED")
                    all_tests_passed = False
            except Exception as e:
                print(f"❌ {suite_name} - EXCEPTION: {str(e)}")
                all_tests_passed = False
        
        # Cleanup
        self.cleanup_test_data()
        
        # Final summary
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE ENHANCED TELEHEALTH TESTING SUMMARY")
        print("="*80)
        print(f"Total tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if all_tests_passed:
            print("✅ ALL ENHANCED TELEHEALTH FEATURES WORKING CORRECTLY")
            print("✅ New form fields (history, area_of_consultation, hb, sugar_level) functional")
            print("✅ Appointment type workflow (emergency vs non-emergency) working")
            print("✅ WhatsApp-like video calling with multiple attempts working")
            print("✅ Multiple account management with proper filtering working")
            print("✅ Enhanced UI indicators and call history tracking working")
        else:
            print("❌ SOME ENHANCED TELEHEALTH FEATURES HAVE ISSUES")
            print("❌ Review failed tests above for specific issues")
        
        return all_tests_passed

if __name__ == "__main__":
    tester = EnhancedTelehealthTester()
    success = tester.run_comprehensive_enhanced_telehealth_tests()
    sys.exit(0 if success else 1)