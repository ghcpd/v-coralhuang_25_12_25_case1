"""
In-process performance runner for API optimization testing.
Simulates concurrent load by directly invoking handler code without HTTP server.
"""
import json
import time
import concurrent.futures
import statistics
from typing import Dict, List, Tuple
import sys
import importlib

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class PerformanceRunner:
    def __init__(self, input_file: str, use_optimized: bool = False):
        self.config = self._load_input(input_file)
        self.results = {}
        self.use_optimized = use_optimized
        self._setup_app()
    def _setup_app(self):
        """Dynamically load baseline or optimized app"""
        if self.use_optimized:
            # Import optimized version (app.py with fixes)
            self.app_module = importlib.import_module("app")
        else:
            # Import baseline version (baseline_app.py with bottlenecks)
            self.app_module = importlib.import_module("baseline_app")
        
        self.app = self.app_module.app
        self.query_counter = self.app_module.query_counter
        
        # Setup query listener
        with self.app.app_context():
            self.app_module.setup_query_listener()
    
    def _load_input(self, file_path: str) -> dict:
        """Load and parse the input configuration file"""
        with open(file_path, "r") as f:
            return json.load(f)
    
    def _execute_request(self, method: str, endpoint: str, query_params: dict) -> Tuple[int, float, int]:
        """
        Execute a single request in-process using Flask test client.
        Returns: (status_code, latency_ms, query_count)
        """
        self.query_counter.reset()
        
        with self.app.test_client() as client:
            start_time = time.perf_counter()
            
            # Add authorization header
            headers = {
                "Authorization": f"Bearer {self.config['environment']['auth']['token']}"
            }
            
            if method == "GET":
                response = client.get(
                    endpoint,
                    query_string=query_params,
                    headers=headers
                )
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            elapsed = (time.perf_counter() - start_time) * 1000  # Convert to ms
            query_count = self.query_counter.count
            
            return response.status_code, elapsed, query_count
    
    def _run_workload(self, label: str) -> Dict:
        """
        Execute the full workload with concurrency simulation.
        Returns metrics: latency stats, error rate, query counts.
        """
        print(f"\n{'='*60}")
        print(f"Running workload: {label}")
        print(f"{'='*60}")
        
        workload_cfg = self.config["workload"]
        requests_cfg = workload_cfg["requests"]
        load_profile = workload_cfg["load_profile"]
        
        total_requests = load_profile["total_requests"]
        concurrency = load_profile["concurrency"]
        warmup_requests = load_profile["warmup_requests"]
        timeout_ms = load_profile["timeout_ms"]
        
        # Warmup phase
        print(f"\nWarmup phase: {warmup_requests} requests...")
        for i in range(warmup_requests):
            req_cfg = requests_cfg[i % len(requests_cfg)]
            try:
                self._execute_request(
                    req_cfg["method"],
                    req_cfg["endpoint"],
                    req_cfg["query"]
                )
            except Exception as e:
                print(f"  Warmup error: {e}")
        
        print(f"[OK] Warmup complete\n")
        
        # Main workload phase
        print(f"Main phase: {total_requests} requests with {concurrency} concurrent workers...")
        
        latencies = []  # All latencies in ms
        errors = []
        status_codes = {}
        query_counts_by_endpoint = {}  # Aggregate query counts per endpoint
        
        def execute_single_request(req_idx):
            req_cfg = requests_cfg[req_idx % len(requests_cfg)]
            endpoint = req_cfg["endpoint"]
            
            try:
                status, latency, query_count = self._execute_request(
                    req_cfg["method"],
                    endpoint,
                    req_cfg["query"]
                )
                
                return {
                    "success": True,
                    "status": status,
                    "latency": latency,
                    "query_count": query_count,
                    "endpoint": endpoint
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "endpoint": endpoint
                }
        
        # Execute with ThreadPoolExecutor for concurrency simulation
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [
                executor.submit(execute_single_request, i)
                for i in range(total_requests)
            ]
            
            completed = 0
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                completed += 1
                
                if completed % 200 == 0:
                    print(f"  ... {completed}/{total_requests} requests")
                
                if result["success"]:
                    latencies.append(result["latency"])
                    status = result["status"]
                    status_codes[status] = status_codes.get(status, 0) + 1
                    
                    endpoint = result["endpoint"]
                    if endpoint not in query_counts_by_endpoint:
                        query_counts_by_endpoint[endpoint] = []
                    query_counts_by_endpoint[endpoint].append(result["query_count"])
                else:
                    errors.append(result["error"])
        
        print(f"[OK] Main phase complete\n")
        
        # Calculate statistics
        if latencies:
            p50 = statistics.quantiles(latencies, n=100)[49] if len(latencies) > 50 else min(latencies)
            p95 = statistics.quantiles(latencies, n=100)[94] if len(latencies) > 95 else max(latencies)
            p99 = statistics.quantiles(latencies, n=100)[98] if len(latencies) > 99 else max(latencies)
            mean_latency = statistics.mean(latencies)
            median_latency = statistics.median(latencies)
        else:
            p50 = p95 = p99 = mean_latency = median_latency = 0
        
        error_rate = (len(errors) / total_requests) * 100 if total_requests > 0 else 0
        
        # Compute average queries per request per endpoint
        avg_queries_per_endpoint = {}
        for endpoint, counts in query_counts_by_endpoint.items():
            avg_queries_per_endpoint[endpoint] = statistics.mean(counts) if counts else 0
        
        results = {
            "label": label,
            "total_requests": total_requests,
            "successful_requests": len(latencies),
            "failed_requests": len(errors),
            "error_rate_percent": error_rate,
            "status_code_distribution": status_codes,
            "latency_stats": {
                "p50_ms": round(p50, 2),
                "p95_ms": round(p95, 2),
                "p99_ms": round(p99, 2),
                "mean_ms": round(mean_latency, 2),
                "median_ms": round(median_latency, 2),
                "min_ms": round(min(latencies), 2) if latencies else 0,
                "max_ms": round(max(latencies), 2) if latencies else 0,
            },
            "query_counts_by_endpoint": {
                endpoint: {
                    "total": sum(counts),
                    "per_request_avg": round(avg, 2),
                    "per_request_count": counts
                }
                for endpoint, avg in avg_queries_per_endpoint.items()
            }
        }
        
        # Print results
        print("\nResults:")
        print(f"  Total requests: {results['total_requests']}")
        print(f"  Successful: {results['successful_requests']}")
        print(f"  Failed: {results['failed_requests']}")
        print(f"  Error rate: {results['error_rate_percent']:.2f}%")
        print(f"\n  Latency percentiles:")
        print(f"    p50: {results['latency_stats']['p50_ms']} ms")
        print(f"    p95: {results['latency_stats']['p95_ms']} ms")
        print(f"    p99: {results['latency_stats']['p99_ms']} ms")
        print(f"    mean: {results['latency_stats']['mean_ms']} ms")
        print(f"\n  Queries per endpoint:")
        for endpoint, stats in results['query_counts_by_endpoint'].items():
            print(f"    {endpoint}: {stats['per_request_avg']} avg queries/request")
        
        return results
    
    def run_baseline(self) -> Dict:
        """Run baseline workload"""
        return self._run_workload("baseline")
    
    def run_optimized(self) -> Dict:
        """Run optimized workload"""
        return self._run_workload("optimized")
    
    def compare_results(self, baseline: Dict, optimized: Dict) -> Dict:
        """Compare baseline and optimized results"""
        print(f"\n{'='*60}")
        print("COMPARISON: Baseline vs Optimized")
        print(f"{'='*60}\n")
        
        baseline_p95 = baseline["latency_stats"]["p95_ms"]
        optimized_p95 = optimized["latency_stats"]["p95_ms"]
        p95_improvement = ((baseline_p95 - optimized_p95) / baseline_p95 * 100) if baseline_p95 > 0 else 0
        
        baseline_p99 = baseline["latency_stats"]["p99_ms"]
        optimized_p99 = optimized["latency_stats"]["p99_ms"]
        p99_improvement = ((baseline_p99 - optimized_p99) / baseline_p99 * 100) if baseline_p99 > 0 else 0
        
        print("Latency comparison:")
        print(f"  p50: {baseline['latency_stats']['p50_ms']} -> {optimized['latency_stats']['p50_ms']} ms")
        print(f"  p95: {baseline_p95} -> {optimized_p95} ms ({p95_improvement:+.1f}%)")
        print(f"  p99: {baseline_p99} -> {optimized_p99} ms ({p99_improvement:+.1f}%)")
        
        print("\nQuery count comparison (avg per request):")
        all_endpoints = set(list(baseline["query_counts_by_endpoint"].keys()) + list(optimized["query_counts_by_endpoint"].keys()))
        for endpoint in sorted(all_endpoints):
            baseline_qc = baseline["query_counts_by_endpoint"].get(endpoint, {}).get("per_request_avg", 0)
            optimized_qc = optimized["query_counts_by_endpoint"].get(endpoint, {}).get("per_request_avg", 0)
            improvement = ((baseline_qc - optimized_qc) / baseline_qc * 100) if baseline_qc > 0 else 0
            print(f"  {endpoint}: {baseline_qc} -> {optimized_qc} ({improvement:+.1f}%)")
        
        return {
            "baseline": baseline,
            "optimized": optimized,
            "p95_improvement_percent": round(p95_improvement, 2),
            "p99_improvement_percent": round(p99_improvement, 2)
        }
    
    def save_results(self, comparison: Dict, output_file: str = "results.json"):
        """Save results to file"""
        with open(output_file, "w") as f:
            json.dump(comparison, f, indent=2)
        print(f"\n[OK] Results saved to {output_file}")

def main():
    """Main execution"""
    # Run baseline with bottlenecks
    print("\n" + "="*60)
    print("RUNNING BASELINE (with known bottlenecks)")
    print("="*60)
    runner_baseline = PerformanceRunner("input.json", use_optimized=False)
    baseline_results = runner_baseline.run_baseline()
    
    # Run optimized version
    print("\n" + "="*60)
    print("RUNNING OPTIMIZED (with fixes)")
    print("="*60)
    runner_optimized = PerformanceRunner("input.json", use_optimized=True)
    optimized_results = runner_optimized.run_optimized()
    
    comparison = runner_baseline.compare_results(baseline_results, optimized_results)
    runner_baseline.save_results(comparison)

if __name__ == "__main__":
    main()
