FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    python3 python3-venv python3-pip curl \
    && rm -rf /var/lib/apt/lists/*

# Install d2
RUN curl -fsSL https://d2lang.com/install.sh | sh -s --

# Create a non-root user (mirrors real install conditions)
RUN useradd -m testuser
USER testuser
WORKDIR /home/testuser
