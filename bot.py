"""Estonia IT / cybersecurity job watcher -> Telegram.

Usage:
  python bot.py                 run forever, check every CHECK_INTERVAL_MIN minutes
  python bot.py --once          one check, then exit (for Task Scheduler / cron)
  python bot.py --dry-run       fetch + filter, print to console, send nothing
  python bot.py --init          mark everything currently listed as seen, send nothing
  python bot.py --get-chat-id   print the chat id of whoever messages the bot in the next 60 s
  python bot.py --test          send a test message to TELEGRAM_CHAT_ID
"""
import html
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

from filters import classify
from sources import cv_ee, cvkeskus, linkedin, tootukassa

HERE = Path(__file__).resolve().parent
STATE_FILE = HERE / "seen.json"
SOURCES = [cv_ee, cvkeskus, linkedin, tootukassa]
MAX_PER_RUN = 40          # don't flood the chat on the first real run
KEEP_SEEN_DAYS = 90

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ---------- config ----------
def load_env():
    env = HERE / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env()
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
INTERVAL_MIN = int(os.environ.get("CHECK_INTERVAL_MIN", "30"))
ONLY_CYBER = os.environ.get("ONLY_CYBER", "0") == "1"
API = f"https://api.telegram.org/bot{TOKEN}"


# ---------- state ----------
def load_seen():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def save_seen(seen):
    cutoff = (datetime.now() - timedelta(days=KEEP_SEEN_DAYS)).isoformat()
    seen = {k: v for k, v in seen.items() if v >= cutoff}
    STATE_FILE.write_text(json.dumps(seen, indent=0, ensure_ascii=False), encoding="utf-8")


# ---------- telegram ----------
def tg(method, **data):
    r = requests.post(f"{API}/{method}", json=data, timeout=30)
    if not r.ok:
        print(f"[telegram] {method} -> {r.status_code}: {r.text[:200]}")
    return r


def send(text):
    r = tg("sendMessage", chat_id=CHAT_ID, text=text, parse_mode="HTML", disable_web_page_preview=True)
    if r.status_code == 429:
        time.sleep(int(r.json().get("parameters", {}).get("retry_after", 5)) + 1)
        r = tg("sendMessage", chat_id=CHAT_ID, text=text, parse_mode="HTML", disable_web_page_preview=True)
    return r.ok


def format_job(j, cyber, internship):
    e = html.escape
    tag = "🔐 Cybersecurity" if cyber else "💻 IT"
    # no nested <b> inside the all-bold internship message
    lines = [e(j["title"]) if internship else f"<b>{e(j['title'])}</b>"]
    if j.get("company"):
        lines.append(f"🏢 {e(j['company'])}")
    if j.get("location"):
        lines.append(f"📍 {e(j['location'])}")
    if j.get("published"):
        lines.append(f"🗓 {e(str(j['published']))}")
    lines.append(f"🌐 {e(j['source'])}")
    lines.append(f"🔗 {e(j['url'])}")
    body = "\n".join(lines)
    if internship:
        # the whole message in bold, as requested for internships
        return f"<b>🎓 INTERNSHIP / PRAKTIKA  ·  {e(tag)}\n\n{body}</b>"
    return f"{tag}\n\n{body}"


# ---------- main ----------
def collect():
    jobs = []
    for mod in SOURCES:
        try:
            got = mod.fetch()
            print(f"[{mod.NAME}] {len(got)} listings fetched")
            jobs.extend(got)
        except Exception as ex:
            print(f"[{mod.NAME}] FAILED: {ex}")
    return jobs


def run_once(dry_run=False, init=False):
    seen = load_seen()
    now = datetime.now().isoformat()
    new, sent = [], 0
    for j in collect():
        key = f"{j['source']}:{j['id']}"
        keep, cyber, internship = classify(j["title"], j.get("extra", ""),
                                           j.get("assume_it", False), j.get("assume_internship", False))
        if not keep or (ONLY_CYBER and not cyber):
            continue
        if key in seen:
            continue
        seen[key] = now
        new.append((j, cyber, internship))

    # internships first, then cyber, then the rest
    new.sort(key=lambda x: (not x[2], not x[1]))
    print(f"{len(new)} new matching vacancies")

    if init:
        save_seen(seen)
        print("Marked as seen, nothing sent.")
        return

    for j, cyber, internship in new[:MAX_PER_RUN]:
        msg = format_job(j, cyber, internship)
        if dry_run:
            print("-" * 60)
            print(msg)
        else:
            if send(msg):
                sent += 1
            time.sleep(1.2)  # Telegram: ~1 msg/s per chat
    if len(new) > MAX_PER_RUN and not dry_run:
        send(f"ℹ️ +{len(new) - MAX_PER_RUN} more new vacancies were found but not sent (limit {MAX_PER_RUN} per run).")
    if not dry_run:
        save_seen(seen)
        print(f"sent {sent}")


def get_chat_id():
    print("Send any message to your bot in Telegram now (waiting 60 s)...")
    offset, deadline = None, time.time() + 60
    while time.time() < deadline:
        r = requests.get(f"{API}/getUpdates", params={"timeout": 10, "offset": offset}, timeout=20).json()
        for u in r.get("result", []):
            offset = u["update_id"] + 1
            m = u.get("message") or u.get("channel_post")
            if m:
                c = m["chat"]
                print(f"chat id: {c['id']}  ({c.get('type')} {c.get('title') or c.get('username') or c.get('first_name')})")
                return
    print("No message received.")


def main():
    args = sys.argv[1:]
    if "--get-chat-id" in args:
        return get_chat_id()
    if not TOKEN or (not CHAT_ID and "--dry-run" not in args):
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env (see .env.example)")
        if "--dry-run" not in args:
            sys.exit(1)
    if "--test" in args:
        ok = send("✅ Estonia IT/cyber job bot is connected.")
        return print("test message sent" if ok else "failed")
    if "--init" in args:
        return run_once(init=True)
    if "--dry-run" in args:
        return run_once(dry_run=True)
    if "--once" in args:
        return run_once()
    print(f"Running every {INTERVAL_MIN} min. Ctrl+C to stop.")
    while True:
        try:
            run_once()
        except Exception as ex:
            print(f"run failed: {ex}")
        time.sleep(INTERVAL_MIN * 60)


if __name__ == "__main__":
    main()
