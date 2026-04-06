FROM mcr.microsoft.com/devcontainers/base:ubuntu

RUN apt-get update && apt-get install -y \
    python3 python3-venv python3-pip \
    # Required by d2's bundled Playwright/Chromium for PNG rendering
    libasound2t64 libatk-bridge2.0-0t64 libatk1.0-0t64 libatspi2.0-0t64 \
    libcairo2 libcups2t64 libdbus-1-3 libdrm2 libgbm1 libglib2.0-0t64 \
    libnspr4 libnss3 libpango-1.0-0 libx11-6 libxcb1 libxcomposite1 \
    libxdamage1 libxext6 libxfixes3 libxkbcommon0 libxrandr2 \
    && rm -rf /var/lib/apt/lists/*

# Install yq (used by test.sh for YAML row-count checks)
RUN curl -fsSL "https://github.com/mikefarah/yq/releases/latest/download/yq_linux_$(dpkg --print-architecture)" -o /usr/local/bin/yq \
    && chmod +x /usr/local/bin/yq

USER vscode

# Install d2
RUN curl -fsSL https://d2lang.com/install.sh | sh -s --

# Install Claude Code
RUN curl -fsSL https://claude.ai/install.sh | bash
