#!/usr/bin/env Rscript
# Deploy the changed Shiny application to Posit Connect.
#
# Content identity is the sanitized repo name, so re-running this workflow
# updates the same Connect content item in place rather than accumulating a
# new item per run.

source(file.path(
  dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)[1]))),
  "app_check.R"
))

input <- read_step_input()
app_root <- "/workspace/app"

setup <- input$steps[["setup-app"]]
if (is.null(setup) || is.null(setup$appName)) {
  stop("setup-app output is missing appName — cannot determine the Connect content name")
}
app_name <- setup$appName

app_dir <- detect_app_dir(app_root)
if (is.null(app_dir)) {
  stop(sprintf("no Shiny entrypoint found under %s — nothing to deploy", app_root))
}

server_url <- Sys.getenv("CONNECT_SERVER", "")
api_key <- Sys.getenv("CONNECT_API_KEY", "")
if (!nzchar(server_url)) stop("CONNECT_SERVER is not set")
if (!nzchar(api_key)) stop("CONNECT_API_KEY is not set")

api_url <- paste0(sub("/+$", "", server_url), "/__api__")
rsconnect::addServer(url = api_url, name = "connect", quiet = TRUE)
rsconnect::connectApiUser(
  account = "mediforce",
  server = "connect",
  apiKey = api_key,
  quiet = TRUE
)

rsconnect::deployApp(
  appDir = app_dir,
  appName = app_name,
  server = "connect",
  account = "mediforce",
  forceUpdate = TRUE,
  launch.browser = FALSE,
  logLevel = "normal"
)

# deployApp does not return the content URL reliably across rsconnect versions;
# the deployment record it writes alongside the app does.
content_url <- NA_character_
records <- tryCatch(rsconnect::deployments(appPath = app_dir), error = function(err) NULL)
if (!is.null(records) && nrow(records) > 0 && "url" %in% names(records)) {
  content_url <- as.character(records$url[[nrow(records)]])
}

write_step_result(list(
  deployed = TRUE,
  appName = app_name,
  appDir = sub(paste0("^", app_root, "/?"), "", app_dir),
  connectServer = server_url,
  contentUrl = content_url
))

cat(sprintf("Deployed %s to %s (%s)\n", app_name, server_url, content_url))
