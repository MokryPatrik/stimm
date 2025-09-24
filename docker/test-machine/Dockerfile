FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY docker/test-machine/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy test files
COPY tests/ tests/
COPY src/ src/

# Set environment variables
ENV PYTHONPATH=/app/src

