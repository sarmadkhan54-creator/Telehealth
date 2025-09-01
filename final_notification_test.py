import requests
import json
import asyncio
import websockets
import threading
import time
from datetime import datetime

class FinalNotificationTester:
    def __init__(self, base_url="https://telehealth-pwa.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.ws_url = f"wss://telehealth-pwa.preview.emergentagent.com/api/ws"
        self.tokens = {}
        self.users = {}
        self.test_results = {}
        
        # Test credentials
        self.demo_credentials = {
            "provider": {"username": "demo_provider", "password": "Demo123!"},
            "doctor": {"username": "demo_doctor", "password": "Demo123!"}
        }

    def login_users(self):
        """Login both users"""
        print("🔑 Logging in users...")
        
        for role, credentials in self.demo_credentials.items():
            response = requests.post(f"{self.api_url}/login", json=credentials)
            if response.status_code == 200:
                data = response.json()
                self.tokens[role] = data['access_token']
                self.users[role] = data['user']
                print(f"   ✅ {role}: {data['user']['full_name']}")
            else:
                print(f"   ❌ {role} login failed")
                return False
        return True

    def get_test_appointment(self):
        """Get a test appointment"""
        response = requests.get(
            f"{self.api_url}/appointments",
            headers={'Authorization': f'Bearer {self.tokens["provider"]}'}
        )
        
        if response.status_code == 200:
            appointments = response.json()
            for apt in appointments:
                if apt.get('doctor_id') and apt.get('status') == 'accepted':
                    return apt['id']
        return None

    async def test_single_notification(self, appointment_id, caller_role, target_role):
        """Test a single notification direction"""
        print(f"\n🎬 Testing {caller_role.title()} → {target_role.title()} notification...")
        
        target_user_id = self.users[target_role]['id']
        notification_received = False
        notification_data = None
        
        # WebSocket listener
        async def listen_for_notification():
            nonlocal notification_received, notification_data
            ws_url = f"{self.ws_url}/{target_user_id}"
            
            try:
                async with websockets.connect(ws_url) as websocket:
                    print(f"   🔌 {target_role} WebSocket connected")
                    
                    # Listen for 10 seconds
                    start_time = time.time()
                    while time.time() - start_time < 10:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                            notification = json.loads(message)
                            
                            if notification.get('type') == 'jitsi_call_invitation':
                                notification_received = True
                                notification_data = notification
                                print(f"   🔔 {target_role} received video call notification!")
                                print(f"      Caller: {notification.get('caller')}")
                                print(f"      Jitsi URL: {notification.get('jitsi_url')}")
                                break
                                
                        except asyncio.TimeoutError:
                            continue
                        except websockets.exceptions.ConnectionClosed:
                            break
                            
            except Exception as e:
                print(f"   ❌ {target_role} WebSocket error: {e}")
        
        # Start listener
        listener_task = asyncio.create_task(listen_for_notification())
        
        # Wait for connection
        await asyncio.sleep(1)
        
        # Trigger notification
        def trigger_call():
            time.sleep(0.5)
            response = requests.get(
                f"{self.api_url}/video-call/session/{appointment_id}",
                headers={'Authorization': f'Bearer {self.tokens[caller_role]}'}
            )
            
            if response.status_code == 200:
                print(f"   ✅ {caller_role} session created successfully")
            else:
                print(f"   ❌ {caller_role} session creation failed: {response.status_code}")
        
        # Start trigger in thread
        threading.Thread(target=trigger_call).start()
        
        # Wait for notification
        await asyncio.sleep(8)
        
        # Cancel listener
        listener_task.cancel()
        
        return notification_received, notification_data

    async def run_comprehensive_test(self):
        """Run comprehensive notification test"""
        print("🎯 COMPREHENSIVE VIDEO CALL NOTIFICATION TEST")
        print("=" * 70)
        
        # Setup
        if not self.login_users():
            return False
        
        appointment_id = self.get_test_appointment()
        if not appointment_id:
            print("❌ No test appointment available")
            return False
        
        print(f"\n📋 Test Configuration:")
        print(f"   Appointment ID: {appointment_id}")
        print(f"   Doctor: {self.users['doctor']['full_name']} ({self.users['doctor']['id']})")
        print(f"   Provider: {self.users['provider']['full_name']} ({self.users['provider']['id']})")
        
        # Test both directions
        test_cases = [
            ("doctor", "provider", "Doctor → Provider"),
            ("provider", "doctor", "Provider → Doctor")
        ]
        
        results = {}
        
        for caller_role, target_role, description in test_cases:
            print(f"\n" + "="*50)
            print(f"🎯 {description} Notification Test")
            print("="*50)
            
            received, data = await self.test_single_notification(appointment_id, caller_role, target_role)
            results[description] = {
                'received': received,
                'data': data
            }
            
            if received:
                print(f"   ✅ SUCCESS: {description} notification working!")
                
                # Validate notification payload
                required_fields = ['jitsi_url', 'caller', 'room_name', 'appointment_id']
                missing_fields = [field for field in required_fields if not data.get(field)]
                
                if missing_fields:
                    print(f"   ⚠️  Missing fields: {missing_fields}")
                else:
                    print(f"   ✅ All required notification fields present")
                    
            else:
                print(f"   ❌ FAILED: {description} notification not received")
        
        # Final summary
        print(f"\n" + "="*70)
        print("🎯 FINAL TEST RESULTS")
        print("="*70)
        
        working_directions = 0
        total_directions = len(test_cases)
        
        for description, result in results.items():
            status = "✅ WORKING" if result['received'] else "❌ FAILED"
            print(f"{status} - {description}")
            if result['received']:
                working_directions += 1
        
        print(f"\n📊 Summary:")
        print(f"   Working directions: {working_directions}/{total_directions}")
        print(f"   Success rate: {(working_directions/total_directions)*100:.0f}%")
        
        if working_directions == total_directions:
            print(f"\n🎉 EXCELLENT: All video call notifications working!")
            print(f"🔔 Sound notification system is fully operational")
            print(f"✅ Both doctor and provider can initiate calls with sound notifications")
        elif working_directions > 0:
            print(f"\n⚠️  PARTIAL: Some notifications working, some failing")
            print(f"🔔 Sound notification system has issues in one direction")
        else:
            print(f"\n❌ CRITICAL: No video call notifications working")
            print(f"🔔 Sound notification system is broken")
        
        # Additional diagnostic info
        print(f"\n🔍 Diagnostic Information:")
        print(f"   - WebSocket endpoints: /api/ws/{{user_id}}")
        print(f"   - Video call session endpoint: /api/video-call/session/{{appointment_id}}")
        print(f"   - Notification type: jitsi_call_invitation")
        print(f"   - Jitsi integration: Using meet.jit.si")
        
        return working_directions == total_directions

def main():
    tester = FinalNotificationTester()
    try:
        result = asyncio.run(tester.run_comprehensive_test())
        return result
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    print(f"\n{'='*70}")
    if success:
        print("🎉 VIDEO CALL NOTIFICATION SYSTEM: FULLY OPERATIONAL")
    else:
        print("❌ VIDEO CALL NOTIFICATION SYSTEM: ISSUES DETECTED")
    print(f"{'='*70}")
    exit(0 if success else 1)