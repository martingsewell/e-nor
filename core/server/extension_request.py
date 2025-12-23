"""
E-NOR Extension Request Module
Handles voice-triggered extension creation via GitHub issues

This replaces the generic code_request system for voice interactions.
Extensions are created in the extensions/ folder without modifying core code.
"""

import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/extension-requests", tags=["extension-requests"])

# Log file for tracking extension requests
REQUESTS_LOG_FILE = Path(__file__).parent.parent.parent / "config" / "extension_requests.json"


def load_extension_requests() -> List[Dict]:
    """Load extension request history"""
    if not REQUESTS_LOG_FILE.exists():
        return []

    try:
        with open(REQUESTS_LOG_FILE, 'r') as f:
            data = json.load(f)
            return data.get("requests", [])
    except (json.JSONDecodeError, IOError):
        return []


def save_extension_requests(requests: List[Dict]) -> bool:
    """Save extension request history"""
    try:
        REQUESTS_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(REQUESTS_LOG_FILE, 'w') as f:
            json.dump({"requests": requests}, f, indent=2)
        return True
    except IOError:
        return False


def add_extension_request(title: str, description: str, issue_number: int = None, issue_url: str = None) -> Dict:
    """Add a new extension request to the log"""
    requests = load_extension_requests()

    new_request = {
        "title": title,
        "description": description,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "issue_number": issue_number,
        "issue_url": issue_url
    }

    requests.append(new_request)

    # Keep only last 30 requests
    if len(requests) > 30:
        requests = requests[-30:]

    save_extension_requests(requests)
    return new_request


def extension_exists(title: str) -> bool:
    """Check if an extension actually exists in the extensions folder"""
    extensions_dir = Path(__file__).parent.parent.parent / "extensions"
    sanitized_name = _sanitize_extension_name(title)

    # Check if extension folder exists
    extension_path = extensions_dir / sanitized_name
    if extension_path.exists() and extension_path.is_dir():
        # Check if it has a manifest.json (meaning it was actually built)
        manifest_path = extension_path / "manifest.json"
        return manifest_path.exists()

    return False


def find_similar_request(title: str, description: str) -> Optional[Dict]:
    """Check if a similar extension request already exists AND was actually built"""
    requests = load_extension_requests()
    title_lower = title.lower().strip()

    for req in requests:
        if req.get("status") in ["pending", "in_progress"]:
            existing_title = req.get("title", "").lower().strip()
            if title_lower == existing_title or title_lower in existing_title or existing_title in title_lower:
                # Only treat as duplicate if the extension was actually created
                if extension_exists(req.get("title", "")):
                    return req
                else:
                    # Extension was requested but never built - allow re-request
                    print(f"[ExtensionRequest] Previous request '{existing_title}' was never built, allowing re-request")
                    return None

    return None


def get_github_config() -> Dict:
    """Get GitHub configuration"""
    from .config import load_config
    config = load_config()
    return config.get("github", {})


def get_child_name() -> str:
    """Get the child's name from config"""
    from .config import get_child_name
    return get_child_name() or "the child"


