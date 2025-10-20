import requests
import json
import asyncio
import websockets
import threading
import time
from datetime import datetime

class NotificationDebugTester:
    def __init__(self, base_url="https://medconnect-live-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.ws_url = f"wss://telehealth-pwa.preview.emergentagent.com/api/ws"
        self.tokens = {}
        self.users = {}
        self.notifications = []
        
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
                print(f"   ✅ {role}: {data['user']['full_name']} ({data['user']['id']})")
            else:
                print(f"   ❌ {role} login failed")
                return False
        return True

    def get_appointment_with_doctor(self):
        """Get an appointment that has a doctor assigned"""
        print("📅 Finding appointment with doctor assigned...")
        
        response = requests.get(
            f"{self.api_url}/appointments",
            headers={'Authorization': f'Bearer {self.tokens["provider"]}'}
        )
        
        if response.status_code == 200:
            appointments = response.json()
            for apt in appointments:
                if apt.get('doctor_id') and apt.get('status') == 'accepted':
                    print(f"   ✅ Found appointment: {apt['id']}")
                    print(f"      Provider: {apt.get('provider_id')}")
                    print(f"      Doctor: {apt.get('doctor_id')}")
                    print(f"      Status: {apt.get('status')}")
                    return apt['id']
            
            print("   ⚠️  No appointments with assigned doctors found")
            # Create and accept an appointment
            return self.create_and_accept_appointment()
        else:
            print(f"   ❌ Failed to get appointments: {response.status_code}")
            return None

    def create_and_accept_appointment(self):
        """Create an appointment and have doctor accept it"""
        print("📝 Creating new appointment and having doctor accept it...")
        
        # Create appointment
        appointment_data = {
            "patient": {
                "name": "Debug Test Patient",
                "age": 35,
                "gender": "Male",
                "vitals": {"blood_pressure": "120/80", "heart_rate": 72},
                "consultation_reason": "Debug notification testing"
            },
            "appointment_type": "non_emergency",
            "consultation_notes": "Debug test appointment"
        }
        
        response = requests.post(
            f"{self.api_url}/appointments",
            json=appointment_data,
            headers={'Authorization': f'Bearer {self.tokens["provider"]}'}
        )
        
        if response.status_code != 200:
            print(f"   ❌ Failed to create appointment: {response.status_code}")
            return None
        
        appointment_id = response.json()['id']
        print(f"   ✅ Created appointment: {appointment_id}")
        
        # Doctor accepts appointment
        update_data = {
            "status": "accepted",
            "doctor_id": self.users['doctor']['id']
        }
        
        response = requests.put(
            f"{self.api_url}/appointments/{appointment_id}",
            json=update_data,
            headers={'Authorization': f'Bearer {self.tokens["doctor"]}'}
        )
        
        if response.status_code == 200:
            print(f"   ✅ Doctor accepted appointment")
            return appointment_id
        else:
            print(f"   ❌ Doctor failed to accept appointment: {response.status_code}")
            return None

    async def websocket_listener(self, user_id, role, duration=15):
        """Listen for WebSocket notifications"""
        ws_url = f"{self.ws_url}/{user_id}"
        print(f"🔌 Starting {role} WebSocket listener: {ws_url}")
        
        try:
            async with websockets.connect(ws_url) as websocket:
                print(f"   ✅ {role} WebSocket connected")
                
                start_time = time.time()
                while time.time() - start_time < duration:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        notification = json.loads(message)
                        
                        self.notifications.append({
                            'role': role,
                            'user_id': user_id,
                            'notification': notification,
                            'timestamp': datetime.now().isoformat()
                        })
                        
                        print(f"   📨 {role} received: {notification.get('type', 'unknown')}")
                        
                        if notification.get('type') == 'jitsi_call_invitation':
                            print(f"      🔔 VIDEO CALL INVITATION!")
                            print(f"         Caller: {notification.get('caller')}")
                            print(f"         Caller Role: {notification.get('caller_role')}")
                            print(f"         Jitsi URL: {notification.get('jitsi_url')}")
                            
                    except asyncio.TimeoutError:
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        print(f"   🔌 {role} WebSocket closed")
                        break
                        
        except Exception as e:
            print(f"   ❌ {role} WebSocket error: {e}")

    def trigger_video_call_session(self, appointment_id, caller_role):
        """Trigger video call session creation"""
        print(f"🎬 {caller_role.title()} creating video call session...")
        
        response = requests.get(
            f"{self.api_url}/video-call/session/{appointment_id}",
            headers={'Authorization': f'Bearer {self.tokens[caller_role]}'}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Session created: {data.get('room_name')}")
            return True
        else:
            print(f"   ❌ Session creation failed: {response.status_code}")
            try:
                error = response.json()
                print(f"      Error: {error}")
            except:
                print(f"      Response: {response.text}")
            return False

    async def run_debug_test(self):
        """Run comprehensive debug test"""
        print("🎯 NOTIFICATION DEBUG TEST")
        print("=" * 60)
        
        # Setup
        if not self.login_users():
            return False
        
        appointment_id = self.get_appointment_with_doctor()
        if not appointment_id:
            return False
        
        doctor_id = self.users['doctor']['id']
        provider_id = self.users['provider']['id']
        
        print(f"\n🔍 Test Setup:")
        print(f"   Appointment ID: {appointment_id}")
        print(f"   Doctor ID: {doctor_id}")
        print(f"   Provider ID: {provider_id}")
        
        # Start WebSocket listeners
        print(f"\n🔌 Starting WebSocket listeners...")
        
        doctor_task = asyncio.create_task(
            self.websocket_listener(doctor_id, 'doctor', 20)
        )
        provider_task = asyncio.create_task(
            self.websocket_listener(provider_id, 'provider', 20)
        )
        
        # Wait for connections
        await asyncio.sleep(2)
        
        # Clear notifications
        self.notifications.clear()
        
        # Test 1: Doctor initiates → Provider should receive notification
        print(f"\n🎬 TEST 1: Doctor → Provider")
        print("-" * 30)
        
        def doctor_trigger():
            time.sleep(1)
            self.trigger_video_call_session(appointment_id, 'doctor')
        
        threading.Thread(target=doctor_trigger).start()
        await asyncio.sleep(5)
        
        provider_notifications = [n for n in self.notifications if n['role'] == 'provider']
        video_notifications = [n for n in provider_notifications 
                             if n['notification'].get('type') == 'jitsi_call_invitation']
        
        print(f"   Provider notifications: {len(provider_notifications)}")
        print(f"   Video call notifications: {len(video_notifications)}")
        
        if video_notifications:
            print("   ✅ Doctor → Provider notification WORKING")
        else:
            print("   ❌ Doctor → Provider notification FAILED")
        
        # Clear notifications
        self.notifications.clear()
        
        # Test 2: Provider initiates → Doctor should receive notification
        print(f"\n🎬 TEST 2: Provider → Doctor")
        print("-" * 30)
        
        def provider_trigger():
            time.sleep(1)
            self.trigger_video_call_session(appointment_id, 'provider')
        
        threading.Thread(target=provider_trigger).start()
        await asyncio.sleep(5)
        
        doctor_notifications = [n for n in self.notifications if n['role'] == 'doctor']
        video_notifications = [n for n in doctor_notifications 
                             if n['notification'].get('type') == 'jitsi_call_invitation']
        
        print(f"   Doctor notifications: {len(doctor_notifications)}")
        print(f"   Video call notifications: {len(video_notifications)}")
        
        if video_notifications:
            print("   ✅ Provider → Doctor notification WORKING")
        else:
            print("   ❌ Provider → Doctor notification FAILED")
            
            # Debug: Check appointment details
            print(f"\n🔍 DEBUG: Checking appointment details...")
            response = requests.get(
                f"{self.api_url}/appointments/{appointment_id}",
                headers={'Authorization': f'Bearer {self.tokens["provider"]}'}
            )
            
            if response.status_code == 200:
                apt_data = response.json()
                print(f"   Appointment provider_id: {apt_data.get('provider_id')}")
                print(f"   Appointment doctor_id: {apt_data.get('doctor_id')}")
                print(f"   Current provider ID: {provider_id}")
                print(f"   Current doctor ID: {doctor_id}")
                
                if apt_data.get('doctor_id') == doctor_id:
                    print("   ✅ Doctor ID matches - should receive notification")
                else:
                    print("   ❌ Doctor ID mismatch - won't receive notification")
            else:
                print(f"   ❌ Could not get appointment details: {response.status_code}")
        
        # Cancel tasks
        doctor_task.cancel()
        provider_task.cancel()
        
        # Summary
        print(f"\n📊 SUMMARY")
        print("=" * 30)
        
        all_notifications = len([n for n in self.notifications 
                               if n['notification'].get('type') == 'jitsi_call_invitation'])
        
        print(f"Total video call notifications: {all_notifications}")
        
        if all_notifications >= 2:
            print("✅ Bi-directional notifications WORKING")
            return True
        elif all_notifications == 1:
            print("⚠️  Only one direction working")
            return False
        else:
            print("❌ No video call notifications working")
            return False

def main():
    tester = NotificationDebugTester()
    try:
        result = asyncio.run(tester.run_debug_test())
        return result
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)