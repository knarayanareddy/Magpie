"""ACTUATOR (US-11) — allowlisted browser actions on the dedicated demo account. Gates are pure code.

Exactly three actions exist (Art XII.1): send_message · edit_own_price · bump_own_listing. There is no generic
"click"/"navigate" entry point, no LLM in the browser loop, and no code path to a payment button (Art V.3).

Flow:  request(action, target, params)  -> gates -> approval token (human, one-shot, 15 min)
       execute(token)                    -> gates again -> Playwright driver (dry-run unless ACT_LIVE=1)
Every step writes a hash-chained receipt to out/actuator/receipts.jsonl; artefacts under out/actuator/runs/<id>/.
"""
from __future__ import annotations
import hashlib, json, os, re, secrets, time, uuid
from pathlib import Path
from urllib.parse import urlparse

from .. import receipts as rc

APP = Path(__file__).resolve().parents[2]
ALLOWLIST = ("send_message", "edit_own_price", "bump_own_listing")
OWN_ACTIONS = ("edit_own_price", "bump_own_listing")
ALLOWED_HOSTS = ("www.marktplaats.nl",)
AD_PATH = re.compile(r"^/v/[a-z0-9\-]+/[a-z0-9\-]+/(m\d{9,11})(-[a-z0-9\-]*)?$")
TOKEN_TTL_S = 15 * 60
MSG_MAX_CHARS = 600


