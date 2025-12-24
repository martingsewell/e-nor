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
    category: str  # UI category: games, modes, tools, quizzes, custom1-4
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


def _infer_category_from_type(ext_type: str) -> str:
    """Infer a default category from extension type for backwards compatibility"""
    type_to_category = {
        "game": "games",
        "mode": "modes",
        "utility": "tools",
        "tool": "tools",
        "action": "tools",
        "feature": "tools",
        "emotion": "modes",
        "quiz": "quizzes",
    }
    return type_to_category.get(ext_type, "tools")


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

    # Infer category from type if not explicitly set
    ext_type = manifest.get("type", "feature")
    default_category = _infer_category_from_type(ext_type)

    # Load the extension
    extension = Extension(
        id=extension_id,
        name=manifest.get("name", extension_id),
        description=manifest.get("description", ""),
        version=manifest.get("version", "1.0.0"),
        author=manifest.get("author", "unknown"),
        extension_type=ext_type,
        category=manifest.get("category", default_category),
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


def get_extensions_by_category(category: str) -> List[Extension]:
    """Get all enabled extensions in a specific category"""
    return [ext for ext in get_enabled_extensions() if ext.category == category]


def get_category_counts() -> Dict[str, int]:
    """Get count of enabled extensions per category"""
    counts = {}
    for ext in get_enabled_extensions():
        cat = ext.category
        counts[cat] = counts.get(cat, 0) + 1
    return counts


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
            "category": ext.category,
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


@router.get("/categories")
async def get_categories() -> Dict:
    """Get all UI categories with their extension counts and configuration"""
    from .config import load_config

    config = load_config()
    ui_categories = config.get("ui_categories", {})
    counts = get_category_counts()

    # Define the 8 category slots
    categories = [
        # Fixed categories (4)
        {
            "id": "games",
            "name": ui_categories.get("games", {}).get("name", "Games"),
            "icon": ui_categories.get("games", {}).get("icon", "🎮"),
            "fixed": True,
            "count": counts.get("games", 0)
        },
        {
            "id": "modes",
            "name": ui_categories.get("modes", {}).get("name", "Modes"),
            "icon": ui_categories.get("modes", {}).get("icon", "🎭"),
            "fixed": True,
            "count": counts.get("modes", 0)
        },
        {
            "id": "tools",
            "name": ui_categories.get("tools", {}).get("name", "Tools"),
            "icon": ui_categories.get("tools", {}).get("icon", "🛠️"),
            "fixed": True,
            "count": counts.get("tools", 0)
        },
        {
            "id": "quizzes",
            "name": ui_categories.get("quizzes", {}).get("name", "Quizzes"),
            "icon": ui_categories.get("quizzes", {}).get("icon", "🧠"),
            "fixed": True,
            "count": counts.get("quizzes", 0)
        },
        # Configurable categories (4)
        {
            "id": "custom1",
            "name": ui_categories.get("custom1", {}).get("name", "Stories"),
            "icon": ui_categories.get("custom1", {}).get("icon", "📖"),
            "fixed": False,
            "count": counts.get("custom1", 0)
        },
        {
            "id": "custom2",
            "name": ui_categories.get("custom2", {}).get("name", "Creative"),
            "icon": ui_categories.get("custom2", {}).get("icon", "🎨"),
            "fixed": False,
            "count": counts.get("custom2", 0)
        },
        {
            "id": "custom3",
            "name": ui_categories.get("custom3", {}).get("name", "Learning"),
            "icon": ui_categories.get("custom3", {}).get("icon", "📚"),
            "fixed": False,
            "count": counts.get("custom3", 0)
        },
        {
            "id": "custom4",
            "name": ui_categories.get("custom4", {}).get("name", "Fun"),
            "icon": ui_categories.get("custom4", {}).get("icon", "😂"),
            "fixed": False,
            "count": counts.get("custom4", 0)
        },
    ]

    return {
        "categories": categories,
        "total_extensions": sum(counts.values())
    }


@router.get("/by-category/{category}")
async def get_extensions_in_category(category: str) -> Dict:
    """Get all enabled extensions in a specific category"""
    valid_categories = ["games", "modes", "tools", "quizzes", "custom1", "custom2", "custom3", "custom4"]
    if category not in valid_categories:
        return {"error": f"Invalid category. Must be one of: {', '.join(valid_categories)}"}

    extensions = []
    for ext in get_extensions_by_category(category):
        ui_config = ext.manifest.get("ui", {})
        extensions.append({
            "id": ext.id,
            "name": ext.name,
            "description": ext.description,
            "version": ext.version,
            "type": ext.extension_type,
            "category": ext.category,
            "icon": ui_config.get("button_emoji", "⭐"),
            "color": ui_config.get("button_color", "#00ffff"),
            "has_voice_triggers": len(ext.voice_triggers) > 0,
            "voice_triggers": [t.get("phrases", [])[0] if t.get("phrases") else "" for t in ext.voice_triggers[:3]]
        })

    return {
        "category": category,
        "extensions": extensions,
        "count": len(extensions)
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
        "category": ext.category,
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


@router.get("/modes")
async def get_modes() -> Dict:
    """Get all mode extensions for the mode selector UI"""
    modes = []
    for ext in get_enabled_extensions():
        # Check both extension_type and category for modes
        if ext.extension_type == "mode" or ext.category == "modes":
            # Get UI config from manifest if available
            ui_config = ext.manifest.get("ui", {})
            modes.append({
                "id": ext.id,
                "name": ext.name,
                "description": ext.description,
                "button_label": ui_config.get("button_label", ext.name.replace(" Mode", "")),
                "button_emoji": ui_config.get("button_emoji", "🎭"),
                "button_color": ui_config.get("button_color", "#00ffff"),
                "has_overlay": len(ext.face_overlays) > 0,
                "has_emotion": len(ext.emotions) > 0,
                "has_sounds": (ext.path / "sounds").exists(),
                "enabled": ext.enabled
            })
    return {"modes": modes, "total": len(modes)}


@router.get("/games")
async def get_games() -> Dict:
    """Get all game extensions for the games list UI"""
    games = []
    for ext in get_enabled_extensions():
        # Check both extension_type and category for games
        if ext.extension_type == "game" or ext.category == "games":
            # Get UI config from manifest if available
            ui_config = ext.manifest.get("ui", {})
            ui_components = ext.manifest.get("ui_components", [])
            # Find the game panel
            game_panel = next((c for c in ui_components if c.get("type") == "game"), None)
            games.append({
                "id": ext.id,
                "name": ext.name,
                "description": ext.description,
                "button_label": ui_config.get("button_label", ext.name.replace(" Game", "")),
                "button_emoji": ui_config.get("button_emoji", "🎮"),
                "button_color": ui_config.get("button_color", "#00ffff"),
                "has_ui": game_panel is not None,
                "panel_id": game_panel.get("id") if game_panel else None,
                "panel_file": game_panel.get("file") if game_panel else None,
                "enabled": ext.enabled
            })
    return {"games": games, "total": len(games)}


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
