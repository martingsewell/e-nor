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
    
    # Get commit message for version tracking
    COMMIT_MSG=$(git log --format="%s" -1 "$REMOTE")
    
    git pull origin main --quiet

    if git diff --name-only "$LOCAL" "$REMOTE" | grep -qE '^server/|^web/|requirements.txt'; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Code changed, creating version and restarting service..." >> "$LOG_FILE"
        
        # Create automatic version using Python API
        # Use virtual environment if it exists
        if [ -d "venv" ]; then
            source venv/bin/activate
        fi
        
        # Create version via internal API call
        python3 -c "
import sys
sys.path.append('$REPO_DIR')
try:
    from server.version_control import add_version
    add_version('$COMMIT_MSG', 'working')
    print('✅ Version created automatically')
except Exception as e:
    print(f'⚠️ Version creation failed: {e}')
" >> "$LOG_FILE" 2>&1
        
        sudo systemctl restart "$SERVICE_NAME" 2>/dev/null
    fi

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Update complete: $(git log -1 --oneline)" >> "$LOG_FILE"
fi
