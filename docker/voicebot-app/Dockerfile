# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Ensure /app is in Python path
ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    gcc \
    g++ \
    build-essential \
    pulseaudio-utils \
    libpulse0 \
    portaudio19-dev \
    python3-pyaudio \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv using pip (simple et efficace)
RUN pip install uv

# Copy requirements first for better caching
COPY . .

# Install dependencies using uv (much faster than pip)
# --system flag installs packages globally (like pip install)
RUN uv pip install --system -r requirements.txt

# Copy the rest of the application code


# Preload RAG models during Docker build to cache them
# This significantly speeds up server startup
RUN python scripts/preload_rag_models.py

# Start the FastAPI application with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]