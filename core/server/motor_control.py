"""
Motor Control API for E-NOR
Provides endpoints for controlling DC motors via DRV8833 driver
Supports voice-controlled movement with calibration settings
"""

import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
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
from .config import load_config, get_config_value

router = APIRouter(prefix="/api/motor", tags=["motor"])

# Track if a movement sequence is running
_sequence_running = False
_sequence_cancel = False


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


# === Timed Movement Endpoints for Voice Control ===

class MoveRequest(BaseModel):
    """Request to move forward or backward"""
    direction: str  # "forward" or "backward"
    distance_cm: Optional[float] = None  # Distance in centimeters
    duration_seconds: Optional[float] = None  # Duration in seconds (used if distance not specified)
    speed: Optional[float] = None  # Override speed (0.0-1.0)


class TurnRequest(BaseModel):
    """Request to turn left or right"""
    direction: str  # "left" or "right"
    degrees: Optional[float] = None  # Turn angle in degrees
    duration_seconds: Optional[float] = None  # Duration in seconds (used if degrees not specified)
    speed: Optional[float] = None  # Override speed (0.0-1.0)


class MovementStep(BaseModel):
    """A single step in a movement sequence"""
    type: str  # "move" or "turn"
    direction: str  # "forward", "backward", "left", "right"
    value: float  # distance in cm for move, degrees for turn
    speed: Optional[float] = None


class SequenceRequest(BaseModel):
    """Request to execute a sequence of movements"""
    steps: List[MovementStep]
    speed: Optional[float] = None  # Default speed for all steps


def get_calibration():
    """Get motor calibration settings"""
    config = load_config()
    return config.get("motor_calibration", {
        "cm_per_second": 20.0,
        "degrees_per_second": 90.0,
        "left_motor_trim": 1.0,
        "right_motor_trim": 1.0,
        "default_speed": 0.7
    })


def calculate_move_duration(distance_cm: float, speed: float, calibration: dict) -> float:
    """Calculate duration to move a given distance at given speed"""
    cm_per_second = calibration.get("cm_per_second", 20.0)
    # Speed affects how fast we move, so duration = distance / (speed * cm_per_second)
    effective_speed = cm_per_second * speed
    return distance_cm / effective_speed if effective_speed > 0 else 0


def calculate_turn_duration(degrees: float, speed: float, calibration: dict) -> float:
    """Calculate duration to turn a given number of degrees at given speed"""
    degrees_per_second = calibration.get("degrees_per_second", 90.0)
    # Speed affects how fast we turn, so duration = degrees / (speed * degrees_per_second)
    effective_speed = degrees_per_second * speed
    return abs(degrees) / effective_speed if effective_speed > 0 else 0


async def execute_timed_movement(direction: str, duration: float, speed: float, calibration: dict):
    """Execute a timed movement (forward, backward, left, right)"""
    global _sequence_cancel

    # Apply motor trim for forward/backward movements
    left_trim = calibration.get("left_motor_trim", 1.0)
    right_trim = calibration.get("right_motor_trim", 1.0)

    controller = get_motor_controller()

    # For directional movements, we might need to adjust individual motor speeds
    # For now, use the controller's built-in methods
    if direction == "forward":
        forward(speed)
    elif direction == "backward":
        backward(speed)
    elif direction == "left":
        left(speed)
    elif direction == "right":
        right(speed)

    # Wait for the specified duration (in small increments to allow cancellation)
    elapsed = 0
    increment = 0.05  # 50ms increments
    while elapsed < duration:
        if _sequence_cancel:
            break
        await asyncio.sleep(increment)
        elapsed += increment

    stop()


