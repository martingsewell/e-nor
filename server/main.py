"""
E-NOR Robot Server
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import List

from .secrets import router as secrets_router
from .chat import router as chat_router
from .code_request import router as code_router
from .memories import router as memories_router

app = FastAPI(title="E-NOR", version="0.2.0")

# Add CORS middleware for API requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(secrets_router)
app.include_router(chat_router)
app.include_router(code_router)
app.include_router(memories_router)

connected_clients: List[WebSocket] = []

robot_state = {
    "emotion": "happy",
    "disco_mode": False,
}

WEB_DIR = Path(__file__).parent.parent / "web"


@app.get("/")
async def root():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "robot": "E-NOR", "clients": len(connected_clients)}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    print(f"📱 Client connected. Total: {len(connected_clients)}")

    await websocket.send_json({"type": "state", "data": robot_state})

    try:
        while True:
            data = await websocket.receive_json()
            await handle_message(data, websocket)
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        print(f"📱 Client disconnected. Total: {len(connected_clients)}")


async def handle_message(data: dict, sender: WebSocket):
    msg_type = data.get("type", "")

    if msg_type == "emotion":
        robot_state["emotion"] = data.get("emotion", "happy")
        await broadcast({"type": "emotion", "emotion": robot_state["emotion"]})
        print(f"😊 Emotion: {robot_state['emotion']}")

    elif msg_type == "disco":
        robot_state["disco_mode"] = data.get("enabled", False)
        await broadcast({"type": "disco", "enabled": robot_state["disco_mode"]})
        print(f"🕺 Disco: {robot_state['disco_mode']}")

    elif msg_type == "ping":
        await sender.send_json({"type": "pong"})


async def broadcast(message: dict):
    for client in connected_clients:
        try:
            await client.send_json(message)
        except:
            pass
