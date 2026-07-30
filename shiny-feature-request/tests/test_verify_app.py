#!/usr/bin/env python3
"""verify_app.R re-checks the modified app and lists the files that changed.

Builds the state setup-app would have left behind — a git clone at
<scratch>/workspace/app — then adds a commit on top, as the agent step would.
"""

import json
import subprocess
import sys
from pathlib import Path

import harness

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "verify-change.input.json"

DOCUMENTED_KEYS = {
    "appDir", "headCommit", "changedFiles", "changedFileCount",
    "boots", "bootDetail", "bootLog", "testsRun", "testsPassed",
    "testDetail", "passed",
}

CHANGED_APP = harness.MINIMAL_APP.replace(
    'output$greeting <- renderText("hello from the fixture app")',
    'output$greeting <- renderText(paste("hello from the fixture app", "v2"))',
)


def run():
    if not harness.r_packages_available("jsonlite", "shiny"):
        return harness.SKIP, "needs R packages jsonlite + shiny"

    scratch = harness.make_scratch()
    try:
        harness.install_scripts(scratch)

        app = harness.make_app_repo(scratch / "workspace" / "app")
        base_commit = subprocess.run(
            ["git", "-C", str(app), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()

        # Stand in for the agent step's commit.
        (app / "app.R").write_text(CHANGED_APP)
        harness.git(app, "add", "-A")
        harness.git(app, "commit", "-m", "feat: bump greeting")

        payload = json.loads(FIXTURE.read_text())
        payload["steps"]["setup-app"]["baseCommit"] = base_commit
        harness.write_input(scratch, payload)

        completed = harness.run_script(scratch, "verify_app.R")
        if completed.returncode != 0:
            return harness.FAIL, f"verify_app.R exited {completed.returncode}: {completed.stderr[-800:]}"

        result = harness.read_result(scratch)

        missing = DOCUMENTED_KEYS - result.keys()
        if missing:
            return harness.FAIL, f"result.json missing documented keys: {sorted(missing)}"
        if result["changedFiles"] != ["app.R"]:
            return harness.FAIL, f"changedFiles was {result['changedFiles']!r}, expected ['app.R']"
        if result["changedFileCount"] != 1:
            return harness.FAIL, f"changedFileCount was {result['changedFileCount']}, expected 1"
        if result["boots"] is not True:
            return harness.FAIL, f"changed app did not boot: {result['bootDetail']} :: {result['bootLog'][-500:]}"
        if result["passed"] is not True:
            return harness.FAIL, f"passed was False: {result['testDetail']}"

        return harness.PASS, "diff detected against baseCommit, changed app boots"
    finally:
        harness.cleanup(scratch)


if __name__ == "__main__":
    status, detail = run()
    print(detail)
    sys.exit(status)
