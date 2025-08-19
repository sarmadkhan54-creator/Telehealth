from fastapi import FastAPI, WebSocket
import uvicorn
import asyncio

# Create a simple test app
test_app = FastAPI()

@test_app.websocket("/test-ws")
async def test_websocket(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Hello from test WebSocket!")
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except:
        pass

if __name__ == "__main__":
    print("🧪 Starting simple WebSocket test server on port 8002...")
    uvicorn.run(test_app, host="0.0.0.0", port=8002)