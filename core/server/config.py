"""
E-NOR Configuration Module
Manages robot configuration settings stored in config/settings.json
"""

import json
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/config", tags=["config"])

# Config file location
CONFIG_FILE = Path(__file__).parent.parent.parent / "config" / "settings.json"

# Default configuration
DEFAULT_CONFIG = {
    "robot": {
        "name": "E-NOR",
        "display_name": "E-NOR"
    },
    "child": {
        "name": "",
        "birthdate": "",
        "pronouns": "they/them"
    },
    "wake_words": {
        "primary": "hey enor",
        "variants": ["hey enor", "enor", "e-nor"]
    },
    "personality": {
        "traits": ["enthusiastic", "curious", "supportive", "loves jokes"],
        "speaking_style": "simple, friendly, age-appropriate",
        "custom_instructions": ""
    },
    "appearance": {
        "primary_color": "#00ffff",
        "secondary_color": "#ff4444",
        "background_colors": ["#1a1a2e", "#16213e"]
    },
    "features": {
        "voice_enabled": True,
        "disco_mode_enabled": True,
        "extension_creation_enabled": True,
        "motor_control_enabled": False,
        "voice_movement_enabled": False
    },
    "motor_calibration": {
        "cm_per_second": 20.0,
        "degrees_per_second": 90.0,
        "left_motor_trim": 1.0,
        "right_motor_trim": 1.0,
        "default_speed": 0.7
    },
    "limits": {
        "max_memories": 50,
        "max_conversation_messages": 20,
        "max_response_tokens": 300
    },
    "github": {
        "owner": "",
        "repo": ""
    },
    "voice": {
        "gender": "female",
        "rate": "1.0",
        "pitch": "1.0"
    }
}


def load_config() -> Dict:
    """Load configuration from file, merging with defaults"""
    config = DEFAULT_CONFIG.copy()

    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                file_config = json.load(f)
                # Deep merge with defaults
                config = _deep_merge(config, file_config)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load config file: {e}")

    return config


def _deep_merge(base: Dict, override: Dict) -> Dict:
    """Deep merge two dictionaries"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def save_config(config: Dict) -> bool:
    """Save configuration to file"""
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except IOError as e:
        print(f"Error saving config: {e}")
        return False


def get_config_value(path: str, default: Any = None) -> Any:
    """Get a config value by dot-separated path (e.g., 'robot.name')"""
    config = load_config()
    keys = path.split('.')
    value = config

    try:
        for key in keys:
            value = value[key]
        return value
    except (KeyError, TypeError):
        return default


def set_config_value(path: str, value: Any) -> bool:
    """Set a config value by dot-separated path"""
    config = load_config()
    keys = path.split('.')

    # Navigate to the parent of the target key
    target = config
    for key in keys[:-1]:
        if key not in target:
            target[key] = {}
        target = target[key]

    # Set the value
    target[keys[-1]] = value
    return save_config(config)


def get_child_age() -> Optional[int]:
    """Calculate child's age from birthdate"""
    config = load_config()
    birthdate_str = config.get("child", {}).get("birthdate", "")

    if not birthdate_str:
        return None

    try:
        birthdate = datetime.strptime(birthdate_str, "%Y-%m-%d").date()
        today = date.today()
        age = today.year - birthdate.year
        if (today.month, today.day) < (birthdate.month, birthdate.day):
            age -= 1
        return age
    except ValueError:
        return None


def get_robot_name() -> str:
    """Get the robot's name"""
    return get_config_value("robot.name", "E-NOR")


def get_child_name() -> str:
    """Get the child's name"""
    return get_config_value("child.name", "")


def _get_phonetic_variants(word: str) -> List[str]:
    """Generate common phonetic misrecognitions for a wake word.

    Speech recognition often mishears certain sounds. This helps catch
    common misrecognitions like 'hey enor' -> 'hey you know'.
    """
    variants = []
    word_lower = word.lower()

    # Common "enor/e-nor" misrecognitions
    enor_variants = [
        ("enor", "you know"),
        ("enor", "you nor"),
        ("enor", "eno"),
        ("enor", "you no"),
        ("enor", "inor"),
        ("e-nor", "you know"),
        ("e-nor", "you nor"),
        ("e-nor", "eno"),
    ]

    for original, replacement in enor_variants:
        if original in word_lower:
            variants.append(word_lower.replace(original, replacement))

    # "hey" can be heard as "hey" "he" "hay" "a"
    if word_lower.startswith("hey "):
        rest = word_lower[4:]
        variants.extend([
            f"he {rest}",
            f"hay {rest}",
            f"a {rest}",
        ])

    return variants


