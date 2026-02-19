#!/bin/bash

# Sync scripts for Tamil2 learner progress to Home Assistant
# Path to the source file
SOURCE_FILE="/home/roshana/projects/Tamil2/progress/learner.json"

# SSH Alias for Home Assistant
REMOTE_HOST="homeassistant"

# Remote directory (standard location for the 'www' folder in Home Assistant)
REMOTE_DIR="/config/www/"

# Transfer the file
scp -i ~/.ssh/id_ed25519_ha -o StrictHostKeyChecking=accept-new "$SOURCE_FILE" "$REMOTE_HOST":"$REMOTE_DIR"

if [ $? -eq 0 ]; then
    echo "$(date): Successfully synced learner.json to Home Assistant."
else
    echo "$(date): Error syncing learner.json to Home Assistant." >&2
    exit 1
fi
