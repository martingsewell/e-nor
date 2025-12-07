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
    
    # Get the commit message for version description
    COMMIT_MSG=$(git log --format=%B -n 1 "$REMOTE")
    
    git pull origin main --quiet

    if git diff --name-only "$LOCAL" "$REMOTE" | grep -qE '^server/|^web/|requirements.txt'; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Code changed, creating version and restarting service..." >> "$LOG_FILE"
        
        # Create new version using Python directly
        cd "$REPO_DIR" && python3 -c "
import sys
sys.path.append('server')
from version_control import add_version
commit_msg = '''$COMMIT_MSG'''
# Use first line of commit message, truncated to 100 chars
description = commit_msg.split('\n')[0][:100]
if not description.strip():
    description = 'Auto-deployment update'
add_version(description, 'working')
print(f'✅ Version created: {description}')
" >> "$LOG_FILE" 2>&1
        
        sudo systemctl restart "$SERVICE_NAME" 2>/dev/null
    fi

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Update complete: $(git log -1 --oneline)" >> "$LOG_FILE"
fi
