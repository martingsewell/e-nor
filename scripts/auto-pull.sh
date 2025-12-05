#!/bin/bash
# E-NOR Auto-Pull Script - runs via cron every minute

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
    git pull origin main --quiet

    if git diff --name-only "$LOCAL" "$REMOTE" | grep -qE '^server/|^web/|requirements.txt'; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Code changed, restarting service..." >> "$LOG_FILE"
        sudo systemctl restart "$SERVICE_NAME" 2>/dev/null
    fi

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Update complete: $(git log -1 --oneline)" >> "$LOG_FILE"
fi
