FROM mcr.microsoft.com/devcontainers/base:ubuntu

ARG CLAUDE_CODE_VERSION=latest

RUN apt-get update && apt-get install -y \
    python3 python3-venv python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Create .claude directory owned by vscode so bind-mounted files overlay a writable dir
RUN mkdir -p /home/vscode/.claude && chown vscode:vscode /home/vscode/.claude

USER vscode

# Install d2
RUN curl -fsSL https://d2lang.com/install.sh | sh -s --

# Install Claude Code
RUN curl -fsSL https://claude.ai/install.sh | bash
