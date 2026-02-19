#!/bin/bash

# Load environment variables if .env exists
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# Sync scripts for Tamil2 learner progress to Home Assistant
# Path to the source file
SOURCE_FILE="./progress/learner.json"

# SSH Alias for Home Assistant
REMOTE_HOST="${HOMEASSISTANT_HOST:-homeassistant}"

# Remote directory (standard location for the 'www' folder in Home Assistant)
REMOTE_DIR="/config/www/"

# Transfer the file
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519_ha}"
scp -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$SOURCE_FILE" "$REMOTE_HOST":"$REMOTE_DIR"

if [ $? -eq 0 ]; then
    echo "$(date): Successfully synced learner.json to Home Assistant."
else
    echo "$(date): Error syncing learner.json to Home Assistant." >&2
    exit 1
fi
