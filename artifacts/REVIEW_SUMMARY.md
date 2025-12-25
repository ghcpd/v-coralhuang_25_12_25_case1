# REVIEW SUMMARY

{
  "baseline": {
    "list_users": {
      "p50_ms": 1367.9620500001874,
      "p95_ms": 1445.69010000032,
      "p99_ms": 1469.6216000002096,
      "avg_queries": 4963.16,
      "sla_pass": false
    },
    "followers_page": {
      "p50_ms": 30.952049999541487,
      "p95_ms": 53.67070000011154,
      "p99_ms": 63.996799999586074,
      "avg_queries": 75.9,
      "sla_pass": true
    }
  },
  "optimized": {
    "list_users": {
      "p50_ms": 104.84979999955613,
      "p95_ms": 136.18809999934456,
      "p99_ms": 185.5027000001428,
      "avg_queries": 97.84222222222222,
      "sla_pass": true
    },
    "followers_page": {
      "p50_ms": 28.046200000062527,
      "p95_ms": 47.793100000490085,
      "p99_ms": 58.79370000002382,
      "avg_queries": 73.85166666666667,
      "sla_pass": true
    }
  }
}