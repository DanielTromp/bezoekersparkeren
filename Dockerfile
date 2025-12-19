# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml requirements.txt README.md ./
COPY src/ src/
RUN pip install --no-cache-dir .

# Stage 2: Runtime
FROM python:3.11-slim

# OCI Labels
LABEL org.opencontainers.image.title="Bezoekersparkeren"
LABEL org.opencontainers.image.description="Telegram bot for automated visitor parking registration"
LABEL org.opencontainers.image.source="https://github.com/DanielTromp/bezoekersparkeren"
LABEL org.opencontainers.image.licenses="MIT"

# Install runtime dependencies for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Playwright Chromium dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set ownership and switch to non-root user
RUN chown -R appuser:appuser /app
USER appuser

# Install Playwright browsers
RUN playwright install chromium

# Set environment variables
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["bezoekersparkeren"]
CMD ["--help"]
