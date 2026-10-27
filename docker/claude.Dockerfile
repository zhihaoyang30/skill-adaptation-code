FROM node:22-bookworm
ARG CLAUDE_VERSION=2.1.114
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip python3-venv git curl unzip jq \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g @anthropic-ai/claude-code@${CLAUDE_VERSION}
USER node
WORKDIR /workspace
