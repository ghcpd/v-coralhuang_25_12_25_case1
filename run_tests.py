"""Run baseline and optimized workloads, seed DB if required, and record artifacts."""
import json
import subprocess
import os
from seed_db import seed
from runner import InProcessRunner

WORKDIR = os.path.dirname(__file__)

def main(input_file="input.json"):
    with open(input_file) as f:
        spec = json.load(f)

    # seed if required
    if spec.get("dataset", {}).get("seed", {}).get("required", False):
        print("Seeding database...")
        seed()

    runner = InProcessRunner(input_file)

    print("Running baseline (optimized=False)...")
    baseline = runner.run(optimized=False)
    with open("baseline_results.json", "w") as f:
        json.dump({k: v["stats"] for k, v in baseline.items()}, f, indent=2)

    # ensure counters cache is loaded before optimized run
    print("Loading counters cache for optimized run...")
    import app as _app
    _app.load_counters_from_db()

    print("Running optimized (optimized=True)...")
    optimized = runner.run(optimized=True)
    with open("optimized_results.json", "w") as f:
        json.dump({k: v["stats"] for k, v in optimized.items()}, f, indent=2)

    # write run log
    with open("run_output_log.txt", "w") as f:
        f.write("BASELINE\n")
        f.write(json.dumps({k: v["stats"] for k, v in baseline.items()}, indent=2))
        f.write("\n\nOPTIMIZED\n")
        f.write(json.dumps({k: v["stats"] for k, v in optimized.items()}, indent=2))

    print("Done. Artifacts: baseline_results.json, optimized_results.json, run_output_log.txt")

if __name__ == "__main__":
    main()
