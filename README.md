# mediforce-shiny-feature-workflow

Mediforce workflow packages for R Shiny application delivery. One subfolder per
workflow; `index.json` at this root lists them all with repo-root-relative
paths, so the repo can be browsed and imported from git.

| Workflow | What it does |
|----------|--------------|
| [`shiny-feature-request`](shiny-feature-request/) | Feature request → clone and set up the app → implement with an agent → verify it still boots → human review → deploy to Posit Connect |

See each workflow's `README.md` for its environment contract, output contracts,
and registration commands.
