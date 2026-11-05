FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /uvx /bin/

WORKDIR /app

# GPU workers build with UV_EXTRAS="--extra torch"; the API and CPU worker skip it.
ARG UV_EXTRAS=""

# Dependencies first, so code changes do not reinstall them.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-cache --no-install-project $UV_EXTRAS

COPY . .
RUN uv sync --frozen --no-dev --no-cache $UV_EXTRAS
ENV PATH="/app/.venv/bin:$PATH"

CMD ["fastapi", "run", "main.py", "--port", "8000", "--host", "0.0.0.0"]
