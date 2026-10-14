# Start with slim Python 3.13 image
FROM python:3.13.10-slim

# Copy uv binary from official uv image (multi-stage build pattern)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

# Set working directory
WORKDIR /app

# Add virtual environment to PATH so we can use installed packages
ENV PATH="/app/.venv/bin:$PATH"

# Copy dependency files first (better layer caching)
COPY "pyproject.toml" "uv.lock" ".python-version" "README.md" ./
# Install only the dependencies (not your project yet, since src/ isn't copied)
RUN uv sync --locked --no-install-project

# Copy application code
COPY src/ src/

# Set entry point
ENTRYPOINT ["uv", "run", "python", "src/pipeline/ingest.py"]