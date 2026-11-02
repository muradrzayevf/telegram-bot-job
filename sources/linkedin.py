"""LinkedIn - public (guest) job search, no login. Rate limited, so few keywords and backoff."""
import logging
import time

from bs4 import BeautifulSoup

from . import clean, session

log = logging.getLogger(__name__)

NAME = "LinkedIn"
SEARCH = "https://www.linkedin.com/jobs/search"
GUEST_API = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
KEYWORDS = ["cyber security", "information security", "IT", "software engineer", "DevOps", "internship IT"]
TIME_WINDOW = "r172800"  # last 48 hours


def _text(card, selector):
    el = card.select_one(selector)
    return clean(el.get_text(" ", strip=True)) if el else ""


def _parse(html):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for card in soup.select("[data-entity-urn]"):
        urn = card.get("data-entity-urn", "")
        if "jobPosting" not in urn:
            continue
        jid = urn.rsplit(":", 1)[-1]
        when = card.select_one("time")
        out.append({
            "id": jid,
            "title": _text(card, ".base-search-card__title"),
            "company": _text(card, ".base-search-card__subtitle"),
            "location": _text(card, ".job-search-card__location"),
            "url": f"https://www.linkedin.com/jobs/view/{jid}/",
            "published": (when.get("datetime", "") if when else "")[:10],
            "source": NAME, "extra": "", "assume_it": False,
        })
    return out


def _get(s, url, params):
    for attempt in range(3):
        r = s.get(url, params=params, timeout=30)
        if r.status_code == 429:
            time.sleep(8 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.text
    raise RuntimeError("rate limited (429)")


def fetch():
    s = session()
    out, seen = [], set()
    for kw in KEYWORDS:
        params = {"keywords": kw, "location": "Estonia", "f_TPR": TIME_WINDOW, "start": 0}
        try:
            try:
                html = _get(s, GUEST_API, params)
            except Exception:
                html = _get(s, SEARCH, params)
            for j in _parse(html):
                if j["id"] not in seen:
                    seen.add(j["id"])
                    out.append(j)
        except Exception as e:
            log.warning("[%s] keyword %r failed: %s", NAME, kw, e)
        time.sleep(2)
    return out
