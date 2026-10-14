FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.10.4 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
ENV TIKTOKEN_CACHE_DIR=/app/.cache/tiktoken
RUN uv run python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"
COPY . .
ENV PATH="/app/.venv/bin:$PATH"
CMD ["sh", "scripts/start_api.sh"]
