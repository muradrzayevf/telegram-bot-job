"""cv.ee - the JSON search API the site itself uses."""
from . import session

NAME = "cv.ee"
API = "https://www.cv.ee/api/v1/vacancy-search-service/search"
KEYWORDS = ["cyber", "security", "küber", "infoturbe", "SOC analyst", "penetration", "praktika IT", "internship"]


def _query(s, params):
    p = {"limit": 50, "offset": 0, "sorting": "LATEST", "isHourlySalary": "false",
         "isRemoteWork": "false", "isQuickApply": "false"}
    p.update(params)
    r = s.get(API, params=p, timeout=30)
    r.raise_for_status()
    return r.json().get("vacancies", [])


def _norm(v, assume_it, assume_internship=False):
    return {
        "assume_internship": assume_internship,
        "id": str(v["id"]),
        "title": v.get("positionTitle") or "",
        "company": v.get("employerName") or "",
        "location": "Eesti" + (" · remote/hybrid" if v.get("remoteWork") else ""),
        "url": f"https://www.cv.ee/et/vacancy/{v['id']}",
        "published": (v.get("publishDate") or "")[:10],
        "source": NAME,
        "extra": " ".join(v.get("keywords") or []),  # site tags only, not the description
        "assume_it": assume_it,
    }


def fetch():
    s = session()
    out, seen = [], set()
    # (params, assume_it, assume_internship)
    batches = [({"categories[]": "INTERNSHIP"}, False, True),
               ({"categories[]": "INFORMATION_TECHNOLOGY"}, True, False)]
    batches += [({"keywords[]": k}, False, False) for k in KEYWORDS]
    for params, assume_it, assume_internship in batches:
        try:
            for v in _query(s, params):
                if str(v.get("countryId")) != "1":  # 1 = Estonia
                    continue
                if v["id"] in seen:
                    continue
                seen.add(v["id"])
                out.append(_norm(v, assume_it, assume_internship))
        except Exception as e:  # one failing query must not kill the rest
            print(f"[{NAME}] query {params} failed: {e}")
    return out
