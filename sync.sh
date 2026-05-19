#!/bin/bash
# sync.sh — runs on your Mac via cron, pushes CareerBot to OCI Ampere
# Add to Mac crontab: 0 6,13,22 * * * /Users/alexsam/Documents/presence-agent/sync.sh

set -e

OCI_USER="ubuntu"
OCI_HOST="${OCI_HOST:-YOUR_OCI_IP}"   # set OCI_HOST in your shell env or replace here
OCI_KEY="${OCI_SSH_KEY:-~/.ssh/oci_key}"

CAREERBOT_SRC="/Users/alexsam/Library/CloudStorage/GoogleDrive-asam@ignyteconsulting.com/My Drive/Career/CareerBot/"
CAREERBOT_DEST="$OCI_USER@$OCI_HOST:/home/ubuntu/careerbot-context/"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Syncing CareerBot to OCI..."

rsync -avz --delete \
  -e "ssh -i $OCI_KEY -o StrictHostKeyChecking=no" \
  "$CAREERBOT_SRC" \
  "$CAREERBOT_DEST"

echo "Sync complete."