def create_extension_issue(title: str, description: str, child_request: str) -> Dict:
    """
    Create a GitHub issue for an extension request.
    The issue body includes strict instructions to ONLY create files in extensions/.
    """
    from .secrets import get_secret, has_secret

    print(f"[ExtensionRequest] Creating issue: '{title}'")

    if not has_secret("GITHUB_TOKEN"):
        print("[ExtensionRequest] ERROR: GITHUB_TOKEN not configured")
        return {"success": False, "message": "GitHub token not configured"}

    # Check for duplicate
    existing = find_similar_request(title, description)
    if existing:
        issue_num = existing.get("issue_number")
        if issue_num:
            return {
                "success": False,
                "duplicate": True,
                "message": f"Already requested! It's Issue #{issue_num}.",
                "existing_issue": issue_num
            }
        return {
            "success": False,
            "duplicate": True,
            "message": "Something similar was already requested!"
        }

    github_config = get_github_config()
    owner = github_config.get("owner", "martingsewell")
    repo = github_config.get("repo", "e-nor")
    child_name = get_child_name()

    # Build the issue body with STRICT extension-only instructions
    body = f"""## Extension Request from {child_name} (via voice)

### Original Request
"{child_request}"

### Feature Description
{description}

---

## Instructions for Claude Code

**IMPORTANT: First read `AGENT_GUIDE.md`** in the repository root for comprehensive documentation.

**Create this feature as an extension.** Place all files in `extensions/` folder.

### CRITICAL RULES - READ CAREFULLY

#### ALLOWED
- Create ANY files in `extensions/{_sanitize_extension_name(title)}/`
- Read files in `core/schemas/` for reference
- Use any Python libraries (add to extension's requirements.txt)
- Create Python code, HTML, CSS, JS, JSON, media files
- Register hooks using the core extension API

#### FORBIDDEN - DO NOT DO THESE
- Modify ANY files in `core/` directory
- Modify ANY files in `config/` directory
- Modify ANY files in `hardware/` directory
- Modify ANY files in `server/` directory (legacy location)
- Modify ANY files in `web/` directory (legacy location)
- Delete or modify existing extensions

### Extension Structure

```
extensions/{_sanitize_extension_name(title)}/
├── manifest.json          # Required: extension metadata
├── handler.py             # Optional: Python logic
├── emotion.json           # Optional: custom emotion definition
├── jokes.json             # Optional: custom jokes
├── overlay.svg            # Optional: face overlay graphics
├── sounds/                # Optional: sound effects
├── ui.html                # Optional: custom UI component
├── data/                  # Optional: extension data storage
└── requirements.txt       # Optional: Python dependencies
```

### manifest.json Template

```json
{{
  "id": "{_sanitize_extension_name(title)}",
  "name": "{title}",
  "description": "{description}",
  "version": "1.0.0",
  "author": "{child_name}",
  "type": "feature",
  "category": "tools",
  "enabled": true,
  "voice_triggers": [
    {{
      "phrases": ["example trigger phrase"],
      "action": "example_action"
    }}
  ]
}}
```

### Category Field (IMPORTANT)

The `category` field determines where the extension appears in the UI button bar. Choose the appropriate category:

| Category | Use for | Icon |
|----------|---------|------|
| `games` | Games, interactive activities | 🎮 |
| `modes` | Personality modes, character transformations | 🎭 |
| `tools` | Utilities, helpers | 🛠️ |
| `quizzes` | Educational quizzes, trivia | 🧠 |
| `custom1` | Stories | 📖 |
| `custom2` | Creative/art | 🎨 |
| `custom3` | Learning/educational | 📚 |
| `custom4` | Fun/jokes | 😂 |

**Default mapping from type:**
- `type: "game"` → `category: "games"`
- `type: "mode"` → `category: "modes"`
- Other types → `category: "tools"`

### Extension API Reference

Extensions can use the ExtensionAPI class which provides:

```python
# Communication
api.speak(text)              # Make E-NOR say something
api.show_message(text)       # Display in chat
api.set_emotion(emotion)     # Change facial expression
api.broadcast(data)          # Send WebSocket message

# Face customization
api.show_face_overlay(id)    # Show overlay (ears, hats, etc.)
api.hide_face_overlay(id)    # Hide overlay
api.set_mode(mode, enabled)  # Activate custom mode

# UI
api.show_panel(html)         # Display custom UI
api.hide_panel()             # Hide UI panel
api.play_sound(file)         # Play sound from extension

# Data storage
api.get_data(key)            # Get saved data
api.set_data(key, value)     # Save data
api.delete_data(key)         # Delete data

# Configuration access
api.get_child_name()         # Get child's name
api.get_child_age()          # Get child's age
api.get_robot_name()         # Get robot's name
api.get_config()             # Get full config

# Claude integration
api.ask_claude(prompt)       # Ask Claude for help

# Hardware (when configured)
api.move(action, params)     # Trigger motor movement
```

### Important Notes

- This is a robot companion for a {child_name} (age 8-14)
- Keep interactions fun, educational, and age-appropriate
- Add helpful feedback and encouragement
- The extension should work standalone without modifying core code
- Test that the manifest.json is valid JSON
- Auto-deploys when merged to main branch

---

*This request was made through E-NOR's voice interface. The child asked for this feature using their own words.*
"""

    try:
        token = get_secret("GITHUB_TOKEN")
        url = f"https://api.github.com/repos/{owner}/{repo}/issues"
        print(f"[ExtensionRequest] GitHub URL: {url}")

        data = {
            "title": f"[Extension] {title}",
            "body": body,
            "labels": ["enor-request", "extension", "voice-request"]
        }

        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "User-Agent": "E-NOR-Robot"
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )

        print(f"[ExtensionRequest] Sending request to GitHub...")
        with urllib.request.urlopen(req) as response:
            issue = json.loads(response.read().decode('utf-8'))

        print(f"[ExtensionRequest] SUCCESS! Created issue #{issue['number']}")

        # Log the request
        add_extension_request(
            title=title,
            description=description,
            issue_number=issue["number"],
            issue_url=issue["html_url"]
        )

        return {
            "success": True,
            "issue_number": issue["number"],
            "url": issue["html_url"],
            "message": f"Created extension request #{issue['number']}!"
        }

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"[ExtensionRequest] HTTP ERROR {e.code}: {error_body}")
        return {"success": False, "message": f"GitHub API error: {e.code} - {error_body[:100]}"}
    except Exception as e:
        print(f"[ExtensionRequest] EXCEPTION: {type(e).__name__}: {e}")
        return {"success": False, "message": str(e)}


