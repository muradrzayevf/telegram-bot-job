"""Job sources.

Each module exposes NAME and fetch() -> list[dict] with the keys:
  id                 unique within the source
  title, company, location, url, source
  published          ISO date (YYYY-MM-DD) or "" when the site does not say
  extra              the site's own tags / keywords, never the free-text description
                     (descriptions mention "security" and "students" far too often)
  assume_it          True when the site itself filed the vacancy under IT
  assume_internship  True when the site itself filed the vacancy as an internship (optional)
"""
import re

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")


def session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "et,en;q=0.9,ru;q=0.8"})
    return s


def clean(text):
    """Collapse whitespace runs; HTML text often carries newlines and indentation."""
    return re.sub(r"\s+", " ", text or "").strip()
