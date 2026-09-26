#!/usr/bin/env python3
"""Deploy the Magpie n8n workflows (wf-m0/m1/m2) to n8n Cloud via the public REST API.

Repo JSONs stay the source of truth (parity test reads them); this script applies the
Cloud-specific transforms at upload time:
  * `$env.X` -> `$vars.X`  (n8n Cloud blocks $env access in expressions/Code nodes)
  * secrets never go into $vars: Apify token -> httpHeaderAuth credential (Bearer);
    Telegram / Airtable / judge-key credentials are attached only if their secret is set
  * Apify NOTICE node brought in line with mm/notice.py: haketa actor input
    {platform, query, maxListings}, one request per MP_TECH_QUERIES entry, `/`->`~` actor id
  * workflows are created INACTIVE (the Python loop remains the hero-run engine) and
    upserted by name, so re-running is idempotent.

Usage:  python3 marketmind/app/n8n/deploy_n8n.py [--dry-run]
Env:    app/.env must contain N8N_API_KEY; N8N_BASE_URL defaults to knreddy.app.n8n.cloud.
Audit C4: no secret is ever printed.
"""
from __future__ import annotations
import copy, json, re, sys, urllib.error, urllib.request
from pathlib import Path

N8N_DIR = Path(__file__).resolve().parent
APP = N8N_DIR.parent
WORKFLOWS = ["wf-m0-scan-decide.json", "wf-m1-full.json", "wf-m2-event-driven.json"]
# non-secret config mirrored into n8n Variables ($vars)
VAR_KEYS = ["APIFY_ACTOR_LISTINGS", "MP_TECH_QUERIES", "MP_MAX_PER_QUERY", "AUTO_PAUSE",
            "MODEL_JUDGE", "TF_BASE_URL", "TELEGRAM_CHAT_ID", "N8N_MAX_DRAFTS",
            "COMPS_JSON", "COMPS_SOURCE", "COMPS_BASIS"]   # COMPS_* derived from out/comps_cache.json (live eBay DE)
COMPS_CACHE = APP / "out" / "comps_cache.json"
SECRET_ENV_REFS = ("APFY_TOKEN", "TF_API_KEY", "OPENAI_API_KEY")
CRED_APIFY = "Magpie · Apify (Bearer)"
CRED_JUDGE = "Magpie · MODEL_JUDGE (Bearer)"
CRED_TELEGRAM = "Magpie · Telegram bot"
CRED_AIRTABLE = "Magpie · Airtable PAT"
STATE_FILE = APP / "out" / "n8n_deploy.json"   # gitignored; remembers credential ids


