# E-NOR Extension Development Guide

This guide is for **Claude Code agents** implementing E-NOR extensions via the automated workflow. Read this carefully before creating any extension.

## Understanding the System

E-NOR is a robot companion that runs on a Raspberry Pi with a phone displaying the face. Extensions add new capabilities without modifying core code.

### How Extension Creation Works (The Full Flow)

1. **Child requests a feature via voice** (e.g., "Create a dragon mode")
2. **E-NOR proposes the feature** and asks for confirmation
3. **E-NOR creates a GitHub issue** with the request
4. **GitHub workflow triggers Claude Code** (this agent - YOU)
5. **You implement the extension** in `extensions/` folder only
6. **Changes auto-merge to main** and deploy to the Pi (~2-5 minutes total)
7. **Extension is now available** for the child to use

**IMPORTANT**: The extension is NOT immediately available. It takes 2-5 minutes to deploy. E-NOR should NOT claim a mode is active right after requesting it.

---

## Extension Types

| Type | Purpose | Example |
|------|---------|---------|
| `mode` | Changes E-NOR's personality/appearance | Dragon Mode, Cat Mode |
| `game` | Interactive games | Times Tables Quiz |
| `feature` | Adds new capabilities | Weather Report |
| `content` | Provides content (jokes, stories) | Pirate Jokes |
| `visual` | Visual effects | Sparkle Effect |
| `sound` | Sound effects | Fart Sounds |
| `utility` | Helper tools | Timer, Calculator |

---

## Extension Categories (UI Organization)

Extensions appear in the main UI under **category buttons** at the bottom of the face screen. The `category` field in manifest.json determines which button the extension appears under.

### Available Categories

| Category | Icon | Purpose | Default for type |
|----------|------|---------|------------------|
| `games` | 🎮 | Games, interactive activities | `game` |
| `modes` | 🎭 | Personality modes, character transformations | `mode`, `emotion` |
| `tools` | 🛠️ | Utilities, helpers, calculators | `utility`, `action`, `feature` |
| `quizzes` | 🧠 | Educational quizzes, trivia | - |
| `custom1` | 📖 | Stories (configurable) | - |
| `custom2` | 🎨 | Creative (configurable) | - |
| `custom3` | 📚 | Learning (configurable) | - |
| `custom4` | 😂 | Fun (configurable) | - |

### Setting the Category

Add the `category` field to your manifest.json:

```json
{
  "id": "times_tables_quiz",
  "name": "Times Tables Quiz",
  "type": "game",
  "category": "quizzes",  // <-- This determines UI placement
  ...
}
```

**Important Notes:**
- If `category` is not specified, it's inferred from the `type` field
- Games (`type: "game"`) default to `category: "games"`
- Modes (`type: "mode"`) default to `category: "modes"`
- Most other types default to `category: "tools"`

### Category Guidelines

| If creating... | Set category to... |
|----------------|-------------------|
| A game or interactive activity | `games` |
| A personality mode with overlays | `modes` |
| An educational quiz | `quizzes` |
| A helper tool or utility | `tools` |
| A story-telling extension | `custom1` (Stories) |
| A creative/art extension | `custom2` (Creative) |
| An educational learning tool | `custom3` (Learning) |
| A fun/jokes extension | `custom4` (Fun) |

---

## Mode Extensions (CRITICAL - Read Carefully)

Mode extensions are special. They:
- Change E-NOR's personality (how it talks/responds)
- Can change E-NOR's appearance (overlays, emotions)
- Have activation and deactivation voice triggers
- Should register in the UI mode selector

### Mode Extension Structure

```
extensions/dragon_mode/
├── manifest.json        # REQUIRED: Mode metadata with voice_triggers
├── handler.py           # REQUIRED: Handle activate/deactivate actions
├── emotion.json         # Custom emotion for this mode
├── overlay.svg          # Face overlay graphics (wings, ears, etc.)
└── sounds/              # Sound effects
    ├── activate.wav
    └── deactivate.wav
```

