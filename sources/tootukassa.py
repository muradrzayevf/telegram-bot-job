"""Töötukassa (tootukassa.ee) - the public GraphQL endpoint the site uses.

Fetches everything published in the last DAYS days and filters locally, because its own
keyword search is Estonian-only and fuzzy."""
import logging

from . import session

log = logging.getLogger(__name__)

NAME = "Töötukassa"
GQL = "https://www.tootukassa.ee/web/graphql"
DAYS = 3
PAGE_SIZE = 50
MAX_PAGES = 20
QUERY = """query jobOfferSearch($first:Int,$cursor:Cursor,$searchInput:InputToopakkumineAvalikOtsingDTO){
  jobOffersQuery(first:$first,after:$cursor,searchInput:$searchInput){
    edges{ id nimetus alias ametinimetusTapsustus aadressid kandideerimineKp asutusNimi brandNimi onKodusTootamine kinnitamineKp }
    pageInfo{ endCursor hasNextPage totalCount } } }"""


def short_location(addresses, remote=False):
    """Full postal addresses -> the town / parish part, deduplicated.

    "Harju maakond, Tallinn, Kesklinna linnaosa, Tõnismägi 11a, 10119" -> "Tallinn"."""
    places = []
    for addr in addresses or []:
        parts = [p.strip() for p in addr.split(",") if p.strip()]
        if not parts:
            continue
        place = parts[1] if len(parts) > 1 else parts[0]
        if place not in places:
            places.append(place)
    loc = " / ".join(places)
    if remote:
        loc = f"{loc} · kodus töötamine" if loc else "kodus töötamine"
    return loc


def _norm(edge):
    return {
        "id": str(edge["id"]),
        "title": edge.get("nimetus") or "",
        "company": edge.get("brandNimi") or edge.get("asutusNimi") or "",
        "location": short_location(edge.get("aadressid"), edge.get("onKodusTootamine")),
        "url": f"https://www.tootukassa.ee/et/toopakkumised/{edge.get('alias') or edge['id']}",
        "published": (edge.get("kinnitamineKp") or "")[:10],
        "source": NAME,
        # ametinimetusTapsustus is a free-text tagline ("Tule meie kogukonna arendajaks!"),
        # not a tag list, so it is deliberately not used for matching.
        "extra": "",
        "assume_it": False,
    }


def fetch():
    s = session()
    s.headers["Content-Type"] = "application/json"
    out, cursor = [], None
    for _ in range(MAX_PAGES):
        try:
            r = s.post(GQL, timeout=30, json={"query": QUERY, "variables": {
                "first": PAGE_SIZE, "cursor": cursor,
                "searchInput": {"eestiToopakkumine": 1, "kinnitamiseVanusPaeviMaks": DAYS,
                                "kaugtoo": 0, "palkAvalik": 0}}})
            r.raise_for_status()
            data = r.json()["data"]["jobOffersQuery"]
        except Exception as e:
            log.warning("[%s] page failed: %s", NAME, e)
            break
        out.extend(_norm(edge) for edge in data["edges"])
        if not data["pageInfo"]["hasNextPage"]:
            break
        cursor = data["pageInfo"]["endCursor"]
    return out
