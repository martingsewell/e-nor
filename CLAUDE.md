# E-NOR Project Guide

## Overview

E-NOR is a customizable robot companion template. It runs on a Raspberry Pi 5 with a phone displaying the face and chat interface. The architecture separates **core code** (protected) from **extensions** (customizable), allowing children to add features via voice without modifying the base system.

## Deployment

**Pi Location:** `/home/ronniesewell/e-nor`
**Service:** uvicorn running on port 8080
**Auto-deploy:** Branches auto-merge to `main` and deploy to the Pi

### Manual deployment (on Pi via SSH):
```bash
cd /home/ronniesewell/e-nor
git pull
sudo systemctl restart enor
```

### Check logs:
```bash
journalctl -u enor -f
# or
tail -f /home/ronniesewell/e-nor/logs/*.log
```

### Push logs for remote debugging:
```bash
cd /home/ronniesewell/e-nor
./scripts/push-logs.sh
```
This pushes logs to the `logs` branch (excluded from auto-merge to main).
Claude Code can then read logs from `https://raw.githubusercontent.com/{owner}/{repo}/logs/logs/enor_*.log`

## Architecture

### Directory Structure

```
e-nor/
├── core/                    # PROTECTED - Base robot code
│   ├── server/              # FastAPI backend
│   │   ├── main.py          # Server entry point
│   │   ├── chat.py          # Claude API integration
│   │   ├── config.py        # Configuration management
│   │   ├── plugin_loader.py # Extension discovery
│   │   ├── extension_api.py # API for extensions
│   │   ├── extension_request.py # Voice extension creation
│   │   ├── secrets.py       # API key management
│   │   ├── memories.py      # Memory storage
│   │   └── ...
│   ├── web/
│   │   ├── index.html       # Main face UI
│   │   └── admin.html       # Parent dashboard
│   └── schemas/
│       └── manifest.schema.json
│
├── extensions/              # CHILD'S SPACE - Custom features
│   └── README.md
│
├── config/
│   ├── settings.json        # Robot/child identity, wake words
│   └── memories.json        # Stored memories
│
├── hardware/                # Motor control (future)
│
└── scripts/
    ├── setup-pi.sh          # One-time Pi setup
    └── auto-pull.sh         # Auto-deployment
```

### Two Access Modes

| Mode | Access | Can Edit Core? |
|------|--------|----------------|
| **CLI (Developer)** | Full codebase | Yes (manual commit) |
| **Voice Pipeline** | Extensions only | No - creates issues in extensions/ only |

## Key URLs

- `/` - Main face UI
- `/admin` - Parent dashboard (configuration, memories, extensions)
- `/api/config` - Configuration API
- `/api/extensions` - Extensions management
- `/health` - Health check

## Configuration System

All identity and settings are in `config/settings.json`:

```json
{
  "robot": { "name": "E-NOR", "display_name": "E-NOR" },
  "child": { "name": "Ronnie", "birthdate": "2015-03-15" },
  "wake_words": { "primary": "hey enor", "variants": [...] },
  "features": { "voice_enabled": true, ... },
  "github": { "owner": "...", "repo": "..." }
}
```

## Extension System

### Creating Extensions via Voice

Child says: "Create a times tables quiz"
→ E-NOR proposes the feature
→ Child confirms: "Yes!"
→ GitHub issue created with extension-only instructions
→ Automated Claude Code implements in `extensions/`
→ Auto-deploys

### Extension Structure

```
extensions/my_feature/
├── manifest.json      # Required: metadata
├── handler.py         # Optional: Python logic
├── emotion.json       # Optional: custom emotion
├── jokes.json         # Optional: custom jokes
├── overlay.svg        # Optional: face overlay
├── sounds/            # Optional: sound effects
└── data/              # Optional: saved data
```

### Extension API

Extensions can use the `ExtensionAPI` class:

```python
# Communication
api.speak(text)              # Make robot speak (text-to-speech)
api.set_emotion(name)        # Change expression (happy, sad, excited, etc.)
api.broadcast(message)       # Send WebSocket message to all clients

# Visual UI
api.show_panel(html)         # Show a fullscreen HTML panel
api.hide_panel()             # Hide the panel
api.show_face_overlay()      # Add visual overlay to face

# Data persistence
api.get_data(key)            # Load saved data
api.set_data(key, value)     # Save data (persisted to disk)

# AI integration
api.ask_claude(prompt)       # Use Claude for logic/decisions

# Motor control and dancing
api.move(action, params)     # Send movement command
api.start_dance(duration)    # Start dancing (moves side to side like disco)
api.stop_dance()             # Stop dancing

# Emergency stop check (use in loops)
api.is_stopped()             # Returns True if emergency stop was triggered
api.clear_stop_flag()        # Clear stop flag when starting new action
```

