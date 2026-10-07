# Isolated runtime for CryptoAudit V1-V3 validation (see cryptoaudit.validation.sandbox.DockerSandbox).
# Build: docker build -t cryptoaudit-sandbox:latest docker/sandbox
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Only the libraries benchmark cases may use; candidates are checked against case allow-lists.
RUN pip install "cryptography==50.0.2"

# Runs as nobody; the container is started with --network none, --read-only and dropped capabilities.
USER 65534:65534
WORKDIR /work
