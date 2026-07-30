# Runtime for the shiny-feature-request workflow.
#
# mediforce-golden-image already provides R + tidyverse, Python 3, Node.js,
# Claude Code and git. This image adds what the golden image lacks: the GitHub
# CLI (the agent step opens the pull request) and the Shiny/deploy R packages.
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

# Pinned to a dated Posit Package Manager snapshot so rebuilds are reproducible.
# install.packages only warns on failure, so assert afterwards to fail the build.
RUN Rscript -e "pkgs <- c('shiny','rsconnect','renv','testthat','jsonlite'); \
      install.packages(pkgs, repos = 'https://packagemanager.posit.co/cran/2026-07-01'); \
      missing <- pkgs[!pkgs %in% rownames(installed.packages())]; \
      if (length(missing)) stop('failed to install: ', paste(missing, collapse = ', '))"

COPY scripts/ /opt/shiny-feature-request/scripts/

WORKDIR /workspace
