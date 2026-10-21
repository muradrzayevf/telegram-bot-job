"""cvkeskus.ee - HTML search results."""
import re
from bs4 import BeautifulSoup
from . import session

NAME = "CVKeskus"
BASE = "https://www.cvkeskus.ee"
KEYWORDS = ["IT", "cyber", "security", "küber", "infoturbe", "arendaja", "developer", "engineer",
            "DevOps", "süsteemiadministraator", "praktika", "internship"]


def _parse(html):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for a in soup.select("a.jobad-url[href]"):
        href = a["href"]
        m = re.search(r"-(\d+)$", href)
        if not m:
            continue
        h2 = a.select_one("h2")
        title = h2.get_text(" ", strip=True) if h2 else ""
        comp = a.select_one(".job-company")
        company = comp.get_text(" ", strip=True) if comp else ""
        loc_el = comp.find_next_sibling("div") if comp else None   # "Tallinn / Hübriid"
        loc = loc_el.get_text(" ", strip=True) if loc_el else ""
        texts = [t.get_text(" ", strip=True) for t in a.select("span")]
        when = next((t for t in texts if len(t) < 30 and re.search(r"tagasi|täna|eile", t, re.I)), "")
        out.append({
            "id": m.group(1), "title": title, "company": company, "location": loc,
            "url": BASE + href, "published": when, "source": NAME, "extra": "", "assume_it": False,
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
            print(f"[{NAME}] keyword {kw!r} failed: {e}")
    return out
