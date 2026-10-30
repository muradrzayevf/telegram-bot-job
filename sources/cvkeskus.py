"""cvkeskus.ee - HTML search results."""
import logging
import re
from datetime import date, timedelta

from bs4 import BeautifulSoup

from . import clean, session

log = logging.getLogger(__name__)

NAME = "CVKeskus"
BASE = "https://www.cvkeskus.ee"
KEYWORDS = ["IT", "cyber", "security", "küber", "infoturbe", "arendaja", "developer", "engineer",
            "DevOps", "süsteemiadministraator", "praktika", "internship"]

_RELATIVE = re.compile(r"tagasi|täna|eile", re.IGNORECASE)


def relative_to_date(text, today=None):
    """Turn CVKeskus' relative age ("2 p. tagasi", "nädal tagasi", "täna") into an ISO date.

    Anything it does not understand is returned unchanged."""
    today = today or date.today()
    t = clean(text).lower()
    if not t:
        return ""
    if "täna" in t or "tund" in t or "min" in t:
        return today.isoformat()
    if "eile" in t:
        return (today - timedelta(days=1)).isoformat()
    m = re.search(r"(\d+)?\s*(p\.|päev|näd|kuu)", t)
    if not m:
        return text
    n = int(m.group(1)) if m.group(1) else 1
    unit = m.group(2)
    days = n * (1 if unit.startswith("p") else 7 if unit.startswith("n") else 30)
    return (today - timedelta(days=days)).isoformat()


def _parse(html):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for a in soup.select("a.jobad-url[href]"):
        href = a["href"]
        m = re.search(r"-(\d+)$", href)
        if not m:
            continue
        h2 = a.select_one("h2")
        title = clean(h2.get_text(" ", strip=True)) if h2 else ""
        comp = a.select_one(".job-company")
        company = clean(comp.get_text(" ", strip=True)) if comp else ""
        loc_el = comp.find_next_sibling("div") if comp else None   # "Tallinn / Hübriid"
        loc = clean(loc_el.get_text(" ", strip=True)) if loc_el else ""
        texts = [clean(t.get_text(" ", strip=True)) for t in a.select("span")]
        when = next((t for t in texts if len(t) < 30 and _RELATIVE.search(t)), "")
        out.append({
            "id": m.group(1), "title": title, "company": company, "location": loc,
            "url": BASE + href, "published": relative_to_date(when), "source": NAME,
            "extra": "", "assume_it": False,
        })
    return out


def fetch():
    s = session()
    out, seen = [], set()
    for kw in KEYWORDS:
        try:
            r = s.get(f"{BASE}/toopakkumised", timeout=30, params={
                "op": "search", "search[keyword]": kw, "search[job_salary]": 3,
                "search[expires_days]": "", "search[job_lang]": ""})
            r.raise_for_status()
            for j in _parse(r.text):
                if j["id"] not in seen:
                    seen.add(j["id"])
                    out.append(j)
        except Exception as e:
            log.warning("[%s] keyword %r failed: %s", NAME, kw, e)
    return out
