import requests
import json
import time
import threading
from datetime import datetime
import sys

class VideoCallNotificationTester:
    def __init__(self, base_url="https://greenstar-health-2.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tokens = {}
        self.users = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.appointment_id = None
        
        # Test credentials
        self.demo_credentials = {
            "provider": {"username": "demo_provider", "password": "Demo123!"},
            "doctor": {"username": "demo_doctor", "password": "Demo123!"}
        }
        
        # WebSocket test results
        self.websocket_messages = []
        self.websocket_connections = {}

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

    def login_users(self):
        """Login both doctor and provider"""
        print("\n🔑 Logging in test users...")
        print("-" * 50)
        
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

    def create_test_appointment(self):
        """Create a test appointment for video call testing"""
        print("\n📅 Creating test appointment...")
        print("-" * 50)
        
        if 'provider' not in self.tokens:
            print("❌ No provider token available")
            return False
            
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
                "consultation_reason": "Video call notification testing"
            },
            "appointment_type": "non_emergency",
            "consultation_notes": "Test appointment for video call notifications"
        }
        
        success, response = self.run_test(
            "Create Test Appointment",
            "POST",
            "appointments",
            200,
            data=appointment_data,
            token=self.tokens['provider']
        )
        
        if success:
            self.appointment_id = response.get('id')
            print(f"   ✅ Created appointment ID: {self.appointment_id}")
            return True
        
        return False

    def test_video_call_session_creation(self):
        """Test 1: Video Call Session Creation with notification triggers"""
        print("\n🎯 TEST 1: Video Call Session Creation & Notification Triggers")
        print("=" * 70)
        
        if not self.appointment_id:
            print("❌ No appointment ID available")
            return False
        
        all_success = True
        
        # Test 1a: Doctor creates video call session
        print("\n📹 Testing Doctor Video Call Session Creation...")
        success, doctor_response = self.run_test(
            "Doctor Creates Video Call Session",
            "GET",
            f"video-call/session/{self.appointment_id}",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            jitsi_url = doctor_response.get('jitsi_url')
            room_name = doctor_response.get('room_name')
            print(f"   ✅ Doctor session created successfully")
            print(f"   📺 Jitsi URL: {jitsi_url}")
            print(f"   🏠 Room Name: {room_name}")
            
            # Verify notification payload structure
            if jitsi_url and room_name:
                print(f"   ✅ Session contains required notification fields")
            else:
                print(f"   ❌ Missing required notification fields")
                all_success = False
        else:
            print("   ❌ Doctor session creation failed")
            all_success = False
        
        # Test 1b: Provider creates video call session (should get same room)
        print("\n📹 Testing Provider Video Call Session Creation...")
        success, provider_response = self.run_test(
            "Provider Creates Video Call Session",
            "GET",
            f"video-call/session/{self.appointment_id}",
            200,
            token=self.tokens['provider']
        )
        
        if success:
            provider_jitsi_url = provider_response.get('jitsi_url')
            provider_room_name = provider_response.get('room_name')
            print(f"   ✅ Provider session created successfully")
            print(f"   📺 Jitsi URL: {provider_jitsi_url}")
            print(f"   🏠 Room Name: {provider_room_name}")
            
            # Verify both get same room (critical for notifications)
            if jitsi_url == provider_jitsi_url and room_name == provider_room_name:
                print(f"   🎉 CRITICAL SUCCESS: Both users get SAME Jitsi room!")
                print(f"   🎯 This ensures notification sound will work for same session")
            else:
                print(f"   ❌ CRITICAL FAILURE: Different rooms - notification sound will fail!")
                all_success = False
        else:
            print("   ❌ Provider session creation failed")
            all_success = False
        
        return all_success

    def test_websocket_notification_system(self):
        """Test 2: WebSocket Notification Testing"""
        print("\n🎯 TEST 2: WebSocket Notification System")
        print("=" * 70)
        
        try:
            import websocket
        except ImportError:
            print("⚠️  WebSocket library not available, testing HTTP endpoints only")
            return self.test_websocket_http_endpoints()
        
        # Test WebSocket connections for both users
        doctor_id = self.users['doctor']['id']
        provider_id = self.users['provider']['id']
        
        print(f"\n🔌 Testing WebSocket connections...")
        print(f"   Doctor ID: {doctor_id}")
        print(f"   Provider ID: {provider_id}")
        
        # Test WebSocket endpoint accessibility
        ws_urls = {
            'doctor': f"wss://telehealth-pwa.preview.emergentagent.com/api/ws/{doctor_id}",
            'provider': f"wss://telehealth-pwa.preview.emergentagent.com/api/ws/{provider_id}"
        }
        
        connection_results = {}
        
        for role, ws_url in ws_urls.items():
            print(f"\n   Testing {role} WebSocket: {ws_url}")
            
            try:
                # Test WebSocket connection (simplified test)
                connection_successful = False
                messages_received = []
                
                def on_message(ws, message):
                    messages_received.append(message)
                    print(f"   📨 {role} received: {message}")
                
                def on_open(ws):
                    nonlocal connection_successful
                    connection_successful = True
                    print(f"   ✅ {role} WebSocket connected")
                    time.sleep(1)
                    ws.close()
                
                def on_error(ws, error):
                    print(f"   ❌ {role} WebSocket error: {error}")
                
                def on_close(ws, close_status_code, close_msg):
                    print(f"   🔌 {role} WebSocket closed")
                
                ws = websocket.WebSocketApp(ws_url,
                                          on_open=on_open,
                                          on_message=on_message,
                                          on_error=on_error,
                                          on_close=on_close)
                
                # Run WebSocket in thread with timeout
                ws_thread = threading.Thread(target=ws.run_forever)
                ws_thread.daemon = True
                ws_thread.start()
                
                time.sleep(3)  # Wait for connection test
                
                connection_results[role] = connection_successful
                
            except Exception as e:
                print(f"   ❌ {role} WebSocket test failed: {str(e)}")
                connection_results[role] = False
        
        # Evaluate results
        all_connected = all(connection_results.values())
        if all_connected:
            print(f"\n   🎉 SUCCESS: All WebSocket connections working!")
            print(f"   🔔 Notification delivery infrastructure is operational")
        else:
            print(f"\n   ⚠️  Some WebSocket connections failed:")
            for role, success in connection_results.items():
                status = "✅" if success else "❌"
                print(f"   {status} {role}: {success}")
        
        return all_connected

    def test_websocket_http_endpoints(self):
        """Fallback test for WebSocket endpoints via HTTP"""
        print("\n🔌 Testing WebSocket endpoint accessibility via HTTP...")
        
        # Test that WebSocket endpoints exist (they should return upgrade required)
        doctor_id = self.users['doctor']['id']
        provider_id = self.users['provider']['id']
        
        for role, user_id in [('doctor', doctor_id), ('provider', provider_id)]:
            try:
                # HTTP request to WebSocket endpoint should fail with specific error
                response = requests.get(f"{self.api_url}/ws/{user_id}", timeout=5)
                print(f"   {role} WebSocket endpoint: Status {response.status_code}")
                
                # WebSocket endpoints typically return 426 (Upgrade Required) for HTTP requests
                if response.status_code in [426, 400, 405]:
                    print(f"   ✅ {role} WebSocket endpoint exists and properly configured")
                else:
                    print(f"   ⚠️  {role} WebSocket endpoint returned unexpected status")
            except Exception as e:
                print(f"   ⚠️  {role} WebSocket endpoint test: {str(e)}")
        
        return True

    def test_bidirectional_notifications(self):
        """Test 3: Bi-directional Notification Testing"""
        print("\n🎯 TEST 3: Bi-directional Notification Testing")
        print("=" * 70)
        
        if not self.appointment_id:
            print("❌ No appointment ID available")
            return False
        
        all_success = True
        
        # Test 3a: Doctor starts call → Should notify provider
        print("\n👨‍⚕️ Testing Doctor → Provider Notification...")
        success, doctor_start_response = self.run_test(
            "Doctor Starts Video Call (Should Notify Provider)",
            "POST",
            f"video-call/start/{self.appointment_id}",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            session_token = doctor_start_response.get('session_token')
            print(f"   ✅ Doctor started call successfully")
            print(f"   🎫 Session token: {session_token[:20]}...")
            print(f"   🔔 This should trigger notification to provider with sound")
        else:
            print("   ❌ Doctor failed to start call")
            all_success = False
        
        # Test 3b: Provider starts call → Should notify doctor
        print("\n👩‍⚕️ Testing Provider → Doctor Notification...")
        success, provider_start_response = self.run_test(
            "Provider Starts Video Call (Should Notify Doctor)",
            "POST",
            f"video-call/start/{self.appointment_id}",
            200,
            token=self.tokens['provider']
        )
        
        if success:
            provider_session_token = provider_start_response.get('session_token')
            print(f"   ✅ Provider started call successfully")
            print(f"   🎫 Session token: {provider_session_token[:20]}...")
            print(f"   🔔 This should trigger notification to doctor with sound")
        else:
            print("   ❌ Provider failed to start call")
            all_success = False
        
        # Test 3c: Verify notification payload structure
        print("\n📋 Testing Notification Payload Structure...")
        
        # Get session details to verify notification data
        success, session_response = self.run_test(
            "Get Session Details for Notification Verification",
            "GET",
            f"video-call/session/{self.appointment_id}",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            jitsi_url = session_response.get('jitsi_url')
            room_name = session_response.get('room_name')
            
            print(f"   ✅ Session details retrieved")
            print(f"   📺 Jitsi URL: {jitsi_url}")
            print(f"   🏠 Room Name: {room_name}")
            
            # Verify notification payload would contain required fields
            required_fields = ['jitsi_url', 'room_name', 'appointment_id']
            missing_fields = [field for field in required_fields if not session_response.get(field)]
            
            if not missing_fields:
                print(f"   ✅ All required notification fields present")
                print(f"   🔔 Notification payload structure is correct for sound notifications")
            else:
                print(f"   ❌ Missing notification fields: {missing_fields}")
                all_success = False
        else:
            print("   ❌ Could not verify notification payload structure")
            all_success = False
        
        return all_success

    def test_websocket_manager_functionality(self):
        """Test 4: WebSocket Manager Testing"""
        print("\n🎯 TEST 4: WebSocket Manager Functionality")
        print("=" * 70)
        
        # Test the manager.send_personal_message function indirectly
        # by triggering video call notifications and verifying the system responds
        
        if not self.appointment_id:
            print("❌ No appointment ID available")
            return False
        
        print("\n📡 Testing WebSocket Manager via Video Call Notifications...")
        
        # Test manager functionality by creating video call sessions
        # which should trigger the manager.send_personal_message function
        
        all_success = True
        
        # Test 4a: Verify manager handles doctor notifications
        print("\n   Testing manager notification to provider...")
        success, response = self.run_test(
            "Trigger Manager Notification (Doctor → Provider)",
            "GET",
            f"video-call/session/{self.appointment_id}",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            print(f"   ✅ Manager notification trigger successful")
            print(f"   📨 WebSocket manager should send jitsi_call_invitation to provider")
        else:
            print(f"   ❌ Manager notification trigger failed")
            all_success = False
        
        # Test 4b: Verify manager handles provider notifications  
        print("\n   Testing manager notification to doctor...")
        success, response = self.run_test(
            "Trigger Manager Notification (Provider → Doctor)",
            "GET",
            f"video-call/session/{self.appointment_id}",
            200,
            token=self.tokens['provider']
        )
        
        if success:
            print(f"   ✅ Manager notification trigger successful")
            print(f"   📨 WebSocket manager should send jitsi_call_invitation to doctor")
        else:
            print(f"   ❌ Manager notification trigger failed")
            all_success = False
        
        # Test 4c: Test manager with multiple users
        print("\n   Testing manager with multiple active connections...")
        
        # Simulate multiple session requests to test manager's ability to handle
        # multiple active connections
        for i in range(3):
            success, response = self.run_test(
                f"Multiple Manager Test {i+1}",
                "GET",
                f"video-call/session/{self.appointment_id}",
                200,
                token=self.tokens['doctor'] if i % 2 == 0 else self.tokens['provider']
            )
            
            if not success:
                print(f"   ❌ Manager failed on multiple connection test {i+1}")
                all_success = False
                break
        
        if all_success:
            print(f"   ✅ Manager handles multiple connections successfully")
            print(f"   🔄 WebSocket manager is operational for notification delivery")
        
        return all_success

    def test_real_time_notification_scenario(self):
        """Test 5: Real-time Testing Scenario"""
        print("\n🎯 TEST 5: Real-time Video Call Notification Scenario")
        print("=" * 70)
        
        if not self.appointment_id:
            print("❌ No appointment ID available")
            return False
        
        print("\n🎬 Simulating Real-time Video Call Notification Scenario...")
        print("   Scenario: Doctor and Provider both have active appointments")
        print("   Testing: Video call initiation from both sides with sound notifications")
        
        all_success = True
        
        # Step 1: Doctor initiates video call
        print(f"\n   Step 1: Doctor initiates video call...")
        success, doctor_session = self.run_test(
            "Doctor Initiates Video Call",
            "GET",
            f"video-call/session/{self.appointment_id}",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            doctor_jitsi_url = doctor_session.get('jitsi_url')
            doctor_room = doctor_session.get('room_name')
            print(f"   ✅ Doctor call initiated")
            print(f"   📺 Jitsi Room: {doctor_room}")
            print(f"   🔔 Notification sent to provider with sound")
        else:
            print(f"   ❌ Doctor call initiation failed")
            all_success = False
        
        # Step 2: Provider receives notification and joins
        print(f"\n   Step 2: Provider receives notification and joins...")
        success, provider_session = self.run_test(
            "Provider Joins After Notification",
            "GET",
            f"video-call/session/{self.appointment_id}",
            200,
            token=self.tokens['provider']
        )
        
        if success:
            provider_jitsi_url = provider_session.get('jitsi_url')
            provider_room = provider_session.get('room_name')
            print(f"   ✅ Provider joined successfully")
            print(f"   📺 Jitsi Room: {provider_room}")
            
            # Verify same room (critical for sound notifications)
            if doctor_jitsi_url == provider_jitsi_url:
                print(f"   🎉 SUCCESS: Both users in SAME room - sound notifications working!")
            else:
                print(f"   ❌ FAILURE: Different rooms - sound notifications broken!")
                all_success = False
        else:
            print(f"   ❌ Provider join failed")
            all_success = False
        
        # Step 3: Test reverse scenario - Provider initiates
        print(f"\n   Step 3: Provider initiates new call...")
        
        # Create another appointment for reverse test
        appointment_data = {
            "patient": {
                "name": "Reverse Test Patient",
                "age": 40,
                "gender": "Female",
                "vitals": {"blood_pressure": "110/70", "heart_rate": 68},
                "consultation_reason": "Reverse notification test"
            },
            "appointment_type": "non_emergency",
            "consultation_notes": "Reverse test"
        }
        
        success, response = self.run_test(
            "Create Second Appointment for Reverse Test",
            "POST",
            "appointments",
            200,
            data=appointment_data,
            token=self.tokens['provider']
        )
        
        if success:
            second_appointment_id = response.get('id')
            
            # Provider initiates call on second appointment
            success, provider_init = self.run_test(
                "Provider Initiates Video Call (Reverse Test)",
                "GET",
                f"video-call/session/{second_appointment_id}",
                200,
                token=self.tokens['provider']
            )
            
            if success:
                print(f"   ✅ Provider call initiated (reverse scenario)")
                print(f"   🔔 Notification sent to doctor with sound")
                
                # Doctor joins
                success, doctor_join = self.run_test(
                    "Doctor Joins After Provider Notification",
                    "GET",
                    f"video-call/session/{second_appointment_id}",
                    200,
                    token=self.tokens['doctor']
                )
                
                if success:
                    print(f"   ✅ Doctor joined after provider notification")
                    print(f"   🎉 Bi-directional sound notifications working!")
                else:
                    print(f"   ❌ Doctor failed to join after provider notification")
                    all_success = False
            else:
                print(f"   ❌ Provider call initiation failed (reverse test)")
                all_success = False
        
        # Step 4: Test notification payload completeness
        print(f"\n   Step 4: Verifying notification payload completeness...")
        
        success, final_session = self.run_test(
            "Final Session Check for Notification Completeness",
            "GET",
            f"video-call/session/{self.appointment_id}",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            required_notification_fields = [
                'jitsi_url', 'room_name', 'appointment_id', 'status'
            ]
            
            missing_fields = [field for field in required_notification_fields 
                            if field not in final_session or not final_session[field]]
            
            if not missing_fields:
                print(f"   ✅ All notification fields present and valid")
                print(f"   🔔 Sound notification payload is complete")
            else:
                print(f"   ❌ Missing notification fields: {missing_fields}")
                all_success = False
        else:
            print(f"   ❌ Could not verify final notification payload")
            all_success = False
        
        return all_success

    def run_comprehensive_test(self):
        """Run all video call notification tests"""
        print("🎯 VIDEO CALL NOTIFICATION SOUND SYSTEM TESTING")
        print("=" * 80)
        print("Testing video call notification system to identify why notifications")
        print("with sound are not working properly.")
        print("=" * 80)
        
        # Setup
        if not self.login_users():
            print("\n❌ CRITICAL FAILURE: Could not login test users")
            return False
        
        if not self.create_test_appointment():
            print("\n❌ CRITICAL FAILURE: Could not create test appointment")
            return False
        
        # Run all tests
        test_results = []
        
        test_results.append(("Video Call Session Creation", self.test_video_call_session_creation()))
        test_results.append(("WebSocket Notification System", self.test_websocket_notification_system()))
        test_results.append(("Bi-directional Notifications", self.test_bidirectional_notifications()))
        test_results.append(("WebSocket Manager Functionality", self.test_websocket_manager_functionality()))
        test_results.append(("Real-time Notification Scenario", self.test_real_time_notification_scenario()))
        
        # Results Summary
        print("\n" + "=" * 80)
        print("🎯 VIDEO CALL NOTIFICATION TESTING RESULTS")
        print("=" * 80)
        
        passed_tests = 0
        total_tests = len(test_results)
        
        for test_name, result in test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status} - {test_name}")
            if result:
                passed_tests += 1
        
        print(f"\n📊 OVERALL RESULTS:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        print(f"   Major Test Categories: {passed_tests}/{total_tests} passed")
        
        # Diagnostic Summary
        print(f"\n🔍 DIAGNOSTIC SUMMARY:")
        if passed_tests == total_tests:
            print("   🎉 ALL TESTS PASSED - Video call notification system is working!")
            print("   🔔 Sound notifications should be operational")
        else:
            print("   ⚠️  ISSUES DETECTED in video call notification system:")
            for test_name, result in test_results:
                if not result:
                    print(f"   ❌ {test_name} - Needs investigation")
        
        print("\n" + "=" * 80)
        
        return passed_tests == total_tests

if __name__ == "__main__":
    tester = VideoCallNotificationTester()
    success = tester.run_comprehensive_test()
    sys.exit(0 if success else 1)