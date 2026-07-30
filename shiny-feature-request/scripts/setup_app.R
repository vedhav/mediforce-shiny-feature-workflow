#!/usr/bin/env Rscript
# Clone the requested Shiny application into the run workspace, restore its
# dependencies, and record a baseline boot/test result.
#
# Fails fast when the clone or the dependency restore fails — those are not
# recoverable by a downstream step. A baseline that does not boot is recorded
# and allowed through: the feature request may be "fix this broken app", and
# the reviewer needs to know whether the agent broke it or found it broken.

source(file.path(
  dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)[1]))),
  "app_check.R"
))

input <- read_step_input()

# The manual-start form values reach this container via the capture-request
# reshape step, not directly: /output/input.json carries only `steps`, and the
# run's triggerPayload is a separate field that never appears there.
payload <- input$steps[["capture-request"]]
if (is.null(payload)) payload <- list()

repo_url <- payload$appRepoUrl
if (is.null(repo_url) || !nzchar(repo_url)) {
  stop("appRepoUrl is empty — check the capture-request step output and the start form")
}
base_branch <- if (!is.null(payload$baseBranch) && nzchar(payload$baseBranch)) {
  payload$baseBranch
} else {
  "main"
}

app_root <- "/workspace/app"
repo_name <- sub("\\.git$", "", basename(repo_url))

# Authenticated clone when a token is available, plain clone otherwise, so a
# public repo needs no configuration at all.
token <- Sys.getenv("GITHUB_TOKEN", "")
clone_url <- repo_url
if (nzchar(token) && grepl("^https://", repo_url)) {
  clone_url <- sub("^https://", sprintf("https://x-access-token:%s@", token), repo_url)
}

if (dir.exists(app_root)) unlink(app_root, recursive = TRUE)
dir.create(dirname(app_root), recursive = TRUE, showWarnings = FALSE)

clone_output <- suppressWarnings(system2(
  "git",
  c("clone", "--branch", base_branch, "--single-branch", clone_url, app_root),
  stdout = TRUE, stderr = TRUE
))
if (!is.null(attr(clone_output, "status"))) {
  redacted <- if (nzchar(token)) gsub(token, "***", clone_output, fixed = TRUE) else clone_output
  stop(sprintf(
    "git clone of %s (branch %s) failed:\n%s",
    repo_url, base_branch, paste(redacted, collapse = "\n")
  ))
}

# The agent step commits and pushes from this clone, so it needs an identity.
system2("git", c("-C", app_root, "config", "user.name", "Mediforce Workflow"), stdout = FALSE)
system2("git", c("-C", app_root, "config", "user.email", "mediforce@appsilon.com"), stdout = FALSE)

base_commit <- trimws(system2("git", c("-C", app_root, "rev-parse", "HEAD"), stdout = TRUE)[1])

restored <- restore_deps(app_root)
baseline <- check_app(app_root)

write_step_result(list(
  appRepoUrl = repo_url,
  appName = sanitize_app_name(repo_name),
  baseBranch = base_branch,
  baseCommit = base_commit,
  appDir = baseline$appDir,
  renvRestored = restored$renvRestored,
  renvDetail = restored$renvDetail,
  boots = baseline$boots,
  bootDetail = baseline$bootDetail,
  bootLog = baseline$bootLog,
  testsRun = baseline$testsRun,
  testsPassed = baseline$testsPassed,
  testDetail = baseline$testDetail,
  baselinePassed = baseline$passed
))

cat(sprintf(
  "Cloned %s@%s into %s — baseline boots=%s testsPassed=%s\n",
  repo_url, substr(base_commit, 1, 8), app_root, baseline$boots, baseline$testsPassed
))
