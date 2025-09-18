import asyncio
import websockets
import json
import requests
import threading
import time
from datetime import datetime

class WebSocketNotificationTester:
    def __init__(self, base_url="https://calltrack-health.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.ws_url = f"wss://telehealth-pwa.preview.emergentagent.com/api/ws"
        self.tokens = {}
        self.users = {}
        self.received_notifications = []
        self.websocket_connections = {}
        
        # Test credentials
        self.demo_credentials = {
            "provider": {"username": "demo_provider", "password": "Demo123!"},
            "doctor": {"username": "demo_doctor", "password": "Demo123!"}
        }

    def login_users(self):
        """Login both users and get tokens"""
        print("🔑 Logging in users...")
        
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
                    print(f"   ✅ {role.title()} logged in: {data['user']['id']}")
                else:
                    print(f"   ❌ {role.title()} login failed: {response.status_code}")
                    return False
            except Exception as e:
                print(f"   ❌ {role.title()} login error: {e}")
                return False
        
        return True

    def create_test_appointment(self):
        """Create a test appointment"""
        print("📅 Creating test appointment...")
        
        appointment_data = {
            "patient": {
                "name": "WebSocket Test Patient",
                "age": 30,
                "gender": "Male",
                "vitals": {"blood_pressure": "120/80", "heart_rate": 70},
                "consultation_reason": "WebSocket notification testing"
            },
            "appointment_type": "non_emergency",
            "consultation_notes": "WebSocket test"
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/appointments",
                json=appointment_data,
                headers={'Authorization': f'Bearer {self.tokens["provider"]}'},
                timeout=10
            )
            
            if response.status_code == 200:
                appointment_id = response.json().get('id')
                print(f"   ✅ Created appointment: {appointment_id}")
                return appointment_id
            else:
                print(f"   ❌ Appointment creation failed: {response.status_code}")
                return None
        except Exception as e:
            print(f"   ❌ Appointment creation error: {e}")
            return None

    async def websocket_listener(self, user_id, role):
        """Listen for WebSocket notifications"""
        ws_url = f"{self.ws_url}/{user_id}"
        print(f"🔌 Connecting {role} WebSocket: {ws_url}")
        
        try:
            async with websockets.connect(ws_url) as websocket:
                print(f"   ✅ {role} WebSocket connected")
                self.websocket_connections[role] = websocket
                
                # Listen for messages for 30 seconds
                try:
                    async for message in websocket:
                        notification = json.loads(message)
                        self.received_notifications.append({
                            'role': role,
                            'user_id': user_id,
                            'notification': notification,
                            'timestamp': datetime.now().isoformat()
                        })
                        print(f"   📨 {role} received: {notification.get('type', 'unknown')} notification")
                        
                        # Check if it's a video call invitation
                        if notification.get('type') == 'jitsi_call_invitation':
                            print(f"   🔔 VIDEO CALL NOTIFICATION RECEIVED!")
                            print(f"      Caller: {notification.get('caller', 'unknown')}")
                            print(f"      Jitsi URL: {notification.get('jitsi_url', 'missing')}")
                            print(f"      Room: {notification.get('room_name', 'missing')}")
                            
                except websockets.exceptions.ConnectionClosed:
                    print(f"   🔌 {role} WebSocket connection closed")
                except asyncio.TimeoutError:
                    print(f"   ⏰ {role} WebSocket timeout")
                    
        except Exception as e:
            print(f"   ❌ {role} WebSocket error: {e}")

    def trigger_video_call_notification(self, appointment_id, caller_role):
        """Trigger a video call notification by creating a session"""
        print(f"🎬 Triggering video call notification from {caller_role}...")
        
        try:
            # Use the session endpoint which triggers notifications
            response = requests.get(
                f"{self.api_url}/video-call/session/{appointment_id}",
                headers={'Authorization': f'Bearer {self.tokens[caller_role]}'},
                timeout=10
            )
            
            if response.status_code == 200:
                session_data = response.json()
                print(f"   ✅ {caller_role} session created")
                print(f"   📺 Jitsi URL: {session_data.get('jitsi_url')}")
                print(f"   🔔 Notification should be sent to other participant")
                return True
            else:
                print(f"   ❌ Session creation failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Session creation error: {e}")
            return False

    async def run_websocket_test(self):
        """Run the complete WebSocket notification test"""
        print("🎯 WEBSOCKET NOTIFICATION TESTING")
        print("=" * 60)
        
        # Setup
        if not self.login_users():
            print("❌ Login failed")
            return False
        
        appointment_id = self.create_test_appointment()
        if not appointment_id:
            print("❌ Appointment creation failed")
            return False
        
        # Start WebSocket listeners for both users
        doctor_id = self.users['doctor']['id']
        provider_id = self.users['provider']['id']
        
        print(f"\n🔌 Starting WebSocket listeners...")
        
        # Create tasks for WebSocket listeners
        doctor_task = asyncio.create_task(
            self.websocket_listener(doctor_id, 'doctor')
        )
        provider_task = asyncio.create_task(
            self.websocket_listener(provider_id, 'provider')
        )
        
        # Wait a moment for connections to establish
        await asyncio.sleep(2)
        
        # Test 1: Doctor triggers notification to provider
        print(f"\n🎬 TEST 1: Doctor → Provider Notification")
        print("-" * 40)
        
        # Clear previous notifications
        self.received_notifications.clear()
        
        # Trigger notification in a separate thread
        def trigger_doctor_call():
            time.sleep(1)  # Small delay
            self.trigger_video_call_notification(appointment_id, 'doctor')
        
        trigger_thread = threading.Thread(target=trigger_doctor_call)
        trigger_thread.start()
        
        # Wait for notification
        await asyncio.sleep(5)
        
        # Check if provider received notification
        provider_notifications = [n for n in self.received_notifications if n['role'] == 'provider']
        video_call_notifications = [n for n in provider_notifications 
                                  if n['notification'].get('type') == 'jitsi_call_invitation']
        
        if video_call_notifications:
            print("   ✅ Provider received video call notification!")
            notification = video_call_notifications[0]['notification']
            print(f"   📋 Notification details:")
            print(f"      Type: {notification.get('type')}")
            print(f"      Caller: {notification.get('caller')}")
            print(f"      Jitsi URL: {notification.get('jitsi_url')}")
            print(f"      Room: {notification.get('room_name')}")
        else:
            print("   ❌ Provider did not receive video call notification")
            print(f"   📊 Total notifications received: {len(provider_notifications)}")
        
        # Test 2: Provider triggers notification to doctor
        print(f"\n🎬 TEST 2: Provider → Doctor Notification")
        print("-" * 40)
        
        # Clear previous notifications
        self.received_notifications.clear()
        
        # Trigger notification in a separate thread
        def trigger_provider_call():
            time.sleep(1)  # Small delay
            self.trigger_video_call_notification(appointment_id, 'provider')
        
        trigger_thread = threading.Thread(target=trigger_provider_call)
        trigger_thread.start()
        
        # Wait for notification
        await asyncio.sleep(5)
        
        # Check if doctor received notification
        doctor_notifications = [n for n in self.received_notifications if n['role'] == 'doctor']
        video_call_notifications = [n for n in doctor_notifications 
                                  if n['notification'].get('type') == 'jitsi_call_invitation']
        
        if video_call_notifications:
            print("   ✅ Doctor received video call notification!")
            notification = video_call_notifications[0]['notification']
            print(f"   📋 Notification details:")
            print(f"      Type: {notification.get('type')}")
            print(f"      Caller: {notification.get('caller')}")
            print(f"      Jitsi URL: {notification.get('jitsi_url')}")
            print(f"      Room: {notification.get('room_name')}")
        else:
            print("   ❌ Doctor did not receive video call notification")
            print(f"   📊 Total notifications received: {len(doctor_notifications)}")
        
        # Cancel tasks
        doctor_task.cancel()
        provider_task.cancel()
        
        # Summary
        print(f"\n📊 WEBSOCKET NOTIFICATION TEST SUMMARY")
        print("=" * 50)
        print(f"Total notifications received: {len(self.received_notifications)}")
        
        video_notifications = [n for n in self.received_notifications 
                             if n['notification'].get('type') == 'jitsi_call_invitation']
        print(f"Video call notifications: {len(video_notifications)}")
        
        if video_notifications:
            print("✅ WebSocket video call notifications are working!")
            print("🔔 Sound notification system should be operational")
            
            # Check notification payload completeness
            for notification in video_notifications:
                notif_data = notification['notification']
                required_fields = ['jitsi_url', 'caller', 'room_name', 'appointment_id']
                missing_fields = [field for field in required_fields if not notif_data.get(field)]
                
                if missing_fields:
                    print(f"⚠️  Missing fields in notification: {missing_fields}")
                else:
                    print("✅ All required notification fields present")
        else:
            print("❌ No video call notifications received")
            print("🔔 Sound notification system may have issues")
        
        return len(video_notifications) > 0

def main():
    """Main function to run the WebSocket test"""
    tester = WebSocketNotificationTester()
    
    try:
        # Run the async test
        result = asyncio.run(tester.run_websocket_test())
        return result
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)