"""In-process performance runner that exercises handlers with concurrent load.
Produces latency percentiles, error rates, status distribution, and query counts.
"""
import time
import statistics
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict, Counter as PyCounter
import json

from app import config, current_request_id, reset_query_counts, get_query_count_for_request
import handlers


class InProcessRunner:
    def __init__(self, input_file="input.json"):
        with open(input_file) as f:
            self.spec = json.load(f)
        self.requests = self.spec["workload"]["requests"]
        self.load_profile = self.spec["workload"]["load_profile"]
        self.auth_token = self.spec["environment"]["auth"]["token"]

    def _make_request(self, req_spec):
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        return {
            "method": req_spec["method"],
            "path": req_spec["endpoint"],
            "query": req_spec.get("query", {}),
            "headers": headers,
        }

    def _dispatch(self, req_spec):
        req = self._make_request(req_spec)
        # set request id for SQL query counting
        req_id = str(uuid.uuid4())
        token = current_request_id.set(req_id)
        start = time.perf_counter()
        try:
            if req_spec["endpoint"].startswith("/api/users/") and "/followers" in req_spec["endpoint"]:
                # extract user id
                parts = req_spec["endpoint"].split("/")
                user_id = parts[3]
                status, body = handlers.get_user_followers(req, user_id)
            else:
                status, body = handlers.get_users(req)
        except Exception as e:
            status = 500
            body = {"error": str(e)}
        finally:
            elapsed = (time.perf_counter() - start) * 1000.0
            current_request_id.reset(token)
        queries = get_query_count_for_request(req_id)
        return {"status": status, "time_ms": elapsed, "queries": queries, "body": body}

    def _run_series(self, target_request_spec, total_requests, concurrency, warmup):
        # warmup
        for _ in range(warmup):
            self._dispatch(target_request_spec)

        results = []
        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            futures = [ex.submit(self._dispatch, target_request_spec) for _ in range(total_requests)]
            for f in as_completed(futures):
                results.append(f.result())
        return results

    def run(self, optimized=False):
        config["OPTIMIZED"] = optimized
        overall = {}
        # We'll run each request definition separately and collect metrics
        for req_spec in self.requests:
            label = req_spec["id"]
            total_requests = self.load_profile["total_requests"]
            concurrency = self.load_profile["concurrency"]
            warmup = self.load_profile.get("warmup_requests", 0)

            reset_query_counts()
            results = self._run_series(req_spec, total_requests, concurrency, warmup)

            times = [r["time_ms"] for r in results]
            statuses = [r["status"] for r in results]
            errors = [1 for s in statuses if s != self.spec["metrics"]["expected_status"]]
            qcounts = [r["queries"] for r in results]

            stats = {
                "p50": statistics.quantiles(times, n=100)[49] if len(times) >= 100 else statistics.median(times),
                "p95": statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times),
                "p99": max(times),
                "error_rate": sum(errors) / len(statuses) if statuses else 0,
                "status_counts": dict(PyCounter(statuses)),
                "avg_queries": sum(qcounts) / len(qcounts) if qcounts else 0,
            }
            overall[label] = {"raw_results": results, "stats": stats}
        return overall


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--optimized", action="store_true")
    args = parser.parse_args()

    runner = InProcessRunner()
    res = runner.run(optimized=args.optimized)
    print(json.dumps({k: v["stats"] for k, v in res.items()}, indent=2))
