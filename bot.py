"""Estonia IT / cybersecurity job watcher -> Telegram.

Usage:
  python bot.py                 run forever, check every CHECK_INTERVAL_MIN minutes
  python bot.py --once          one check, then exit (for Task Scheduler / cron)
  python bot.py --dry-run       fetch + filter, print to console, send nothing
  python bot.py --init          mark everything currently listed as seen, send nothing
  python bot.py --get-chat-id   print the chat id of whoever messages the bot in the next 60 s
  python bot.py --test          send a test message to TELEGRAM_CHAT_ID
"""
import argparse
import html
import json
import logging
import os
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import requests

from dedup import fingerprint
from filters import classify
from sources import cv_ee, cvkeskus, linkedin, tootukassa

HERE = Path(__file__).resolve().parent
STATE_FILE = HERE / "seen.json"
# Order matters: when the same vacancy appears on several sites, the earliest source wins
# (cv.ee carries the most reliable publish dates).
SOURCES = [cv_ee, cvkeskus, linkedin, tootukassa]
TG_MAX_LEN = 4096
TITLE_MAX_LEN = 300

log = logging.getLogger("jobbot")

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ---------- config ----------
def load_env(path=None):
    """Minimal .env loader; real environment variables win over the file."""
    path = path or HERE / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _int_env(name, default):
    raw = os.environ.get(name, "")
    try:
        return int(raw) if raw else default
    except ValueError:
        log.warning("%s=%r is not a number, using %d", name, raw, default)
        return default


load_env()
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper(),
                    format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
INTERVAL_MIN = _int_env("CHECK_INTERVAL_MIN", 30)
MAX_PER_RUN = _int_env("MAX_PER_RUN", 40)          # don't flood the chat on the first real run
KEEP_SEEN_DAYS = _int_env("KEEP_SEEN_DAYS", 90)
SOURCE_ALERT_AFTER = _int_env("SOURCE_ALERT_AFTER", 3)  # 0 disables the "site broken" alerts
ONLY_CYBER = os.environ.get("ONLY_CYBER", "0") == "1"
API = f"https://api.telegram.org/bot{TOKEN}"


# ---------- state ----------
def load_seen(path=None):
    path = path or STATE_FILE
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as ex:
            log.error("%s is corrupt (%s), starting with an empty list", path.name, ex)
    return {}


