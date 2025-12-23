#!/bin/bash
# E-NOR Auto-Pull Script - runs via cron every minute
# Updated for new core/extensions architecture

REPO_DIR="/home/ronniesewell/e-nor"
LOG_FILE="/home/ronniesewell/e-nor/logs/auto-pull.log"
SERVICE_NAME="e-nor"

mkdir -p "$(dirname "$LOG_FILE")"
cd "$REPO_DIR" || exit 1

git fetch origin main --quiet 2>/dev/null

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Update detected, pulling..." >> "$LOG_FILE"

    # Get the commit message for version description
    COMMIT_MSG=$(git log --format=%B -n 1 "$REMOTE")

    git pull origin main --quiet

    # Check if core code, config, or extensions changed (new structure)
    if git diff --name-only "$LOCAL" "$REMOTE" | grep -qE '^core/|^config/|^extensions/|^server/|^web/|requirements.txt'; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Code changed, creating version and restarting service..." >> "$LOG_FILE"

        # Create new version using Python directly (updated path for new structure)
        cd "$REPO_DIR" && python3 -c "
import sys
sys.path.insert(0, 'core/server')
from version_control import add_version
commit_msg = '''$COMMIT_MSG'''
# Use first line of commit message, truncated to 100 chars
description = commit_msg.split('\n')[0][:100]
if not description.strip():
    description = 'Auto-deployment update'
add_version(description, 'working')
print(f'Version created: {description}')
" >> "$LOG_FILE" 2>&1

        # Try systemctl first, fall back to pkill/nohup if not available
        if sudo systemctl restart "$SERVICE_NAME" 2>/dev/null; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Service restarted via systemctl" >> "$LOG_FILE"
        else
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] systemctl failed, using pkill/nohup..." >> "$LOG_FILE"
            pkill -f "uvicorn core.server.main:app" 2>/dev/null
            sleep 1
            cd "$REPO_DIR"
            mkdir -p logs
            nohup uvicorn core.server.main:app --host 0.0.0.0 --port 8080 > logs/enor.log 2>&1 &
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Service restarted via nohup (PID: $!)" >> "$LOG_FILE"
        fi
    fi

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Update complete: $(git log -1 --oneline)" >> "$LOG_FILE"
fi
