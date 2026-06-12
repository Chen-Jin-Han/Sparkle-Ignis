FROM node:22-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SPARKLE_LLM_DIR=/app/LLM \
    SPARKLE_INDEX_DIR=/app/.sparkle/index \
    SPARKLE_FRONTEND_DIST_DIR=/app/frontend/dist

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./
COPY sparkle_researcher ./sparkle_researcher
COPY sparkle-ignis-logo.svg ./sparkle-ignis-logo.svg
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

EXPOSE 8765

CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "8765"]
