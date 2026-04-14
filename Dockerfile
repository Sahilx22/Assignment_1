# =============================================================================
# Stage 1: Builder — install Python dependencies
# =============================================================================
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements first (better layer caching)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-cache-dir -r requirements.txt


# =============================================================================
# Stage 2: Runtime — lean final image
# =============================================================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Runtime dependency for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from the builder stage
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Create a non-root user for security
RUN useradd --system --create-home appuser && chown -R appuser:appuser /app
USER appuser

# Expose the application port
EXPOSE 8000

# Default command — override in docker-compose for migrations etc.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
