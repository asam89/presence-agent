#!/bin/bash
# setup.sh — run once on OCI Ampere (Ubuntu 24.04 ARM64) to bootstrap the agent

set -e

echo "=== Presence Agent — OCI Setup ==="

# System deps
sudo apt-get update -qq
sudo apt-get install -y python3.12 python3.12-venv python3-pip git rsync

# Python env
python3.12 -m venv ~/presence-agent/venv
source ~/presence-agent/venv/bin/activate
pip install --quiet anthropic python-dotenv

# Clone alex-builds output repo (replace with your GitHub URL)
if [ ! -d ~/alex-builds ]; then
  git clone https://github.com/asam89/alex-builds.git ~/alex-builds
  echo "Cloned alex-builds"
fi

# Create careerbot-context dir (populated by sync.sh from Mac)
mkdir -p ~/careerbot-context

# Copy .env.example to .env and remind user to fill it in
if [ ! -f ~/presence-agent/.env ]; then
  cp ~/presence-agent/.env.example ~/presence-agent/.env
  echo ""
  echo "ACTION REQUIRED: fill in ~/presence-agent/.env with your API key and paths"
fi

# Install crontab entries
CRON_FILE=$(mktemp)
crontab -l 2>/dev/null > "$CRON_FILE" || true
cat >> "$CRON_FILE" << 'EOF'
# Presence agent — 3x daily (7am, 2pm, 11pm Toronto time = UTC-4 in summer)
0 11 * * * cd /home/ubuntu/presence-agent && /home/ubuntu/presence-agent/venv/bin/python agent.py >> /home/ubuntu/presence-agent/agent.log 2>&1
0 18 * * * cd /home/ubuntu/presence-agent && /home/ubuntu/presence-agent/venv/bin/python agent.py >> /home/ubuntu/presence-agent/agent.log 2>&1
0 3  * * * cd /home/ubuntu/presence-agent && /home/ubuntu/presence-agent/venv/bin/python agent.py >> /home/ubuntu/presence-agent/agent.log 2>&1
EOF
crontab "$CRON_FILE"
rm "$CRON_FILE"

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Fill in .env"
echo "  2. Run: python agent.py   (to test manually)"
echo "  3. Check agent.log after first cron fires"
