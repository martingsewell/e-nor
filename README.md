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
- **S22**: Displays animated face, connects via WebSocket
- **Auto-deploy**: Push to GitHub, Pi pulls automatically every minute

## Development

Edit code locally, push to GitHub. The Pi will auto-pull and restart within 1 minute.

## Commands

```bash
# Check status
sudo systemctl status e-nor

# View logs
journalctl -u e-nor -f

# Manual restart
sudo systemctl restart e-nor
```
