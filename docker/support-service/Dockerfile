FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and security updates
RUN apt-get update && apt-get install -y \
    curl \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first for better caching
COPY docker/support-service/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY docker/support-service/app.py .

# Copy shared utilities
COPY shared/ ./shared/

# Create non-root user with specific UID/GID
RUN groupadd -g 1000 appuser \
    && useradd -r -u 1000 -g appuser -d /app -s /sbin/nologin appuser \
    && chown -R appuser:appuser /app \
    && chmod -R 755 /app

# Switch to non-root user
USER appuser

# Health check with proper error handling
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# Security: Don't run as root, use specific port
EXPOSE 5001

# Use exec form for better signal handling
CMD ["python", "-u", "app.py"]