"""
E-NOR Robot Server
Core server with extension support and parent dashboard
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import List

# Import routers from core modules
from .secrets import router as secrets_router
from .chat import router as chat_router
from .code_request import router as code_router
from .memories import router as memories_router
from .code_requests_log import router as requests_router
from .version_control import router as versions_router
from .config import router as config_router
from .plugin_loader import router as extensions_router, init_extensions, get_all_extensions
from .extension_request import router as extension_request_router
from .extension_versions import router as extension_versions_router
from .motor_control import router as motor_router
from .deployment import router as deployment_router

app = FastAPI(title="E-NOR", version="1.0.0")

# Add CORS middleware for API requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include core routers
app.include_router(secrets_router)
app.include_router(chat_router)
app.include_router(code_router)
app.include_router(memories_router)
app.include_router(requests_router)
app.include_router(versions_router)
app.include_router(config_router)
app.include_router(extensions_router)
app.include_router(extension_request_router)
app.include_router(extension_versions_router)
app.include_router(motor_router)
app.include_router(deployment_router)

connected_clients: List[WebSocket] = []

robot_state = {
    "emotion": "happy",
    "disco_mode": False,
    "active_mode": None,  # For extension modes like "cat_mode"
    "active_overlays": [],  # For face overlays
}

# Directory paths
CORE_WEB_DIR = Path(__file__).parent.parent / "web"
PROJECT_ROOT = Path(__file__).parent.parent.parent
EXTENSIONS_DIR = PROJECT_ROOT / "extensions"


@app.on_event("startup")
async def startup_event():
    """Initialize extensions and other startup tasks"""
    print("E-NOR server starting up...")
    init_extensions()
    print(f"Loaded {len(get_all_extensions())} extensions")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    print("E-NOR server shutting down...")
    # Clean up motor GPIO
    from hardware.motors import cleanup as motor_cleanup
    motor_cleanup()
    print("Cleanup complete")


@app.get("/")
async def root():
    """Serve the main face UI"""
    return FileResponse(CORE_WEB_DIR / "index.html")


@app.get("/admin")
async def admin_dashboard():
    """Serve the parent dashboard"""
    admin_file = CORE_WEB_DIR / "admin.html"
    if admin_file.exists():
        return FileResponse(admin_file)
    return HTMLResponse("<h1>Admin Dashboard</h1><p>Coming soon...</p>")


@app.get("/health")
async def health():
    """Health check endpoint"""
    from .version_control import load_versions
    from .config import get_robot_name, get_child_name, is_setup_complete

    versions = load_versions()
    current_version = next((v for v in versions if v.get("is_current")), None)

    return {
        "status": "ok",
        "robot": get_robot_name(),
        "child": get_child_name(),
        "setup_complete": is_setup_complete(),
        "clients": len(connected_clients),
        "extensions_loaded": len(get_all_extensions()),
        "version": current_version["version_number"] if current_version else "unknown",
        "version_description": current_version["description"] if current_version else "unknown"
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await websocket.accept()
    connected_clients.append(websocket)
    print(f"Client connected. Total: {len(connected_clients)}")

    # Send current state to new client
    await websocket.send_json({"type": "state", "data": robot_state})

    try:
        while True:
            data = await websocket.receive_json()
            await handle_message(data, websocket)
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        print(f"Client disconnected. Total: {len(connected_clients)}")


async def handle_message(data: dict, sender: WebSocket):
    """Handle incoming WebSocket messages"""
    msg_type = data.get("type", "")

    if msg_type == "emotion":
        robot_state["emotion"] = data.get("emotion", "happy")
        await broadcast({"type": "emotion", "emotion": robot_state["emotion"]})
        print(f"Emotion: {robot_state['emotion']}")

    elif msg_type == "disco":
        robot_state["disco_mode"] = data.get("enabled", False)
        await broadcast({"type": "disco", "enabled": robot_state["disco_mode"]})
        print(f"Disco: {robot_state['disco_mode']}")

    elif msg_type == "set_mode":
        # Handle extension modes (e.g., cat_mode, pirate_mode)
        mode = data.get("mode")
        enabled = data.get("enabled", True)
        if enabled:
            robot_state["active_mode"] = mode
        elif robot_state["active_mode"] == mode:
            robot_state["active_mode"] = None
        await broadcast({"type": "mode_change", "mode": mode, "enabled": enabled})
        print(f"Mode: {mode} = {enabled}")

    elif msg_type == "show_overlay":
        # Handle face overlays from extensions
        overlay_id = data.get("overlay_id")
        if overlay_id and overlay_id not in robot_state["active_overlays"]:
            robot_state["active_overlays"].append(overlay_id)
        await broadcast({"type": "show_overlay", "overlay_id": overlay_id, "overlays": robot_state["active_overlays"]})

    elif msg_type == "hide_overlay":
        overlay_id = data.get("overlay_id")
        if overlay_id:
            robot_state["active_overlays"] = [o for o in robot_state["active_overlays"] if o != overlay_id]
        else:
            robot_state["active_overlays"] = []
        await broadcast({"type": "hide_overlay", "overlay_id": overlay_id, "overlays": robot_state["active_overlays"]})

    elif msg_type == "ping":
        await sender.send_json({"type": "pong"})

    elif msg_type == "action":
        # Broadcast action events (for action overlay display)
        await broadcast({"type": "action", "action": data.get("action", {})})


async def broadcast(message: dict):
    """Broadcast a message to all connected WebSocket clients"""
    for client in connected_clients:
        try:
            await client.send_json(message)
        except:
            pass


# Make broadcast function available to other modules
def get_broadcast_func():
    """Get the broadcast function for use by extensions"""
    return broadcast
