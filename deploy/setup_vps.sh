#!/bin/bash
# ==============================================================================
# Delta Exchange Bot - 1-Click VPS Auto Setup & 24/7 Systemd Service
# Works on Ubuntu / Debian VPS
# ==============================================================================

set -e

echo "=========================================================="
echo " Starting Delta Exchange Bot 24/7 Setup..."
echo "=========================================================="

# 1. Update system and install Python 3 & pip
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git

# 2. Setup Virtual Environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 3. Create .env if not present
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env file. Please edit it with your API keys:"
    echo "nano .env"
fi

# 4. Create Systemd Service for 24/7 Auto-Restart
BOT_DIR=$(pwd)
USER_NAME=$(whoami)

sudo bash -c "cat > /etc/systemd/system/delta-bot.service <<EOF
[Unit]
Description=Delta Exchange 24/7 Trading Bot
After=network.target

[Service]
Type=simple
User=${USER_NAME}
WorkingDirectory=${BOT_DIR}
ExecStart=${BOT_DIR}/venv/bin/python -m bot.standalone_bot
Restart=always
RestartSec=10
EnvironmentFile=${BOT_DIR}/.env

[Install]
WantedBy=multi-user.target
EOF"

# 5. Enable and Start the Service
sudo systemctl daemon-reload
sudo systemctl enable delta-bot
sudo systemctl restart delta-bot

echo "=========================================================="
echo " SUCCESS: Delta Exchange Bot is running 24/7 in background!"
echo " Useful Commands:"
echo " - View live logs : sudo journalctl -u delta-bot -f"
echo " - Check status   : sudo systemctl status delta-bot"
echo " - Restart bot    : sudo systemctl restart delta-bot"
echo " - Stop bot       : sudo systemctl stop delta-bot"
echo "=========================================================="
