# presence-agent

Autonomous agent that runs on OCI Ampere (ARM64), reads CareerBot context, and commits daily build logs to [alex-builds](https://github.com/asam89/alex-builds) on GitHub.

## What it does

- Reads live CareerBot data (brag doc, job tracker, applications)
- Calls Claude API to generate a meaningful daily log entry
- Commits and pushes to `alex-builds` repo 3x/day via cron
- Keeps GitHub green with real career activity — not noise

## Architecture

```
Mac (cron via sync.sh)
  └─ rsync CareerBot → OCI Ampere

OCI Ampere (cron 3x/day)
  └─ agent.py
       ├─ reads careerbot-context/
       ├─ calls Claude API
       └─ git commit + push → alex-builds
```

## Setup

```bash
# On OCI Ampere
git clone https://github.com/asam89/presence-agent.git ~/presence-agent
cd ~/presence-agent
cp .env.example .env   # fill in your API key
bash setup.sh
```

## Mac sync (add to crontab)

```
0 6,13,22 * * * /Users/alexsam/Documents/presence-agent/sync.sh
```

## Files

| File | Purpose |
|---|---|
| `agent.py` | Main agent — reads context, generates log, commits |
| `sync.sh` | Runs on Mac, rsyncs CareerBot to OCI |
| `setup.sh` | One-time OCI bootstrap script |
| `.env.example` | Environment variable template |
