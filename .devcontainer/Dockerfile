FROM mcr.microsoft.com/devcontainers/base:ubuntu

RUN apt-get update && apt-get install -y \
    python3 python3-venv python3-pip \
    # Chromium dependencies required by d2 for PNG rendering
    chromium-browser fonts-liberation libatk-bridge2.0-0 libatk1.0-0 libcups2 \
    libdrm2 libgbm1 libgtk-3-0 libnspr4 libnss3 libxcomposite1 libxdamage1 \
    libxrandr2 xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Create .claude directory owned by vscode so bind-mounted files overlay a writable dir
RUN mkdir -p /home/vscode/.claude && chown vscode:vscode /home/vscode/.claude

USER vscode

# Install d2
RUN curl -fsSL https://d2lang.com/install.sh | sh -s --

# Install Claude Code
RUN curl -fsSL https://claude.ai/install.sh | bash
