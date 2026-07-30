#!/usr/bin/env python3
"""A failed renv::restore() must produce a diagnosable error.

Regression test. The first version called renv::restore() directly, so a failure
surfaced only its last line — for a 100-package lock that is a list of every
package name and no cause, which is exactly what made the Rhino-app failure
impossible to diagnose from the run page. restore_deps now runs renv in a
subprocess and, on failure, reports the resolved repos, the
RENV_CONFIG_REPOS_OVERRIDE value, and the tail of the transcript.
"""

import json
import sys

import harness

BOGUS_LOCK = {
    "R": {
        "Version": "4.4.0",
        "Repositories": [{"Name": "CRAN", "URL": "https://cloud.r-project.org"}],
    },
    "Packages": {
        "mediforceDefinitelyNotARealPackage9999": {
            "Package": "mediforceDefinitelyNotARealPackage9999",
            "Version": "1.0.0",
            "Source": "Repository",
            "Repository": "CRAN",
        }
    },
}

REQUIRED_MARKERS = [
    "renv::restore() failed",
    "packages in renv.lock",
    "Repos R resolved to",
    "RENV_CONFIG_REPOS_OVERRIDE",
]


def run():
    if not harness.r_packages_available("jsonlite", "renv"):
        return harness.SKIP, "needs R packages jsonlite + renv"

    scratch = harness.make_scratch()
    try:
        harness.install_scripts(scratch)
        app_repo = harness.make_app_repo(scratch / "source" / "broken-app")
        (app_repo / "renv.lock").write_text(json.dumps(BOGUS_LOCK, indent=2))
        harness.git(app_repo, "add", "-A")
        harness.git(app_repo, "commit", "-m", "add an unsatisfiable renv.lock")

        payload = json.loads(
            (harness.SCRIPTS_DIR.parent / "tests" / "fixtures" / "setup-app.input.json").read_text()
        )
        payload["steps"]["capture-request"]["appRepoUrl"] = f"file://{app_repo}"
        harness.write_input(scratch, payload)

        completed = harness.run_script(scratch, "setup_app.R")

        if completed.returncode == 0:
            return harness.FAIL, "an unsatisfiable renv.lock exited 0 — restore failure is not detected"

        missing = [m for m in REQUIRED_MARKERS if m not in completed.stderr]
        if missing:
            return harness.FAIL, f"error text lacks diagnostic markers {missing}: {completed.stderr[-400:]}"

        return harness.PASS, "unsatisfiable lock fails with repos + override + transcript reported"
    finally:
        harness.cleanup(scratch)


if __name__ == "__main__":
    status, detail = run()
    print(detail)
    sys.exit(status)
