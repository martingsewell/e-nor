"""
E-NOR Plugin Loader
Discovers and loads extensions from the extensions/ folder
"""

import json
import importlib.util
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from fastapi import APIRouter

router = APIRouter(prefix="/api/extensions", tags=["extensions"])

# Extensions directory
EXTENSIONS_DIR = Path(__file__).parent.parent.parent / "extensions"


@dataclass
class Extension:
    """Represents a loaded extension"""
    id: str
    name: str
    description: str
    version: str
    author: str
    extension_type: str  # e.g., "emotion", "action", "game", "feature"
    enabled: bool
    path: Path
    manifest: Dict

    # Registered hooks
    voice_triggers: List[Dict] = field(default_factory=list)
    api_endpoints: List[Dict] = field(default_factory=list)
    emotions: List[Dict] = field(default_factory=list)
    jokes: List[str] = field(default_factory=list)
    actions: List[Dict] = field(default_factory=list)
    ui_components: List[Dict] = field(default_factory=list)
    face_overlays: List[Dict] = field(default_factory=list)

    # Handler module (if Python code)
    handler_module: Optional[Any] = None


# Global registry of loaded extensions
_extensions: Dict[str, Extension] = {}
_voice_triggers: Dict[str, Callable] = {}
_custom_actions: Dict[str, Callable] = {}


def get_extensions_dir() -> Path:
    """Get the extensions directory, creating it if needed"""
    EXTENSIONS_DIR.mkdir(parents=True, exist_ok=True)
    return EXTENSIONS_DIR


