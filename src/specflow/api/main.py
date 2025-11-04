"""FastAPI main application for SpecFlow API.

This module defines the main FastAPI application with CORS middleware,
health check endpoints, and API route registration.
"""

from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from specflow.api.schemas import HealthCheckResponse


def create_app() -> FastAPI:
    """Factory function to create and configure FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="SpecFlow API",
        description="Transform PRDs into production-ready Jira tickets in 15 minutes",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Configure in production with specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Import and include routers
    # We'll create these in the next steps
    from specflow.api.routes import oauth, prd, tickets

    app.include_router(prd.router, prefix="/api/prd", tags=["PRD"])
    app.include_router(tickets.router, prefix="/api/tickets", tags=["Tickets"])
    app.include_router(oauth.router, prefix="/api/oauth", tags=["OAuth"])

    return app


# Create the application instance
app = create_app()


@app.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """Health check endpoint to verify API is running.

    Returns:
        Health status with version information.
    """
    return HealthCheckResponse(
        status="healthy",
        version="0.1.0",
        timestamp=datetime.now(UTC),
    )
