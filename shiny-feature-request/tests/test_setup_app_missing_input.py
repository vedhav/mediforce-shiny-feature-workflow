#!/usr/bin/env python3
"""setup_app.R must fail loudly when the request values did not reach it.

Regression test. The first version of this script read the request from
`triggerPayload` in /output/input.json — a key the platform never puts there,
because a run's trigger payload is a separate field and only `steps` reaches the
container. Every run failed with "appRepoUrl is required on the trigger
payload". These cases pin the contract: values come from
steps["capture-request"], and their absence is a hard error rather than a clone
of the empty string.
"""

import json
import sys

import harness

CASES = {
    "no steps at all": {},
    "capture-request missing": {"steps": {}},
    "appRepoUrl empty": {"steps": {"capture-request": {"appRepoUrl": "", "baseBranch": "main"}}},
    "old triggerPayload shape": {
        "triggerPayload": {"appRepoUrl": "file:///nope", "baseBranch": "main"},
        "steps": {},
    },
}


def run():
    if not harness.r_packages_available("jsonlite"):
        return harness.SKIP, "needs R package jsonlite"

    for label, payload in CASES.items():
        scratch = harness.make_scratch()
        try:
            harness.install_scripts(scratch)
            harness.write_input(scratch, payload)
            completed = harness.run_script(scratch, "setup_app.R")

            if completed.returncode == 0:
                return harness.FAIL, f"{label}: exited 0, should have failed"
            if "appRepoUrl is empty" not in completed.stderr:
                return harness.FAIL, f"{label}: wrong error: {completed.stderr[-300:]}"
            if (scratch / "workspace" / "app").exists():
                return harness.FAIL, f"{label}: cloned something despite missing input"
        finally:
            harness.cleanup(scratch)

    return harness.PASS, f"{len(CASES)} malformed inputs each fail loudly with no clone"


if __name__ == "__main__":
    status, detail = run()
    print(detail)
    sys.exit(status)
