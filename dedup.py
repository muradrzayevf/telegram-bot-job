"""Cross-source duplicate detection.

Estonian employers post the same vacancy on cv.ee, CVKeskus and LinkedIn, and cv.ee often
lists one position several times (one entry per language or town). A fingerprint built
from the normalised company name and title catches those so each vacancy is sent once."""
import re
import unicodedata

# Tokens that differ between sites for the same employer: legal forms, "Estonia", towns.
_NOISE = {
    "as", "oü", "ou", "sa", "mtü", "mtu", "fie", "sihtasutus", "aktsiaselts", "osaühing", "osauhing",
    "grupp", "group", "estonia", "eesti", "baltic", "baltics", "ltd", "llc", "inc", "oy", "ab",
    "gmbh", "se", "plc", "klient", "tallinn", "tartu", "parnu", "narva",
}


def _tokens(text):
    text = unicodedata.normalize("NFKD", (text or "").lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", text)


def norm_company(name):
    return " ".join(t for t in _tokens(name) if t not in _NOISE)


def norm_title(title):
    return " ".join(_tokens(title))


def fingerprint(job):
    """A key shared by every copy of the same vacancy, or None when there is too little to go on."""
    company, title = norm_company(job.get("company", "")), norm_title(job.get("title", ""))
    if not company or not title:
        return None
    return f"dup:{company}|{title}"
