# E-NOR Project Guide

## Overview

E-NOR is a robot companion for Ronnie (age 9). It runs on a Raspberry Pi 5 with a Samsung Galaxy S22 displaying the face and chat interface.

## Architecture

- **Raspberry Pi 5** (192.168.0.40:8080): FastAPI server, motor control, LED control
- **Galaxy S22**: Browser-based face display, voice interface, chat UI
- **Claude API**: Powers E-NOR's conversational intelligence

## Key Files

| File | Purpose |
|------|---------|
| `web/index.html` | Main UI - face animation, chat, voice interface |
| `server/main.py` | FastAPI app entry point |
| `server/chat.py` | Claude API integration, E-NOR personality |
| `server/secrets.py` | API key management (stored in secrets.json) |
| `server/memories.py` | Memory storage about Ronnie (stored in memories.json) |
| `server/code_request.py` | GitHub issue creation for self-improvement |
| `scripts/setup-pi.sh` | One-time Pi setup (systemd, cron, venv) |
| `scripts/auto-pull.sh` | Auto-deployment script (runs every minute) |

## Deployment

### Auto-Deploy Pipeline

1. Push changes to any branch (e.g., `claude/...`)
2. GitHub Action automatically merges to `main`
3. Cron job on Pi runs `auto-pull.sh` every minute
4. Script detects changes, pulls from `origin/main`
5. If `server/` or `web/` files changed, restarts the `e-nor` systemd service
6. Changes are live within ~1-2 minutes

**No manual merge required** - just push and wait!

## Voice Interface

- **Wake word**: "Hey E-NOR" (many phonetic variations supported)
- **Silence delay**: 2 seconds before processing speech
- **Auto-start**: Mic activates automatically if permission was previously granted
- **Echo prevention**: Mic stops while E-NOR speaks
- **Interrupt**: Red "TAP TO INTERRUPT" button during speech
- **Chat panel**: Hidden by default, tap face to show/hide
- **End conversation**: Say "goodbye", "end the conversation", "stop listening", etc.

## E-NOR Special Abilities

- **Memory**: E-NOR remembers things about Ronnie (favorite color, friends, hobbies). Memories are stored in `memories.json` and loaded into every conversation.
- **Self-improvement**: E-NOR can create GitHub issues to request code changes to himself.

## Development Notes

- Server uses uvicorn (no --reload in production)
- Secrets stored in `secrets.json` (gitignored)
- Required secret: `ANTHROPIC_API_KEY`
- Optional secret: `GITHUB_TOKEN` (for self-improvement feature)
- Max response tokens: 150 (for voice-friendly brevity)

## Testing Voice

1. Enable Developer Mode in settings
2. On-screen console shows speech recognition in real-time
3. Use Copy button to share logs for debugging
