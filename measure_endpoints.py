"""Measure each endpoint separately for baseline and optimized handlers.

Writes per-endpoint JSON summaries required by the evaluation contract.
"""
import json
import sys
from pathlib import Path
import importlib
import subprocess

from app import SessionLocal, engine

OUT = Path("artifacts")
OUT.mkdir(exist_ok=True)

WORKLOAD = [
    {"id": "list_users", "method": "GET", "endpoint": "/api/users", "query": {"page": 1, "per_page": 100}},
    {"id": "followers_page", "method": "GET", "endpoint": "/api/users/1/followers", "query": {"page": 1, "per_page": 100}},
]

LOAD = {"total_requests": 2000, "concurrency": 50, "warmup_requests": 200, "timeout_ms": 5000}

PY = sys.executable


def run_for_module(module_name, req):
    # run the same in-process runner subprocess but import the requested module
    cmd = [
        PY,
        "-u",
        "-c",
        (
            "import importlib, json; import sys; from app import SessionLocal, engine;"
            "m = importlib.import_module('%s'); import perf_runner;"
            "h = m.get_users if 'users' in '%s' and 'followers' not in '%s' else m.get_user_followers;"
            "runner = perf_runner.InProcessRunner(h, engine, SessionLocal, {'authorization':'Bearer test-token'});"
            "results = runner.run_workload(%s, %d, %d, %d, %d); print(json.dumps({'module':'%s','handler': h.__name__,'results': perf_runner.summarize(results)}))"
        ) % (module_name, req['endpoint'], req['endpoint'], json.dumps([req]), LOAD['total_requests'], LOAD['concurrency'], LOAD['warmup_requests'], LOAD['timeout_ms'], module_name)
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    for line in p.stdout.splitlines():
        if line.strip().startswith('{'):
            return json.loads(line.strip())
    raise RuntimeError('no output')


def main():
    # baseline (standalone module)
    for req in WORKLOAD:
        out = run_for_module('handlers_baseline', req)
        Path(OUT / f"baseline_{req['id']}.json").write_text(json.dumps(out, indent=2))

    # optimized (current handlers module)
    for req in WORKLOAD:
        out = run_for_module('handlers', req)
        Path(OUT / f"optimized_{req['id']}.json").write_text(json.dumps(out, indent=2))

    print('wrote per-endpoint summaries to artifacts/')


if __name__ == '__main__':
    main()
