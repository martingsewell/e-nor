"""
E-NOR Controller API
Endpoints for the mobile controller UI
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import json

from .secrets import get_secret, has_secret
from .plugin_loader import get_all_extensions, get_extension, execute_custom_action

router = APIRouter(prefix="/api/controller", tags=["controller"])


class LaunchGameRequest(BaseModel):
    game_id: str


class ExtensionButton(BaseModel):
    extension_id: str
    label: str
    emoji: str
    action: str


@router.post("/generate-joke")
async def generate_original_joke():
    """Generate an original kid-friendly joke using Claude"""
    if not has_secret("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=503, detail="Claude API key not configured")

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=get_secret("ANTHROPIC_API_KEY"))

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=150,
            messages=[
                {
                    "role": "user",
                    "content": """Generate one original, kid-friendly joke that would make a 9-year-old laugh.
The joke should be:
- Clean and appropriate for children
- Creative and NOT a common joke you'd find everywhere
- Could be a pun, wordplay, silly question, or a short funny story
- Between 1-3 sentences long

Just respond with the joke, nothing else."""
                }
            ]
        )

        joke = message.content[0].text.strip()
        return {"joke": joke, "generated": True}

    except Exception as e:
        print(f"Error generating joke: {e}")
        # Return a fallback joke
        import random
        fallback_jokes = [
            "Why don't robots ever get tired? Because they run on batteries, not bedtime!",
            "What do you call a robot who takes the scenic route? R2-Detour!",
            "Why did the computer go to the doctor? It had a virus!",
            "What's a robot's favorite type of music? Heavy metal!",
            "Why did the robot cross the road? To recharge on the other side!"
        ]
        return {"joke": random.choice(fallback_jokes), "generated": False}


@router.post("/launch-game")
async def launch_game(request: LaunchGameRequest):
    """Launch a game extension on the main UI"""
    extension = get_extension(request.game_id)

    if not extension:
        raise HTTPException(status_code=404, detail=f"Game '{request.game_id}' not found")

    if extension.extension_type != "game":
        raise HTTPException(status_code=400, detail=f"Extension '{request.game_id}' is not a game")

    # Find the game's UI component
    ui_components = extension.manifest.get("ui_components", [])
    game_panel = None
    for comp in ui_components:
        if comp.get("type") == "game":
            game_panel = comp
            break

    if not game_panel:
        raise HTTPException(status_code=400, detail=f"Game '{request.game_id}' has no UI panel")

    # Broadcast to main UI to open the game
    try:
        from .main import broadcast
        await broadcast({
            "type": "launch_game",
            "extension_id": request.game_id,
            "panel_id": game_panel.get("id"),
            "panel_file": game_panel.get("file")
        })
        return {"success": True, "game_id": request.game_id}
    except Exception as e:
        print(f"Error launching game: {e}")
        raise HTTPException(status_code=500, detail="Failed to launch game")


@router.get("/extension-buttons")
async def get_extension_buttons():
    """Get buttons that extensions want to add to the controller"""
    buttons = []

    for ext in get_all_extensions():
        if not ext.enabled:
            continue

        # Check if extension defines controller buttons in manifest
        controller_buttons = ext.manifest.get("controller_buttons", [])
        for btn in controller_buttons:
            buttons.append({
                "extension_id": ext.id,
                "label": btn.get("label", ext.name),
                "emoji": btn.get("emoji", "⚡"),
                "action": btn.get("action", "default")
            })

    return {"buttons": buttons}


@router.post("/emergency-stop")
async def emergency_stop():
    """Perform an emergency stop - stop all motors, reset state, and stop all extension loops"""
    results = {
        "motors_stopped": False,
        "sequences_cancelled": False,
        "state_reset": False,
        "extensions_reset": False
    }

    # FIRST: Signal all extensions to stop their loops immediately
    try:
        from .extension_api import reset_all_extensions
        reset_all_extensions()
        results["extensions_reset"] = True
        print("Emergency stop: All extensions signaled to stop")
    except Exception as e:
        print(f"Error resetting extensions: {e}")

    # Stop motors
    try:
        from .motor_control import stop_motors, cancel_sequence
        await stop_motors()
        results["motors_stopped"] = True
    except Exception as e:
        print(f"Error stopping motors: {e}")

    # Cancel any running sequences
    try:
        from .motor_control import cancel_sequence
        cancel_sequence()
        results["sequences_cancelled"] = True
    except Exception as e:
        print(f"Error cancelling sequences: {e}")

    # Reset robot state
    try:
        from .main import robot_state, broadcast
        robot_state["emotion"] = "happy"
        robot_state["disco_mode"] = False
        robot_state["active_mode"] = None
        robot_state["active_overlays"] = []
        robot_state["active_panel"] = None
        robot_state["game_active"] = False

        # Broadcast reset to all clients
        await broadcast({
            "type": "emergency_stop",
            "state": robot_state
        })
        results["state_reset"] = True
    except Exception as e:
        print(f"Error resetting state: {e}")

    return results
