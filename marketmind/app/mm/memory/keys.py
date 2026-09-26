"""PRODUCT KEYS — deterministic title -> product_key normalizer (US-10). JEV only as a cached proposal.

A product key is a comparable-price bucket: "iphone 14 pro", "switch oled", "ps5 disc", "macbook pro m2".
Precision beats recall: a wrong key produces a wrong price (a 14 Pro Max priced as a 14), so the rules
return None rather than guess, and non-device titles (repairs, parts, games-bundles, accessories-for-X)
never get a device key. Storage is kept as a separate facet (not part of the key) so buckets stay dense.
"""
from __future__ import annotations
import json, re, shutil, subprocess, time, unicodedata
from typing import Callable

from .. import rerank

_WS = re.compile(r"\s+")


def norm(title: str) -> str:
    t = unicodedata.normalize("NFKD", title or "").encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9+ ]", " ", t)
    return _WS.sub(" ", t).strip()[:160]


def storage_gb(title: str) -> int | None:
    m = re.search(r"\b(64|128|256|512|1024)\s*gb\b|\b(1|2)\s*tb\b", norm(title))
    if not m:
        return None
    return int(m.group(1)) if m.group(1) else int(m.group(2)) * 1024


# each rule: (regex over normalized title, key builder). First match wins; order = most specific first.
def _iphone(m):
    gen, var = m.group(1), (m.group(2) or "").strip()
    var = {"pro max": "pro max", "promax": "pro max", "pro": "pro", "plus": "plus", "mini": "mini"}.get(var, "")
    return f"iphone {gen}{(' ' + var) if var else ''}"


RULES: list[tuple[re.Pattern, Callable[[re.Match], str]]] = [
    (re.compile(r"\biphone\s*(1[1-7]|[89]|x[rs]?|se)\s*(pro\s*max|promax|pro|plus|mini)?\b"), _iphone),
    (re.compile(r"\b(?:nintendo\s*)?switch\s*2\b"), lambda m: "switch 2"),
    (re.compile(r"\b(?:nintendo\s*)?switch\s*(?:lite)\b"), lambda m: "switch lite"),
    (re.compile(r"\b(?:nintendo\s*)?switch\s*oled\b"), lambda m: "switch oled"),
    (re.compile(r"\bnintendo\s*switch\b(?!\s*(?:games?|spellen|controller|hoes|case|dock\s*only))"), lambda m: "switch"),
    (re.compile(r"\bps5\s*pro\b|\bplaystation\s*5\s*pro\b"), lambda m: "ps5 pro"),
    (re.compile(r"\bps5\s*(?:slim\s*)?(?:digital)\b|\bplaystation\s*5\s*digital\b"), lambda m: "ps5 digital"),
    (re.compile(r"\bps5\b(?=.*\b(?:disc|console|konsole|1tb|825\s*gb|slim)\b)|\bplaystation\s*5\s*(?:disc|console|slim)\b"), lambda m: "ps5 disc"),
    (re.compile(r"\bps4\s*pro\b"), lambda m: "ps4 pro"),
    (re.compile(r"\bps4\b(?=.*\b(?:slim|console|500\s*gb|1tb)\b)"), lambda m: "ps4"),
    (re.compile(r"\bmacbook\s*air\b.*?\bm([1-5])\b"), lambda m: f"macbook air m{m.group(1)}"),
    (re.compile(r"\bmacbook\s*pro\b.*?\bm([1-5])\s*(pro|max)?\b"),
     lambda m: f"macbook pro m{m.group(1)}{(' ' + m.group(2)) if m.group(2) else ''}"),
    (re.compile(r"\bmacbook\s*pro\b.*?\b(201[5-9]|2020)\b"), lambda m: f"macbook pro intel {m.group(1)}"),
    (re.compile(r"\bairpods\s*pro\s*2\b|\bairpods\s*pro\s*(?:2nd|gen\s*2|usb\s*c)\b"), lambda m: "airpods pro 2"),
    (re.compile(r"\bairpods\s*pro\b"), lambda m: "airpods pro"),
    (re.compile(r"\bapple\s*watch\s*(?:series\s*)?(\d{1,2})\b"), lambda m: f"apple watch s{m.group(1)}"),
    (re.compile(r"\bapple\s*watch\s*ultra\s*(2)?\b"), lambda m: f"apple watch ultra{(' ' + m.group(1)) if m.group(1) else ''}"),
    (re.compile(r"\bcanon\s*eos\s*(\d{2,4}d|r\d{0,2})\b"), lambda m: f"canon eos {m.group(1)}"),
]
NON_DEVICE_EXTRA = re.compile(r"\b(games?|spellen|diverse|titels|controllers?|covers?|headset|stuur|racing\s*wheel|"
                              r"pre\s*order|portal|remote|clickers?)\b")


