#!/usr/bin/env python3
"""deploy_connect.R publishes the app to Posit Connect.

This test PUBLISHES CONTENT to whatever Connect instance the credentials point
at, so credential presence alone is not enough to run it — it also requires an
explicit MEDIFORCE_ALLOW_CONNECT_DEPLOY_TEST=1 opt-in. Running the suite must
never touch a real Connect by accident. It deploys the minimal fixture app
under its own content name, not any real application.
"""

import json
import os
import sys
from pathlib import Path

import harness

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "verify-change.input.json"

DOCUMENTED_KEYS = {"deployed", "appName", "appDir", "connectServer", "contentUrl"}


def run():
    if not harness.r_packages_available("jsonlite", "rsconnect"):
        return harness.SKIP, "needs R packages jsonlite + rsconnect"
    if not (os.environ.get("CONNECT_SERVER") and os.environ.get("CONNECT_API_KEY")):
        return harness.SKIP, "needs CONNECT_SERVER + CONNECT_API_KEY"
    if os.environ.get("MEDIFORCE_ALLOW_CONNECT_DEPLOY_TEST") != "1":
        return harness.SKIP, "publishes to a real Connect — set MEDIFORCE_ALLOW_CONNECT_DEPLOY_TEST=1 to run"

    scratch = harness.make_scratch()
    try:
        harness.install_scripts(scratch)
        harness.make_app_repo(scratch / "workspace" / "app")

        payload = json.loads(FIXTURE.read_text())
        payload["steps"]["setup-app"]["appName"] = "mediforce-deploy-smoke-test"
        harness.write_input(scratch, payload)

        completed = harness.run_script(scratch, "deploy_connect.R")
        if completed.returncode != 0:
            return harness.FAIL, f"deploy_connect.R exited {completed.returncode}: {completed.stderr[-800:]}"

        result = harness.read_result(scratch)
        missing = DOCUMENTED_KEYS - result.keys()
        if missing:
            return harness.FAIL, f"result.json missing documented keys: {sorted(missing)}"
        if result["deployed"] is not True:
            return harness.FAIL, "deployed was not True"

        return harness.PASS, f"deployed to {result['contentUrl']}"
    finally:
        harness.cleanup(scratch)


if __name__ == "__main__":
    status, detail = run()
    print(detail)
    sys.exit(status)
