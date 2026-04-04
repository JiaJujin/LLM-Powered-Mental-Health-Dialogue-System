FROM python:3.12-slim

WORKDIR /app

# Install system tools and Node.js 20
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for Docker layer caching)
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy and build frontend
COPY frontend/package.json frontend/package-lock.json* /app/frontend/
RUN cd /app/frontend && npm install

COPY frontend/ /app/frontend/
RUN cd /app/frontend && npm run build

# Copy backend
COPY backend/ /app/backend/

# Expose Railway dynamic port
ENV PORT=8000
EXPOSE 8000

# Run from /app so module path "backend.app.main" resolves correctly
CMD ["sh", "-c", "cd /app && uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
