import json
import time
import concurrent.futures
from flask import g
from app import app, db
from handlers import get_users, get_user_followers
import statistics
from sqlalchemy import event
import threading

class QueryCounter:
    def __init__(self):
        self.count = 0
        self.thread_id = threading.get_ident()
        self.listener = None

    def start(self):
        self.count = 0
        self.listener = lambda conn, clauseelement, multiparams, params: self.increment()
        event.listen(db.engine, 'before_execute', self.listener)

    def stop(self):
        if self.listener:
            event.remove(db.engine, 'before_execute', self.listener)
        count = self.count
        self.listener = None
        return count

    def increment(self):
        if threading.get_ident() == self.thread_id:
            self.count += 1

def run_request(req):
    counter = QueryCounter()
    with app.test_request_context(req['endpoint'] + '?' + '&'.join(f'{k}={v}' for k, v in req['query'].items()), headers={'Authorization': 'Bearer test-token'}):
        counter.start()
        start = time.time()
        try:
            if req['endpoint'] == '/api/users':
                response = get_users()
            elif req['endpoint'] == '/api/users/1/followers':
                response = get_user_followers(1)
            status = 200
            error = False
        except Exception as e:
            status = 500
            error = True
            response = None
        end = time.time()
        query_count = counter.stop()
        latency = (end - start) * 1000
        return latency, query_count, status, error

def run_workload(input_data, label):
    workload = input_data['workload']
    requests = workload['requests']
    load_profile = workload['load_profile']
    total_requests = load_profile['total_requests']
    concurrency = load_profile['concurrency']
    warmup_requests = load_profile['warmup_requests']
    timeout_ms = load_profile['timeout_ms']

    # seed if required
    if input_data['dataset']['seed']['required']:
        import subprocess
        subprocess.run(['python', 'seed_db.py'])

    # warmup
    for i in range(warmup_requests):
        req = requests[i % len(requests)]
        run_request(req)

    # run
    latencies = []
    query_counts = []
    statuses = []
    errors = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        for i in range(total_requests):
            req = requests[i % len(requests)]
            future = executor.submit(run_request, req)
            futures.append(future)
        for future in concurrent.futures.as_completed(futures):
            try:
                latency, qc, status, error = future.result()
                latencies.append(latency)
                query_counts.append(qc)
                statuses.append(status)
                if error:
                    errors += 1
            except concurrent.futures.TimeoutError:
                errors += 1
                latencies.append(timeout_ms)
                query_counts.append(0)
                statuses.append(504)

    # compute metrics
    latencies.sort()
    n = len(latencies)
    p50 = latencies[n // 2]
    p95 = latencies[int(n * 0.95)]
    p99 = latencies[int(n * 0.99)]
    error_rate = errors / total_requests * 100
    avg_query_count = statistics.mean(query_counts) if query_counts else 0

    # write artifacts
    with open(f'{label}_latency_summary.json', 'w') as f:
        json.dump({'p50': p50, 'p95': p95, 'p99': p99, 'error_rate': error_rate}, f)
    with open(f'{label}_query_count_per_request.json', 'w') as f:
        json.dump({'avg_query_count': avg_query_count}, f)
    with open(f'{label}_run_output_log.json', 'w') as f:
        json.dump({'latencies': latencies, 'query_counts': query_counts, 'statuses': statuses}, f)

    return p50, p95, p99, error_rate, avg_query_count

if __name__ == '__main__':
    with open('input.json') as f:
        input_data = json.load(f)

    # run baseline
    print("Running optimized")
    baseline_p50, baseline_p95, baseline_p99, baseline_error, baseline_qc = run_workload(input_data, 'optimized')

    print(f"Optimized: p50={baseline_p50}, p95={baseline_p95}, p99={baseline_p99}, error={baseline_error}, qc={baseline_qc}")

    # now, to run optimized, change code, then run again
    # but for now, assume we run optimized separately