#!/usr/bin/env python3
"""Run every script test in this directory.

Tests whose prerequisites are absent SKIP rather than fail, so this is safe to
run on a machine without R packages or Posit Connect credentials.

    python tests/run_tests.py
"""

import importlib.util
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
LABEL = {0: "PASS", 1: "FAIL", 2: "SKIP"}


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    sys.path.insert(0, str(TESTS_DIR))
    counts = {0: 0, 1: 0, 2: 0}

    for path in sorted(TESTS_DIR.glob("test_*.py")):
        try:
            status, detail = load(path).run()
        except Exception as err:  # a broken test is a failure, not a crash
            status, detail = 1, f"test raised {type(err).__name__}: {err}"
        counts[status] += 1
        print(f"{LABEL[status]:5} {path.stem:22} {detail}")

    print(f"\n{counts[0]} passed, {counts[2]} skipped, {counts[1]} failed")
    return 1 if counts[1] else 0


if __name__ == "__main__":
    sys.exit(main())
