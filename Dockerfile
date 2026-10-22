FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.8.0 /uv /usr/local/bin/uv

# No .git in the build context, so pass the release version in explicitly.
ARG VERSION=0.0.0
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${VERSION}

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy \
    PWN_MCP_CACHE_DIR=/data/cache PWN_MCP_OUTPUT_DIR=/data/output

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev

VOLUME /data
# MCP over stdio: run with `docker run -i --rm ghcr.io/wdconinc/pwn-mcp-server`
ENTRYPOINT ["/app/.venv/bin/pwn-mcp"]
