import asyncio
import websockets
import json
import requests

async def test_notification_websocket():
    """Test the real notification WebSocket endpoint"""
    print("🔔 Testing notification WebSocket endpoint...")
    
    # Login to get a real user ID
    login_response = requests.post(
        "https://telehealth-pwa.preview.emergentagent.com/api/login",
        json={"username": "demo_doctor", "password": "Demo123!"}
    )
    
    if login_response.status_code != 200:
        print("   ❌ Failed to login")
        return False
    
    user_data = login_response.json()
    user_id = user_data['user']['id']
    print(f"   ✅ Logged in as doctor: {user_id}")
    
    try:
        async with websockets.connect(f"ws://localhost:8001/ws/{user_id}") as websocket:
            print("   ✅ Connected to notification WebSocket!")
            
            # Don't send anything initially - just listen for notifications
            print("   👂 Listening for notifications...")
            
            # Wait a bit to see if we get any notifications
            try:
                notification = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                print(f"   📨 Received notification: {notification}")
            except asyncio.TimeoutError:
                print("   ℹ️  No notifications received (expected)")
            
            # Now try sending a message
            test_message = {"type": "test", "message": "Hello from client"}
            await websocket.send(json.dumps(test_message))
            print("   ✅ Sent test message")
            
            return True
            
    except Exception as e:
        print(f"   ❌ Failed: {str(e)}")
        return False

async def test_video_call_websocket():
    """Test the video call WebSocket endpoint with proper protocol"""
    print("\n📹 Testing video call WebSocket endpoint...")
    
    # First create a video call session
    login_response = requests.post(
        "https://telehealth-pwa.preview.emergentagent.com/api/login",
        json={"username": "demo_doctor", "password": "Demo123!"}
    )
    
    if login_response.status_code != 200:
        print("   ❌ Failed to login")
        return False
    
    token = login_response.json()['access_token']
    
    # Create an appointment first
    provider_login = requests.post(
        "https://telehealth-pwa.preview.emergentagent.com/api/login",
        json={"username": "demo_provider", "password": "Demo123!"}
    )
    
    if provider_login.status_code != 200:
        print("   ❌ Failed to login provider")
        return False
    
    provider_token = provider_login.json()['access_token']
    
    # Create appointment
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
    
    appointment_response = requests.post(
        "https://telehealth-pwa.preview.emergentagent.com/api/appointments",
        json=appointment_data,
        headers={'Authorization': f'Bearer {provider_token}'}
    )
    
    if appointment_response.status_code != 200:
        print("   ❌ Failed to create appointment")
        return False
    
    appointment_id = appointment_response.json()['id']
    
    # Start video call
    video_call_response = requests.post(
        f"https://telehealth-pwa.preview.emergentagent.com/api/video-call/start/{appointment_id}",
        headers={'Authorization': f'Bearer {token}'}
    )
    
    if video_call_response.status_code != 200:
        print("   ❌ Failed to start video call")
        return False
    
    session_token = video_call_response.json()['session_token']
    print(f"   ✅ Video call started: {session_token[:20]}...")
    
    try:
        async with websockets.connect(f"ws://localhost:8001/ws/video-call/{session_token}") as websocket:
            print("   ✅ Connected to video call WebSocket!")
            
            # Send the required join message first
            join_message = {
                "type": "join",
                "userId": "test_doctor_123",
                "userName": "Test Doctor"
            }
            await websocket.send(json.dumps(join_message))
            print("   ✅ Sent join message")
            
            # Send a WebRTC offer
            offer_message = {
                "type": "offer",
                "target": "test_provider_456",
                "sdp": "fake_offer_sdp_data"
            }
            await websocket.send(json.dumps(offer_message))
            print("   ✅ Sent WebRTC offer")
            
            return True
            
    except Exception as e:
        print(f"   ❌ Failed: {str(e)}")
        return False

async def main():
    print("🚀 Testing Real WebSocket Endpoints")
    print("=" * 50)
    
    # Test notification WebSocket
    notification_success = await test_notification_websocket()
    
    # Test video call WebSocket
    video_call_success = await test_video_call_websocket()
    
    print(f"\n{'='*50}")
    print(f"📊 Results:")
    print(f"   Notification WebSocket: {'✅ Working' if notification_success else '❌ Failed'}")
    print(f"   Video Call WebSocket: {'✅ Working' if video_call_success else '❌ Failed'}")
    
    if notification_success and video_call_success:
        print("🎉 Both WebSocket endpoints are working!")
        return 0
    else:
        print("⚠️  Some WebSocket endpoints failed")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))