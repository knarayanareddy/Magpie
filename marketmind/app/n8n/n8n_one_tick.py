"""Activate an n8n workflow for exactly one production tick, capture the execution, deactivate.
Usage: python3 n8n_one_tick.py <workflow_id> [timeout_s]. Writes out/n8n_exec_<id>.json (full execution data)."""
import json, sys, time, urllib.request, urllib.error
from pathlib import Path
APP = Path('/Users/macbookpro/Downloads/Magpie/marketmind/app')
k = [l.split('=', 1)[1].strip() for l in (APP / '.env').read_text().splitlines() if l.startswith('N8N_API_KEY=')][0]
B = 'https://knreddy.app.n8n.cloud/api/v1'
def call(m, ep, body=None):
    req = urllib.request.Request(B + ep, method=m, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'X-N8N-API-KEY': k, 'accept': 'application/json', 'content-type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode(); return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise SystemExit(f'{m} {ep} -> {e.code} {e.read()[:300]}')
wid = sys.argv[1]; timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 420
before = {e['id'] for e in call('GET', f'/executions?workflowId={wid}&limit=20').get('data', [])}
t0 = time.time()
call('POST', f'/workflows/{wid}/activate'); print('activated', wid, time.strftime('%H:%M:%S'))
ex = None
try:
    while time.time() - t0 < timeout:
        time.sleep(15)
        new = [e for e in call('GET', f'/executions?workflowId={wid}&limit=20').get('data', []) if e['id'] not in before]
        done = [e for e in new if e.get('finished') or e.get('status') in ('success', 'error', 'crashed')]
        if done:
            ex = done[-1]; break
        if new:
            print('  running…', new[0]['id'], new[0].get('status'))
finally:
    call('POST', f'/workflows/{wid}/deactivate'); print('deactivated', time.strftime('%H:%M:%S'))
if not ex:
    raise SystemExit('no finished execution within timeout')
full = call('GET', f"/executions/{ex['id']}?includeData=true")
(APP / 'out' / f"n8n_exec_{ex['id']}.json").write_text(json.dumps(full, indent=1))
rd = full.get('data', {}).get('resultData', {})
print('execution', ex['id'], 'status', full.get('status'), 'mode', full.get('mode'), 'started', full.get('startedAt'), 'stopped', full.get('stoppedAt'))
if rd.get('error'):
    print('ERROR:', json.dumps(rd['error'])[:800])
for node, runs in rd.get('runData', {}).items():
    r = runs[-1]
    n_out = sum(len(b or []) for b in (r.get('data', {}).get('main') or []))
    print(f"  {node:48} items_out={n_out:<4} {'ERROR ' + str(r['error'].get('message'))[:120] if r.get('error') else ''}")
