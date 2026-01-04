#!/usr/bin/env python
"""
run_tests - Executes the full baseline vs optimized performance comparison.
Reads input.json, seeds the database, and runs both workloads.
"""
import json
import subprocess
import sys

def main():
    print("API Performance Optimization Test Suite")
    print("=" * 60)
    
    # Read input file
    print("\n[1] Reading input configuration...")
    try:
        with open("input.json", "r") as f:
            config = json.load(f)
        print("[OK] Configuration loaded")
    except FileNotFoundError:
        print("[ERROR] input.json not found")
        sys.exit(1)
    
    # Seed database
    print("\n[2] Seeding database...")
    try:
        result = subprocess.run([sys.executable, "seed_db.py"], check=True, capture_output=False)
        print("[OK] Database seeded")
    except subprocess.CalledProcessError:
        print("[ERROR] Database seeding failed")
        sys.exit(1)
    
    # Run performance tests
    print("\n[3] Running performance tests...")
    try:
        result = subprocess.run([sys.executable, "runner.py"], check=True, capture_output=False)
        print("[OK] Performance tests completed")
    except subprocess.CalledProcessError:
        print("[ERROR] Performance tests failed")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("All tests completed successfully!")
    print("Results saved to: results.json")

if __name__ == "__main__":
    main()