def get_wake_words() -> List[str]:
    """Get all wake words (primary + variants) including phonetic variants"""
    config = load_config()
    wake_config = config.get("wake_words", {})
    primary = wake_config.get("primary", "hey enor")
    variants = wake_config.get("variants", [])

    # Combine configured words
    all_words = [primary] + variants

    # Add phonetic variants for each configured word
    for word in [primary] + variants:
        all_words.extend(_get_phonetic_variants(word))

    # Deduplicate while preserving order
    return list(dict.fromkeys(all_words))


def add_wake_word_variant(variant: str) -> bool:
    """Add a new wake word variant"""
    config = load_config()
    variants = config.get("wake_words", {}).get("variants", [])

    # Normalize the variant
    normalized = variant.lower().strip()

    # Don't add duplicates
    if normalized in [v.lower() for v in variants]:
        return False

    variants.append(normalized)
    config["wake_words"]["variants"] = variants
    return save_config(config)


def remove_wake_word_variant(variant: str) -> bool:
    """Remove a wake word variant"""
    config = load_config()
    variants = config.get("wake_words", {}).get("variants", [])

    normalized = variant.lower().strip()
    new_variants = [v for v in variants if v.lower() != normalized]

    if len(new_variants) == len(variants):
        return False  # Nothing removed

    config["wake_words"]["variants"] = new_variants
    return save_config(config)


def is_setup_complete() -> bool:
    """Check if initial setup has been completed"""
    config = load_config()
    child_name = config.get("child", {}).get("name", "")
    return bool(child_name and child_name.strip())


# Pydantic models for API
class ConfigUpdate(BaseModel):
    path: str
    value: Any


class RobotConfig(BaseModel):
    name: str
    display_name: str


class ChildConfig(BaseModel):
    name: str
    birthdate: Optional[str] = ""
    pronouns: Optional[str] = "they/them"


class WakeWordAdd(BaseModel):
    variant: str


class VoiceConfig(BaseModel):
    gender: str = "female"
    rate: str = "1.0"
    pitch: str = "1.0"


class DisplayConfig(BaseModel):
    overlay_position: int = 40


# API Endpoints

@router.get("")
async def get_full_config() -> Dict:
    """Get the full configuration"""
    config = load_config()
    # Add computed values
    config["_computed"] = {
        "child_age": get_child_age(),
        "setup_complete": is_setup_complete(),
        "all_wake_words": get_wake_words()
    }
    return config


@router.get("/robot")
async def get_robot_config() -> Dict:
    """Get robot configuration"""
    config = load_config()
    return config.get("robot", {})


@router.put("/robot")
async def update_robot_config(robot: RobotConfig) -> Dict:
    """Update robot configuration"""
    config = load_config()
    config["robot"] = {
        "name": robot.name,
        "display_name": robot.display_name
    }
    success = save_config(config)
    return {"success": success, "robot": config["robot"]}


@router.get("/child")
async def get_child_config() -> Dict:
    """Get child configuration"""
    config = load_config()
    child = config.get("child", {})
    child["age"] = get_child_age()
    return child


@router.put("/child")
async def update_child_config(child: ChildConfig) -> Dict:
    """Update child configuration"""
    config = load_config()
    config["child"] = {
        "name": child.name,
        "birthdate": child.birthdate or "",
        "pronouns": child.pronouns or "they/them"
    }
    success = save_config(config)
    result = config["child"].copy()
    result["age"] = get_child_age()
    return {"success": success, "child": result}


@router.get("/wake-words")
async def get_wake_words_config() -> Dict:
    """Get wake words configuration"""
    config = load_config()
    return {
        "wake_words": config.get("wake_words", {}),
        "all_words": get_wake_words()
    }


@router.post("/wake-words")
async def add_wake_word(data: WakeWordAdd) -> Dict:
    """Add a new wake word variant"""
    if not data.variant or len(data.variant.strip()) < 2:
        raise HTTPException(status_code=400, detail="Wake word too short")

    success = add_wake_word_variant(data.variant)
    return {
        "success": success,
        "message": "Wake word added" if success else "Wake word already exists",
        "all_words": get_wake_words()
    }


@router.delete("/wake-words/{variant}")
async def delete_wake_word(variant: str) -> Dict:
    """Remove a wake word variant"""
    success = remove_wake_word_variant(variant)
    return {
        "success": success,
        "message": "Wake word removed" if success else "Wake word not found",
        "all_words": get_wake_words()
    }


