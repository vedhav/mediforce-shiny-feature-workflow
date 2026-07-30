# shiny-feature-request

Takes a clearly defined feature request for an R Shiny application, clones and
sets the app up for testing, implements the change with an agent, verifies the
app still boots, gates on human review, and deploys to Posit Connect.

The target application is **per request** — the repository URL is a field on the
start form, so one registered workflow serves any Shiny app.

## Flow

```
(manual start form: appRepoUrl, featureRequest, baseBranch)
        │
setup-app          script  clone → renv::restore() → baseline boot/test check
        │
implement-feature  agent   L4 — implement, commit, push branch, open PR
        │
verify-change      script  same boot/test check + git diff vs baseline
        │
review-change      human   review — approve / revise / abandon
        ├── approve → deploy-app  script  rsconnect::deployApp() → done
        ├── revise  → implement-feature   (comment required)
        └── abandon → abandoned           (comment required)
```

`review-change` has **no outbound transitions** — routing is entirely by verdict
target, which is what the schema requires of a `type: review` step.

## Design notes

- **The workspace is shared.** Every step of a run mounts the same git worktree
  at `/workspace`, so `setup-app` clones once into `/workspace/app` and the
  implement, verify, and deploy steps all reuse it. No re-clone, no re-restore.
- **`setup-app` fails fast** on a failed clone or a failed `renv::restore()` —
  neither is recoverable downstream. A baseline that *does not boot* is recorded
  (`boots: false`) and allowed through on purpose: the feature request may be
  "fix this broken app", and the reviewer needs the baseline to tell whether the
  agent broke the app or found it broken.
- **One check, two steps.** `setup-app` and `verify-change` call the same
  functions in `scripts/app_check.R`, which is what makes their outputs
  comparable at the review step.
- **The human gate sits after the verify step, not on the agent.** An `L3` agent
  step pauses for approve/revise *before* any script can run, so the reviewer
  would be judging the diff with no test results. Running the agent at `L4` and
  putting a separate `type: review` step after `verify-change` means the
  reviewer sees boot and test outcomes, the changed-file list, and the PR URL
  before approving a deployment.
- **Connect content identity is the sanitized repo name**, so re-running the
  workflow (or an approve → revise → re-deploy cycle) updates the same Connect
  content item in place instead of accumulating one item per run.
- **The clone is authenticated only when a token exists.** `GITHUB_TOKEN`
  present → HTTPS clone with `x-access-token`; absent → plain clone. Public
  repos therefore need no configuration, and a token failure is redacted out of
  the error message.

## Environment contract

| Name | Secret | Scope | Used by | Meaning | How to set | Example |
|------|--------|-------|---------|---------|------------|---------|
| `GITHUB_TOKEN` | yes | workflow | `setup-app`, `implement-feature` | Clones private app repos and opens the pull request. Absent → unauthenticated clone and no PR (the branch is still committed locally). Also exported as `GH_TOKEN` for the `gh` CLI. | Workflow secrets panel | `ghp_…` |
| `CONNECT_SERVER` | no | workflow or namespace | `deploy-app` | Posit Connect base URL. `/__api__` is appended by the script. | Workflow env or namespace env | `https://connect.appsilon.com` |
| `CONNECT_API_KEY` | yes | workflow | `deploy-app` | Posit Connect API key used by `rsconnect::connectApiUser()`. | Workflow secrets panel | 32-char key |
| `OPENROUTER_API_KEY` | yes | workflow or namespace | `implement-feature` | LLM key; also mapped to `ANTHROPIC_AUTH_TOKEN` against the OpenRouter base URL. | Workflow secrets panel | `sk-or-v1-…` |

## Agents, MCPs, skills

**None to configure.** The agent step uses the default `claude-code-agent`
plugin with the built-in tool set plus `WebSearch` and `WebFetch`; `git` and
`gh` are reached through `Bash`. There is no `agentId`, no MCP server, and no
external skill — so there is **no MANUAL Tool Catalog or Agent Definition
setup** for this package. Only the four environment values above.

