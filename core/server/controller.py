"""
Controller API for E-NOR
Provides endpoints for detecting and managing game controllers
"""

from fastapi import APIRouter, HTTPException, WebSocket
from pydantic import BaseModel
from typing import Optional, List
import sys
import asyncio
from pathlib import Path

# Add hardware directory to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from hardware.controller import (
    get_controller_manager,
    scan_controllers,
    get_controllers,
    select_controller,
    status,
    cleanup
)
from hardware.motors import (
    forward as motor_forward,
    backward as motor_backward,
    left as motor_left,
    right as motor_right,
    stop as motor_stop
)

router = APIRouter(prefix="/api/controller", tags=["controller"])

# Store WebSocket connections for controller events
controller_clients: List[WebSocket] = []

# Broadcast function (will be set by main.py)
_broadcast_func = None


def set_broadcast_function(func):
    """Set the broadcast function from main.py"""
    global _broadcast_func
    _broadcast_func = func


class ControllerSelectRequest(BaseModel):
    path: str


class ControllerConfigRequest(BaseModel):
    dead_zone: Optional[float] = None


class ControllerResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


@router.get("/status")
async def get_controller_status():
    """Get current controller status"""
    return status()


@router.get("/scan")
async def scan_for_controllers():
    """
    Scan for connected game controllers.
    Returns list of detected controllers.
    """
    try:
        controllers = scan_controllers()
        return {
            "success": True,
            "message": f"Found {len(controllers)} controller(s)",
            "controllers": controllers,
            "status": status()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_controllers():
    """Get list of already-detected controllers (doesn't rescan)"""
    return {
        "success": True,
        "controllers": get_controllers()
    }


@router.post("/select")
async def select_active_controller(request: ControllerSelectRequest):
    """Select a controller to use for input"""
    try:
        success = select_controller(request.path)
        if success:
            return ControllerResponse(
                success=True,
                message="Controller selected",
                data=status()
            )
        else:
            raise HTTPException(status_code=404, detail="Controller not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_controller():
    """Start reading input from the selected controller"""
    try:
        manager = get_controller_manager()

        # Set up motor callback
        def motor_callback(direction: str, speed: float):
            if direction == "forward":
                motor_forward(speed)
            elif direction == "backward":
                motor_backward(speed)
            elif direction == "left":
                motor_left(speed)
            elif direction == "right":
                motor_right(speed)
            elif direction == "stop":
                motor_stop()

            # Broadcast to UI
            if _broadcast_func:
                asyncio.create_task(_broadcast_func({
                    "type": "controller_input",
                    "direction": direction,
                    "speed": speed
                }))

        # Set up input callback for UI feedback
        def input_callback(path: str, input_name: str, value):
            if _broadcast_func:
                asyncio.create_task(_broadcast_func({
                    "type": "controller_event",
                    "controller": path,
                    "input": input_name,
                    "value": value
                }))

        manager.set_motor_callback(motor_callback)
        manager.set_input_callback(input_callback)

        await manager.start_reading()

        return ControllerResponse(
            success=True,
            message="Controller reading started",
            data=status()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_controller():
    """Stop reading input from the controller"""
    try:
        manager = get_controller_manager()
        await manager.stop_reading()
        motor_stop()

        return ControllerResponse(
            success=True,
            message="Controller reading stopped",
            data=status()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config")
async def configure_controller(request: ControllerConfigRequest):
    """Update controller configuration"""
    try:
        manager = get_controller_manager()

        if request.dead_zone is not None:
            manager.dead_zone = max(0.0, min(0.5, request.dead_zone))

        return ControllerResponse(
            success=True,
            message="Configuration updated",
            data=status()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disconnect")
async def disconnect_controller():
    """Disconnect and clean up controller resources"""
    try:
        manager = get_controller_manager()
        await manager.stop_reading()
        cleanup()
        motor_stop()

        return ControllerResponse(
            success=True,
            message="Controller disconnected",
            data={"connected": False}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint for real-time controller events
@router.websocket("/ws")
async def controller_websocket(websocket: WebSocket):
    """WebSocket for real-time controller event streaming"""
    await websocket.accept()
    controller_clients.append(websocket)

    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except:
        pass
    finally:
        if websocket in controller_clients:
            controller_clients.remove(websocket)
