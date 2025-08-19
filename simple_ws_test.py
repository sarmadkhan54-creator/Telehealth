import asyncio
import websockets
import json

async def test_simple_websocket():
    """Test WebSocket connection with a simple user ID"""
    print("🔌 Testing simple WebSocket connection...")
    
    # Try different possible endpoints
    endpoints_to_try = [
        "ws://localhost:8001/ws/test-user-123",
        "ws://localhost:8001/api/ws/test-user-123",
        "wss://greenstar-health.preview.emergentagent.com/ws/test-user-123",
        "wss://greenstar-health.preview.emergentagent.com/api/ws/test-user-123"
    ]
    
    for endpoint in endpoints_to_try:
        print(f"\n   Trying: {endpoint}")
        try:
            async with websockets.connect(endpoint, timeout=5) as websocket:
                print(f"   ✅ Connected successfully!")
                
                # Send a test message
                test_message = {"type": "test", "message": "Hello"}
                await websocket.send(json.dumps(test_message))
                print(f"   ✅ Message sent")
                
                # Try to receive a response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    print(f"   📨 Response: {response}")
                except asyncio.TimeoutError:
                    print(f"   ℹ️  No response (expected for notification endpoint)")
                
                return True
                
        except Exception as e:
            print(f"   ❌ Failed: {str(e)}")
    
    return False

async def test_video_call_websocket():
    """Test video call WebSocket with a dummy session token"""
    print("\n📹 Testing video call WebSocket connection...")
    
    # Try different possible endpoints
    endpoints_to_try = [
        "ws://localhost:8001/ws/video-call/dummy-session-token",
        "ws://localhost:8001/api/ws/video-call/dummy-session-token",
        "wss://greenstar-health.preview.emergentagent.com/ws/video-call/dummy-session-token",
        "wss://greenstar-health.preview.emergentagent.com/api/ws/video-call/dummy-session-token"
    ]
    
    for endpoint in endpoints_to_try:
        print(f"\n   Trying: {endpoint}")
        try:
            async with websockets.connect(endpoint, timeout=5) as websocket:
                print(f"   ✅ Connected successfully!")
                
                # Send join message
                join_message = {
                    "type": "join",
                    "userId": "test-user-123",
                    "userName": "Test User"
                }
                await websocket.send(json.dumps(join_message))
                print(f"   ✅ Join message sent")
                
                return True
                
        except Exception as e:
            print(f"   ❌ Failed: {str(e)}")
    
    return False

async def main():
    print("🚀 Simple WebSocket Connection Test")
    print("=" * 50)
    
    # Test basic WebSocket
    ws_success = await test_simple_websocket()
    
    # Test video call WebSocket
    video_ws_success = await test_video_call_websocket()
    
    print(f"\n{'='*50}")
    print(f"📊 Results:")
    print(f"   Basic WebSocket: {'✅ Working' if ws_success else '❌ Failed'}")
    print(f"   Video Call WebSocket: {'✅ Working' if video_ws_success else '❌ Failed'}")
    
    if ws_success or video_ws_success:
        print("🎉 At least one WebSocket endpoint is working!")
        return 0
    else:
        print("❌ No WebSocket endpoints are accessible")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))