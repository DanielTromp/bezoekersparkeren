#!/bin/bash
# Incus/LXC Setup Script for Bezoekersparkeren
# Run this script to prepare your Debian system for container deployment

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Bezoekersparkeren Incus Setup ===${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Please do not run this script as root. Run as your normal user.${NC}"
    exit 1
fi

# Check if Debian-based
if ! command -v apt &> /dev/null; then
    echo -e "${RED}This script requires a Debian-based system with apt.${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1: Installing Incus...${NC}"
sudo apt update
sudo apt install -y incus incus-client

echo ""
echo -e "${YELLOW}Step 2: Adding user to incus-admin group...${NC}"
sudo usermod -aG incus-admin "$USER"

echo ""
echo -e "${YELLOW}Step 3: Initializing Incus...${NC}"
echo "Please answer the following questions to configure Incus."
echo "Recommended: Accept defaults for a simple setup."
echo ""

# Check if Incus is already initialized
if sudo incus admin init --dump &> /dev/null; then
    echo -e "${GREEN}Incus appears to be already initialized.${NC}"
    read -p "Do you want to reinitialize? (y/N): " reinit
    if [[ "$reinit" =~ ^[Yy]$ ]]; then
        sudo incus admin init
    fi
else
    sudo incus admin init
fi

echo ""
echo -e "${YELLOW}Step 4: Creating data directory...${NC}"
sudo mkdir -p /opt/bezoekersparkeren
sudo chown "$USER:$USER" /opt/bezoekersparkeren

# Copy config files if they exist in the current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"

if [ -f "$APP_DIR/config.yaml" ]; then
    cp "$APP_DIR/config.yaml" /opt/bezoekersparkeren/
    echo -e "${GREEN}Copied config.yaml to /opt/bezoekersparkeren/${NC}"
elif [ -f "$APP_DIR/config.example.yaml" ]; then
    cp "$APP_DIR/config.example.yaml" /opt/bezoekersparkeren/config.yaml
    echo -e "${YELLOW}Copied config.example.yaml - please edit /opt/bezoekersparkeren/config.yaml${NC}"
fi

if [ -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env" /opt/bezoekersparkeren/
    echo -e "${GREEN}Copied .env to /opt/bezoekersparkeren/${NC}"
elif [ -f "$APP_DIR/.env.example" ]; then
    cp "$APP_DIR/.env.example" /opt/bezoekersparkeren/.env
    echo -e "${YELLOW}Copied .env.example - please edit /opt/bezoekersparkeren/.env${NC}"
fi

touch /opt/bezoekersparkeren/sessions.json

echo ""
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo ""
echo "Next steps:"
echo "1. Log out and log back in (or run: newgrp incus-admin)"
echo "2. Edit configuration files in /opt/bezoekersparkeren/"
echo "3. Run the deployment script: ./scripts/deploy-incus.sh"
echo ""
echo -e "${YELLOW}To verify Incus is working:${NC}"
echo "  incus list"
echo ""
