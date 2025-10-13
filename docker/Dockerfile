FROM debian:bookworm-slim

# Basics
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates python3 python3-pip python-is-python3 \
    && rm -rf /var/lib/apt/lists/*

# Node 20 + pnpm 9
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get update && apt-get install -y nodejs \
    && corepack enable && corepack prepare pnpm@9.0.0 --activate

# Python deps pre-baked (optional)
RUN pip install --no-cache-dir "openai>=1.35.0" requests

WORKDIR /work