@router.get("/features")
async def get_features_config() -> Dict:
    """Get feature toggles"""
    config = load_config()
    return config.get("features", {})


@router.put("/features")
async def update_features_config(features: Dict) -> Dict:
    """Update feature toggles"""
    config = load_config()
    # Only update known feature keys
    known_features = ["voice_enabled", "disco_mode_enabled", "extension_creation_enabled", "motor_control_enabled", "voice_movement_enabled"]
    for key in known_features:
        if key in features:
            config["features"][key] = bool(features[key])

    success = save_config(config)
    return {"success": success, "features": config["features"]}


@router.get("/limits")
async def get_limits_config() -> Dict:
    """Get limit settings"""
    config = load_config()
    return config.get("limits", {})


@router.put("/limits")
async def update_limits_config(limits: Dict) -> Dict:
    """Update limit settings"""
    config = load_config()
    known_limits = ["max_memories", "max_conversation_messages", "max_response_tokens"]
    for key in known_limits:
        if key in limits:
            config["limits"][key] = int(limits[key])

    success = save_config(config)
    return {"success": success, "limits": config["limits"]}


@router.get("/github")
async def get_github_config() -> Dict:
    """Get GitHub configuration"""
    config = load_config()
    return config.get("github", {})


@router.put("/github")
async def update_github_config(github: Dict) -> Dict:
    """Update GitHub configuration"""
    config = load_config()
    if "owner" in github:
        config["github"]["owner"] = github["owner"]
    if "repo" in github:
        config["github"]["repo"] = github["repo"]

    success = save_config(config)
    return {"success": success, "github": config["github"]}


@router.get("/setup-status")
async def get_setup_status() -> Dict:
    """Check if initial setup is complete"""
    return {
        "complete": is_setup_complete(),
        "robot_name": get_robot_name(),
        "child_name": get_child_name(),
        "child_age": get_child_age()
    }


@router.get("/voice")
async def get_voice_config() -> Dict:
    """Get voice configuration"""
    config = load_config()
    return config.get("voice", {"gender": "female", "rate": "1.0", "pitch": "1.0"})


@router.put("/voice")
async def update_voice_config(voice: VoiceConfig) -> Dict:
    """Update voice configuration"""
    config = load_config()

    # Validate values
    valid_genders = ["female", "male"]
    valid_rates = ["0.8", "1.0", "1.2"]
    valid_pitches = ["0.8", "1.0", "1.2"]

    gender = voice.gender if voice.gender in valid_genders else "female"
    rate = voice.rate if voice.rate in valid_rates else "1.0"
    pitch = voice.pitch if voice.pitch in valid_pitches else "1.0"

    config["voice"] = {
        "gender": gender,
        "rate": rate,
        "pitch": pitch
    }

    success = save_config(config)
    return {"success": success, "voice": config["voice"]}


@router.put("/display")
async def update_display_config(display: DisplayConfig) -> Dict:
    """Update display configuration"""
    config = load_config()

    # Validate overlay position (20-60%)
    overlay_pos = max(20, min(60, display.overlay_position))

    config["display"] = {
        "overlay_position": overlay_pos
    }

    success = save_config(config)
    return {"success": success, "display": config["display"]}


class MotorCalibrationConfig(BaseModel):
    cm_per_second: float = 20.0
    degrees_per_second: float = 90.0
    left_motor_trim: float = 1.0
    right_motor_trim: float = 1.0
    default_speed: float = 0.7


@router.get("/motor-calibration")
async def get_motor_calibration() -> Dict:
    """Get motor calibration settings"""
    config = load_config()
    return config.get("motor_calibration", {
        "cm_per_second": 20.0,
        "degrees_per_second": 90.0,
        "left_motor_trim": 1.0,
        "right_motor_trim": 1.0,
        "default_speed": 0.7
    })


@router.put("/motor-calibration")
async def update_motor_calibration(calibration: MotorCalibrationConfig) -> Dict:
    """Update motor calibration settings"""
    config = load_config()

    # Validate and clamp values
    config["motor_calibration"] = {
        "cm_per_second": max(1.0, min(100.0, calibration.cm_per_second)),
        "degrees_per_second": max(10.0, min(360.0, calibration.degrees_per_second)),
        "left_motor_trim": max(0.5, min(1.5, calibration.left_motor_trim)),
        "right_motor_trim": max(0.5, min(1.5, calibration.right_motor_trim)),
        "default_speed": max(0.1, min(1.0, calibration.default_speed))
    }

    success = save_config(config)
    return {"success": success, "motor_calibration": config["motor_calibration"]}
