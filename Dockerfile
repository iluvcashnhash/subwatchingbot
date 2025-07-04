# Use Python 3.12 slim image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.8.2

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install "poetry==$POETRY_VERSION"

# Set working directory
WORKDIR /app

# Copy only requirements to cache them in docker layer
COPY poetry.lock pyproject.toml /app/

# Install Python dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-dev

# Copy the rest of the application
COPY . .

# Create a non-root user and switch to it
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser /app
USER appuser

# Set the entrypoint
ENTRYPOINT ["python", "-m", "app.main"]

# Default command (can be overridden)
CMD []
