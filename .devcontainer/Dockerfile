# Dev container for Content Research Pipeline
# Based on the official VS Code Python devcontainer image (Python 3.11)
FROM mcr.microsoft.com/vscode/devcontainers/python:3.11

ENV DEBIAN_FRONTEND=noninteractive

# Install additional packages: git, curl, build tools, node, npm
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    ca-certificates \
    nodejs \
    npm \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Install Poetry (optional Python dependency manager)
RUN curl -sSL https://install.python-poetry.org | python3 - --yes

# Ensure poetry is on PATH for vscode user
ENV PATH="/home/vscode/.local/bin:${PATH}"

# Create a convenience script hook (optional)
COPY postCreate.sh /tmp/postCreate.sh
RUN chmod +x /tmp/postCreate.sh

# Set default user back to vscode
USER vscode
