#!/usr/bin/env python3
"""setup_app.R clones the requested repo and reports a baseline check.

Uses a local file:// repo so the test needs no network and no GITHUB_TOKEN.
"""

import json
import re
import sys
from pathlib import Path

import harness

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "setup-app.input.json"

DOCUMENTED_KEYS = {
    "appRepoUrl", "appName", "baseBranch", "baseCommit", "appDir",
    "renvRestored", "renvDetail", "renvLog", "boots", "bootDetail", "bootLog",
    "testsRun", "testsPassed", "testDetail", "baselinePassed",
}


def run():
    if not harness.r_packages_available("jsonlite", "shiny"):
        return harness.SKIP, "needs R packages jsonlite + shiny"

    scratch = harness.make_scratch()
    try:
        harness.install_scripts(scratch)
        app_repo = harness.make_app_repo(scratch / "source" / "my-shiny-app")

        payload = json.loads(FIXTURE.read_text())
        payload["steps"]["capture-request"]["appRepoUrl"] = f"file://{app_repo}"
        harness.write_input(scratch, payload)

        completed = harness.run_script(scratch, "setup_app.R")
        if completed.returncode != 0:
            return harness.FAIL, f"setup_app.R exited {completed.returncode}: {completed.stderr[-800:]}"

        result = harness.read_result(scratch)

        missing = DOCUMENTED_KEYS - result.keys()
        if missing:
            return harness.FAIL, f"result.json missing documented keys: {sorted(missing)}"
        if result["appName"] != "my-shiny-app":
            return harness.FAIL, f"appName was {result['appName']!r}, expected 'my-shiny-app'"
        if not re.fullmatch(r"[0-9a-f]{40}", result["baseCommit"] or ""):
            return harness.FAIL, f"baseCommit is not a sha: {result['baseCommit']!r}"
        if result["renvRestored"] is not False:
            return harness.FAIL, "renvRestored should be False when there is no renv.lock"
        if not (scratch / "workspace" / "app" / "app.R").exists():
            return harness.FAIL, "app.R was not cloned into the workspace"
        if result["boots"] is not True:
            return harness.FAIL, f"fixture app did not boot: {result['bootDetail']} :: {result['bootLog'][-500:]}"
        if result["baselinePassed"] is not True:
            return harness.FAIL, f"baselinePassed was False: {result['testDetail']}"

        return harness.PASS, f"cloned, baseline boots, appName={result['appName']}"
    finally:
        harness.cleanup(scratch)


if __name__ == "__main__":
    status, detail = run()
    print(detail)
    sys.exit(status)
