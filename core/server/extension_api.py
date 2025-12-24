"""
E-NOR Extension API
Provides a rich API for extensions to interact with core robot systems
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from pathlib import Path
import json
import asyncio

# Global registry of API instances - must be defined before ExtensionAPI class
_api_instances: Dict[str, "ExtensionAPI"] = {}


class ExtensionAPI:
    """
    API class that extensions can use to interact with E-NOR's core systems.
    Each extension gets its own instance with access to shared services.
    """

    def __init__(self, extension_id: str, extension_path: Path):
        self.extension_id = extension_id
        self.extension_path = extension_path
        self._data_dir = extension_path / "data"
        self._broadcast_func = None
        self._speak_func = None
        self._emotion_func = None
        # Auto-register this instance so broadcast function can be set later
        _api_instances[extension_id] = self

    # ==================== COMMUNICATION ====================

    async def speak(self, text: str) -> None:
        """Make E-NOR say something (via text-to-speech)"""
        if self._speak_func:
            await self._speak_func(text)
        else:
            # Fallback: broadcast a speak event
            await self.broadcast({
                "type": "speak",
                "text": text,
                "source": self.extension_id
            })

    async def show_message(self, text: str, message_type: str = "extension") -> None:
        """Display a message in the chat UI"""
        await self.broadcast({
            "type": "message",
            "text": text,
            "message_type": message_type,
            "source": self.extension_id
        })

    async def broadcast(self, data: Dict) -> None:
        """Broadcast a message to all connected clients via WebSocket"""
        if self._broadcast_func:
            data["_extension"] = self.extension_id
            print(f"[ExtensionAPI] Broadcasting from {self.extension_id}: {data.get('type', 'unknown')}")
            await self._broadcast_func(data)
        else:
            print(f"[ExtensionAPI] WARNING: No broadcast function set for {self.extension_id}, message dropped: {data.get('type', 'unknown')}")

    # ==================== EMOTION & APPEARANCE ====================

    async def set_emotion(self, emotion: str) -> None:
        """Change E-NOR's facial expression"""
        await self.broadcast({
            "type": "emotion",
            "emotion": emotion
        })

    async def show_face_overlay(self, overlay_id: str) -> None:
        """Show a face overlay (e.g., cat ears, hats)"""
        await self.broadcast({
            "type": "show_overlay",
            "overlay_id": overlay_id,
            "extension_id": self.extension_id
        })

    async def hide_face_overlay(self, overlay_id: str = None) -> None:
        """Hide a face overlay (or all overlays if no ID specified)"""
        await self.broadcast({
            "type": "hide_overlay",
            "overlay_id": overlay_id,
            "extension_id": self.extension_id
        })

    async def set_mode(self, mode: str, enabled: bool = True) -> None:
        """Activate a custom mode (e.g., 'cat_mode', 'pirate_mode')"""
        await self.broadcast({
            "type": "set_mode",
            "mode": mode,
            "enabled": enabled,
            "extension_id": self.extension_id
        })

    # ==================== UI ====================

    async def show_panel(self, html: str, panel_id: str = None, panel_type: str = None) -> None:
        """
        Display a custom UI panel (fullscreen, mobile-first).

        Args:
            html: The HTML content for the panel
            panel_id: Optional ID for the panel (defaults to extension_id_panel)
            panel_type: Type of panel ('game', 'tool', 'feature', 'action') - used for E-NOR awareness
        """
        await self.broadcast({
            "type": "show_panel",
            "html": html,
            "panel_id": panel_id or f"{self.extension_id}_panel",
            "extension_id": self.extension_id,
            "panel_type": panel_type or "feature"
        })

    async def hide_panel(self, panel_id: str = None) -> None:
        """Hide a custom UI panel"""
        await self.broadcast({
            "type": "hide_panel",
            "panel_id": panel_id or f"{self.extension_id}_panel",
            "extension_id": self.extension_id
        })

    async def update_panel(self, updates: Dict, panel_id: str = None) -> None:
        """Update content in a displayed panel"""
        await self.broadcast({
            "type": "update_panel",
            "updates": updates,
            "panel_id": panel_id or f"{self.extension_id}_panel"
        })

    async def play_sound(self, sound_file: str) -> None:
        """Play a sound file from the extension's directory"""
        sound_path = self.extension_path / "sounds" / sound_file
        if sound_path.exists():
            await self.broadcast({
                "type": "play_sound",
                "path": str(sound_path),
                "extension_id": self.extension_id
            })

    # ==================== DATA STORAGE ====================

    def _ensure_data_dir(self) -> None:
        """Ensure the extension's data directory exists"""
        self._data_dir.mkdir(parents=True, exist_ok=True)

    def get_data(self, key: str, default: Any = None) -> Any:
        """Get a stored data value"""
        self._ensure_data_dir()
        data_file = self._data_dir / f"{key}.json"

        if not data_file.exists():
            return default

        try:
            with open(data_file, 'r') as f:
                data = json.load(f)
                return data.get("value", default)
        except (json.JSONDecodeError, IOError):
            return default

    def set_data(self, key: str, value: Any) -> bool:
        """Store a data value"""
        self._ensure_data_dir()
        data_file = self._data_dir / f"{key}.json"

        try:
            with open(data_file, 'w') as f:
                json.dump({"key": key, "value": value}, f, indent=2)
            return True
        except IOError:
            return False

    def delete_data(self, key: str) -> bool:
        """Delete a stored data value"""
        data_file = self._data_dir / f"{key}.json"
        if data_file.exists():
            try:
                data_file.unlink()
                return True
            except IOError:
                return False
        return False

    def get_all_data(self) -> Dict:
        """Get all stored data for this extension"""
        self._ensure_data_dir()
        data = {}

        for data_file in self._data_dir.glob("*.json"):
            try:
                with open(data_file, 'r') as f:
                    content = json.load(f)
                    key = content.get("key", data_file.stem)
                    data[key] = content.get("value")
            except (json.JSONDecodeError, IOError):
                pass

        return data

    # ==================== CONFIGURATION ACCESS ====================

    def get_config(self) -> Dict:
        """Get the robot's configuration"""
        from .config import load_config
        return load_config()

    def get_child_name(self) -> str:
        """Get the child's name from config"""
        from .config import get_child_name
        return get_child_name()

    def get_child_age(self) -> Optional[int]:
        """Get the child's age from config"""
        from .config import get_child_age
        return get_child_age()

    def get_robot_name(self) -> str:
        """Get the robot's name from config"""
        from .config import get_robot_name
        return get_robot_name()

    # ==================== MEMORIES ====================

    def get_memories(self) -> List[str]:
        """Get all memories about the child"""
        from .memories import load_memories
        return load_memories()

    async def add_memory(self, fact: str) -> bool:
        """Add a new memory"""
        from .memories import save_memory
        return save_memory(fact)

    # ==================== HARDWARE (MOTORS) ====================

    async def move(self, action: str, params: Dict = None) -> Dict:
        """Trigger a motor movement (when hardware is configured)"""
        # This will be implemented when motor control is added
        await self.broadcast({
            "type": "movement",
            "action": action,
            "params": params or {},
            "extension_id": self.extension_id
        })
        return {"success": True, "message": "Movement command sent"}

    # ==================== CLAUDE INTEGRATION ====================

    async def ask_claude(self, prompt: str, context: str = None) -> str:
        """Ask Claude a question for extension logic"""
        from .secrets import get_secret
        import anthropic

        api_key = get_secret("ANTHROPIC_API_KEY")
        if not api_key:
            return "Error: API key not configured"

        try:
            client = anthropic.Anthropic(api_key=api_key)

            system = f"You are helping with an E-NOR robot extension. Be concise and helpful."
            if context:
                system += f"\n\nContext: {context}"

            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=200,
                system=system,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text
        except Exception as e:
            return f"Error: {str(e)}"

    # ==================== UTILITIES ====================

    def get_asset_path(self, filename: str) -> Path:
        """Get the full path to an asset file in the extension directory"""
        return self.extension_path / filename

    def read_asset(self, filename: str) -> Optional[str]:
        """Read a text asset file from the extension directory"""
        asset_path = self.get_asset_path(filename)
        if asset_path.exists():
            try:
                with open(asset_path, 'r') as f:
                    return f.read()
            except IOError:
                return None
        return None

    def read_json_asset(self, filename: str) -> Optional[Dict]:
        """Read a JSON asset file from the extension directory"""
        content = self.read_asset(filename)
        if content:
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return None
        return None


