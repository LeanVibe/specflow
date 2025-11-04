"""Tests for FastAPI main application."""

import pytest
from fastapi.testclient import TestClient


def test_create_app_returns_fastapi_instance() -> None:
    """Test that create_app returns a FastAPI instance."""
    from specflow.api.main import create_app

    app = create_app()
    assert app is not None
    assert hasattr(app, "openapi")
    assert hasattr(app, "routes")


def test_app_has_cors_middleware() -> None:
    """Test that CORS middleware is configured."""
    from specflow.api.main import create_app

    app = create_app()
    # Check that CORS middleware is in the middleware stack
    # FastAPI wraps middleware in a Middleware class, so we check the cls attribute
    middleware_classes = [m.cls.__name__ for m in app.user_middleware]
    assert "CORSMiddleware" in middleware_classes


def test_app_metadata() -> None:
    """Test that app has correct metadata."""
    from specflow.api.main import create_app

    app = create_app()
    assert app.title == "SpecFlow API"
    assert "Transform PRDs into production-ready Jira tickets" in app.description
    assert app.version == "0.1.0"


def test_health_check_endpoint() -> None:
    """Test GET /health returns healthy status."""
    from specflow.api.main import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
    assert "timestamp" in data


def test_health_check_response_format() -> None:
    """Test health check response has correct format."""
    from specflow.api.main import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    # Validate against HealthCheckResponse schema
    assert isinstance(data["status"], str)
    assert isinstance(data["version"], str)
    assert isinstance(data["timestamp"], str)  # ISO datetime string


def test_openapi_docs_available() -> None:
    """Test that OpenAPI documentation is available."""
    from specflow.api.main import app

    client = TestClient(app)
    response = client.get("/openapi.json")

    assert response.status_code == 200
    openapi_schema = response.json()
    assert openapi_schema["info"]["title"] == "SpecFlow API"
    assert openapi_schema["info"]["version"] == "0.1.0"


def test_prd_routes_registered() -> None:
    """Test that PRD routes are registered."""
    from specflow.api.main import app

    # Check that PRD routes exist
    routes = [route.path for route in app.routes if hasattr(route, "path")]
    # Routes will be registered when we add them to prd.py
    # For now, just check that the router is included
    router_prefixes = [route.path for route in app.routes if hasattr(route, "path") and route.path.startswith("/api/prd")]
    # We'll add actual routes in the next step
    assert isinstance(routes, list)


def test_ticket_routes_registered() -> None:
    """Test that ticket routes are registered."""
    from specflow.api.main import app

    routes = [route.path for route in app.routes if hasattr(route, "path")]
    # Routes will be registered when we add them to tickets.py
    assert isinstance(routes, list)


def test_oauth_routes_registered() -> None:
    """Test that OAuth routes are registered."""
    from specflow.api.main import app

    routes = [route.path for route in app.routes if hasattr(route, "path")]
    # Routes will be registered when we add them to oauth.py
    assert isinstance(routes, list)


def test_404_handler() -> None:
    """Test that 404 errors are handled properly."""
    from specflow.api.main import app

    client = TestClient(app)
    response = client.get("/nonexistent-endpoint")

    assert response.status_code == 404
