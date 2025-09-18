import asyncio
import websockets
import json
import requests
import sys

class LocalWebSocketTester:
    def __init__(self):
        # Test against local backend directly
        self.api_url = "https://calltrack-health.preview.emergentagent.com/api"
        self.local_ws_url = "ws://localhost:8001"  # Direct connection to backend
        self.tokens = {}
        self.users = {}
        
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

    async def test_local_websocket_connection(self, user_role):
        """Test WebSocket connection to local backend"""
        print(f"\n🔌 Testing Local WebSocket Connection for {user_role.title()}")
        
        if user_role not in self.users:
            print(f"   ❌ No user data for {user_role}")
            return False
        
        user_id = self.users[user_role]['id']
        ws_endpoint = f"{self.local_ws_url}/ws/{user_id}"
        
        try:
            async with websockets.connect(ws_endpoint) as websocket:
                print(f"   ✅ Local WebSocket connected for {user_role}")
                
                # Test sending a message
                test_message = {"type": "test", "message": "Hello Local WebSocket"}
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
            print(f"   ❌ Local WebSocket connection failed: {str(e)}")
            return False

    async def test_local_video_call_websocket(self):
        """Test video call WebSocket to local backend"""
        print(f"\n📹 Testing Local Video Call WebSocket")
        
        # Create appointment and get session token
        appointment_data = {
            "patient": {
                "name": "WebSocket Test Patient",
                "age": 35,
                "gender": "Male",
                "vitals": {"blood_pressure": "120/80", "heart_rate": 72},
                "consultation_reason": "WebSocket testing"
            },
            "appointment_type": "non_emergency",
            "consultation_notes": "Testing WebSocket functionality"
        }
        
        # Create appointment
        response = requests.post(
            f"{self.api_url}/appointments",
            json=appointment_data,
            headers={'Authorization': f'Bearer {self.tokens["provider"]}'},
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"   ❌ Failed to create appointment: {response.status_code}")
            return False
        
        appointment_id = response.json().get('id')
        
        # Start video call
        response = requests.post(
            f"{self.api_url}/video-call/start/{appointment_id}",
            headers={'Authorization': f'Bearer {self.tokens["doctor"]}'},
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"   ❌ Failed to start video call: {response.status_code}")
            return False
        
        session_token = response.json().get('session_token')
        print(f"   ✅ Video call started, session token: {session_token[:20]}...")
        
        # Test WebSocket connection
        ws_endpoint = f"{self.local_ws_url}/ws/video-call/{session_token}"
        
        try:
            async with websockets.connect(ws_endpoint) as websocket:
                print(f"   ✅ Local video call WebSocket connected")
                
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
                
                return True
                
        except Exception as e:
            print(f"   ❌ Local video call WebSocket failed: {str(e)}")
            return False

    async def test_notification_system_locally(self):
        """Test real-time notifications using local WebSocket"""
        print(f"\n🔔 Testing Local Real-time Notification System")
        
        # Connect doctor WebSocket
        doctor_id = self.users['doctor']['id']
        doctor_ws_endpoint = f"{self.local_ws_url}/ws/{doctor_id}"
        
        try:
            async with websockets.connect(doctor_ws_endpoint) as doctor_ws:
                print(f"   ✅ Doctor WebSocket connected locally")
                
                # Create emergency appointment (should notify doctor)
                emergency_data = {
                    "patient": {
                        "name": "Emergency Notification Test",
                        "age": 45,
                        "gender": "Female",
                        "vitals": {
                            "blood_pressure": "180/120",
                            "heart_rate": 110,
                            "temperature": 102.5
                        },
                        "consultation_reason": "Severe chest pain - notification test"
                    },
                    "appointment_type": "emergency",
                    "consultation_notes": "URGENT: Testing emergency notifications"
                }
                
                print(f"   📝 Creating emergency appointment...")
                response = requests.post(
                    f"{self.api_url}/appointments",
                    json=emergency_data,
                    headers={'Authorization': f'Bearer {self.tokens["provider"]}'},
                    timeout=10
                )
                
                if response.status_code != 200:
                    print(f"   ❌ Failed to create emergency appointment: {response.status_code}")
                    return False
                
                appointment_id = response.json().get('id')
                print(f"   ✅ Emergency appointment created: {appointment_id}")
                
                # Listen for emergency notification
                print(f"   👂 Listening for emergency notification...")
                try:
                    notification = await asyncio.wait_for(doctor_ws.recv(), timeout=5.0)
                    notification_data = json.loads(notification)
                    
                    if notification_data.get('type') == 'emergency_appointment':
                        print(f"   ✅ Doctor received emergency notification!")
                        print(f"      Patient: {notification_data.get('patient_name')}")
                        print(f"      Provider: {notification_data.get('provider_name')}")
                        print(f"      Reason: {notification_data.get('consultation_reason')}")
                        return True
                    else:
                        print(f"   ⚠️  Unexpected notification type: {notification_data.get('type')}")
                        print(f"      Full notification: {notification_data}")
                        return False
                        
                except asyncio.TimeoutError:
                    print(f"   ❌ No emergency notification received within timeout")
                    return False
                
        except Exception as e:
            print(f"   ❌ Local notification test failed: {str(e)}")
            return False

    async def run_local_tests(self):
        """Run local WebSocket tests"""
        print("🚀 Starting Local WebSocket Tests")
        print("=" * 60)
        
        # Login all users first
        if not self.login_all_users():
            print("❌ Failed to login users - cannot proceed with tests")
            return False
        
        tests_run = 0
        tests_passed = 0
        
        # Test 1: Basic local WebSocket connections
        print(f"\n{'='*15} Local WebSocket Connections {'='*15}")
        for role in ['admin', 'doctor', 'provider']:
            tests_run += 1
            if await self.test_local_websocket_connection(role):
                tests_passed += 1
        
        # Test 2: Local video call WebSocket
        print(f"\n{'='*15} Local Video Call WebSocket {'='*15}")
        tests_run += 1
        if await self.test_local_video_call_websocket():
            tests_passed += 1
        
        # Test 3: Local notification system
        print(f"\n{'='*15} Local Notification System {'='*15}")
        tests_run += 1
        if await self.test_notification_system_locally():
            tests_passed += 1
        
        # Print results
        print(f"\n{'='*60}")
        print(f"📊 Local WebSocket Testing Results:")
        print(f"   Tests Run: {tests_run}")
        print(f"   Tests Passed: {tests_passed}")
        print(f"   Success Rate: {(tests_passed/tests_run*100):.1f}%" if tests_run > 0 else "No tests run")
        
        if tests_passed == tests_run:
            print("🎉 All local WebSocket tests passed!")
            return True
        else:
            print("⚠️  Some local WebSocket tests failed")
            return False

async def main():
    tester = LocalWebSocketTester()
    success = await tester.run_local_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))