def _sanitize_extension_name(name: str) -> str:
    """Convert a title to a valid extension folder name"""
    # Lowercase, replace spaces with underscores, remove special chars
    sanitized = name.lower().strip()
    sanitized = sanitized.replace(" ", "_")
    sanitized = "".join(c for c in sanitized if c.isalnum() or c == "_")
    # Remove consecutive underscores
    while "__" in sanitized:
        sanitized = sanitized.replace("__", "_")
    return sanitized[:50]  # Limit length


def suggest_alternative(request: str) -> Optional[str]:
    """
    When a request would need core changes, suggest an extension alternative.
    Returns a suggestion string or None.
    """
    request_lower = request.lower()

    # Map of core-change requests to extension alternatives
    alternatives = {
        "change voice": "I can't change my core voice, but I could create a special talking mode! Want me to make a 'silly voice mode' where I add fun effects to what I say?",
        "change my face": "I can't redesign my whole face, but I could add overlays! Want me to create a mode with different eyes, ears, or accessories?",
        "make faster": "I can't speed up my brain, but I could create a quick-response mode for simple questions! Would you like that?",
        "change color permanently": "I can't change my core colors, but I could create color themes as modes! Want me to make a purple mode, rainbow mode, or something else?",
        "change wake word": "The wake word is set in my settings, but I could create additional trigger phrases! What word would you like me to also respond to?",
        "remove feature": "I can't remove my core features, but I could create a mode that hides or changes things! What would you like to change?",
    }

    for trigger, suggestion in alternatives.items():
        if trigger in request_lower:
            return suggestion

    return None


def create_bug_report_issue(power_name: str, description: str) -> dict:
    """Create a GitHub issue for a bug report about an extension"""
    from .config import load_config
    from .secrets import get_secret, has_secret

    config = load_config()
    owner = config.get("github", {}).get("owner")
    repo = config.get("github", {}).get("repo")

    if not owner or not repo:
        return {"success": False, "message": "GitHub not configured"}

    if not has_secret("GITHUB_TOKEN"):
        return {"success": False, "message": "GitHub token not configured"}

    body = f"""## Bug Report

**Extension:** {power_name}
**Reported via:** Voice interface

## Description
{description}

---

## Instructions for fixing

1. Find the extension in `extensions/` folder
2. Review the manifest.json and handler.py (if exists)
3. Fix the reported issue
4. Test the extension works correctly
5. Commit and push changes

*This bug was reported through E-NOR's voice interface.*
"""

    try:
        token = get_secret("GITHUB_TOKEN")
        url = f"https://api.github.com/repos/{owner}/{repo}/issues"

        data = {
            "title": f"[Bug] {power_name}: {description[:50]}",
            "body": body,
            "labels": ["enor-request", "bug", "extension"]
        }

        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "User-Agent": "E-NOR-Robot"
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )

        with urllib.request.urlopen(req) as response:
            issue = json.loads(response.read().decode('utf-8'))

        return {
            "success": True,
            "issue_number": issue["number"],
            "url": issue["html_url"],
            "message": f"Bug report created as issue #{issue['number']}"
        }

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        return {"success": False, "message": f"GitHub API error: {e.code}"}
    except Exception as e:
        return {"success": False, "message": str(e)}


# Pydantic models
class ExtensionRequestInput(BaseModel):
    title: str
    description: str
    child_request: str  # The original words the child used


# API Endpoints

@router.post("")
async def create_request(request: ExtensionRequestInput) -> Dict:
    """Create a new extension request"""
    return create_extension_issue(
        title=request.title,
        description=request.description,
        child_request=request.child_request
    )


@router.get("")
async def get_requests() -> Dict:
    """Get all extension requests"""
    requests = load_extension_requests()
    pending = [r for r in requests if r.get("status") in ["pending", "in_progress"]]
    completed = [r for r in requests if r.get("status") == "completed"]

    return {
        "requests": requests,
        "pending": pending,
        "completed": completed,
        "pending_count": len(pending)
    }


@router.get("/pending")
async def get_pending_requests() -> Dict:
    """Get only pending extension requests"""
    requests = load_extension_requests()
    pending = [r for r in requests if r.get("status") in ["pending", "in_progress"]]
    return {"pending": pending, "count": len(pending)}


@router.get("/status")
async def get_extension_request_status() -> Dict:
    """Check if extension requests are enabled"""
    from .secrets import has_secret
    from .config import load_config

    config = load_config()
    features = config.get("features", {})

    has_token = has_secret("GITHUB_TOKEN")
    extension_creation_enabled = features.get("extension_creation_enabled", True)

    return {
        "enabled": has_token and extension_creation_enabled,
        "github_configured": has_token,
        "feature_enabled": extension_creation_enabled,
        "message": "Extension requests enabled!" if (has_token and extension_creation_enabled) else "Extension requests not available"
    }