def rules_key(title: str) -> str | None:
    """Deterministic key or None. None is a valid, honest answer (-> no memory comps)."""
    if rerank.is_non_device_listing(title or ""):
        return None
    t = norm(title)
    for rx, build in RULES:
        m = rx.search(t)
        if m:
            key = build(m)
            # a console key must not come from an accessory/games title ("PS5 controllers", "Switch games").
            # A concrete model marker in the title (switch 2 / oled / lite / disc / 1tb …) means a console bundle.
            if key.startswith(("ps5", "ps4", "switch")) and NON_DEVICE_EXTRA.search(t) and not re.search(
                    r"\b(console|konsole|compleet|in doos|met joy|1tb|825|oled|lite|v1|v2|disc|digital|switch 2)\b", t):
                return None
            return key
    return None


def jev_propose(title: str, candidates: list[str], timeout_ms: int = 4000) -> tuple[str | None, float]:
    """JEV `choice` over EXISTING keys + none. Proposal only; caller caches it. (None, 0) on any failure."""
    if not candidates or not shutil.which("jev"):
        return None, 0.0
    opts = ",".join(f"{c}:{c}" for c in candidates[:12]) + ",none:none of these products"
    try:
        r = subprocess.run(["jev", "choice", "Which product does this Dutch classifieds title refer to? "
                            "Pick none for accessories, games, repairs, parts or bundles.",
                            "--state", (title or "")[:200], "--options", opts, "--json", "--no-hedge",
                            "--timeout", str(timeout_ms)], capture_output=True, text=True, timeout=timeout_ms / 1000 + 3)
        d = json.loads(r.stdout)["answers"]["decision"]
        choice, conf = d["choice"], float(d.get("confidence") or 0)
        return (None if choice == "none" else choice), conf
    except Exception:
        return None, 0.0


def jev_allowed(title: str, key: str | None) -> bool:
    """Deterministic veto over a JEV proposal: the same non-device / games / accessory guards the rules use.
    (Measured Sat: JEV mapped 'Switch spellen Mario Kart' -> 'switch' at conf 0.85.)"""
    if not key:
        return True
    t = norm(title)
    if rerank.is_non_device_listing(title or ""):
        return False
    if key.startswith(("ps5", "ps4", "switch")) and (NON_DEVICE_EXTRA.search(t) or re.search(r"\b(spel|spellen|game)\b", t)) \
            and not re.search(r"\b(console|konsole|compleet|in doos|met joy|1tb|825|oled|lite|disc|digital)\b", t):
        return False
    return True


def resolve(con, title: str, *, use_jev: bool = False, jev_min_conf: float = 0.90) -> tuple[str | None, str]:
    """Cached key lookup: product_keys table -> rules -> (optional) JEV. Returns (key, method)."""
    tn = norm(title)
    row = con.execute("SELECT product_key, method FROM product_keys WHERE title_norm=?", (tn,)).fetchone()
    if row:
        con.execute("UPDATE product_keys SET hits=hits+1 WHERE title_norm=?", (tn,))
        return row["product_key"], f"cache:{row['method']}"
    key = rules_key(title)
    method, conf = "rules", 1.0
    if key is None and use_jev and not rerank.is_non_device_listing(title or ""):
        cands = [r[0] for r in con.execute(
            "SELECT product_key FROM price_obs GROUP BY product_key ORDER BY COUNT(*) DESC LIMIT 12")]
        jk, conf = jev_propose(title, cands)
        if jk and conf >= jev_min_conf and jev_allowed(title, jk):
            key, method = jk, "jev"
    con.execute("INSERT OR REPLACE INTO product_keys(title_norm, product_key, method, confidence, at) VALUES (?,?,?,?,?)",
                (tn, key, method, conf, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
    return key, method
