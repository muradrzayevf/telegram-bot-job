# Estonia IT / Cybersecurity job watcher → Telegram

Checks Estonian job sites for new IT and cybersecurity vacancies and sends each new one
to you on Telegram with a link. **Internships are sent fully in bold.** A vacancy posted on
several sites (or several times on cv.ee) is sent once.

Sources:

| Site | How |
|---|---|
| cv.ee | official JSON search API (IT category + cyber keywords + internship category) |
| CVKeskus.ee | HTML search results |
| LinkedIn | public guest job search, location = Estonia, last 48 h |
| Töötukassa (tootukassa.ee) | public GraphQL endpoint, last 3 days, filtered locally |

## Setup

1. In Telegram open **@BotFather** → `/newbot` → copy the token.
2. Install deps:
   ```
   python -m pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env`, paste the token.
4. Find your chat id: run `python bot.py --get-chat-id`, then send any message to your bot. Put the id in `.env`.
5. `python bot.py --test` → you should get a message.
6. First run without flooding yourself: `python bot.py --init` marks all current listings as seen.
   (Skip this if you want the current listings sent too; they arrive `MAX_PER_RUN` (40) per check
   until the backlog is gone.)
7. Start the bot: `python bot.py` (or double-click `run_bot.bat`). It checks every
   `CHECK_INTERVAL_MIN` minutes (default 30). `python bot.py --help` lists all modes.

### Run automatically on Windows
Task Scheduler → Create Task → trigger "At log on" or every 30 min → action:
`python C:\...\tg_bot\bot.py --once`. Or just keep `run_bot.bat` running.

### Run on a Linux VPS (systemd)
The bot needs no open ports and runs happily on the smallest VPS plan.

```
sudo apt install -y git python3 python3-venv
git clone https://github.com/muradrzayevf/telegram-bot-job.git /opt/jobbot
cd /opt/jobbot
cp .env.example .env && nano .env        # token + chat id
sudo bash deploy/install.sh
```

`deploy/install.sh` creates a virtualenv, a `jobbot` system user, sends a test message, offers
to mark today's listings as seen (so the first run doesn't flood you; `INIT=1` or `INIT=0`
answers that without asking) and installs
`deploy/jobbot.service` as a hardened systemd unit that starts on boot and restarts on
failure. Re-run it any time to refresh dependencies. Afterwards:

```
journalctl -u jobbot -f                  # live log
sudo systemctl restart jobbot            # after `git pull` or editing .env
sudo systemctl disable --now jobbot      # stop for good
```

To get your chat id on the server: `sudo -u jobbot .venv/bin/python bot.py --get-chat-id`.

Note: LinkedIn's guest search often rate-limits data-centre IPs. If it keeps returning
0 listings you will get a ⚠️ message; remove `linkedin` from `SOURCES` in `bot.py` if so.

## Message format

```
🔐 Cybersecurity            (or 💻 IT)

Security Analyst
🏢 Company
📍 Tallinn
🗓 2026-10-21
🌐 cv.ee
🔗 https://...
```
Internships: `🎓 INTERNSHIP / PRAKTIKA` header and the **whole message in bold**.

## Tuning
- `filters.py` – keyword lists. `IT`, `CYBER`, `INTERNSHIP` select; `EXCLUDE` drops guard jobs
  and non-IT engineering (HVAC, mechanical…); `NON_IT` drops sales / finance / HR / teaching
  roles that sites file under IT ("B2B IT teenuste müügijuht", "Tax Technology Manager").
  Remove an entry from `NON_IT` if you do want those.
- `ONLY_CYBER=1` in `.env` – only cybersecurity jobs.
- `MAX_PER_RUN`, `KEEP_SEEN_DAYS`, `SOURCE_ALERT_AFTER`, `LOG_LEVEL` – see `.env.example`.
- `sources/*.py` – `KEYWORDS` searched on each site. To add a site, write `fetch()` returning
  the same dict shape (see `sources/__init__.py`) and add the module to `SOURCES` in `bot.py`.
- `dedup.py` – how two listings are recognised as the same vacancy (normalised company + title).
- `seen.json` – what has already been sent. Delete it to resend everything.

## How it behaves
- Sites are fetched in parallel; one failing site never blocks the others.
- A vacancy is only marked as seen after Telegram accepted it. Network trouble or rate limits
  mean a retry on the next check, nothing is lost.
- When a site fails `SOURCE_ALERT_AFTER` checks in a row (or returns 0 listings, which usually
  means its HTML changed), you get one ⚠️ message, and one ✅ when it works again.
- `seen.json` is written atomically and pruned to `KEEP_SEEN_DAYS`.

## Tests
```
python -m unittest
```
No network needed; the suites cover the filters, duplicate detection, site parsers and the
send / remember logic.
