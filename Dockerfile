FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    musl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml requirements.txt README.md ./
COPY src/ src/
RUN pip install --no-cache-dir .

# Install Playwright browsers
RUN playwright install --with-deps chromium

# Set environment variables
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["bezoekersparkeren"]
CMD ["--help"]