def load_manifest(extension_path: Path) -> Optional[Dict]:
    """Load an extension's manifest.json"""
    manifest_file = extension_path / "manifest.json"
    if not manifest_file.exists():
        return None

    try:
        with open(manifest_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading manifest for {extension_path.name}: {e}")
        return None


def load_extension_handler(extension_path: Path, extension_id: str) -> Optional[Any]:
    """Load a Python handler module from an extension"""
    handler_file = extension_path / "handler.py"
    if not handler_file.exists():
        return None

    try:
        spec = importlib.util.spec_from_file_location(
            f"extension_{extension_id}",
            handler_file
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"extension_{extension_id}"] = module
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        print(f"Error loading handler for {extension_id}: {e}")
        return None


def load_extension_emotions(extension_path: Path) -> List[Dict]:
    """Load custom emotions from an extension"""
    emotions = []

    # Check for emotion.json (single emotion)
    emotion_file = extension_path / "emotion.json"
    if emotion_file.exists():
        try:
            with open(emotion_file, 'r') as f:
                emotion = json.load(f)
                emotions.append(emotion)
        except (json.JSONDecodeError, IOError):
            pass

    # Check for emotions.json (multiple emotions)
    emotions_file = extension_path / "emotions.json"
    if emotions_file.exists():
        try:
            with open(emotions_file, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    emotions.extend(data)
                elif isinstance(data, dict) and "emotions" in data:
                    emotions.extend(data["emotions"])
        except (json.JSONDecodeError, IOError):
            pass

    return emotions


def load_extension_jokes(extension_path: Path) -> List[str]:
    """Load custom jokes from an extension"""
    jokes = []

    jokes_file = extension_path / "jokes.json"
    if jokes_file.exists():
        try:
            with open(jokes_file, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    jokes.extend(data)
                elif isinstance(data, dict) and "jokes" in data:
                    jokes.extend(data["jokes"])
        except (json.JSONDecodeError, IOError):
            pass

    return jokes


def load_extension_face_overlays(extension_path: Path) -> List[Dict]:
    """Load face overlays (SVG components) from an extension"""
    overlays = []

    # Check for overlay.svg
    overlay_file = extension_path / "overlay.svg"
    if overlay_file.exists():
        try:
            with open(overlay_file, 'r') as f:
                overlays.append({
                    "type": "svg",
                    "content": f.read()
                })
        except IOError:
            pass

    # Check for overlays.json (defines multiple overlays)
    overlays_file = extension_path / "overlays.json"
    if overlays_file.exists():
        try:
            with open(overlays_file, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    overlays.extend(data)
        except (json.JSONDecodeError, IOError):
            pass

    return overlays


def load_single_extension(extension_path: Path) -> Optional[Extension]:
    """Load a single extension from its directory"""
    if not extension_path.is_dir():
        return None

    manifest = load_manifest(extension_path)
    if not manifest:
        print(f"Skipping {extension_path.name}: no valid manifest.json")
        return None

    extension_id = manifest.get("id", extension_path.name)

    # Load the extension
    extension = Extension(
        id=extension_id,
        name=manifest.get("name", extension_id),
        description=manifest.get("description", ""),
        version=manifest.get("version", "1.0.0"),
        author=manifest.get("author", "unknown"),
        extension_type=manifest.get("type", "feature"),
        enabled=manifest.get("enabled", True),
        path=extension_path,
        manifest=manifest
    )

    # Load emotions
    extension.emotions = load_extension_emotions(extension_path)

    # Load jokes
    extension.jokes = load_extension_jokes(extension_path)

    # Load face overlays
    extension.face_overlays = load_extension_face_overlays(extension_path)

    # Load voice triggers from manifest
    extension.voice_triggers = manifest.get("voice_triggers", [])

    # Load UI components from manifest
    extension.ui_components = manifest.get("ui_components", [])

    # Load Python handler if exists
    handler = load_extension_handler(extension_path, extension_id)
    if handler:
        extension.handler_module = handler

        # Register handler functions
        if hasattr(handler, 'get_voice_triggers'):
            extension.voice_triggers.extend(handler.get_voice_triggers())

        if hasattr(handler, 'get_actions'):
            extension.actions = handler.get_actions()

        # Register custom action handlers
        if hasattr(handler, 'handle_action'):
            _custom_actions[extension_id] = handler.handle_action

    return extension


def discover_extensions() -> List[Extension]:
    """Discover and load all extensions"""
    extensions_dir = get_extensions_dir()
    extensions = []

    for item in extensions_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            extension = load_single_extension(item)
            if extension:
                extensions.append(extension)
                _extensions[extension.id] = extension
                print(f"Loaded extension: {extension.name} (v{extension.version})")

    # Register all voice triggers
    for ext in extensions:
        for trigger in ext.voice_triggers:
            phrases = trigger.get("phrases", [])
            for phrase in phrases:
                _voice_triggers[phrase.lower()] = {
                    "extension_id": ext.id,
                    "action": trigger.get("action"),
                    "handler": trigger.get("handler")
                }

    return extensions


def get_extension(extension_id: str) -> Optional[Extension]:
    """Get a loaded extension by ID"""
    return _extensions.get(extension_id)


def get_all_extensions() -> List[Extension]:
    """Get all loaded extensions"""
    return list(_extensions.values())


def get_enabled_extensions() -> List[Extension]:
    """Get only enabled extensions"""
    return [ext for ext in _extensions.values() if ext.enabled]


def get_all_custom_emotions() -> List[Dict]:
    """Get all custom emotions from all enabled extensions"""
    emotions = []
    for ext in get_enabled_extensions():
        for emotion in ext.emotions:
            emotion["_extension_id"] = ext.id
            emotions.append(emotion)
    return emotions


def get_all_custom_jokes() -> List[str]:
    """Get all custom jokes from all enabled extensions"""
    jokes = []
    for ext in get_enabled_extensions():
        jokes.extend(ext.jokes)
    return jokes


def get_all_face_overlays() -> List[Dict]:
    """Get all face overlays from all enabled extensions"""
    overlays = []
    for ext in get_enabled_extensions():
        for overlay in ext.face_overlays:
            overlay["_extension_id"] = ext.id
            overlays.append(overlay)
    return overlays


def check_voice_trigger(text: str) -> Optional[Dict]:
    """Check if text matches any registered voice trigger"""
    text_lower = text.lower().strip()

    # Direct match
    if text_lower in _voice_triggers:
        return _voice_triggers[text_lower]

    # Partial match (text contains trigger phrase)
    for phrase, trigger in _voice_triggers.items():
        if phrase in text_lower:
            return trigger

    return None


async def execute_custom_action(extension_id: str, action: str, params: Dict = None) -> Dict:
    """Execute a custom action from an extension"""
    if extension_id not in _custom_actions:
        return {"success": False, "error": "Extension has no action handler"}

    try:
        handler = _custom_actions[extension_id]
        result = await handler(action, params or {})
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def set_extension_enabled(extension_id: str, enabled: bool) -> bool:
    """Enable or disable an extension"""
    if extension_id not in _extensions:
        return False

    ext = _extensions[extension_id]
    ext.enabled = enabled

    # Update manifest file
    manifest_file = ext.path / "manifest.json"
    try:
        ext.manifest["enabled"] = enabled
        with open(manifest_file, 'w') as f:
            json.dump(ext.manifest, f, indent=2)
        return True
    except IOError:
        return False


def delete_extension(extension_id: str) -> bool:
    """Delete an extension (removes files)"""
    import shutil

    if extension_id not in _extensions:
        return False

    ext = _extensions[extension_id]
    try:
        shutil.rmtree(ext.path)
        del _extensions[extension_id]
        return True
    except Exception as e:
        print(f"Error deleting extension {extension_id}: {e}")
        return False


# API Endpoints

@router.get("")
async def list_extensions() -> Dict:
    """List all extensions"""
    extensions = []
    for ext in get_all_extensions():
        extensions.append({
            "id": ext.id,
            "name": ext.name,
            "description": ext.description,
            "version": ext.version,
            "author": ext.author,
            "type": ext.extension_type,
            "enabled": ext.enabled,
            "has_emotions": len(ext.emotions) > 0,
            "has_jokes": len(ext.jokes) > 0,
            "has_voice_triggers": len(ext.voice_triggers) > 0,
            "has_face_overlays": len(ext.face_overlays) > 0,
            "has_handler": ext.handler_module is not None
        })

    return {
        "extensions": extensions,
        "total": len(extensions),
        "enabled_count": len([e for e in extensions if e["enabled"]])
    }


@router.get("/{extension_id}")
async def get_extension_details(extension_id: str) -> Dict:
    """Get details of a specific extension"""
    ext = get_extension(extension_id)
    if not ext:
        return {"error": "Extension not found"}

    return {
        "id": ext.id,
        "name": ext.name,
        "description": ext.description,
        "version": ext.version,
        "author": ext.author,
        "type": ext.extension_type,
        "enabled": ext.enabled,
        "manifest": ext.manifest,
        "emotions": ext.emotions,
        "jokes_count": len(ext.jokes),
        "voice_triggers": ext.voice_triggers,
        "face_overlays_count": len(ext.face_overlays)
    }


@router.put("/{extension_id}/enabled")
async def toggle_extension(extension_id: str, enabled: bool) -> Dict:
    """Enable or disable an extension"""
    success = set_extension_enabled(extension_id, enabled)
    return {
        "success": success,
        "message": f"Extension {'enabled' if enabled else 'disabled'}" if success else "Extension not found"
    }


@router.delete("/{extension_id}")
async def remove_extension(extension_id: str) -> Dict:
    """Delete an extension"""
    success = delete_extension(extension_id)
    return {
        "success": success,
        "message": "Extension deleted" if success else "Failed to delete extension"
    }


@router.get("/emotions/all")
async def get_custom_emotions() -> Dict:
    """Get all custom emotions from extensions"""
    return {"emotions": get_all_custom_emotions()}


@router.get("/jokes/all")
async def get_custom_jokes() -> Dict:
    """Get all custom jokes from extensions"""
    return {"jokes": get_all_custom_jokes()}


@router.get("/overlays/all")
async def get_face_overlays() -> Dict:
    """Get all face overlays from extensions"""
    return {"overlays": get_all_face_overlays()}


@router.post("/reload")
async def reload_extensions() -> Dict:
    """Reload all extensions"""
    global _extensions, _voice_triggers, _custom_actions
    _extensions = {}
    _voice_triggers = {}
    _custom_actions = {}

    extensions = discover_extensions()
    return {
        "success": True,
        "loaded": len(extensions),
        "message": f"Reloaded {len(extensions)} extensions"
    }


# Initialize extensions on import
def init_extensions():
    """Initialize the extension system"""
    print("Loading extensions...")
    extensions = discover_extensions()
    print(f"Loaded {len(extensions)} extensions")


# Don't auto-initialize on import - let main.py control this
