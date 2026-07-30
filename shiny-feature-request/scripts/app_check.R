#!/usr/bin/env Rscript
# Shared checks for a cloned Shiny application.
#
# Sourced by setup_app.R (baseline, straight after clone) and verify_app.R
# (after the agent has changed the code). Keeping the check in one file is what
# makes the two step outputs comparable at the human review step.

suppressPackageStartupMessages(library(jsonlite))

script_dir <- function() {
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("^--file=", args, value = TRUE)
  if (length(file_arg) == 0) return(getwd())
  dirname(normalizePath(sub("^--file=", "", file_arg[1])))
}

read_step_input <- function(path = "/output/input.json") {
  if (!file.exists(path)) return(list())
  fromJSON(path, simplifyVector = FALSE)
}

write_step_result <- function(result, path = "/output/result.json") {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  write_json(result, path, auto_unbox = TRUE, null = "null", na = "null")
}

# Connect content names accept alphanumerics, dashes and underscores only.
sanitize_app_name <- function(name) {
  cleaned <- gsub("[^A-Za-z0-9_-]", "-", name)
  cleaned <- gsub("-+", "-", cleaned)
  cleaned <- gsub("^-|-$", "", cleaned)
  if (nchar(cleaned) < 3) cleaned <- paste0(cleaned, "-app")
  substr(cleaned, 1, 64)
}

# A Shiny app lives either at the repo root or in one of a few conventional
# subdirectories. Returns the directory holding the entrypoint, or NULL.
detect_app_dir <- function(root) {
  candidates <- c(root, file.path(root, c("app", "inst/app", "shiny", "R")))
  for (dir in candidates) {
    if (!dir.exists(dir)) next
    if (file.exists(file.path(dir, "app.R"))) return(dir)
    if (file.exists(file.path(dir, "ui.R")) && file.exists(file.path(dir, "server.R"))) return(dir)
  }
  NULL
}

restore_deps <- function(app_root) {
  lockfile <- file.path(app_root, "renv.lock")
  if (!file.exists(lockfile)) {
    return(list(renvRestored = FALSE, renvDetail = "no renv.lock — skipped"))
  }
  renv::restore(project = app_root, prompt = FALSE)
  list(renvRestored = TRUE, renvDetail = "renv.lock restored")
}

# Start the app in a subprocess and poll until it answers HTTP 200 or dies.
# This is the check that separates "the code parses" from "the app runs".
boot_check <- function(app_dir, port = 7654L, timeout_seconds = 90L) {
  log_path <- tempfile(fileext = ".log")
  expr <- sprintf(
    "shiny::runApp(appDir = '%s', port = %d, host = '127.0.0.1', launch.browser = FALSE)",
    app_dir, port
  )
  pid <- system(
    sprintf("Rscript -e %s > %s 2>&1 & echo $!", shQuote(expr), shQuote(log_path)),
    intern = TRUE
  )
  pid <- trimws(pid[length(pid)])

  alive <- function() {
    system2("kill", c("-0", pid), stdout = FALSE, stderr = FALSE) == 0
  }
  responded <- FALSE
  deadline <- Sys.time() + timeout_seconds
  while (Sys.time() < deadline) {
    curl_code <- system2(
      "curl",
      c("-s", "-f", "-o", "/dev/null", sprintf("http://127.0.0.1:%d/", port)),
      stdout = FALSE, stderr = FALSE
    )
    if (curl_code == 0) {
      responded <- TRUE
      break
    }
    if (!alive()) break
    Sys.sleep(2)
  }
  if (alive()) system2("kill", c("-9", pid), stdout = FALSE, stderr = FALSE)

  boot_log <- if (file.exists(log_path)) paste(readLines(log_path, warn = FALSE), collapse = "\n") else ""
  list(
    boots = responded,
    bootDetail = if (responded) {
      sprintf("app answered HTTP 200 on port %d", port)
    } else {
      "app did not answer within the timeout"
    },
    bootLog = substr(boot_log, 1, 4000)
  )
}

run_tests <- function(app_root) {
  tests_dir <- file.path(app_root, "tests")
  if (!dir.exists(tests_dir)) {
    return(list(testsRun = FALSE, testsPassed = TRUE, testDetail = "no tests/ directory — skipped"))
  }
  target <- if (dir.exists(file.path(tests_dir, "testthat"))) {
    file.path(tests_dir, "testthat")
  } else {
    tests_dir
  }
  outcome <- tryCatch(
    {
      results <- testthat::test_dir(target, stop_on_failure = FALSE, reporter = "silent")
      summary <- as.data.frame(results)
      broken <- sum(summary$failed) + sum(as.integer(summary$error))
      list(
        testsRun = TRUE,
        testsPassed = broken == 0,
        testDetail = sprintf(
          "%d test files, %d passed, %d failed/errored",
          nrow(summary), sum(summary$passed), broken
        )
      )
    },
    error = function(err) {
      list(
        testsRun = TRUE,
        testsPassed = FALSE,
        testDetail = paste("testthat could not run:", conditionMessage(err))
      )
    }
  )
  outcome
}

# Aggregate check. `passed` is the gate value the workflow branches and the
# human reviewer read: the app must boot, and any tests it has must be green.
check_app <- function(app_root) {
  app_dir <- detect_app_dir(app_root)
  if (is.null(app_dir)) {
    return(list(
      appDir = NULL,
      boots = FALSE,
      bootDetail = "no Shiny entrypoint (app.R, or ui.R + server.R) found",
      bootLog = "",
      testsRun = FALSE,
      testsPassed = FALSE,
      testDetail = "skipped — no app to test",
      passed = FALSE
    ))
  }
  boot <- boot_check(app_dir)
  tests <- run_tests(app_root)
  c(
    list(appDir = sub(paste0("^", app_root, "/?"), "", app_dir)),
    boot,
    tests,
    list(passed = isTRUE(boot$boots) && isTRUE(tests$testsPassed))
  )
}
