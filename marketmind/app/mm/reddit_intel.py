"""REDDIT INTEL — On-demand defect detection & trend discovery via labrat011/reddit-scraper.
Used by the AI agent via MCP or Python helper for qualitative seller questions and trend seeds.

Art III Compliance: strictly inspects product models, defect checklists, and category trends.
Zero person-profiling — never scrapes seller usernames or individual accounts."""
from __future__ import annotations
import json, os, urllib.request
from typing import Any

# Verified common failure modes / defect traps for secondhand resale categories
KNOWN_DEFECT_TRAPS: dict[str, list[str]] = {
    "canon ae": ["shutter squeak (spiegelpiep)", "vergane lichtafdichtingen (light seals)"],
    "canon ae-1": ["shutter squeak (spiegelpiep)", "vergane lichtafdichtingen (light seals)"],
    "switch": ["joy-con drift", "docking port speling"],
    "nintendo switch": ["joy-con drift", "docking port speling"],
    "ps4 pro": ["luide ventilator / uitgedroogde koelpasta", "disc drive eject bug"],
    "ps4": ["luide ventilator / stofophoping", "hdmi-poort speling"],
    "ps5": ["hdmi-poort schade", "controller stick drift"],
    "gazelle": ["accu actieradius afname", "display sensor storing"],
    "iphone 14": ["batterijconditie onder 80%", "face-id storing na schermreparatie"],
}

TRENDING_NICHE_SEEDS = [
    "digicam", "powershot", "polaroid 600", "oled", "game boy color",
    "canon g7x", "fujifilm x100", "minolta x700", "gamecube", "tamagotchi"
]


def query_defects(item_title: str, mode: str = "sim") -> list[str]:
    """Returns known failure modes / defect traps for the product model.
    In sim mode, returns verified offline defect catalog.
    In live mode, queries Apify actor labrat011/reddit-scraper if token is present."""
    t = (item_title or "").lower()
    for model_key, defects in KNOWN_DEFECT_TRAPS.items():
        if model_key in t:
            return list(defects)

    if mode == "live" and os.environ.get("APFY_TOKEN"):
        try:
            return _query_reddit_live(item_title, search_type="defects")
        except Exception:
            return []
    return []


def format_inspection_question(item: dict, defects: list[str]) -> tuple[str, str] | None:
    """Formats a professional reseller inspection question for offer drafts.
    Signals domain expertise to the seller (e.g. asking about AE-1 shutter squeak)."""
    if not defects:
        return None
    title = str(item.get("title", "item"))
    top_defect = defects[0]

    hook_nl = f"Werkt alles naar behoren, en heeft hij toevallig last van {top_defect}? "
    hook_en = f"Is everything working properly, and does it happen to have any {top_defect}? "
    return hook_nl, hook_en


def query_trending_seeds(mode: str = "sim") -> list[str]:
    """Returns trending secondhand search seeds from enthusiast communities.
    Directly feeds expand.py to discover high-demand niche inventory."""
    if mode == "live" and os.environ.get("APFY_TOKEN"):
        try:
            live_seeds = _query_reddit_live("trending thrift flipping", search_type="trends")
            if live_seeds:
                return live_seeds
        except Exception:
            pass
    return list(TRENDING_NICHE_SEEDS)


def _query_reddit_live(query: str, search_type: str = "defects") -> list[str]:
    """Queries labrat011/reddit-scraper on Apify via HTTP REST API (fail-closed)."""
    token = os.environ.get("APFY_TOKEN", "")
    if not token:
        return []
    url = "https://api.apify.com/v2/acts/labrat011~reddit-scraper/run-sync-get-dataset-items"
    search_q = f'"{query}" common issues OR defects' if search_type == "defects" else query
    payload = {
        "mode": "search",
        "searchQueriesList": [search_q],
        "searchSort": "top",
        "maxResults": 10,
        "includeComments": False
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        items = json.load(r)
    results = []
    for it in (items if isinstance(items, list) else []):
        t = it.get("title") or ""
        if t and len(t) > 5:
            results.append(t[:60])
    return results[:5]
