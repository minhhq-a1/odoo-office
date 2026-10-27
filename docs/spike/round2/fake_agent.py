# Fake Paperclip agent for the spike: reports a cost event, comments, marks issue done.
import json, os, sys, time, urllib.request, builtins
_p = builtins.print
def print(*a, **k):  # keep working if the server (stdout reader) died
    try: _p(*a, **k)
    except Exception: pass
api = os.environ.get("PAPERCLIP_API_URL", "http://127.0.0.1:3100").rstrip("/")
tok = os.environ["PAPERCLIP_API_KEY"]
run = os.environ.get("PAPERCLIP_RUN_ID", "")
log = open("/tmp/claude-0/spike/agent/side_effects.log", "a")
def call(method, path, body=None):
    req = urllib.request.Request(api + path, method=method, data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json", "X-Paperclip-Run-Id": run})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:300]
st, me = call("GET", "/api/agents/me")
task = os.environ.get("PAPERCLIP_TASK_ID")
if not task:  # process adapter does not inject PAPERCLIP_TASK_ID: pick from inbox
    st, rows = call("GET", f"/api/companies/{me['companyId']}/issues?assigneeAgentId={me['id']}&status=todo,in_progress,blocked")
    task = rows[0]["id"] if isinstance(rows, list) and rows else None
    if task:
        st, body = call("POST", f"/api/issues/{task}/checkout", {"agentId": me["id"], "expectedStatuses": ["todo", "in_progress", "blocked"]})
        print("checkout", st, flush=True)
        if st != 200: sys.exit(0)  # 409 = another run owns it; never retry, no cost/side effect
print("run", run, "agent", me.get("id") if isinstance(me, dict) else me, "task", task, flush=True)
log.write(f"{time.time():.0f} START run={run} task={task}\n"); log.flush()
time.sleep(float(os.environ.get("FAKE_SLEEP", "0")))
cents = int(os.environ.get("FAKE_COST_CENTS", "3"))
print("cost", call("POST", f"/api/companies/{me['companyId']}/cost-events", {"agentId": me["id"], "issueId": task,
    "provider": "fake", "model": "fake-1", "inputTokens": 1000, "outputTokens": 100, "costCents": cents, "occurredAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}), flush=True)
log.write(f"{time.time():.0f} SIDE_EFFECT run={run} task={task}\n"); log.flush()
if task:
    print("done", call("PATCH", f"/api/issues/{task}", {"status": "done", "comment": f"Fake agent output for run {run}: draft BRD v1."}), flush=True)
