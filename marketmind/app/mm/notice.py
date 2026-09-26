"""NOTICE — real-world data in (Apify in live mode, fixtures in sim). Never fetches seller-supplied URLs (Art XII.1)."""
from __future__ import annotations
import json, os, time, urllib.error, urllib.request
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
APIFY_BASE = "https://api.apify.com/v2"


class MMFeedError(RuntimeError):
    """Feed failure, cleanly reported (no URLs, no tokens in the message — audit C4)."""


def _safe_float(v) -> float:
    try:
        return float(str(v).replace("€", "").replace(",", "").strip() or 0)
    except (TypeError, ValueError):
        return 0.0  # audit R3: "€150" from an actor must not crash the run


def load(mode: str, measure: bool = False) -> tuple[list[dict], dict]:
    """Returns (listings, meta). meta carries honest timing notes (Art IV.3)."""
    t0 = time.perf_counter()
    if mode == "sim":
        listings = json.loads((FIXTURES / "apify_sample_dataset.json").read_text())
        comps_path = Path(os.environ.get("COMPS_PATH", FIXTURES / "comps_sample.json"))
        comps = json.loads(comps_path.read_text())
        meta = {"source": "fixtures", "mode": "sim",
                "timing_note": "simulated local read; live cycle time measured at T15/T05"}
    else:
        token = os.environ.get("APFY_TOKEN", "")
        actor = os.environ.get("APIFY_ACTOR_LISTINGS", "")
        if not token or not actor:
            missing = ", ".join(k for k in ("APFY_TOKEN", "APIFY_ACTOR_LISTINGS") if not os.environ.get(k))
            raise MMFeedError(f"{missing} missing — copy app/env.example to app/.env (WIRING §1)")
        body = json.dumps({"search": "nintendo switch OR canon lens OR ps4 OR ps5 OR polaroid",
                           "category": "games_consoles_camera", "maxItems": 25}).encode()
        try:
            listings = [_normalize(x) for x in _apify_post(token, actor, body)]
        except MMFeedError:
            raise
        except Exception as e:
            raise MMFeedError(f"apify_unreachable:{type(e).__name__}") from None
        comps = _load_comps_live(token)
        meta = {"source": f"apify:{actor}", "mode": "live"}
    meta["cycle_time_s"] = round(time.perf_counter() - t0, 3)
    return listings, {**meta, "comps": comps}


def _apify_post(token: str, actor: str, body: bytes) -> list:
    """Token travels in the Authorization header, never in the URL (audit C4: URLs leak via
    tracebacks, proxies, and process listings)."""
    url = f"{APIFY_BASE}/acts/{actor}/run-sync-get-dataset-items"
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=300) as r:
        out = json.load(r)
    return out if isinstance(out, list) else out.get("items", [])


def _load_comps_live(token: str) -> dict:
    actor = os.environ.get("APIFY_ACTOR_COMPS", "")
    if not actor:
        return {}
    body = json.dumps({"query": "nintendo switch v2 sold", "maxItems": 40, "sold": True}).encode()
    try:
        items = _apify_post(token, actor, body)
    except Exception:
        return {}  # missing grounding => decide() will fail closed to no_comps
    prices = sorted(_safe_float(i.get("price_eur") or i.get("price")) for i in items
                    if i.get("price_eur") or i.get("price"))
    prices = [p for p in prices if p > 0]
    if not prices:
        return {}
    med = prices[len(prices) // 2]
    mad = sorted(abs(p - med) for p in prices)[len(prices) // 2] or 1.0
    return {"nintendo switch": {"median": med, "mad": mad, "n": len(prices), "source": actor}}


def _normalize(raw: dict) -> dict:
    """Map actor output -> canonical item (shape documented in WIRING.md §1)."""
    return {
        "id": raw.get("id") or raw.get("url", "")[-24:],
        "url": raw.get("url", ""),
        "title": raw.get("title", ""),
        "description": raw.get("description", ""),
        "price_eur": _safe_float(raw.get("price_eur") or raw.get("price")),
        "category": raw.get("category", "other"),
        "images": raw.get("images", [])[:3],
        "seller": raw.get("seller", {}) or {},
        "posted_at": raw.get("posted_at", ""),
        "is_mine": bool(raw.get("is_mine", False)),
    }
