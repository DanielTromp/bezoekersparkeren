#!/bin/bash
# Incus Deployment Script for Bezoekersparkeren
# Deploys the app as a system container with the Telegram bot service

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

CONTAINER_NAME="parkeerbot"
DATA_DIR="/opt/bezoekersparkeren"
REPO_URL="https://github.com/danieltromp/bezoekersparkeren.git"

echo -e "${GREEN}=== Bezoekersparkeren Incus Deployment ===${NC}"
echo ""

# Check if incus is available
if ! command -v incus &> /dev/null; then
    echo -e "${RED}Incus is not installed. Run setup-incus.sh first.${NC}"
    exit 1
fi

# Check if user can run incus commands
if ! incus list &> /dev/null; then
    echo -e "${RED}Cannot access Incus. You may need to:${NC}"
    echo "  1. Log out and log back in"
    echo "  2. Or run: newgrp incus-admin"
    exit 1
fi

# Check for existing container
if incus info "$CONTAINER_NAME" &> /dev/null; then
    echo -e "${YELLOW}Container '$CONTAINER_NAME' already exists.${NC}"
    read -p "Do you want to delete and recreate it? (y/N): " recreate
    if [[ "$recreate" =~ ^[Yy]$ ]]; then
        echo "Stopping and deleting existing container..."
        incus delete "$CONTAINER_NAME" --force
    else
        echo "Aborting deployment."
        exit 0
    fi
fi

# Check for config files
if [ ! -f "$DATA_DIR/config.yaml" ]; then
    echo -e "${RED}Configuration file not found: $DATA_DIR/config.yaml${NC}"
    echo "Please create the config file first."
    exit 1
fi

if [ ! -f "$DATA_DIR/.env" ]; then
    echo -e "${RED}Environment file not found: $DATA_DIR/.env${NC}"
    echo "Please create the .env file first."
    exit 1
fi

echo -e "${YELLOW}Step 1: Creating Debian container...${NC}"
incus launch images:debian/13 "$CONTAINER_NAME"

echo "Waiting for container to be ready..."
sleep 10

echo ""
echo -e "${YELLOW}Step 2: Installing dependencies in container...${NC}"
incus exec "$CONTAINER_NAME" -- bash -c "
    apt-get update
    apt-get install -y python3 python3-pip python3-venv git curl
"

echo ""
echo -e "${YELLOW}Step 3: Cloning and installing application...${NC}"
incus exec "$CONTAINER_NAME" -- bash -c "
    cd /opt
    git clone $REPO_URL
    cd bezoekersparkeren
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install .
"

echo ""
echo -e "${YELLOW}Step 4: Installing Playwright and Chromium...${NC}"
incus exec "$CONTAINER_NAME" -- bash -c "
    cd /opt/bezoekersparkeren
    source venv/bin/activate
    playwright install --with-deps chromium
"

echo ""
echo -e "${YELLOW}Step 5: Copying configuration files...${NC}"
incus file push "$DATA_DIR/config.yaml" "$CONTAINER_NAME/opt/bezoekersparkeren/config.yaml"
incus file push "$DATA_DIR/.env" "$CONTAINER_NAME/opt/bezoekersparkeren/.env"

if [ -f "$DATA_DIR/sessions.json" ] && [ -s "$DATA_DIR/sessions.json" ]; then
    incus file push "$DATA_DIR/sessions.json" "$CONTAINER_NAME/opt/bezoekersparkeren/sessions.json"
fi

echo ""
echo -e "${YELLOW}Step 6: Creating systemd service...${NC}"
incus exec "$CONTAINER_NAME" -- bash -c 'cat > /etc/systemd/system/parkeerbot.service << EOF
[Unit]
Description=Bezoekersparkeren Telegram Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/bezoekersparkeren
Environment="PATH=/opt/bezoekersparkeren/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/opt/bezoekersparkeren/.env
ExecStart=/opt/bezoekersparkeren/venv/bin/bezoekersparkeren bot
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF'

echo ""
echo -e "${YELLOW}Step 7: Enabling and starting service...${NC}"
incus exec "$CONTAINER_NAME" -- systemctl daemon-reload
incus exec "$CONTAINER_NAME" -- systemctl enable parkeerbot
incus exec "$CONTAINER_NAME" -- systemctl start parkeerbot

echo ""
echo -e "${YELLOW}Step 8: Configuring auto-start on boot...${NC}"
incus config set "$CONTAINER_NAME" boot.autostart true

echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo -e "${BLUE}Container Status:${NC}"
incus list "$CONTAINER_NAME"
echo ""
echo -e "${BLUE}Service Status:${NC}"
incus exec "$CONTAINER_NAME" -- systemctl status parkeerbot --no-pager || true
echo ""
echo -e "${GREEN}Useful Commands:${NC}"
echo "  View logs:        incus exec $CONTAINER_NAME -- journalctl -u parkeerbot -f"
echo "  Restart service:  incus exec $CONTAINER_NAME -- systemctl restart parkeerbot"
echo "  Stop container:   incus stop $CONTAINER_NAME"
echo "  Start container:  incus start $CONTAINER_NAME"
echo "  List sessions:    incus exec $CONTAINER_NAME -- /opt/bezoekersparkeren/venv/bin/bezoekersparkeren list"
echo "  Check balance:    incus exec $CONTAINER_NAME -- /opt/bezoekersparkeren/venv/bin/bezoekersparkeren balance"
echo ""