### Motor Control for Extensions

Extensions can make E-NOR move and dance! Here's how:

```python
# In your handler.py:
import asyncio
from core.server.extension_api import ExtensionAPI

api = ExtensionAPI("my_extension", Path(__file__).parent)

async def handle_action(action: str, params: dict = None) -> dict:
    if action == "start_dancing":
        # Start a dance routine (5 seconds by default)
        await api.start_dance(duration=5.0)
        return {"success": True, "message": "Dancing!"}

    elif action == "long_dance":
        # For longer dances, run in background task
        asyncio.create_task(dance_loop())
        return {"success": True}

async def dance_loop():
    """Keep dancing while active"""
    api.set_data("dancing", True)
    while api.get_data("dancing", False) and not api.is_stopped():
        await api.start_dance(duration=10.0)
        await asyncio.sleep(1)  # Brief pause between dance sessions
    await api.stop_dance()
```

**Important notes for extensions with loops:**
- Always check `api.is_stopped()` in your loops
- Call `api.clear_stop_flag()` when starting a new action
- The emergency stop button will stop all running extensions

### Game Extensions

For game extensions, use `ui_components` in your manifest.json:

```json
{
  "type": "game",
  "ui_components": [
    {
      "id": "my_game_panel",
      "type": "game",
      "file": "ui.html"
    }
  ]
}
```

Games can receive controller input by listening for messages:

```javascript
// In your game's ui.html
window.addEventListener('message', (event) => {
    if (event.data.type === 'game_control') {
        // direction: 'up', 'down', 'left', 'right'
        handleDirection(event.data.direction);
    } else if (event.data.type === 'game_action') {
        // action: 'restart', 'close'
        handleAction(event.data.action);
    }
});
```

## Voice Pipeline Rules

**IMPORTANT**: Voice-triggered extension requests:

- Can ONLY create files in `extensions/` folder
- CANNOT modify `core/`, `config/`, or `hardware/`
- Should suggest creative alternatives when core changes are needed

Example: "Make yourself look like a cat"
→ E-NOR: "I can't change my core face, but I could create a cat mode with ears and whiskers overlay! Want me to make that?"

## Parent Dashboard

Access at `/admin` to manage:
- Robot name and identity
- Child name, birthdate, pronouns
- Wake word variants (with voice recording)
- Memories (view, delete, set limits)
- Feature toggles
- Installed extensions
- API keys

## Deployment

1. Push changes to any branch
2. GitHub Action auto-merges to `main`
3. Pi cron job pulls every minute
4. If `core/`, `config/`, or `extensions/` changed → restart service
5. Live within ~1-2 minutes

## Development Guidelines

### For CLI Sessions (This Mode)

- Full access to modify any files
- Commits are manual (developer reviews)
- Can edit core code when needed
- Update `config/settings.json` for identity changes

### For Voice Pipeline Issues

Include these instructions in GitHub issues:

```
ALLOWED:
- Create files in extensions/{name}/
- Read core/schemas/ for reference

FORBIDDEN:
- Modify core/
- Modify config/
- Modify hardware/
```

## Key Files Reference

| File | Purpose |
|------|---------|
| `core/web/index.html` | Main face UI, voice interface |
| `core/web/admin.html` | Parent dashboard |
| `core/server/main.py` | FastAPI entry point, routes |
| `core/server/chat.py` | Claude integration, extension actions |
| `core/server/config.py` | Configuration API |
| `core/server/plugin_loader.py` | Extension discovery |
| `core/server/extension_request.py` | Voice extension creation |
| `config/settings.json` | Robot/child identity |
| `extensions/` | Child's custom features |

## Running the Server

```bash
cd /path/to/e-nor
uvicorn core.server.main:app --host 0.0.0.0 --port 8080
```

## Secrets

Required: `ANTHROPIC_API_KEY` - Claude API access
Optional: `GITHUB_TOKEN` - For extension creation via voice

Stored in `secrets.json` (gitignored), managed via dashboard.
