#!/usr/bin/env python3
"""
Presence Agent — reads CareerBot context, generates a daily log entry,
commits it to the alex-builds repo on GitHub.
"""

import os
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import anthropic
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
CAREERBOT_PATH = Path(os.environ["CAREERBOT_CONTEXT_PATH"])
ALEX_BUILDS_PATH = Path(os.environ["ALEX_BUILDS_REPO_PATH"])
TIMEZONE = ZoneInfo("America/Toronto")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# ── Context readers ──────────────────────────────────────────────────────────

def read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


def build_context() -> dict:
    brag = read_file(CAREERBOT_PATH / "brag-doc.md")
    tracker = read_file(CAREERBOT_PATH / "job-tracker.md")
    apps = read_file(CAREERBOT_PATH / "applications.md")
    resume_summary = read_file(CAREERBOT_PATH / "resume-versions" / "technical-pm.md")

    # Count applied jobs from tracker
    applied_count = tracker.count("| Applied") + tracker.count("| Applied ✓")

    return {
        "brag_doc": brag[:3000],
        "job_tracker": tracker[:2000],
        "applications": apps[:1500],
        "resume_snapshot": resume_summary[:1500],
        "applied_count": applied_count,
    }


# ── Claude call ──────────────────────────────────────────────────────────────

def generate_log_entry(ctx: dict, now: datetime) -> str:
    time_label = now.strftime("%I:%M %p")
    date_label = now.strftime("%A, %B %d %Y")

    prompt = f"""You are writing a short, honest daily build log entry for Alex Sam — a senior IT/PM professional actively job hunting and building his personal brand.

Today is {date_label} at {time_label} EST.

Alex's context:
- Active job applications: {ctx['applied_count']} roles in pipeline
- Recent brag doc (wins & metrics):
{ctx['brag_doc'][:1500]}

- Current job tracker:
{ctx['job_tracker'][:1000]}

Write a 3–5 sentence log entry for today. Rules:
- Reference specific real details from his context (company names, numbers, role types)
- Sound like a founder/builder journaling, not a press release
- Mention what he is actively working on or thinking about
- No hashtags, no emojis, no fluff
- End with one short forward-looking sentence (what's next)
- Plain text only, no markdown headers"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def generate_readme(recent_entries: list[tuple[str, str]]) -> str:
    entries_block = "\n\n".join(
        f"**{date}**\n{content}" for date, content in recent_entries[:5]
    )

    prompt = f"""Write a README.md for a GitHub repo called "alex-builds" that serves as Alex Sam's public build log.

Alex is a senior IT Project Manager & DevOps engineer (13 years, PMP, Azure SA) based in Toronto, building his career and personal brand in public.

Recent log entries:
{entries_block}

Write the README in this format:
- 2-line intro about what this repo is
- "What I'm building" section (3 bullets, derived from the log entries)
- "Recent log" section showing the last entry date and first sentence
- Footer: "Updated automatically by my presence agent."

Keep it under 200 words. Use minimal markdown."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


# ── Git helpers ──────────────────────────────────────────────────────────────

def git(cmd: list[str], cwd: Path) -> str:
    result = subprocess.run(
        ["git"] + cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(cmd)} failed:\n{result.stderr}")
    return result.stdout.strip()


def commit_and_push(repo: Path, message: str):
    git(["pull", "--rebase", "origin", "main"], repo)
    git(["add", "."], repo)
    try:
        git(["commit", "-m", message], repo)
        git(["push", "origin", "main"], repo)
    except RuntimeError as e:
        if "nothing to commit" in str(e):
            print("Nothing new to commit.")
        else:
            raise


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    now = datetime.now(tz=TIMEZONE)
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    print(f"[{now.isoformat()}] Presence agent starting...")

    # 1. Read CareerBot context
    ctx = build_context()
    print(f"  Context loaded — {ctx['applied_count']} active applications")

    # 2. Generate log entry
    entry = generate_log_entry(ctx, now)
    print(f"  Log entry generated ({len(entry)} chars)")

    # 3. Write to log file
    log_dir = ALEX_BUILDS_PATH / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{date_str}.md"

    if log_file.exists():
        existing = log_file.read_text(encoding="utf-8")
        log_file.write_text(
            existing + f"\n\n---\n*{time_str}*\n\n{entry}\n",
            encoding="utf-8",
        )
    else:
        log_file.write_text(
            f"# {now.strftime('%B %d, %Y')}\n\n*{time_str}*\n\n{entry}\n",
            encoding="utf-8",
        )

    # 4. Update stats.json
    stats_file = ALEX_BUILDS_PATH / "stats.json"
    stats = json.loads(stats_file.read_text()) if stats_file.exists() else {}
    stats["last_updated"] = now.isoformat()
    stats["applied_count"] = ctx["applied_count"]
    stats["total_log_days"] = len(list(log_dir.glob("*.md")))
    stats_file.write_text(json.dumps(stats, indent=2))

    # 5. Regenerate README from recent logs
    recent = []
    for f in sorted(log_dir.glob("*.md"), reverse=True)[:5]:
        recent.append((f.stem, f.read_text(encoding="utf-8")[:400]))
    readme = generate_readme(recent)
    (ALEX_BUILDS_PATH / "README.md").write_text(readme + "\n", encoding="utf-8")

    # 6. Commit and push
    commit_msg = f"build({date_str} {time_str}): daily log entry — {ctx['applied_count']} roles in pipeline"
    commit_and_push(ALEX_BUILDS_PATH, commit_msg)
    print(f"  Committed and pushed: {commit_msg}")
    print("Done.")


if __name__ == "__main__":
    main()
