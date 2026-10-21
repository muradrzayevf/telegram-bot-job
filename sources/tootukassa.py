"""Töötukassa (tootukassa.ee) - the public GraphQL endpoint the site uses.

Fetches everything published in the last DAYS days and filters locally, because its own
keyword search is Estonian-only and fuzzy."""
from . import session

NAME = "Töötukassa"
GQL = "https://www.tootukassa.ee/web/graphql"
DAYS = 3
QUERY = """query jobOfferSearch($first:Int,$cursor:Cursor,$searchInput:InputToopakkumineAvalikOtsingDTO){
  jobOffersQuery(first:$first,after:$cursor,searchInput:$searchInput){
    edges{ id nimetus alias ametinimetusTapsustus aadressid kandideerimineKp asutusNimi brandNimi onKodusTootamine kinnitamineKp }
    pageInfo{ endCursor hasNextPage totalCount } } }"""


def fetch():
    s = session()
    s.headers["Content-Type"] = "application/json"
    out, cursor = [], None
    for _ in range(20):  # at most 20 pages x 50
        try:
            r = s.post(GQL, timeout=30, json={"query": QUERY, "variables": {
                "first": 50, "cursor": cursor,
                "searchInput": {"eestiToopakkumine": 1, "kinnitamiseVanusPaeviMaks": DAYS,
                                "kaugtoo": 0, "palkAvalik": 0}}})
            r.raise_for_status()
            data = r.json()["data"]["jobOffersQuery"]
        except Exception as e:
            print(f"[{NAME}] page failed: {e}")
            break
        for e in data["edges"]:
            addr = "; ".join(e.get("aadressid") or [])
            out.append({
                "id": str(e["id"]),
                "title": e.get("nimetus") or "",
                "company": e.get("brandNimi") or e.get("asutusNimi") or "",
                "location": addr + (" · kodus töötamine" if e.get("onKodusTootamine") else ""),
                "url": f"https://www.tootukassa.ee/et/toopakkumised/{e.get('alias') or e['id']}",
                "published": e.get("kinnitamineKp") or "",
                "source": NAME,
                "extra": e.get("ametinimetusTapsustus") or "",
                "assume_it": False,
            })
        if not data["pageInfo"]["hasNextPage"]:
            break
        cursor = data["pageInfo"]["endCursor"]
    return out
