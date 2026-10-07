# CryptoAudit API (website backend). Build from the repository root:
#   docker build -f docker/api.Dockerfile -t cryptoaudit-api .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY backend/pyproject.toml backend/README.md ./
COPY backend/src ./src
COPY backend/configs ./configs
COPY backend/prompts ./prompts
# Editable install keeps configs/ and prompts/ resolvable at the repository paths under /app.
RUN pip install -e ".[web,scanners]" && useradd --uid 10001 --create-home cryptoaudit && mkdir -p /app/data && chown cryptoaudit /app/data

USER cryptoaudit
EXPOSE 8000
CMD ["cryptoaudit", "serve", "--host", "0.0.0.0", "--port", "8000"]
