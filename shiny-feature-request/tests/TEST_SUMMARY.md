# Test summary

Run everything: `python3 tests/run_tests.py` (from the `shiny-feature-request/`
directory). Tests skip rather than fail when their prerequisites are absent.

| Script | Status | Asserted |
|--------|--------|----------|
| `setup_app.R` | **tested** | Clones a local `file://` fixture repo into the workspace; `result.json` carries all 14 documented keys; `appName` sanitizes to `my-shiny-app`; `baseCommit` is a 40-hex SHA; `renvRestored` is `false` with no `renv.lock`; the fixture app boots (`boots: true`, `baselinePassed: true`) |
| `verify_app.R` | **tested** | Diffs the agent's commit against `steps["setup-app"].baseCommit` → `changedFiles == ["app.R"]`, `changedFileCount == 1`; the modified app boots; `passed: true`; all 11 documented keys present |
| `deploy_connect.R` | **skipped — publishes real content** | Not yet verified against a live Posit Connect |

## Running the skipped test

`test_deploy_connect.py` **publishes a fixture app** to whichever Connect the
credentials point at. Credential presence alone does *not* run it — an explicit
opt-in is required, so that a routine `run_tests.py` can never deploy by
accident:

```bash
CONNECT_SERVER=https://connect.appsilon.com \
CONNECT_API_KEY=<a valid key> \
MEDIFORCE_ALLOW_CONNECT_DEPLOY_TEST=1 \
python3 tests/run_tests.py
```

It creates Connect content named `mediforce-deploy-smoke-test` — delete it
afterwards.

## Known state as of authoring

`deploy_connect.R`'s auth path was exercised against
`https://connect.appsilon.com` and returned **HTTP 401**. A plain
`curl -H "Authorization: Key …" /__api__/v1/user` returned 401 for the same key,
which locates the fault in the **key**, not the script: the URL construction
(`<CONNECT_SERVER>/__api__`), the `rsconnect::addServer` +
`connectApiUser` handshake, and the error surfacing all behaved correctly.
Re-run the command above with a valid key to move this row to **tested**.

## Not covered by these tests

- The Dockerfile is **not built** here. `COPY` build-context correctness is
  checked statically (see the README's validation section), but no image is
  produced, so the `gh` install and the pinned R package set are unverified.
- No end-to-end workflow run. Step wiring, secret resolution, and the agent
  step's PR flow are only exercised by an actual run on the platform.
