"""Shared helpers for the shiny-feature-request script tests.

Mirrors how the platform runs a script step: the script reads
/output/input.json and writes /output/result.json, with the run's git worktree
mounted at /workspace. Locally we redirect both roots into a scratch directory
by rewriting those literals in a copy of the script, which is the same trick
local mode uses in script-container-plugin.ts.
"""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"

PASS, SKIP, FAIL = 0, 2, 1

MINIMAL_APP = """library(shiny)

ui <- fluidPage(
  titlePanel("Fixture App"),
  textOutput("greeting")
)

server <- function(input, output, session) {
  output$greeting <- renderText("hello from the fixture app")
}

shinyApp(ui, server)
"""


def r_packages_available(*packages):
    """True when every named R package can be loaded by the local Rscript."""
    expr = ";".join(
        f'if (!requireNamespace("{pkg}", quietly=TRUE)) quit(status=1)' for pkg in packages
    )
    return subprocess.run(["Rscript", "-e", expr], capture_output=True).returncode == 0


def make_scratch():
    scratch = Path(tempfile.mkdtemp(prefix="shiny-feature-request-test-"))
    (scratch / "output").mkdir()
    (scratch / "workspace").mkdir()
    return scratch


def install_scripts(scratch):
    """Copy the scripts into the scratch dir with /output and /workspace rebased."""
    target = scratch / "scripts"
    target.mkdir(exist_ok=True)
    for source in SCRIPTS_DIR.glob("*.R"):
        text = source.read_text()
        text = text.replace('"/output/', f'"{scratch}/output/')
        text = text.replace('"/workspace/app"', f'"{scratch}/workspace/app"')
        (target / source.name).write_text(text)
    return target


def write_input(scratch, payload):
    (scratch / "output" / "input.json").write_text(json.dumps(payload))


def read_result(scratch):
    return json.loads((scratch / "output" / "result.json").read_text())


def run_script(scratch, name):
    return subprocess.run(
        ["Rscript", str(scratch / "scripts" / name)],
        capture_output=True,
        text=True,
        cwd=scratch,
    )


def git(repo, *args):
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        env={**os.environ, "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "f@x.test",
             "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "f@x.test"},
    )


def make_app_repo(root, app_body=MINIMAL_APP):
    """Create a local git repo on branch main holding a minimal Shiny app."""
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main", str(root)], check=True, capture_output=True)
    (root / "app.R").write_text(app_body)
    git(root, "add", "-A")
    git(root, "commit", "-m", "initial fixture app")
    return root


def cleanup(scratch):
    shutil.rmtree(scratch, ignore_errors=True)
