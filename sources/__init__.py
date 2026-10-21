"""Each source module exposes fetch() -> list[dict] with keys:
id (unique within the source), title, company, location, url, published, source, extra, assume_it
"""
import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")


def session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "et,en;q=0.9,ru;q=0.8"})
    return s
