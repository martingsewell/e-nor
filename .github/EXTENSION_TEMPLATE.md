# E-NOR Extension Request

## Context
This issue was created by E-NOR's voice interface. A child has requested a new feature that should be implemented as an extension.

## CRITICAL RULES - READ CAREFULLY

### What You CAN Do:
- Create NEW files ONLY in the `extensions/` directory
- Create a new extension folder: `extensions/{extension_name}/`
- Add any files needed within that extension folder:
  - `manifest.json` (required)
  - `handler.py` (Python logic)
  - `emotion.json` (custom emotions)
  - `jokes.json` (custom jokes)
  - `overlay.svg` (face overlays)
  - `sounds/` folder (audio files)
  - `ui.html` (custom UI panels)
  - `data/` folder (saved data)
  - `requirements.txt` (Python dependencies)

### What You CANNOT Do:
- **NEVER** modify ANY files in `core/`
- **NEVER** modify ANY files in `config/`
- **NEVER** modify ANY files in `hardware/`
- **NEVER** modify `CLAUDE.md`
- **NEVER** modify workflow files in `.github/`
- **NEVER** modify `scripts/`
- **NEVER** delete or rename existing extensions (only create new ones)

### If the Request Seems to Require Core Changes:
Find a creative way to implement it as an extension. For example:
- "Change my face to a cat" → Create a cat_mode extension with face overlays
- "Make me speak faster" → Create a speed_mode extension that adjusts speech rate
- "Add a new emotion" → Create an extension with custom emotion.json
- "Change my personality" → Create a personality_mode extension with system prompt modifiers

## Extension Manifest Template

```json
{
  "id": "extension_id",
  "name": "Extension Name",
  "description": "What this extension does",
  "version": "1.0.0",
  "author": "Created by voice request",
  "type": "feature",
  "enabled": true,
  "voice_triggers": [
    {
      "phrases": ["trigger phrase 1", "trigger phrase 2"],
      "action": "action_name"
    }
  ],
  "provides": {
    "emotions": false,
    "jokes": false,
    "overlay": false,
    "sounds": false,
    "handler": false,
    "ui": false
  }
}
```

## Extension Types Reference:
- `feature` - General features and abilities
- `game` - Interactive games
- `mode` - Personality or behavior modes
- `content` - Jokes, facts, stories
- `visual` - Face overlays and animations
- `sound` - Sound effects and audio
- `utility` - Helper features

## Using the Extension API

Extensions can use `ExtensionAPI` from `core.server.extension_api`:

```python
from core.server.extension_api import ExtensionAPI

api = ExtensionAPI("my_extension")

# Available methods:
api.speak("Hello!")                    # Make robot speak
api.set_emotion("happy")               # Change emotion
api.show_face_overlay("my_overlay")    # Show custom overlay
api.get_memory("topic")                # Get a memory
api.add_memory("fact")                 # Add a memory
api.get_data("key")                    # Get extension data
api.set_data("key", value)             # Save extension data
api.ask_claude("prompt")               # Ask Claude a question
api.get_child_name()                   # Get child's name
api.get_robot_name()                   # Get robot's name
api.get_child_age()                    # Get child's age
```

## Testing Your Extension

1. Create all required files in `extensions/{name}/`
2. Ensure `manifest.json` is valid JSON
3. If using handler.py, ensure it's valid Python
4. Extensions are loaded when the server starts
5. Use voice triggers or UI to test functionality

## Checklist Before Completion:
- [ ] Extension folder created in `extensions/`
- [ ] `manifest.json` is valid and complete
- [ ] All voice triggers are natural phrases a child might say
- [ ] NO core files were modified
- [ ] Extension tested (if possible)
- [ ] Commit message clearly describes the new extension
