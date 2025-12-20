#!/bin/bash
# E-NOR Raspberry Pi Setup Script - run once to configure everything

set -e

echo "🤖 E-NOR Setup Script"
echo "===================="

REPO_URL="https://github.com/martingsewell/e-nor.git"
INSTALL_DIR="/home/ronniesewell/e-nor"
VENV_DIR="$INSTALL_DIR/venv"

echo ""
echo "📦 Installing system packages..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv git

echo ""
echo "📥 Setting up repository..."
if [ -d "$INSTALL_DIR" ]; then
    cd "$INSTALL_DIR"
    git pull origin main
else
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

echo ""
echo "🐍 Setting up Python environment..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "🔧 Setting permissions..."
chmod +x scripts/*.sh

mkdir -p "$INSTALL_DIR/logs"

echo ""
echo "📝 Setting up config files..."
# Copy template to settings.json if it doesn't exist
if [ ! -f "$INSTALL_DIR/config/settings.json" ]; then
    cp "$INSTALL_DIR/config/settings.template.json" "$INSTALL_DIR/config/settings.json"
    echo "   Created config/settings.json from template"
else
    echo "   config/settings.json already exists, preserving existing settings"
fi

echo ""
echo "⏰ Setting up auto-pull cron job..."
CRON_JOB="* * * * * $INSTALL_DIR/scripts/auto-pull.sh"
(crontab -l 2>/dev/null | grep -v "auto-pull.sh"; echo "$CRON_JOB") | crontab -

echo ""
echo "🚀 Creating systemd service..."
sudo tee /etc/systemd/system/e-nor.service > /dev/null << EOF
[Unit]
Description=E-NOR Robot Server
After=network.target

[Service]
Type=simple
User=ronniesewell
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$VENV_DIR/bin:/usr/bin:/bin
ExecStart=$VENV_DIR/bin/python -m uvicorn core.server.main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable e-nor
sudo systemctl start e-nor

PI_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "✅ Setup complete!"
echo ""
echo "═══════════════════════════════════════════"
echo "  E-NOR is now running!"
echo ""
echo "  📱 Open this URL on the Galaxy S22:"
echo "     http://$PI_IP:8080"
echo ""
echo "  📊 Check service status:"
echo "     sudo systemctl status e-nor"
echo ""
echo "  📜 View logs:"
echo "     journalctl -u e-nor -f"
echo ""
echo "  🔄 Auto-updates enabled (every minute)"
echo "═══════════════════════════════════════════"
