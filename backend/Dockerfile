# Parallax API for nexus: builds from backend/ (source.subdir = "backend").
FROM python:3.11-slim-bookworm AS build
RUN apt-get update && apt-get install -y --no-install-recommends git build-essential && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PIP_NO_CACHE_DIR=1
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

FROM python:3.11-slim-bookworm
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    PARALLAX_VAR_DIR=/tmp/parallax HF_HOME=/tmp/hf MPLCONFIGDIR=/tmp/mpl
RUN useradd --create-home --uid 10001 parallax
COPY --from=build /opt/venv /opt/venv
WORKDIR /app
COPY --chown=parallax:parallax . .
USER parallax
CMD ["python", "-m", "parallax.cli", "serve-prod"]
