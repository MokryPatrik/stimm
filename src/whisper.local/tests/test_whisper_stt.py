"""Tests for the Whisper STT service."""

import pytest
from fastapi.testclient import TestClient
from whisper.local.main import app

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)

def test_healthz(client):
    """Test the health check endpoint."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert "model" in data
    assert "device" in data
    assert "compute_type" in data
    assert "stream_sample_rate" in data

def test_transcribe_empty_audio(client):
    """Test transcribing an empty audio file."""
    with open("/dev/null", "rb") as empty_file:
        response = client.post("/api/stt", files={"audio": empty_file})
    assert response.status_code == 400
    assert "Uploaded audio file is empty" in response.text

# Note: Additional tests would require audio file fixtures
# and mocking of the Whisper model to avoid external dependencies