def save_seen(seen, path=None):
    """Write atomically so a crash mid-write can't leave a broken seen.json behind."""
    path = path or STATE_FILE
    cutoff = (datetime.now() - timedelta(days=KEEP_SEEN_DAYS)).isoformat()
    seen = {k: v for k, v in seen.items() if v >= cutoff}
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(seen, indent=0, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


# ---------- telegram ----------
SENT, REJECTED, FAILED = "sent", "rejected", "failed"


def tg(method, **data):
    """One Telegram API call. Returns the Response, or None on a network error."""
    try:
        return requests.post(f"{API}/{method}", json=data, timeout=30)
    except requests.RequestException as ex:
        log.warning("[telegram] %s network error: %s", method, ex)
        return None


def send(text):
    """Send one HTML message.

    Returns SENT, REJECTED (Telegram refused the message itself, don't retry it) or
    FAILED (network / rate limit / server trouble, safe to retry on the next run)."""
    if len(text) > TG_MAX_LEN:
        text = text[:TG_MAX_LEN - 1] + "…"
    for _ in range(2):
        r = tg("sendMessage", chat_id=CHAT_ID, text=text, parse_mode="HTML", disable_web_page_preview=True)
        if r is None:
            return FAILED
        if r.ok:
            return SENT
        if r.status_code == 429:
            try:
                wait = int(r.json().get("parameters", {}).get("retry_after", 5))
            except (ValueError, AttributeError):
                wait = 5
            log.warning("[telegram] rate limited, waiting %ds", wait + 1)
            time.sleep(wait + 1)
            continue
        if r.status_code == 400:
            log.error("[telegram] message rejected: %s", r.text[:200])
            return REJECTED
        log.warning("[telegram] sendMessage -> %s: %s", r.status_code, r.text[:200])
        return FAILED
    return FAILED


def format_job(j, cyber, internship):
    e = html.escape
    tag = "🔐 Cybersecurity" if cyber else "💻 IT"
    title = e(j["title"][:TITLE_MAX_LEN])
    # no nested <b> inside the all-bold internship message
    lines = [title if internship else f"<b>{title}</b>"]
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


# ---------- fetching ----------
@dataclass
class SourceResult:
    name: str
    jobs: list = field(default_factory=list)
    error: str = ""  # "" means the fetch looked healthy


def fetch_source(mod):
    t0 = time.monotonic()
    try:
        jobs = mod.fetch()
    except Exception as ex:
        log.error("[%s] FAILED: %s", mod.NAME, ex)
        return SourceResult(mod.NAME, [], f"{type(ex).__name__}: {ex}")
    log.info("[%s] %d listings fetched in %.1fs", mod.NAME, len(jobs), time.monotonic() - t0)
    if not jobs:
        # an HTML scraper that finds nothing almost always means the site changed its markup
        return SourceResult(mod.NAME, [], "returned 0 listings (site layout changed?)")
    return SourceResult(mod.NAME, jobs)


def collect():
    """Fetch every source concurrently; results come back in SOURCES order."""
    with ThreadPoolExecutor(max_workers=len(SOURCES)) as pool:
        return list(pool.map(fetch_source, SOURCES))


class SourceHealth:
    """Tells the chat once when a site keeps failing, and once when it recovers."""

    def __init__(self, alert_after=SOURCE_ALERT_AFTER):
        self.alert_after = alert_after
        self.failures = Counter()

    def update(self, results, notify):
        if not self.alert_after:
            return
        for r in results:
            if r.error:
                self.failures[r.name] += 1
                if self.failures[r.name] == self.alert_after:
                    notify(f"⚠️ {r.name} has failed {self.alert_after} checks in a row: {r.error}")
            else:
                if self.failures[r.name] >= self.alert_after:
                    notify(f"✅ {r.name} is working again.")
                self.failures[r.name] = 0


# ---------- main ----------
def run_once(dry_run=False, init=False):
    seen = load_seen()
    now = datetime.now().isoformat(timespec="seconds")
    results = collect()

    new, fingerprints_this_run = [], set()
    for res in results:
        for j in res.jobs:
            key = f"{j['source']}:{j['id']}"
            if key in seen:
                continue
            keep, cyber, internship = classify(j["title"], j.get("extra", ""),
                                               j.get("assume_it", False), j.get("assume_internship", False))
            if not keep or (ONLY_CYBER and not cyber):
                continue
            fp = fingerprint(j)
            if fp and (fp in seen or fp in fingerprints_this_run):
                seen[key] = now  # same vacancy already sent from another listing
                log.debug("duplicate skipped: %s (%s)", j["title"], key)
                continue
            if fp:
                fingerprints_this_run.add(fp)
            new.append((j, cyber, internship, key, fp))

    # internships first, then cyber, then the rest
    new.sort(key=lambda x: (not x[2], not x[1]))
    log.info("%d new matching vacancies", len(new))

    def mark(key, fp):
        seen[key] = now
        if fp:
            seen[fp] = now

    if init:
        for *_, key, fp in new:
            mark(key, fp)
        save_seen(seen)
        log.info("Marked as seen, nothing sent.")
        return results

    sent = 0
    for j, cyber, internship, key, fp in new[:MAX_PER_RUN]:
        msg = format_job(j, cyber, internship)
        if dry_run:
            print("-" * 60)
            print(msg)
            continue
        status = send(msg)
        if status == FAILED:
            log.warning("%s not marked as seen, will retry next run", key)
        else:
            mark(key, fp)
            sent += status == SENT
        time.sleep(1.2)  # Telegram: ~1 msg/s per chat

    left = len(new) - MAX_PER_RUN
    if left > 0 and not dry_run:
        send(f"ℹ️ {left} more new vacancies are waiting and will follow on the next run "
             f"(limit {MAX_PER_RUN} per run).")
    if not dry_run:
        save_seen(seen)
        log.info("sent %d", sent)
    return results


def get_chat_id():
    print("Send any message to your bot in Telegram now (waiting 60 s)...")
    offset, deadline = None, time.time() + 60
    while time.time() < deadline:
        try:
            r = requests.get(f"{API}/getUpdates", params={"timeout": 10, "offset": offset}, timeout=20).json()
        except (requests.RequestException, ValueError) as ex:
            log.warning("getUpdates failed: %s", ex)
            time.sleep(2)
            continue
        if not r.get("ok", True):
            print(f"Telegram error: {r.get('description')}")
            return
        for u in r.get("result", []):
            offset = u["update_id"] + 1
            m = u.get("message") or u.get("channel_post")
            if m:
                c = m["chat"]
                print(f"chat id: {c['id']}  ({c.get('type')} {c.get('title') or c.get('username') or c.get('first_name')})")
                return
    print("No message received.")


def loop():
    log.info("Running every %d min. Ctrl+C to stop.", INTERVAL_MIN)
    health = SourceHealth()
    try:
        while True:
            try:
                health.update(run_once(), send)
            except Exception:
                log.exception("run failed")
            time.sleep(INTERVAL_MIN * 60)
    except KeyboardInterrupt:
        log.info("Stopped.")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Estonia IT / cybersecurity job watcher -> Telegram")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="one check, then exit (Task Scheduler / cron)")
    mode.add_argument("--dry-run", action="store_true", help="fetch + filter, print to console, send nothing")
    mode.add_argument("--init", action="store_true", help="mark everything currently listed as seen, send nothing")
    mode.add_argument("--get-chat-id", action="store_true", help="print the chat id of whoever messages the bot")
    mode.add_argument("--test", action="store_true", help="send a test message to TELEGRAM_CHAT_ID")
    args = ap.parse_args(argv)

    if not TOKEN and not args.dry_run:
        log.error("Set TELEGRAM_BOT_TOKEN in .env (see .env.example)")
        sys.exit(1)
    if args.get_chat_id:
        return get_chat_id()
    if not CHAT_ID and not args.dry_run:
        log.error("Set TELEGRAM_CHAT_ID in .env (run: python bot.py --get-chat-id)")
        sys.exit(1)
    if args.test:
        status = send("✅ Estonia IT/cyber job bot is connected.")
        print("test message sent" if status == SENT else f"failed ({status})")
        return
    if args.init:
        return run_once(init=True)
    if args.dry_run:
        return run_once(dry_run=True)
    if args.once:
        return run_once()
    loop()


if __name__ == "__main__":
    main()
