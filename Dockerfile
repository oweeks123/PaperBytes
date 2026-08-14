# syntax=docker/dockerfile:1
# PaperBytes / "Paper Hero" — single-container image: FastAPI serves the API and
# the pre-built SvelteKit frontend (at /ui) on one origin.

# ---- Stage 1: build the SvelteKit frontend ----
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python runtime ----
FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY main.py article_bucket.txt ./
COPY paperbytes ./paperbytes
# Built static frontend from stage 1 (served by FastAPI at /ui).
COPY --from=frontend /app/frontend/build ./frontend/build

EXPOSE 8000
# Runtime config (keys, PUBMED_EMAIL, CONTACT_EMAIL, DATABASE_URL, …) is passed
# via environment variables, not baked into the image.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
