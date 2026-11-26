# RoadSense API: FastAPI + ONNX Runtime (CPU). Built by .github/workflows/deploy.yml.
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    ENVIRONMENT=production \
    PORT=8000

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv
WORKDIR /app

# Dependencies first, for layer caching.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts ./scripts

# Optional: bake the models into the image so cold starts skip the download.
ARG HF_MODEL_REPO=""
RUN if [ -n "$HF_MODEL_REPO" ]; then \
      uv run python -c "from huggingface_hub import hf_hub_download as d; import shutil, os; \
os.makedirs('models', exist_ok=True); \
[shutil.copy(d('$HF_MODEL_REPO', f), 'models/' + f) for f in ('yolo-small.onnx', 'depth-anything-v2-small.onnx')]"; \
    fi

RUN useradd --create-home --uid 10001 app && chown -R app /app
USER app

EXPOSE 8000
CMD ["sh", "-c", "uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
