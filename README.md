# E-NOR Robot

A tracked robot with a smartphone face, built by Ronnie (age 9) and Dad.

## Quick Start

### On Raspberry Pi (first time only):

```bash
git clone https://github.com/martingsewell/e-nor.git
cd e-nor
chmod +x scripts/setup-pi.sh
./scripts/setup-pi.sh
```

### On Galaxy S22:

Open Chrome and go to: `http://192.168.0.40:8080`

Add to home screen for fullscreen PWA experience.

## Architecture

- **Pi 5**: Runs FastAPI server, controls motors/LEDs
- **S22**: Displays animated face, voice chat via Web Speech API
- **Claude**: Powers E-NOR's conversational AI brain

## Deployment

### Auto-Deploy (Recommended)

Just push to any branch! A GitHub Action automatically merges to `main`, then the Pi:
1. Pulls changes every minute via cron
2. Restarts the service if server/web files changed
3. Changes are live within ~1-2 minutes

**No manual merge required** - push and wait!

### Manual Deploy

```bash
# On the Pi
cd ~/e-nor
git pull origin main
sudo systemctl restart e-nor
```

## Configuration

Open settings (gear icon) in the web UI to configure:
- **ANTHROPIC_API_KEY** (required) - For Claude chat
- **GITHUB_TOKEN** (optional) - For self-improvement feature

## Commands

```bash
# Check status
sudo systemctl status e-nor

# View logs
journalctl -u e-nor -f

# Manual restart
sudo systemctl restart e-nor

# View auto-pull logs
cat ~/e-nor/logs/auto-pull.log
```

## Features

- Animated face with emotions (happy, sad, surprised, thinking, sleepy)
- Voice interface with "Hey E-NOR" wake word
- Text chat as fallback
- Disco mode with music and lights
- Developer console for debugging (in settings)
