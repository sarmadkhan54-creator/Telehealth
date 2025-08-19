import asyncio
import websockets
import json

async def test_simple_ws():
    print("🧪 Testing simple WebSocket server...")
    
    try:
        async with websockets.connect("ws://localhost:8002/test-ws") as websocket:
            print("   ✅ Connected to test WebSocket server!")
            
            # Receive initial message
            initial_msg = await websocket.recv()
            print(f"   📨 Received: {initial_msg}")
            
            # Send a test message
            await websocket.send("Hello test server!")
            
            # Receive echo
            echo_msg = await websocket.recv()
            print(f"   📨 Echo: {echo_msg}")
            
            return True
            
    except Exception as e:
        print(f"   ❌ Failed: {str(e)}")
        return False

async def main():
    success = await test_simple_ws()
    if success:
        print("🎉 Simple WebSocket test successful!")
    else:
        print("❌ Simple WebSocket test failed!")
    
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))