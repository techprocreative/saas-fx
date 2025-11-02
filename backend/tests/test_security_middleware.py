"""
Tests for Security Middleware
"""
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, Request
from app.core.security_middleware import (
    setup_security_middleware,
    SecurityHeadersMiddleware,
    RequestValidationMiddleware,
    RequestIDMiddleware,
)


@pytest.fixture
def app():
    """Create test FastAPI app"""
    test_app = FastAPI()
    
    @test_app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}
    
    @test_app.get("/test-params")
    async def test_params_endpoint(query: str = ""):
        return {"query": query}
    
    return test_app


@pytest.fixture
def client(app):
    """Create test client"""
    setup_security_middleware(app)
    return TestClient(app)


def test_security_headers_present(client):
    """Test that security headers are added to responses"""
    response = client.get("/test")
    
    assert response.status_code == 200
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "X-Frame-Options" in response.headers
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "X-XSS-Protection" in response.headers
    assert "Strict-Transport-Security" in response.headers


def test_request_id_added(client):
    """Test that request ID is added to responses"""
    response = client.get("/test")
    
    assert "X-Request-ID" in response.headers
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) > 0


def test_sql_injection_protection(client):
    """Test SQL injection attempt is blocked"""
    malicious_queries = [
        "1' OR '1'='1",
        "1; DROP TABLE users--",
        "UNION SELECT * FROM users",
    ]
    
    for query in malicious_queries:
        response = client.get(f"/test-params?query={query}")
        assert response.status_code == 400, f"Failed to block: {query}"


def test_xss_protection(client):
    """Test XSS attack is blocked"""
    xss_payloads = [
        "<script>alert('xss')</script>",
        "javascript:alert(1)",
        "<iframe src='evil.com'>",
    ]
    
    for payload in xss_payloads:
        response = client.get(f"/test-params?query={payload}")
        assert response.status_code == 400, f"Failed to block: {payload}"


def test_path_traversal_protection(client):
    """Test path traversal is blocked"""
    response = client.get("/../../../etc/passwd")
    assert response.status_code == 400


def test_request_size_limit(client):
    """Test large requests are rejected"""
    # Create 11MB of data
    large_data = "x" * (11 * 1024 * 1024)
    response = client.post("/test", data=large_data)
    assert response.status_code == 413


def test_rate_limiting():
    """Test rate limiting works"""
    # This would need Redis mock in real implementation
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
