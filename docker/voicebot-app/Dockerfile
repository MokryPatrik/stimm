# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app
COPY . .

# Ensure /app is in Python path
ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Install pytest for testing
RUN pip install pytest pytest-asyncio

# Start the FastAPI application with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]