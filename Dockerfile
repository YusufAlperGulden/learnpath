# Unified single-service cloud Dockerfile (used by Render Blueprint `render.yaml`)
# Builds the React SPA and bundles it into the FastAPI + Uvicorn image on a single HTTPS URL.

FROM node:22-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
ENV VITE_API_BASE_URL=/api/v1
RUN npm run build

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STATIC_DIST_DIR=/app/static_dist

WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY backend/ ./
COPY --from=frontend-build /frontend/dist /app/static_dist

EXPOSE 8000
CMD ["python", "-m", "scripts.start_server"]
