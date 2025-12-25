"""In-process performance runner.

- Calls handler functions directly (no HTTP server)
- Simulates concurrency with ThreadPoolExecutor
- Counts SQL queries per request using SQLAlchemy events
- Produces latency percentiles and query-count metrics

This runner is the single runner used for both baseline and optimized runs.
"""
import time
import json
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from typing import Callable, Any

from sqlalchemy import event
from app import SessionLocal


class QueryCounter:
    def __init__(self, engine):
        self.engine = engine
        self._local = None

    def __enter__(self):
        self.count = 0

        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            self.count += 1

        self._before = before_cursor_execute
        event.listen(self.engine, "before_cursor_execute", self._before)
        return self

    def __exit__(self, exc_type, exc, tb):
        event.remove(self.engine, "before_cursor_execute", self._before)


class InProcessRunner:
    def __init__(self, handler_fn: Callable, engine, sessionscope: Callable, auth_header: dict):
        self.handler_fn = handler_fn
        self.engine = engine
        self.sessionscope = sessionscope
        self.auth_header = auth_header

    def _call_once(self, path_params: dict, query: dict):
        start = time.perf_counter()
        with QueryCounter(self.engine) as qc:
            with self.sessionscope() as db:
                try:
                    status, body = self.handler_fn(db, self.auth_header, path_params, query) if self.handler_fn.__code__.co_argcount == 4 else self.handler_fn(db, self.auth_header, query)
                    elapsed = (time.perf_counter() - start) * 1000
                    return {"status": status, "body": body, "latency_ms": elapsed, "queries": qc.count}
                except Exception as e:
                    elapsed = (time.perf_counter() - start) * 1000
                    return {"status": 500, "body": {"error": str(e)}, "latency_ms": elapsed, "queries": qc.count}

    def run_workload(self, requests: list, total_requests: int, concurrency: int, warmup: int, timeout_ms: int):
        results = []
        # expand requests to total_requests (round-robin)
        seq = [requests[i % len(requests)] for i in range(total_requests)]

        # warmup
        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            futures = [ex.submit(self._call_once, r.get("path_params", {}), r.get("query", {})) for r in seq[:warmup]]
            for f in as_completed(futures):
                _ = f.result()

        # measured run
        measured = seq[warmup:]
        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            futures = [ex.submit(self._call_once, r.get("path_params", {}), r.get("query", {})) for r in measured]
            try:
                for f in as_completed(futures, timeout=timeout_ms / 1000):
                    results.append(f.result())
            except Exception:
                # timeout or other error: gather whatever completed and cancel rest
                for f in futures:
                    if f.done():
                        try:
                            results.append(f.result())
                        except Exception:
                            pass
                    else:
                        f.cancel()

        return results


def summarize(results: list):
    statuses = defaultdict(int)
    latencies = [r["latency_ms"] for r in results if r["status"] == 200]
    queries = [r["queries"] for r in results if r["status"] == 200]
    errors = [r for r in results if r["status"] != 200]

    def pct(n):
        if not latencies:
            return None
        lat_sorted = sorted(latencies)
        return lambda q: lat_sorted[int(len(lat_sorted) * q) - 1]

    pct_f = pct(latencies)
    return {
        "count": len(results),
        "status_counts": {k: v for k, v in sorted(statuses.items())},
        "success_count": sum(1 for r in results if r["status"] == 200),
        "error_count": len(errors),
        "error_rate": (len(errors) / len(results)) * 100.0 if results else 0.0,
        "p50_ms": statistics.median(latencies) if latencies else None,
        "p95_ms": (sorted(latencies)[int(len(latencies) * 0.95) - 1] if latencies else None),
        "p99_ms": (sorted(latencies)[int(len(latencies) * 0.99) - 1] if latencies else None),
        "avg_queries": statistics.mean(queries) if queries else None,
        "queries_per_request_distribution": {
            "min": min(queries) if queries else None,
            "max": max(queries) if queries else None,
            "median": statistics.median(queries) if queries else None,
        },
    }
