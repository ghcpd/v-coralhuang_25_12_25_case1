"""
In-process performance runner.
- Reads `input.json` for workload and environment
- Calls handler functions in-process (no HTTP server)
- Measures latency percentiles and SQL query counts per request using SQLAlchemy events
- Writes JSON metrics to disk and prints a short summary

Usage: python runner.py --label baseline
The runner is intentionally framework-free and reproducible.
"""
import json
import time
import threading
from statistics import mean
from concurrent.futures import ThreadPoolExecutor, as_completed
import importlib
import argparse

from sqlalchemy import event
from app import engine

# thread-local storage used by SQLAlchemy event handler to count queries per thread
_thread_state = threading.local()


def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    if getattr(_thread_state, 'counting', False):
        _thread_state.query_count = getattr(_thread_state, 'query_count', 0) + 1


# attach once
event.listen(engine, 'before_cursor_execute', _before_cursor_execute)


class SimpleRequest:
    def __init__(self, method, path, query=None, headers=None):
        self.method = method
        self.path = path
        self.query = query or {}
        self.headers = headers or {}


def _call_handler(func, request, timeout_s):
    # enable counting for this thread
    _thread_state.counting = True
    _thread_state.query_count = 0
    start = time.perf_counter()
    try:
        status, body = func(request)
        duration = (time.perf_counter() - start) * 1000.0
        qc = _thread_state.query_count
        return {
            'success': True,
            'status': status,
            'body': body,
            'latency_ms': duration,
            'query_count': qc,
            'error': None
        }
    except Exception as e:
        duration = (time.perf_counter() - start) * 1000.0
        qc = _thread_state.query_count
        return {
            'success': False,
            'status': None,
            'body': None,
            'latency_ms': duration,
            'query_count': qc,
            'error': str(e)
        }
    finally:
        _thread_state.counting = False


def run_workload(config, handlers_module, label):
    workload = config['workload']
    total_requests = workload['load_profile']['total_requests']
    concurrency = workload['load_profile']['concurrency']
    warmup = workload['load_profile']['warmup_requests']
    timeout_ms = workload['load_profile'].get('timeout_ms', 5000)

    # prepare requests: distribute total_requests equally among defined requests
    requests_def = workload['requests']
    per_type = max(1, total_requests // len(requests_def))
    prepared = []
    for rdef in requests_def:
        for _ in range(per_type):
            prepared.append(rdef)

    print(f"[{label}] Warmup: {warmup} requests")
    # warmup (run sequentially)
    for i in range(warmup):
        rdef = requests_def[i % len(requests_def)]
        func_name = config['entrypoints']['handler_map'][f"{rdef['method']} {rdef['endpoint']}"]
        module_name, fn_name = func_name.rsplit('.', 1)
        handler_func = getattr(handlers_module, fn_name)
        req = SimpleRequest(rdef['method'], rdef['endpoint'], rdef.get('query', {}), headers={'Authorization': 'Bearer test-token'})
        _call_handler(handler_func, req, timeout_ms/1000.0)

    print(f"[{label}] Running {len(prepared)} requests with concurrency={concurrency}")
    results = []
    # map endpoint->list of result dicts
    per_endpoint_results = {r['id']: [] for r in requests_def}

    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = []
        for rdef in prepared:
            func_name = config['entrypoints']['handler_map'][f"{rdef['method']} {rdef['endpoint']}"]
            module_name, fn_name = func_name.rsplit('.', 1)
            handler_func = getattr(handlers_module, fn_name)
            req = SimpleRequest(rdef['method'], rdef['endpoint'], rdef.get('query', {}), headers={'Authorization': 'Bearer test-token'})
            futures.append(ex.submit(_call_handler, handler_func, req, timeout_ms/1000.0))

        # collect
        i = 0
        for fut in as_completed(futures):
            res = fut.result()
            rid = requests_def[i % len(requests_def)]['id']
            per_endpoint_results[rid].append(res)
            results.append(res)
            i += 1

    # compute metrics
    def summarize(list_of_res):
        latencies = [r['latency_ms'] for r in list_of_res if r['success']]
        statuses = {}
        for r in list_of_res:
            k = r['status'] if r['status'] is not None else 'ERR'
            statuses[k] = statuses.get(k, 0) + 1
        query_counts = [r['query_count'] for r in list_of_res]
        errors = [r for r in list_of_res if not r['success']]
        total = len(list_of_res)
        error_rate = len(errors) / total if total else 0.0
        lat_sorted = sorted(latencies)
        def pct(p):
            if not lat_sorted:
                return None
            idx = max(0, min(len(lat_sorted)-1, int(len(lat_sorted)*p/100)))
            return lat_sorted[idx]
        return {
            'count': total,
            'error_rate': error_rate,
            'status_distribution': statuses,
            'p50_ms': pct(50),
            'p95_ms': pct(95),
            'p99_ms': pct(99),
            'avg_query_count': mean(query_counts) if query_counts else 0,
            'raw': list_of_res
        }

    summary = {rid: summarize(reslist) for rid, reslist in per_endpoint_results.items()}

    # write artifacts
    out = {
        'label': label,
        'summary': summary,
        'config': config
    }
    out_path = f"metrics_{label}.json"
    with open(out_path, 'w') as f:
        json.dump(out, f, indent=2)

    print(f"[{label}] Results written to {out_path}")
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', choices=['baseline', 'optimized'], required=True)
    args = parser.parse_args()

    with open('input.json') as fh:
        config = json.load(fh)

    # import handlers module dynamically (the file `handlers.py` will be swapped for optimized run)
    handlers = importlib.import_module('handlers')

    out = run_workload(config, handlers, args.label)
    print(json.dumps(out['summary'], indent=2))