### Mode Manifest Template

```json
{
  "id": "dragon_mode",
  "name": "Dragon Mode",
  "description": "Transforms E-NOR into a fierce dragon with roars and fire effects",
  "version": "1.0.0",
  "author": "the child",
  "type": "mode",
  "category": "modes",
  "enabled": true,
  "voice_triggers": [
    {
      "phrases": [
        "dragon mode",
        "activate dragon mode",
        "turn on dragon mode",
        "become a dragon"
      ],
      "action": "activate_dragon_mode",
      "handler": "handle_action"
    },
    {
      "phrases": [
        "deactivate dragon mode",
        "turn off dragon mode",
        "stop dragon mode",
        "normal mode"
      ],
      "action": "deactivate_dragon_mode",
      "handler": "handle_action"
    }
  ],
  "ui": {
    "button_label": "Dragon",
    "button_emoji": "🐲",
    "button_color": "#ff4500"
  },
  "provides": {
    "emotions": true,
    "overlay": true,
    "sounds": true,
    "handler": true
  }
}
```

### Mode Handler Template (handler.py)

```python
"""
Dragon Mode Extension Handler
"""

import random
from pathlib import Path
from core.server.extension_api import ExtensionAPI

# Create API instance - MUST match extension folder name
api = ExtensionAPI("dragon_mode", Path(__file__).parent)

# Mode-specific responses
GREETINGS = [
    "ROAR! I am now a dragon!",
    "Feel my dragon power!"
]

FAREWELLS = [
    "The dragon returns to slumber...",
    "Back to normal mode!"
]

async def handle_action(action: str, params: dict = None) -> dict:
    """Handle mode actions"""

    if action == "activate_dragon_mode":
        # Step 1: Set the mode as active (broadcasts to UI)
        await api.set_mode("dragon_mode", True)

        # Step 2: Show custom emotion
        await api.set_emotion("fierce")

        # Step 3: Show face overlay (if you created one)
        await api.show_face_overlay("dragon_mode")

        # Step 4: Play activation sound
        await api.play_sound("activate.wav")

        # Step 5: Speak the activation message
        await api.speak(random.choice(GREETINGS))

        # Step 6: Store mode state (for checking later)
        api.set_data("active", True)

        return {"success": True, "message": "Dragon mode activated!"}

    elif action == "deactivate_dragon_mode":
        # Step 1: Deactivate mode
        await api.set_mode("dragon_mode", False)

        # Step 2: Return to happy emotion
        await api.set_emotion("happy")

        # Step 3: Hide overlay
        await api.hide_face_overlay("dragon_mode")

        # Step 4: Play deactivation sound
        await api.play_sound("deactivate.wav")

        # Step 5: Speak farewell
        await api.speak(random.choice(FAREWELLS))

        # Step 6: Update mode state
        api.set_data("active", False)

        return {"success": True, "message": "Dragon mode deactivated!"}

    return {"success": False, "message": f"Unknown action: {action}"}

async def on_load():
    """Called when extension loads - reset state"""
    api.set_data("active", False)
```

---

## Extension API Reference

The `ExtensionAPI` class provides all the tools extensions need:

### Communication

```python
# Make E-NOR speak (text-to-speech)
await api.speak("Hello!")

# Show a message in the chat interface
await api.show_message("Status update here")

# Broadcast raw data to all connected clients
await api.broadcast({"type": "custom_event", "data": "value"})
```

### Emotions & Appearance

```python
# Change facial expression (see emotion list below)
await api.set_emotion("happy")

# Show a face overlay (ears, hats, accessories)
await api.show_face_overlay("overlay_id")

# Hide a face overlay
await api.hide_face_overlay("overlay_id")

# Activate/deactivate a mode
await api.set_mode("mode_id", True)   # activate
await api.set_mode("mode_id", False)  # deactivate
```

### Built-in Emotions