@router.post("/move")
async def motor_move(request: MoveRequest):
    """Move forward or backward for a distance or duration"""
    global _sequence_running, _sequence_cancel

    if _sequence_running:
        raise HTTPException(status_code=409, detail="A movement sequence is already running")

    if request.direction not in ["forward", "backward"]:
        raise HTTPException(status_code=400, detail="Direction must be 'forward' or 'backward'")

    calibration = get_calibration()
    speed = request.speed or calibration.get("default_speed", 0.7)

    # Calculate duration
    if request.distance_cm is not None:
        duration = calculate_move_duration(request.distance_cm, speed, calibration)
        description = f"{request.distance_cm}cm"
    elif request.duration_seconds is not None:
        duration = request.duration_seconds
        description = f"{duration}s"
    else:
        raise HTTPException(status_code=400, detail="Either distance_cm or duration_seconds must be specified")

    try:
        _sequence_running = True
        _sequence_cancel = False

        await execute_timed_movement(request.direction, duration, speed, calibration)

        return {
            "success": True,
            "command": "move",
            "direction": request.direction,
            "description": description,
            "duration": round(duration, 2),
            "status": status()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _sequence_running = False


@router.post("/turn")
async def motor_turn(request: TurnRequest):
    """Turn left or right for a number of degrees or duration"""
    global _sequence_running, _sequence_cancel

    if _sequence_running:
        raise HTTPException(status_code=409, detail="A movement sequence is already running")

    if request.direction not in ["left", "right"]:
        raise HTTPException(status_code=400, detail="Direction must be 'left' or 'right'")

    calibration = get_calibration()
    speed = request.speed or calibration.get("default_speed", 0.7)

    # Calculate duration
    if request.degrees is not None:
        duration = calculate_turn_duration(request.degrees, speed, calibration)
        description = f"{request.degrees} degrees"
    elif request.duration_seconds is not None:
        duration = request.duration_seconds
        description = f"{duration}s"
    else:
        raise HTTPException(status_code=400, detail="Either degrees or duration_seconds must be specified")

    try:
        _sequence_running = True
        _sequence_cancel = False

        await execute_timed_movement(request.direction, duration, speed, calibration)

        return {
            "success": True,
            "command": "turn",
            "direction": request.direction,
            "description": description,
            "duration": round(duration, 2),
            "status": status()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _sequence_running = False


@router.post("/sequence")
async def motor_sequence(request: SequenceRequest):
    """Execute a sequence of movements"""
    global _sequence_running, _sequence_cancel

    if _sequence_running:
        raise HTTPException(status_code=409, detail="A movement sequence is already running")

    if not request.steps:
        raise HTTPException(status_code=400, detail="Sequence must have at least one step")

    calibration = get_calibration()
    default_speed = request.speed or calibration.get("default_speed", 0.7)

    results = []
    total_duration = 0

    try:
        _sequence_running = True
        _sequence_cancel = False

        for i, step in enumerate(request.steps):
            if _sequence_cancel:
                results.append({"step": i + 1, "status": "cancelled"})
                break

            speed = step.speed or default_speed

            if step.type == "move":
                if step.direction not in ["forward", "backward"]:
                    results.append({"step": i + 1, "status": "error", "message": "Invalid direction for move"})
                    continue
                duration = calculate_move_duration(step.value, speed, calibration)
                await execute_timed_movement(step.direction, duration, speed, calibration)
                results.append({
                    "step": i + 1,
                    "type": "move",
                    "direction": step.direction,
                    "distance_cm": step.value,
                    "duration": round(duration, 2),
                    "status": "completed"
                })

            elif step.type == "turn":
                if step.direction not in ["left", "right"]:
                    results.append({"step": i + 1, "status": "error", "message": "Invalid direction for turn"})
                    continue
                duration = calculate_turn_duration(step.value, speed, calibration)
                await execute_timed_movement(step.direction, duration, speed, calibration)
                results.append({
                    "step": i + 1,
                    "type": "turn",
                    "direction": step.direction,
                    "degrees": step.value,
                    "duration": round(duration, 2),
                    "status": "completed"
                })
            else:
                results.append({"step": i + 1, "status": "error", "message": f"Unknown step type: {step.type}"})
                continue

            total_duration += duration

        return {
            "success": True,
            "command": "sequence",
            "steps_completed": len([r for r in results if r.get("status") == "completed"]),
            "total_steps": len(request.steps),
            "total_duration": round(total_duration, 2),
            "results": results,
            "status": status()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _sequence_running = False


@router.post("/cancel")
async def motor_cancel():
    """Cancel any running movement sequence"""
    global _sequence_cancel

    _sequence_cancel = True
    stop()

    return {
        "success": True,
        "message": "Movement cancelled",
        "status": status()
    }


@router.get("/sequence-status")
async def get_sequence_status():
    """Check if a movement sequence is currently running"""
    return {
        "running": _sequence_running,
        "status": status()
    }
