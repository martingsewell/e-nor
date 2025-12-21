"""
Motor Control API for E-NOR
Provides endpoints for controlling DC motors via DRV8833 driver
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import sys
from pathlib import Path

# Add hardware directory to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from hardware.motors import (
    get_motor_controller,
    forward,
    backward,
    left,
    right,
    stop,
    status,
    cleanup
)

router = APIRouter(prefix="/api/motor", tags=["motor"])


class SpeedRequest(BaseModel):
    speed: Optional[float] = None


class MotorResponse(BaseModel):
    success: bool
    command: str
    message: str
    status: dict


@router.get("/status")
async def get_motor_status():
    """Get current motor controller status"""
    return status()


@router.post("/forward")
async def motor_forward(request: SpeedRequest = None):
    """Move forward - both motors forward"""
    try:
        speed = request.speed if request else None
        forward(speed)
        return MotorResponse(
            success=True,
            command="forward",
            message="Moving forward",
            status=status()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backward")
async def motor_backward(request: SpeedRequest = None):
    """Move backward - both motors backward"""
    try:
        speed = request.speed if request else None
        backward(speed)
        return MotorResponse(
            success=True,
            command="backward",
            message="Moving backward",
            status=status()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/left")
async def motor_left(request: SpeedRequest = None):
    """Turn left - pivot turn"""
    try:
        speed = request.speed if request else None
        left(speed)
        return MotorResponse(
            success=True,
            command="left",
            message="Turning left",
            status=status()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/right")
async def motor_right(request: SpeedRequest = None):
    """Turn right - pivot turn"""
    try:
        speed = request.speed if request else None
        right(speed)
        return MotorResponse(
            success=True,
            command="right",
            message="Turning right",
            status=status()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def motor_stop():
    """Stop all motors"""
    try:
        stop()
        return MotorResponse(
            success=True,
            command="stop",
            message="Motors stopped",
            status=status()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/speed")
async def set_motor_speed(request: SpeedRequest):
    """Set default motor speed (0.0 to 1.0)"""
    if request.speed is None:
        raise HTTPException(status_code=400, detail="Speed is required")
    try:
        controller = get_motor_controller()
        controller.set_speed(request.speed)
        return {
            "success": True,
            "message": f"Speed set to {controller.speed}",
            "status": status()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
