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
