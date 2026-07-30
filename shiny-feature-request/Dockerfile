# Runtime for the shiny-feature-request workflow.
#
# mediforce-golden-image already provides R + tidyverse, Python 3, Node.js,
# Claude Code and git. This image adds what the golden image lacks:
#
#   1. the GitHub CLI, so the agent step can open the pull request;
#   2. a BINARY R package repository, so `renv::restore()` on a target app
#      downloads prebuilt packages instead of compiling from source;
#   3. the system headers that source builds need anyway, as a fallback for
#      packages the binary repo has no build for;
#   4. Chromium, for apps whose tests use shinytest2/chromote.
#
# Deliberately NOT here: the target application's own packages. The app is
# chosen per request, so its renv.lock is unknown at image build time —
# pre-installing one app's dependencies would fix that app only. Points 2–4
# are what make restore work for an arbitrary lock.
#
# NOTE: this file must stay at the workflow subfolder root — the image builder
# uses the Dockerfile's own directory as the build context, so `COPY scripts/`
# resolves to shiny-feature-request/scripts/.
FROM mediforce-golden-image

RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends gh \
    && rm -rf /var/lib/apt/lists/*

# System libraries for the compiled CRAN packages that Shiny apps commonly pull
# in. Each entry maps to a package that fails to build without it: libnode-dev
# for V8, gdal/proj/geos for sf/raster/terra, unixodbc for odbc, libpq for
# RPostgreSQL, icu for stringi, harfbuzz/fribidi/freetype for textshaping and
# ragg, and the image libraries for png/jpeg/tiff.
RUN apt-get update && apt-get install -y --no-install-recommends \
      chromium \
      libnode-dev \
      libgdal-dev \
      libproj-dev \
      libgeos-dev \
      libudunits2-dev \
      unixodbc-dev \
      libpq-dev \
      libxml2-dev \
      libcurl4-openssl-dev \
      libssl-dev \
      libicu-dev \
      libsqlite3-dev \
      libsodium-dev \
      libfontconfig1-dev \
      libfreetype6-dev \
      libharfbuzz-dev \
      libfribidi-dev \
      libpng-dev \
      libjpeg-dev \
      libtiff5-dev \
      libcairo2-dev \
      libmagick++-dev \
    && rm -rf /var/lib/apt/lists/*

# Point R at the Posit Package Manager BINARY repository for this image's own
# Ubuntu release, and make renv use it too.
#
# This is the fix for the wholesale restore failure. Two things were wrong
# before: the repo URL had no `__linux__/<codename>/` segment, so PPM served
# source tarballs; and renv defaults to the repositories recorded inside the
# target app's renv.lock, which is usually plain CRAN — also source-only for
# Linux. RENV_CONFIG_REPOS_OVERRIDE makes renv ignore the lock's repos and use
# this one, so restore downloads binaries regardless of which app is being set
# up. HTTPUserAgent is required: PPM decides whether to serve a binary by
# sniffing the R user agent, and returns source silently if it does not match.
#
# The codename is resolved at build time rather than hardcoded, so the image
# stays correct if the golden image's Ubuntu base changes.
RUN . /etc/os-release \
    && PPM="https://packagemanager.posit.co/cran/__linux__/${VERSION_CODENAME}/2026-07-01" \
    && printf '%s\n' \
      "RENV_CONFIG_REPOS_OVERRIDE=${PPM}" \
      "RENV_PATHS_CACHE=/opt/renv-cache" \
      "CHROMOTE_CHROME=/usr/bin/chromium" \
      >> /usr/local/lib/R/etc/Renviron.site \
    && printf '%s\n' \
      "options(repos = c(CRAN = '${PPM}'))" \
      "options(HTTPUserAgent = sprintf('R/%s R (%s)', getRversion(), paste(getRversion(), R.version[['platform']], R.version[['arch']], R.version[['os']])))" \
      "options(Ncpus = max(1L, parallel::detectCores()))" \
      >> /usr/local/lib/R/etc/Rprofile.site \
    && mkdir -p /opt/renv-cache && chmod 0777 /opt/renv-cache \
    && echo "Configured binary PPM for ${VERSION_CODENAME}: ${PPM}"

# Workflow's own R dependencies, resolved through the binary repo configured
# above. install.packages only warns on failure, so assert afterwards to fail
# the build loudly rather than shipping a half-built image.
RUN Rscript -e "pkgs <- c('shiny','rsconnect','renv','testthat','jsonlite'); \
      install.packages(pkgs); \
      missing <- pkgs[!pkgs %in% rownames(installed.packages())]; \
      if (length(missing)) stop('failed to install: ', paste(missing, collapse = ', '))"

COPY scripts/ /opt/shiny-feature-request/scripts/

WORKDIR /workspace