## Docker image

`Dockerfile` builds `mediforce-shiny-feature-request:latest` from
`mediforce-golden-image`, adding what the golden image lacks:

- the **GitHub CLI** (`gh`), used by the agent step to open the pull request;
- R packages `shiny`, `rsconnect`, `renv`, `testthat`, `jsonlite`, installed
  from the dated Posit Package Manager snapshot `2026-07-01` so rebuilds are
  reproducible. `install.packages` only warns on failure, so the build asserts
  the packages are present afterwards and fails loudly if not.

The `:latest` tag is safe here because the image is in **build mode**: the
builder labels the image with the `commit` SHA and rebuilds whenever that label
goes stale, so the `commit` field is the real pin, not the tag.

The Dockerfile must stay at this subfolder's root. The image builder resolves
`dockerfile` relative to the repo root but uses the **Dockerfile's own
directory** as the `docker build` context, so `COPY scripts/` only resolves
while the Dockerfile and `scripts/` are siblings.

Note: the PPM snapshot URL has no distro path, so R packages build **from
source**. The image build is correspondingly slow the first time. Adding
`__linux__/<codename>/` to the URL would fetch binaries, at the cost of pinning
the image to one base distribution.

## Output contracts

`setup-app`
```json
{ "appRepoUrl": "string", "appName": "string", "baseBranch": "string",
  "baseCommit": "string", "appDir": "string|null",
  "renvRestored": "boolean", "renvDetail": "string",
  "boots": "boolean", "bootDetail": "string", "bootLog": "string",
  "testsRun": "boolean", "testsPassed": "boolean", "testDetail": "string",
  "baselinePassed": "boolean" }
```

`implement-feature`
```json
{ "implemented": "boolean", "branch": "string", "prUrl": "string|null",
  "filesChanged": ["string"], "summary": "string", "notes": "string" }
```

`verify-change`
```json
{ "appDir": "string|null", "headCommit": "string",
  "changedFiles": ["string"], "changedFileCount": "number",
  "boots": "boolean", "bootDetail": "string", "bootLog": "string",
  "testsRun": "boolean", "testsPassed": "boolean", "testDetail": "string",
  "passed": "boolean" }
```

`deploy-app`
```json
{ "deployed": "boolean", "appName": "string", "appDir": "string",
  "connectServer": "string", "contentUrl": "string|null" }
```

## Known-good input

| Field | Value |
|-------|-------|
| `appRepoUrl` | `https://github.com/rstudio/shiny-examples.git` |
| `featureRequest` | `In 001-hello, change the histogram fill colour to steel blue and add a slider to control the number of bins between 5 and 50.` |
| `baseBranch` | `main` |

## Register

Local file — reads the working tree, no commit required:

```bash
pnpm exec mediforce workflow register \
  --file shiny-feature-request/src/shiny-feature-request.wd.json \
  --namespace <your-namespace>
```

Import from git (public repo; paths are repo-root-relative):

```bash
pnpm exec mediforce workflow import \
  --repo https://github.com/vedhav/mediforce-shiny-feature-workflow \
  --path shiny-feature-request/src/shiny-feature-request.wd.json \
  --ref <HEAD sha> \
  --namespace <your-namespace>
```

Then set the four environment values, and add the `requester` / `reviewer`
roles to the people who need them. The `manual` trigger is auto-seeded on
register, so the workflow is hand-startable immediately.

## Validation performed

- `mediforce workflow register --dry-run` — **passes** (7 steps, 4 transitions).
- Dockerfile build context — every `COPY` source resolves inside the context.
- `parse()` on all four R scripts — clean.
- Script behavior tests — see [`tests/TEST_SUMMARY.md`](tests/TEST_SUMMARY.md).
  `setup_app.R` and `verify_app.R` are tested and green; `deploy_connect.R` is
  **not yet verified against a live Connect**.

None of the above builds the Docker image or runs the workflow end to end.
Those are only exercised by an actual run on the platform.