class Refused(Exception):
    """A gate said no. .code is the receipt reason code."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code, self.detail = code, detail


def act_dir(out: str | Path | None = None) -> Path:
    d = Path(out) if out else APP / "out" / "actuator"
    (d / "runs").mkdir(parents=True, exist_ok=True)
    return d


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ------------------------------------------------------------------ gates (pure, offline-testable)
def ad_id(url: str) -> str:
    """Validate a Marktplaats ad URL and return its m-number. Refuses anything else (Art XII.1)."""
    p = urlparse(url or "")
    if p.scheme != "https" or p.hostname not in ALLOWED_HOSTS or p.query or p.fragment or p.username or p.port:
        raise Refused("target_not_allowlisted", f"{p.scheme}://{p.hostname}")
    m = AD_PATH.match(p.path)
    if not m:
        raise Refused("target_not_an_ad", p.path[:80])
    return m.group(1)


def kill_switch_on(state_path: Path | None = None) -> bool:
    if os.environ.get("AUTO_PAUSE") == "1":
        return True
    p = state_path or APP / "out" / "state.json"
    try:
        return bool(json.loads(p.read_text()).get("paused"))
    except Exception:
        return False                                     # no state file = loop never ran; not a pause


def provenance(action: str, url: str, *, feed_urls: set[str], own_listing_ids: set[str],
               drafted_listing_urls: set[str]) -> str:
    """Where the target came from. send_message: a URL from the pinned feed AND with a Magpie draft.
    Own-listing actions: the m-number is in the own-ads registry. Anything else refuses."""
    lid = ad_id(url)
    if action == "send_message":
        if url not in feed_urls:
            raise Refused("target_not_from_feed", lid)
        if url not in drafted_listing_urls:
            raise Refused("no_draft_for_target", lid)
        return "apify_feed+draft"
    if action in OWN_ACTIONS:
        if lid not in own_listing_ids:
            raise Refused("not_own_listing", lid)
        return "own_accounts_registry"
    raise Refused("action_not_allowlisted", action)


def validate_params(action: str, params: dict) -> dict:
    if action == "send_message":
        text = str(params.get("text") or "").strip()
        if not text or len(text) > MSG_MAX_CHARS:
            raise Refused("bad_message", f"len={len(text)}")
        if re.search(r"https?://|www\.|\b\d{9,}\b|tikkie|iban|whatsapp", text, re.I):
            raise Refused("message_offplatform_content")      # our own drafts never contain these
        return {"text": text}
    if action == "edit_own_price":
        try:
            new, old = int(params["new_price_eur"]), int(params["old_price_eur"])
        except Exception:
            raise Refused("bad_price")
        if not (1 <= new <= 20000) or new >= old or new < old * 0.5:
            # only DOWNWARD reprices within 50% are allowed unattended of intent; raising price is a human act
            raise Refused("price_change_out_of_bounds", f"{old}->{new}")
        return {"new_price_eur": new, "old_price_eur": old}
    if action == "bump_own_listing":
        return {}
    raise Refused("action_not_allowlisted", action)


def budget_used_today(d: Path) -> int:
    today = time.strftime("%Y-%m-%d", time.gmtime())
    p = d / "receipts.jsonl"
    if not p.exists():
        return 0
    n = 0
    for ln in p.read_text().splitlines():
        try:
            r = json.loads(ln)
        except Exception:
            continue
        if r.get("ts", "").startswith(today) and r.get("action_state") in ("pursued_assisted", "pursued_auto") \
                and r.get("policy_branch", "").startswith("act:") and r.get("scores", {}).get("live"):
            n += 1
    return n


# ------------------------------------------------------------------ receipts
def receipt(d: Path, action: str, target: str, state: str, reasons: list[str], *, actor: str,
            scores: dict | None = None, extra: dict | None = None) -> dict:
    body = {"receipt_id": str(uuid.uuid4()), "ts": now(), "listing_id": target, "actor": actor,
            "hostile": False, "policy_branch": f"act:{action}", "action_state": state, "tier": "T1" if action in OWN_ACTIONS else "T2",
            "reason_codes": list(reasons), "scores": scores or {}, "side": "act",
            "action_state_note": "dry-run: final button NOT pressed" if (scores or {}).get("live") is False else ""}
    if extra:
        body.update(extra)
    body["input_hash"] = rc._row_hash({k: body[k] for k in ("listing_id", "policy_branch", "reason_codes", "scores")})
    rc.write(d / "receipts.jsonl", [body])
    return body


# ------------------------------------------------------------------ approval tokens (human, one-shot)
def _tokens_path(d: Path) -> Path:
    return d / "approvals.json"


def _load_tokens(d: Path) -> dict:
    p = _tokens_path(d)
    return json.loads(p.read_text()) if p.exists() else {}


def _save_tokens(d: Path, t: dict) -> None:
    p = _tokens_path(d)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(t, indent=2))
    os.replace(tmp, p)


def request(action: str, url: str, params: dict, *, context: dict, d: Path | None = None) -> dict:
    """Run every pre-browser gate, then mint a one-shot human approval token for this EXACT action.
    context = {feed_urls, own_listing_ids, drafted_listing_urls, state_path?}. Returns {token, summary}."""
    d = d or act_dir()
    lid = "?"
    try:
        if action not in ALLOWLIST:
            raise Refused("action_not_allowlisted", action)
        lid = ad_id(url)
        if kill_switch_on(context.get("state_path")):
            raise Refused("kill_switch")
        src = provenance(action, url, feed_urls=context.get("feed_urls", set()),
                         own_listing_ids=context.get("own_listing_ids", set()),
                         drafted_listing_urls=context.get("drafted_listing_urls", set()))
        p = validate_params(action, params)
    except Refused as e:
        receipt(d, action if action in ALLOWLIST else "refused", lid, "skipped", [e.code], actor="agent",
                scores={"detail": e.detail[:120]})
        raise
    token = secrets.token_hex(4)
    digest = hashlib.sha256(json.dumps([action, url, p], sort_keys=True).encode()).hexdigest()[:16]
    t = _load_tokens(d)
    t = {k: v for k, v in t.items() if v["expires"] > time.time() and not v.get("used")}
    t[token] = {"action": action, "url": url, "params": p, "digest": digest, "provenance": src,
                "created": time.time(), "expires": time.time() + TOKEN_TTL_S, "used": False, "listing_id": lid}
    _save_tokens(d, t)
    receipt(d, action, lid, "drafted", ["act_requested", f"provenance:{src}"], actor="agent",
            scores={"digest": digest, **({"new_price_eur": p["new_price_eur"], "old_price_eur": p["old_price_eur"]}
                                         if action == "edit_own_price" else {})})
    summary = {"send_message": lambda: f"send message to seller of {lid}: “{p['text'][:80]}…”",
               "edit_own_price": lambda: f"lower price of your ad {lid}: €{p['old_price_eur']} → €{p['new_price_eur']}",
               "bump_own_listing": lambda: f"bump your ad {lid}"}[action]()
    return {"token": token, "summary": summary, "digest": digest, "expires_in_s": TOKEN_TTL_S}


def approve(token: str, d: Path | None = None) -> dict:
    """Human approval (actor=human). Consumes nothing yet; marks the token approved for execute()."""
    d = d or act_dir()
    t = _load_tokens(d)
    e = t.get(token)
    if not e or e.get("used") or e["expires"] < time.time():
        raise Refused("approval_token_invalid_or_expired", token)
    e["approved_at"] = time.time()
    _save_tokens(d, t)
    receipt(d, e["action"], e["listing_id"], "pursued_assisted", ["human_approved"], actor="human",
            scores={"digest": e["digest"]})
    return e


def claim(token: str, *, live: bool, d: Path | None = None, state_path: Path | None = None) -> dict:
    """Last gate before the browser: token approved + unused + unexpired, kill switch off, daily budget.
    Marks the token used (one-shot) BEFORE the browser opens, so a crash can never replay it."""
    d = d or act_dir()
    t = _load_tokens(d)
    e = t.get(token)
    try:
        if not e or e["expires"] < time.time():
            raise Refused("approval_token_invalid_or_expired", token)
        if e.get("used"):
            raise Refused("approval_token_already_used", token)
        if not e.get("approved_at"):
            raise Refused("not_human_approved", token)
        if kill_switch_on(state_path):
            raise Refused("kill_switch")
        cap = int(os.environ.get("ACT_MAX_PER_DAY", "5"))
        if live and budget_used_today(d) >= cap:
            raise Refused("act_budget_exhausted", f"{cap}/day")
    except Refused as ex:
        receipt(d, (e or {}).get("action", "refused"), (e or {}).get("listing_id", "?"), "skipped", [ex.code], actor="agent")
        raise
    e["used"] = True
    e["claimed_at"] = time.time()
    _save_tokens(d, t)
    return e