- `happy` - Default, smiling
- `sad` - Downturned, blue tint
- `surprised` - Wide eyes, raised brows
- `thinking` - Looking up, processing
- `excited` - Big smile, sparkles
- `cool` - Sunglasses effect
- `sleepy` - Half-closed eyes
- `glitchy` - Glitch effect
- `sparkling` - Sparkle particles
- `laser-focused` - Intense focus
- `processing` - Loading animation
- `overclocked` - Energetic pulsing
- `energetic` - Bouncy animation
- `mysterious` - Purple glow
- `mischievous` - Sly grin

### Custom Emotions

Create `emotion.json` in your extension folder:

```json
{
  "fierce": {
    "name": "Fierce Dragon",
    "eyebrows": {
      "angle": -15,
      "position": "low"
    },
    "eyes": {
      "shape": "narrow",
      "color": "#ff4500",
      "glow": true
    },
    "mouth": {
      "shape": "roar",
      "teeth_visible": true
    },
    "effects": {
      "color": "#ff4500",
      "particles": "fire"
    },
    "animation": {
      "type": "pulse",
      "intensity": "high"
    }
  }
}
```

### UI Panels

```python
# Show a custom HTML panel
await api.show_panel("<div>Custom content</div>", panel_id="my_panel")

# Update panel content
await api.update_panel({"text": "Updated!"}, panel_id="my_panel")

# Hide a panel
await api.hide_panel(panel_id="my_panel")
```

### Sound Effects

```python
# Play a sound from extension's sounds/ folder
await api.play_sound("roar.wav")
```

Supported formats: `.wav`, `.mp3`, `.ogg`

### Data Storage

```python
# Save data (persists across restarts)
api.set_data("high_score", 100)

# Get data (returns default if not set)
score = api.get_data("high_score", 0)

# Delete data
api.delete_data("high_score")

# Get all stored data
all_data = api.get_all_data()
```

Data is stored in `extensions/{name}/data/` as JSON files.

### Configuration Access

```python
# Get child's name (for personalization)
name = api.get_child_name()  # Returns "Ronnie"

# Get child's age
age = api.get_child_age()  # Returns 9

# Get robot's name
robot = api.get_robot_name()  # Returns "E-NOR"

# Get full configuration
config = api.get_config()
```

### Memory Access

```python
# Get memories about the child
memories = api.get_memories()  # ["Loves dinosaurs", "Favorite color is blue"]

# Add a new memory
await api.add_memory("Just beat the quiz game with 100% score")
```

### Claude Integration

```python
# Ask Claude for help with extension logic
answer = await api.ask_claude("What's 42 divided by 7?")
```

### Hardware (Future)

```python
# Trigger motor movement (when hardware is configured)
await api.move("wave", {"speed": "fast"})
```

---

## Face Overlays

Create `overlay.svg` to add visual elements on top of E-NOR's face:

```svg
<svg viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg">
  <!-- Dragon horns -->
  <path d="M 80 100 L 60 30 L 100 80 Z" fill="#ff4500" opacity="0.9"/>
  <path d="M 320 100 L 340 30 L 300 80 Z" fill="#ff4500" opacity="0.9"/>

  <!-- Dragon wings (behind face) -->
  <path d="M 0 200 Q 50 100 100 200" stroke="#ff4500" fill="none" stroke-width="3"/>
  <path d="M 400 200 Q 350 100 300 200" stroke="#ff4500" fill="none" stroke-width="3"/>
</svg>
```

The overlay is displayed on top of the face SVG. Use the same 400x400 viewBox.

---

## Voice Triggers

Voice triggers let users activate features by speaking:

```json
{
  "voice_triggers": [
    {
      "phrases": [
        "tell me a dragon fact",
        "dragon fact",
        "what do you know about dragons"
      ],
      "action": "tell_dragon_fact",
      "handler": "handle_action"
    }
  ]
}
```

Tips:
- Include variations of how a child might say it
- Keep phrases natural and conversational
- Use lowercase (matching is case-insensitive)
- Include both "please" and non-"please" versions if relevant

