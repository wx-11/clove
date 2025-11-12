# Multi-stage Dockerfile for Clove

# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder

# Set timezone
ENV TZ=Asia/Shanghai
RUN apk add --no-cache tzdata

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app/front

# Copy frontend configuration files first
COPY front/tsconfig*.json front/vite.config.ts front/package.json front/pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy frontend source (src directory and other files)
COPY front/src ./src
COPY front/index.html front/eslint.config.js front/components.json ./

# Build frontend
RUN pnpm run build

# Stage 2: Build Python application
FROM python:3.11-slim AS app

# Set timezone
ENV TZ=Asia/Shanghai
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && \
    ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python requirements
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/front/dist ./app/static

# Create data directory
RUN mkdir -p /data

# Environment variables
ENV DATA_FOLDER=/data
ENV HOST=0.0.0.0
ENV PORT=${PORT:-5201}
ENV WORKERS=${WORKERS:-4}

# Expose port
EXPOSE ${PORT:-5201}

# Run the application with uvicorn and multiple workers
CMD ["python", "-m", "app.main"]
