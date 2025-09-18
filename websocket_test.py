import asyncio
import websockets
import json
import requests
import sys
from datetime import datetime
import uuid

class WebSocketTester:
    def __init__(self, base_url="https://calltrack-health.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.ws_url = base_url.replace("https://", "wss://").replace("http://", "ws://")
        self.tokens = {}
        self.users = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.appointment_id = None
        
        # Demo credentials
        self.demo_credentials = {
            "provider": {"username": "demo_provider", "password": "Demo123!"},
            "doctor": {"username": "demo_doctor", "password": "Demo123!"},
            "admin": {"username": "demo_admin", "password": "Demo123!"}
        }

    def login_all_users(self):
        """Login all demo users and get tokens"""
        print("🔑 Logging in all demo users...")
        
        for role, credentials in self.demo_credentials.items():
            try:
                response = requests.post(
                    f"{self.api_url}/login",
                    json=credentials,
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.tokens[role] = data['access_token']
                    self.users[role] = data['user']
                    print(f"   ✅ {role.title()} logged in successfully")
                else:
                    print(f"   ❌ {role.title()} login failed: {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"   ❌ {role.title()} login error: {str(e)}")
                return False
        
        return len(self.tokens) == 3

    async def test_websocket_connection(self, user_role):
        """Test basic WebSocket connection for a user"""
        print(f"\n🔌 Testing WebSocket Connection for {user_role.title()}")
        
        if user_role not in self.users:
            print(f"   ❌ No user data for {user_role}")
            return False
        
        user_id = self.users[user_role]['id']
        ws_endpoint = f"{self.ws_url}/ws/{user_id}"
        
        try:
            async with websockets.connect(ws_endpoint) as websocket:
                print(f"   ✅ WebSocket connected for {user_role}")
                
                # Test sending a message
                test_message = {"type": "test", "message": "Hello WebSocket"}
                await websocket.send(json.dumps(test_message))
                print(f"   ✅ Message sent successfully")
                
                # Wait briefly for any response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    print(f"   📨 Received response: {response}")
                except asyncio.TimeoutError:
                    print(f"   ℹ️  No immediate response (expected for notification endpoint)")
                
                return True
                
        except Exception as e:
            print(f"   ❌ WebSocket connection failed: {str(e)}")
            return False

    async def test_video_call_websocket(self, session_token):
        """Test video call WebSocket signaling"""
        print(f"\n📹 Testing Video Call WebSocket Signaling")
        
        ws_endpoint = f"{self.ws_url}/ws/video-call/{session_token}"
        
        try:
            async with websockets.connect(ws_endpoint) as websocket:
                print(f"   ✅ Video call WebSocket connected")
                
                # Send join message
                join_message = {
                    "type": "join",
                    "userId": "test_user_123",
                    "userName": "Test User"
                }
                await websocket.send(json.dumps(join_message))
                print(f"   ✅ Join message sent")
                
                # Send WebRTC offer
                offer_message = {
                    "type": "offer",
                    "target": "other_user",
                    "sdp": "fake_sdp_offer_data"
                }
                await websocket.send(json.dumps(offer_message))
                print(f"   ✅ WebRTC offer sent")
                
                # Send ICE candidate
                ice_message = {
                    "type": "ice-candidate",
                    "target": "other_user",
                    "candidate": "fake_ice_candidate_data"
                }
                await websocket.send(json.dumps(ice_message))
                print(f"   ✅ ICE candidate sent")
                
                return True
                
        except Exception as e:
            print(f"   ❌ Video call WebSocket failed: {str(e)}")
            return False

    def create_emergency_appointment(self):
        """Create an emergency appointment to test notifications"""
        print(f"\n🚨 Creating Emergency Appointment for Notification Testing")
        
        if 'provider' not in self.tokens:
            print("   ❌ No provider token available")
            return None
        
        appointment_data = {
            "patient": {
                "name": "Emergency Test Patient",
                "age": 55,
                "gender": "Male",
                "vitals": {
                    "blood_pressure": "190/110",
                    "heart_rate": 120,
                    "temperature": 103.2,
                    "oxygen_saturation": "88%"
                },
                "consultation_reason": "Severe chest pain and shortness of breath"
            },
            "appointment_type": "emergency",
            "consultation_notes": "URGENT: Patient experiencing cardiac symptoms"
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/appointments",
                json=appointment_data,
                headers={'Authorization': f'Bearer {self.tokens["provider"]}'},
                timeout=10
            )
            
            if response.status_code == 200:
                appointment = response.json()
                appointment_id = appointment.get('id')
                print(f"   ✅ Emergency appointment created: {appointment_id}")
                return appointment_id
            else:
                print(f"   ❌ Failed to create appointment: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"   ❌ Error creating appointment: {str(e)}")
            return None

    def accept_appointment(self, appointment_id):
        """Doctor accepts an appointment to test acceptance notifications"""
        print(f"\n✅ Doctor Accepting Appointment for Notification Testing")
        
        if 'doctor' not in self.tokens:
            print("   ❌ No doctor token available")
            return False
        
        update_data = {
            "status": "accepted",
            "doctor_id": self.users['doctor']['id'],
            "doctor_notes": "Appointment accepted by doctor for testing"
        }
        
        try:
            response = requests.put(
                f"{self.api_url}/appointments/{appointment_id}",
                json=update_data,
                headers={'Authorization': f'Bearer {self.tokens["doctor"]}'},
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"   ✅ Appointment accepted by doctor")
                return True
            else:
                print(f"   ❌ Failed to accept appointment: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error accepting appointment: {str(e)}")
            return False

    def start_video_call(self, appointment_id):
        """Start a video call to get session token"""
        print(f"\n🎬 Starting Video Call for WebSocket Testing")
        
        if 'doctor' not in self.tokens:
            print("   ❌ No doctor token available")
            return None
        
        try:
            response = requests.post(
                f"{self.api_url}/video-call/start/{appointment_id}",
                headers={'Authorization': f'Bearer {self.tokens["doctor"]}'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                session_token = data.get('session_token')
                print(f"   ✅ Video call started, session token: {session_token[:20]}...")
                return session_token
            else:
                print(f"   ❌ Failed to start video call: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"   ❌ Error starting video call: {str(e)}")
            return None

    async def test_notification_workflow(self):
        """Test complete notification workflow"""
        print(f"\n🔔 Testing Complete Real-time Notification Workflow")
        
        # Step 1: Connect doctor WebSocket to listen for emergency notifications
        doctor_id = self.users['doctor']['id']
        doctor_ws_endpoint = f"{self.ws_url}/ws/{doctor_id}"
        
        # Step 2: Connect provider WebSocket to listen for acceptance notifications
        provider_id = self.users['provider']['id']
        provider_ws_endpoint = f"{self.ws_url}/ws/{provider_id}"
        
        try:
            # Connect both WebSockets
            async with websockets.connect(doctor_ws_endpoint) as doctor_ws, \
                       websockets.connect(provider_ws_endpoint) as provider_ws:
                
                print(f"   ✅ Both WebSocket connections established")
                
                # Step 3: Create emergency appointment (should notify doctor)
                print(f"   📝 Creating emergency appointment...")
                appointment_id = self.create_emergency_appointment()
                
                if not appointment_id:
                    return False
                
                # Step 4: Listen for emergency notification on doctor WebSocket
                print(f"   👂 Listening for emergency notification...")
                try:
                    notification = await asyncio.wait_for(doctor_ws.recv(), timeout=5.0)
                    notification_data = json.loads(notification)
                    
                    if notification_data.get('type') == 'emergency_appointment':
                        print(f"   ✅ Doctor received emergency notification!")
                        print(f"      Patient: {notification_data.get('patient_name')}")
                        print(f"      Provider: {notification_data.get('provider_name')}")
                    else:
                        print(f"   ⚠️  Unexpected notification type: {notification_data.get('type')}")
                        
                except asyncio.TimeoutError:
                    print(f"   ❌ No emergency notification received within timeout")
                    return False
                
                # Step 5: Doctor accepts appointment (should notify provider)
                print(f"   ✅ Doctor accepting appointment...")
                if not self.accept_appointment(appointment_id):
                    return False
                
                # Step 6: Listen for acceptance notification on provider WebSocket
                print(f"   👂 Listening for acceptance notification...")
                try:
                    notification = await asyncio.wait_for(provider_ws.recv(), timeout=5.0)
                    notification_data = json.loads(notification)
                    
                    if notification_data.get('type') == 'appointment_accepted':
                        print(f"   ✅ Provider received acceptance notification!")
                        print(f"      Doctor: {notification_data.get('doctor_name')}")
                        print(f"      Patient: {notification_data.get('patient_name')}")
                    else:
                        print(f"   ⚠️  Unexpected notification type: {notification_data.get('type')}")
                        
                except asyncio.TimeoutError:
                    print(f"   ❌ No acceptance notification received within timeout")
                    return False
                
                # Step 7: Start video call (should send invitation notification)
                print(f"   🎬 Starting video call...")
                session_token = self.start_video_call(appointment_id)
                
                if not session_token:
                    return False
                
                # Step 8: Listen for video call invitation
                print(f"   👂 Listening for video call invitation...")
                try:
                    notification = await asyncio.wait_for(provider_ws.recv(), timeout=5.0)
                    notification_data = json.loads(notification)
                    
                    if notification_data.get('type') == 'video_call_invitation':
                        print(f"   ✅ Provider received video call invitation!")
                        print(f"      Caller: {notification_data.get('caller')}")
                        print(f"      Session Token: {notification_data.get('session_token')[:20]}...")
                    else:
                        print(f"   ⚠️  Unexpected notification type: {notification_data.get('type')}")
                        
                except asyncio.TimeoutError:
                    print(f"   ❌ No video call invitation received within timeout")
                    return False
                
                # Step 9: Test video call WebSocket signaling
                print(f"   📹 Testing video call WebSocket signaling...")
                video_call_success = await self.test_video_call_websocket(session_token)
                
                if video_call_success:
                    print(f"   ✅ Complete notification workflow successful!")
                    return True
                else:
                    print(f"   ❌ Video call WebSocket signaling failed")
                    return False
                
        except Exception as e:
            print(f"   ❌ Notification workflow failed: {str(e)}")
            return False

    async def test_multiple_users_video_call(self):
        """Test multiple users joining the same video call session"""
        print(f"\n👥 Testing Multiple Users in Video Call Session")
        
        # Create an appointment and start video call
        appointment_id = self.create_emergency_appointment()
        if not appointment_id:
            return False
        
        self.accept_appointment(appointment_id)
        session_token = self.start_video_call(appointment_id)
        
        if not session_token:
            return False
        
        ws_endpoint = f"{self.ws_url}/ws/video-call/{session_token}"
        
        try:
            # Connect multiple users to the same session
            async with websockets.connect(ws_endpoint) as ws1, \
                       websockets.connect(ws_endpoint) as ws2:
                
                print(f"   ✅ Two WebSocket connections established")
                
                # User 1 joins
                join_message_1 = {
                    "type": "join",
                    "userId": "doctor_123",
                    "userName": "Dr. Smith"
                }
                await ws1.send(json.dumps(join_message_1))
                
                # User 2 joins
                join_message_2 = {
                    "type": "join",
                    "userId": "provider_456",
                    "userName": "Provider Johnson"
                }
                await ws2.send(json.dumps(join_message_2))
                
                print(f"   ✅ Both users joined the session")
                
                # User 1 should receive notification about User 2 joining
                try:
                    notification = await asyncio.wait_for(ws1.recv(), timeout=3.0)
                    notification_data = json.loads(notification)
                    
                    if notification_data.get('type') == 'user-joined':
                        print(f"   ✅ User 1 received user-joined notification")
                        print(f"      New user: {notification_data.get('userName')}")
                    else:
                        print(f"   ⚠️  Unexpected notification: {notification_data}")
                        
                except asyncio.TimeoutError:
                    print(f"   ❌ User 1 did not receive join notification")
                    return False
                
                # Test WebRTC signaling between users
                offer_message = {
                    "type": "offer",
                    "target": "provider_456",
                    "sdp": "fake_offer_sdp_data"
                }
                await ws1.send(json.dumps(offer_message))
                
                # User 2 should receive the offer
                try:
                    offer_received = await asyncio.wait_for(ws2.recv(), timeout=3.0)
                    offer_data = json.loads(offer_received)
                    
                    if offer_data.get('type') == 'offer':
                        print(f"   ✅ WebRTC offer successfully relayed")
                        print(f"      From: {offer_data.get('from')}")
                    else:
                        print(f"   ❌ Unexpected message type: {offer_data.get('type')}")
                        return False
                        
                except asyncio.TimeoutError:
                    print(f"   ❌ WebRTC offer not received")
                    return False
                
                print(f"   ✅ Multiple users video call session working correctly!")
                return True
                
        except Exception as e:
            print(f"   ❌ Multiple users video call test failed: {str(e)}")
            return False

    async def run_all_tests(self):
        """Run all WebSocket and real-time notification tests"""
        print("🚀 Starting WebSocket and Real-time Notification Tests")
        print("=" * 80)
        
        # Login all users first
        if not self.login_all_users():
            print("❌ Failed to login users - cannot proceed with tests")
            return False
        
        self.tests_run = 0
        self.tests_passed = 0
        
        # Test 1: Basic WebSocket connections
        print(f"\n{'='*20} Basic WebSocket Connections {'='*20}")
        for role in ['admin', 'doctor', 'provider']:
            self.tests_run += 1
            if await self.test_websocket_connection(role):
                self.tests_passed += 1
        
        # Test 2: Complete notification workflow
        print(f"\n{'='*20} Real-time Notification Workflow {'='*20}")
        self.tests_run += 1
        if await self.test_notification_workflow():
            self.tests_passed += 1
        
        # Test 3: Multiple users in video call
        print(f"\n{'='*20} Multiple Users Video Call {'='*20}")
        self.tests_run += 1
        if await self.test_multiple_users_video_call():
            self.tests_passed += 1
        
        # Print results
        print(f"\n{'='*80}")
        print(f"📊 WebSocket Testing Results:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "No tests run")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All WebSocket and real-time notification tests passed!")
            return True
        else:
            print("⚠️  Some WebSocket tests failed - check logs above")
            return False

async def main():
    tester = WebSocketTester()
    success = await tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))