# Factory function to create API instances for extensions
def get_extension_api(extension_id: str, extension_path: Path) -> ExtensionAPI:
    """Get or create an ExtensionAPI instance for an extension"""
    if extension_id not in _api_instances:
        _api_instances[extension_id] = ExtensionAPI(extension_id, extension_path)
    return _api_instances[extension_id]


def set_broadcast_function(func: Callable) -> None:
    """Set the broadcast function for all extension APIs"""
    print(f"[ExtensionAPI] Setting broadcast function for {len(_api_instances)} extension APIs: {list(_api_instances.keys())}")
    for api in _api_instances.values():
        api._broadcast_func = func


def set_speak_function(func: Callable) -> None:
    """Set the speak function for all extension APIs"""
    for api in _api_instances.values():
        api._speak_func = func


# Extension handler base class that extension developers can subclass
class ExtensionHandler:
    """
    Base class for extension handlers.
    Extensions can subclass this to implement their logic.
    """

    def __init__(self, api: ExtensionAPI):
        self.api = api

    async def on_load(self) -> None:
        """Called when the extension is loaded"""
        pass

    async def on_unload(self) -> None:
        """Called when the extension is unloaded"""
        pass

    async def on_voice_trigger(self, trigger: str, full_text: str) -> Optional[str]:
        """
        Called when a registered voice trigger is detected.
        Return a response string or None.
        """
        pass

    async def handle_action(self, action: str, params: Dict) -> Any:
        """
        Handle a custom action.
        Return the result of the action.
        """
        pass

    def get_voice_triggers(self) -> List[Dict]:
        """Return list of voice triggers this extension handles"""
        return []

    def get_actions(self) -> List[Dict]:
        """Return list of custom actions this extension provides"""
        return []