---

## Game Extensions

For game extensions, use a state machine pattern:

```python
"""Simple Quiz Game"""

from pathlib import Path
from core.server.extension_api import ExtensionAPI

api = ExtensionAPI("quiz_game", Path(__file__).parent)

async def handle_action(action: str, params: dict = None) -> dict:
    if action == "start_quiz":
        # Initialize game state
        api.set_data("score", 0)
        api.set_data("question_index", 0)

        await api.speak("Let's start the quiz! Question 1...")
        # Ask first question
        await ask_question(0)
        return {"success": True}

    elif action == "answer_question":
        answer = params.get("answer", "").lower()
        # Check answer logic...

async def ask_question(index):
    questions = api.get_data("questions", [
        {"q": "What is 2 + 2?", "a": "4"},
        {"q": "What color is the sky?", "a": "blue"}
    ])

    if index < len(questions):
        await api.speak(questions[index]["q"])
    else:
        score = api.get_data("score", 0)
        await api.speak(f"Quiz complete! You scored {score}!")
```

---

## Error Handling

Always handle errors gracefully:

```python
async def handle_action(action: str, params: dict = None) -> dict:
    try:
        if action == "risky_action":
            # ... do something
            return {"success": True}
    except Exception as e:
        await api.speak("Oops, something went wrong!")
        return {"success": False, "error": str(e)}

    return {"success": False, "message": f"Unknown action: {action}"}
```

---

## Testing Your Extension

Before committing, verify:

1. **manifest.json is valid JSON** - Use a JSON validator
2. **handler.py has no syntax errors** - Python syntax check
3. **All file references exist** - Sounds, overlays, etc.
4. **Voice triggers are unique** - Don't conflict with other extensions

---

## Common Mistakes to Avoid

❌ **DON'T modify core/ files** - Extensions ONLY go in extensions/
❌ **DON'T use hardcoded paths** - Use `Path(__file__).parent`
❌ **DON'T forget await** - All api methods are async
❌ **DON'T use blocking code** - Use asyncio if needed
❌ **DON'T assume mode is instant** - Deployment takes 2-5 minutes

✅ **DO use the ExtensionAPI** - It handles all communication
✅ **DO store state with api.set_data()** - For persistence
✅ **DO include activation AND deactivation** - For modes
✅ **DO test JSON validity** - Broken manifest = broken extension
✅ **DO keep responses short** - They're spoken aloud

---

## File Checklist for Mode Extensions

- [ ] `manifest.json` with `type: "mode"`
- [ ] Voice triggers for activation (multiple phrases)
- [ ] Voice triggers for deactivation (multiple phrases)
- [ ] `handler.py` with `handle_action` function
- [ ] `activate_{mode_id}` action handler
- [ ] `deactivate_{mode_id}` action handler
- [ ] Custom emotion in `emotion.json` (optional but recommended)
- [ ] Face overlay in `overlay.svg` (optional but recommended)
- [ ] Sound effects in `sounds/` (optional)
- [ ] `ui` section with button config in manifest

---

## Quick Reference

| Task | API Call |
|------|----------|
| Speak | `await api.speak("text")` |
| Change emotion | `await api.set_emotion("happy")` |
| Activate mode | `await api.set_mode("mode_id", True)` |
| Deactivate mode | `await api.set_mode("mode_id", False)` |
| Show overlay | `await api.show_face_overlay("id")` |
| Hide overlay | `await api.hide_face_overlay("id")` |
| Play sound | `await api.play_sound("file.wav")` |
| Save data | `api.set_data("key", value)` |
| Load data | `api.get_data("key", default)` |
| Show panel | `await api.show_panel("<html>")` |
| Get child name | `api.get_child_name()` |
| Ask Claude | `await api.ask_claude("question")` |

---

## Need Help?

- Check existing extensions in `extensions/` for examples
- Read `core/server/extension_api.py` for full API
- Look at `core/schemas/manifest.schema.json` for manifest format
