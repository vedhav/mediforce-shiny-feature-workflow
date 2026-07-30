#!/usr/bin/env Rscript
# Re-run the setup_app.R checks against the application the agent just changed,
# and list the files it touched. Output feeds the human review step, so the
# reviewer compares this against the baseline before approving a deployment.

source(file.path(
  dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)[1]))),
  "app_check.R"
))

input <- read_step_input()
app_root <- "/workspace/app"

if (!dir.exists(app_root)) {
  stop(sprintf("%s does not exist — setup-app must run before verify-change", app_root))
}

setup <- input$steps[["setup-app"]]
base_commit <- if (!is.null(setup)) setup$baseCommit else NULL

changed_files <- character(0)
head_commit <- trimws(system2("git", c("-C", app_root, "rev-parse", "HEAD"), stdout = TRUE)[1])
if (!is.null(base_commit) && nzchar(base_commit)) {
  diff_output <- suppressWarnings(system2(
    "git",
    c("-C", app_root, "diff", "--name-only", base_commit, "HEAD"),
    stdout = TRUE, stderr = FALSE
  ))
  if (is.null(attr(diff_output, "status"))) changed_files <- diff_output
}

verified <- check_app(app_root)

write_step_result(list(
  appDir = verified$appDir,
  headCommit = head_commit,
  changedFiles = as.list(changed_files),
  changedFileCount = length(changed_files),
  boots = verified$boots,
  bootDetail = verified$bootDetail,
  bootLog = verified$bootLog,
  testsRun = verified$testsRun,
  testsPassed = verified$testsPassed,
  testDetail = verified$testDetail,
  passed = verified$passed
))

cat(sprintf(
  "Verified %s — boots=%s testsPassed=%s changedFiles=%d\n",
  app_root, verified$boots, verified$testsPassed, length(changed_files)
))
