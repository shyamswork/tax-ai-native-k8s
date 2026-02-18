"""Test cases for Tax AI API endpoints"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add api directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "api"))


@pytest.fixture
def client():
    """Create a test client"""
    from main import app
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_ai_tax_simple_request(client):
    """Test simple AI tax request (Phi-3 path)"""
    response = client.post(
        "/ai-tax",
        json={
            "amount": 100000,
            "jurisdictions": ["US"],
            "complexity": "low"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "tax" in data
    assert "latency_ms" in data
    assert "engine" in data
    assert data["engine"] == "Phi-3"


def test_ai_tax_complex_request(client):
    """Test complex AI tax request (Legacy path)"""
    response = client.post(
        "/ai-tax",
        json={
            "amount": 5000000,
            "jurisdictions": ["US", "CA", "UK"],
            "complexity": "high"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "tax" in data
    assert "latency_ms" in data
    assert "engine" in data
    assert data["engine"] == "Legacy Monolith"


def test_ai_tax_missing_jurisdictions(client):
    """Test request validation"""
    response = client.post(
        "/ai-tax",
        json={
            "amount": 100000
        }
    )
    assert response.status_code == 422


def test_legacy_tax_calc(client):
    """Test legacy monolith endpoint"""
    response = client.post(
        "/legacy-tax-calc",
        json={
            "amount": 100000,
            "jurisdictions": ["US"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "tax" in data
    assert "latency" in data
    assert data["engine"] == "Monolith"
