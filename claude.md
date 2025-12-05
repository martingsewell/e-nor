# E-NOR Robot Project

A Raspberry Pi 5 tracked robot with a Galaxy S22 smartphone as its face/display.

## Architecture

- **Raspberry Pi 5** (192.168.0.40, user: ronniesewell): Runs FastAPI server, will control motors/LEDs/audio
- **Galaxy S22**: Displays animated face via web browser, connects over WiFi
- **Communication**: WebSocket for real-time bidirectional messaging

## Project Structure

```
e-nor/
├── server/          # Python FastAPI backend
│   ├── __init__.py
│   └── main.py      # WebSocket server, serves web UI
├── web/             # Frontend displayed on phone
│   └── index.html   # SVG animated face with emotions
├── scripts/         # Deployment scripts for Pi
│   ├── setup-pi.sh  # One-time setup (systemd, venv, cron)
│   └── auto-pull.sh # Cron job for auto-updates
└── requirements.txt # Python dependencies
```

## Development Workflow

1. Make changes locally
2. Push to GitHub
3. Pi auto-pulls every minute via cron and restarts service if needed

## Key Technologies

- **Backend**: FastAPI, uvicorn, WebSockets
- **Frontend**: Vanilla JS, SVG animations
- **Deployment**: systemd service, cron auto-pull

## Common Commands (on Pi)

```bash
sudo systemctl status e-nor    # Check service
sudo systemctl restart e-nor   # Manual restart
journalctl -u e-nor -f         # View logs
```

## WebSocket Protocol

Messages are JSON with a `type` field:

| Type | Direction | Data |
|------|-----------|------|
| `emotion` | both | `{emotion: "happy"\|"sad"\|"angry"\|"surprised"\|"thinking"\|"sleepy"}` |
| `disco` | both | `{enabled: boolean}` |
| `state` | server→client | `{emotion, disco_mode}` |
| `ping`/`pong` | both | heartbeat |

## Future Hardware (not yet implemented)

- Motor control for tracks
- LED strips
- Audio output
- Sensors
