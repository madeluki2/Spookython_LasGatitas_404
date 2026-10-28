# Lightweight Python Container for Escape de Manta Zombie Routing Engine
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV SPOOKY_API_KEY="spooky-manta-key-2026"

# Install system dependencies if required
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose HTTP port
EXPOSE 8000

# Health check to ensure microsecond latency responsiveness
HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD curl -f http://localhost:8000/estado || exit 1

# Start Uvicorn production server
CMD ["python", "scripts/run_local.py"]