def load_env() -> dict:
    env = {}
    for line in (APP / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


class N8N:
    def __init__(self, base: str, key: str, dry: bool):
        self.base, self.key, self.dry = base.rstrip("/") + "/api/v1", key, dry

    def call(self, method: str, ep: str, body=None):
        if self.dry and method != "GET":
            print(f"  [dry-run] {method} {ep}")
            return {"id": "dry"}
        req = urllib.request.Request(
            self.base + ep, method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"X-N8N-API-KEY": self.key, "accept": "application/json",
                     "content-type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read().decode()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raise SystemExit(f"n8n API {method} {ep} -> HTTP {e.code}: {e.read().decode()[:300]}")

    def list_all(self, ep: str) -> list:
        out, cursor = [], None
        while True:
            sep = "&" if "?" in ep else "?"
            d = self.call("GET", ep + (f"{sep}cursor={cursor}" if cursor else ""))
            out += d.get("data", [])
            cursor = d.get("nextCursor")
            if not cursor:
                return out


def comps_vars() -> dict:
    """Live comps for the n8n price node: {key: [median, mad, n]} + provenance line (asking prices)."""
    if not COMPS_CACHE.exists():
        return {}
    c = json.loads(COMPS_CACHE.read_text())
    import datetime
    ts = datetime.datetime.utcfromtimestamp(COMPS_CACHE.stat().st_mtime).strftime("%Y-%m-%dT%H:%MZ")
    src = sorted({v.get("source", "?") for v in c.values()})
    bases = sorted({v.get("basis", "asking") for v in c.values()})
    basis = bases[0] if len(bases) == 1 else "mixed(" + ",".join(f"{k}:{v.get('basis', 'asking')}" for k, v in c.items()) + ")"
    return {"COMPS_JSON": json.dumps({k: [v["median"], v["mad"], v.get("n", 0)] for k, v in c.items()},
                                     separators=(",", ":")),
            "COMPS_SOURCE": f"{', '.join(src)} @ {ts} · {len(c)} families · basis={basis}",
            "COMPS_BASIS": basis}


def upsert_variables(api: N8N, env: dict) -> None:
    env = {**env, "N8N_MAX_DRAFTS": env.get("N8N_MAX_DRAFTS", "3"), **comps_vars()}
    existing = {v["key"]: v for v in api.list_all("/variables")}
    for k in VAR_KEYS:
        val = env.get(k, "")
        if k == "APIFY_ACTOR_LISTINGS":
            val = val.replace("/", "~")
        if not val:
            print(f"  var {k}: skipped (empty in app/.env)")
            continue
        if k in existing:
            if existing[k]["value"] != val:
                api.call("PUT", f"/variables/{existing[k]['id']}", {"key": k, "value": val})
                print(f"  var {k}: updated")
            else:
                print(f"  var {k}: unchanged")
        else:
            api.call("POST", "/variables", {"key": k, "value": val})
            print(f"  var {k}: created")
    if "MM_PROBE" in existing:  # leftover from connectivity probe
        api.call("DELETE", f"/variables/{existing['MM_PROBE']['id']}")


def ensure_credential(api: N8N, state: dict, name: str, ctype: str, data: dict) -> dict | None:
    """Create once; n8n's public API cannot read secrets back, so ids are cached in STATE_FILE."""
    if name in state.get("credentials", {}):
        return state["credentials"][name]
    res = api.call("POST", "/credentials", {"name": name, "type": ctype, "data": data})
    ref = {"id": res["id"], "name": name}
    state.setdefault("credentials", {})[name] = ref
    print(f"  credential created: {name} ({ctype})")
    return ref


def env_to_vars(obj):
    if isinstance(obj, str):
        return re.sub(r"\$env\.", "$vars.", obj)
    if isinstance(obj, list):
        return [env_to_vars(x) for x in obj]
    if isinstance(obj, dict):
        return {k: env_to_vars(v) for k, v in obj.items()}
    return obj


def strip_auth_header(params: dict) -> None:
    hp = params.get("headerParameters", {}).get("parameters", [])
    hp[:] = [h for h in hp if h.get("name", "").lower() != "authorization"]
    if not hp:
        params.pop("headerParameters", None)
        params["sendHeaders"] = False


QUERIES_JS = """// NOTICE fan-out: one Apify request per tech query (mirrors mm/notice.py)
const qs = String($vars.MP_TECH_QUERIES || 'nintendo switch,ps5,iphone 14,macbook')
  .split(',').map(s => s.trim()).filter(Boolean);
const maxL = Math.max(5, Number($vars.MP_MAX_PER_QUERY || 15));
return qs.map(q => ({ json: { query: q, maxListings: maxL } }));"""


def transform(wf: dict, creds: dict) -> dict:
    wf = copy.deepcopy(wf)
    nodes, conns = wf["nodes"], wf["connections"]
    for n in nodes:
        t, p = n["type"], n["parameters"]
        is_apify_http = t.endswith("httpRequest") and "api.apify.com" in json.dumps(p)
        is_judge = t.endswith("httpRequest") and n["name"].startswith("MODEL_JUDGE")
        if is_apify_http:
            strip_auth_header(p)
            p["url"] = "=https://api.apify.com/v2/acts/{{ $vars.APIFY_ACTOR_LISTINGS }}/run-sync-get-dataset-items"
            p["jsonBody"] = ('={"platform":"marktplaats.nl","query":"{{ $json.query }}",'
                             '"maxListings":{{ $json.maxListings }}}')
            p["authentication"] = "genericCredentialType"
            p["genericAuthType"] = "httpHeaderAuth"
            p.setdefault("options", {})["timeout"] = 300000
            n["credentials"] = {"httpHeaderAuth": creds[CRED_APIFY]}
        elif is_judge:
            strip_auth_header(p)
            p["authentication"] = "genericCredentialType"
            p["genericAuthType"] = "httpHeaderAuth"
            n["credentials"] = {"httpHeaderAuth": creds[CRED_JUDGE]} if creds.get(CRED_JUDGE) else {}
        elif t.endswith("telegram"):
            n["credentials"] = {"telegramApi": creds[CRED_TELEGRAM]} if creds.get(CRED_TELEGRAM) else {}
        elif t.endswith("airtable"):
            n["credentials"] = {"airtableTokenApi": creds[CRED_AIRTABLE]} if creds.get(CRED_AIRTABLE) else {}
        elif "credentials" in n:  # placeholder ids (e.g. "apify-creds") would fail import
            n["credentials"] = {}

    # insert the query fan-out node between the trigger and the Apify HTTP node
    apify = next((n for n in nodes if n["type"].endswith("httpRequest")
                  and "api.apify.com" in json.dumps(n["parameters"])), None)
    if apify:
        fan = {"parameters": {"jsCode": QUERIES_JS}, "id": "mp-queries", "name": "MP tech queries (fan-out)",
               "type": "n8n-nodes-base.code", "typeVersion": 2,
               "position": [apify["position"][0] - 110, apify["position"][1] + 160]}
        for src, outs in conns.items():
            for branch in outs.get("main", []):
                for c in branch:
                    if c["node"] == apify["name"]:
                        c["node"] = fan["name"]
        conns[fan["name"]] = {"main": [[{"node": apify["name"], "type": "main", "index": 0}]]}
        nodes.append(fan)

    out: dict = env_to_vars(wf)  # type: ignore[assignment]
    leaked = [r for r in SECRET_ENV_REFS if f"$vars.{r}" in json.dumps(out)]
    if leaked:
        raise SystemExit(f"refusing to deploy: secret refs would resolve via $vars: {leaked}")
    return {"name": out["name"], "nodes": out["nodes"], "connections": out["connections"],
            "settings": {"executionOrder": out.get("settings", {}).get("executionOrder", "v1")}}


def main() -> int:
    dry = "--dry-run" in sys.argv
    env = load_env()
    if not env.get("N8N_API_KEY"):
        raise SystemExit("N8N_API_KEY missing in app/.env")
    api = N8N(env.get("N8N_BASE_URL", "https://knreddy.app.n8n.cloud"), env["N8N_API_KEY"], dry)
    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}

    print("variables:")
    upsert_variables(api, env)

    print("credentials:")
    creds = {CRED_APIFY: ensure_credential(api, state, CRED_APIFY, "httpHeaderAuth",
                                           {"name": "Authorization", "value": f"Bearer {env['APFY_TOKEN']}"})}
    judge_key = env.get("TF_API_KEY") or env.get("OPENAI_API_KEY")
    if judge_key:
        creds[CRED_JUDGE] = ensure_credential(api, state, CRED_JUDGE, "httpHeaderAuth",
                                              {"name": "Authorization", "value": f"Bearer {judge_key}"})
    if env.get("TELEGRAM_BOT_TOKEN"):
        creds[CRED_TELEGRAM] = ensure_credential(api, state, CRED_TELEGRAM, "telegramApi",
                                                 {"accessToken": env["TELEGRAM_BOT_TOKEN"]})
    if env.get("AIRTABLE_PAT"):
        creds[CRED_AIRTABLE] = ensure_credential(api, state, CRED_AIRTABLE, "airtableTokenApi",
                                                 {"accessToken": env["AIRTABLE_PAT"]})
    for name in (CRED_JUDGE, CRED_TELEGRAM, CRED_AIRTABLE):
        if name not in creds:
            print(f"  credential skipped: {name} (secret empty in app/.env)")

    print("workflows:")
    existing = {w["name"]: w for w in api.list_all("/workflows?limit=100")}
    deployed = {}
    for fname in WORKFLOWS:
        body = transform(json.loads((N8N_DIR / fname).read_text()), creds)
        if body["name"] in existing:
            wid = existing[body["name"]]["id"]
            api.call("PUT", f"/workflows/{wid}", body)
            print(f"  updated  {wid}  {body['name']}  ({len(body['nodes'])} nodes)")
        else:
            wid = api.call("POST", "/workflows", body)["id"]
            print(f"  created  {wid}  {body['name']}  ({len(body['nodes'])} nodes)")
        deployed[fname] = wid
    state["workflows"] = deployed
    if not dry:
        STATE_FILE.parent.mkdir(exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
