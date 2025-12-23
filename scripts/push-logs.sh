#!/bin/bash
# Push E-NOR logs to the 'logs' branch for remote debugging
# This branch is excluded from auto-merge to main

set -e

ENOR_DIR="/home/ronniesewell/e-nor"
LOGS_DIR="$ENOR_DIR/logs"
TEMP_DIR="/tmp/enor-logs-push"
BRANCH="logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== E-NOR Log Push ===${NC}"

# Check if we're in the e-nor directory
cd "$ENOR_DIR"

# Create temp directory for log operations
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

# Collect logs
echo -e "${YELLOW}Collecting logs...${NC}"

# Get current timestamp
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="$TEMP_DIR/enor_$TIMESTAMP.log"

# Collect systemd service logs (last 1000 lines)
echo "=== E-NOR Service Logs (last 1000 lines) ===" > "$LOG_FILE"
echo "Collected at: $(date)" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
journalctl -u enor --no-pager -n 1000 >> "$LOG_FILE" 2>/dev/null || echo "No journalctl logs available" >> "$LOG_FILE"

# Collect any file-based logs
if [ -d "$LOGS_DIR" ]; then
    echo "" >> "$LOG_FILE"
    echo "=== File-based logs ===" >> "$LOG_FILE"
    for f in "$LOGS_DIR"/*.log; do
        if [ -f "$f" ]; then
            echo "" >> "$LOG_FILE"
            echo "--- $(basename $f) (last 500 lines) ---" >> "$LOG_FILE"
            tail -n 500 "$f" >> "$LOG_FILE" 2>/dev/null || true
        fi
    done
fi

# Collect system info
echo "" >> "$LOG_FILE"
echo "=== System Info ===" >> "$LOG_FILE"
echo "Hostname: $(hostname)" >> "$LOG_FILE"
echo "Uptime: $(uptime)" >> "$LOG_FILE"
echo "Memory: $(free -h | head -2)" >> "$LOG_FILE"
echo "Disk: $(df -h / | tail -1)" >> "$LOG_FILE"

# Git operations - push to logs branch
echo -e "${YELLOW}Pushing to logs branch...${NC}"

# Fetch the logs branch (create if doesn't exist)
git fetch origin "$BRANCH" 2>/dev/null || true

# Check if branch exists remotely
if git ls-remote --heads origin "$BRANCH" | grep -q "$BRANCH"; then
    # Branch exists, check it out
    git checkout "$BRANCH" 2>/dev/null || git checkout -b "$BRANCH" "origin/$BRANCH"
    git pull origin "$BRANCH" --rebase 2>/dev/null || true
else
    # Create orphan branch (no history from main)
    git checkout --orphan "$BRANCH"
    git rm -rf . 2>/dev/null || true
    echo "# E-NOR Debug Logs" > README.md
    echo "" >> README.md
    echo "This branch contains debug logs pushed from the Pi." >> README.md
    echo "It is excluded from auto-merge to main." >> README.md
    echo "" >> README.md
    echo "## Reading logs" >> README.md
    echo "Logs are named with timestamps: \`enor_YYYY-MM-DD_HH-MM-SS.log\`" >> README.md
    git add README.md
    git commit -m "Initialize logs branch"
fi

# Create logs directory in branch
mkdir -p logs

# Copy the log file
cp "$LOG_FILE" "logs/"

# Keep only last 20 log files to avoid bloat
cd logs
ls -t *.log 2>/dev/null | tail -n +21 | xargs -r rm -f
cd ..

# Commit and push
git add logs/
git commit -m "Log snapshot: $TIMESTAMP" 2>/dev/null || {
    echo -e "${YELLOW}No new logs to commit${NC}"
    git checkout main
    exit 0
}

git push origin "$BRANCH"

# Return to main branch
git checkout main

# Cleanup
rm -rf "$TEMP_DIR"

echo -e "${GREEN}Logs pushed successfully!${NC}"
echo -e "View at: https://github.com/\$(git remote get-url origin | sed 's/.*github.com[:/]//' | sed 's/.git$//')/tree/logs/logs"
