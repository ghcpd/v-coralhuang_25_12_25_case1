"""
Orchestration script required by the challenge. Performs:
 - read input.json
 - seed the DB
 - run baseline workload (in-process)
 - apply code + schema optimization (handlers + index)
 - run optimized workload
 - produce REVIEW_SUMMARY.md and save run logs

Usage: python run_tests.py
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent


def run(cmd, **kwargs):
    print(f"> {cmd}")
    res = subprocess.run(cmd, shell=True, check=False, capture_output=True, text=True, **kwargs)
    print(res.stdout)
    if res.stderr:
        print(res.stderr)
    return res


def main():
    with open(ROOT / 'input.json') as fh:
        cfg = json.load(fh)

    # 1) seed
    print('=== Seeding DB ===')
    res = run(f"{sys.executable} seed_db.py")
    if res.returncode != 0:
        print('Seeding failed')
        sys.exit(1)

    # 2) baseline run
    print('\n=== Baseline run ===')
    res = run(f"{sys.executable} runner.py --label baseline")
    (ROOT / 'run_output_baseline.log').write_text(res.stdout + '\n' + res.stderr)
    if res.returncode != 0:
        print('Baseline run failed')
        sys.exit(1)

    # 3) Apply code optimization: replace handlers.py with handlers_optimized.py
    print('\n=== Applying code changes (optimized handlers + index) ===')
    shutil.copyfile(ROOT / 'handlers_optimized.py', ROOT / 'handlers.py')

    # 4) Update app.py to add composite index for followers (non-destructive)
    #    (we modify the source so the repository contains the optimization)
    app_src = (ROOT / 'app.py').read_text()
    old = "__table_args__ = ()"
    new = "__table_args__ = (\n        Index('ix_followers_user_follower', 'user_id', 'follower_id'),\n    )"
    if old in app_src:
        (ROOT / 'app.py').write_text(app_src.replace(old, new))
        print('app.py updated with composite index')
    else:
        print('app.py already updated')

    # 5) apply migration (create index)
    res = run(f"{sys.executable} apply_migration.py")
    if res.returncode != 0:
        print('Migration failed')
        sys.exit(1)

    # 6) optimized run
    print('\n=== Optimized run ===')
    res = run(f"{sys.executable} runner.py --label optimized")
    (ROOT / 'run_output_optimized.log').write_text(res.stdout + '\n' + res.stderr)
    if res.returncode != 0:
        print('Optimized run failed')
        sys.exit(1)

    print('\nAll runs complete. Metrics are in metrics_baseline.json and metrics_optimized.json')


if __name__ == '__main__':
    main()
