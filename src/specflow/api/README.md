# SpecFlow REST API

FastAPI REST API layer for transforming PRDs into production-ready Jira tickets.

## Quick Start

```bash
# Start the API server
uvicorn specflow.api.main:app --reload

# Visit interactive API docs
open http://localhost:8000/docs
```

## API Endpoints

### Health Check
```bash
# Check API health
curl http://localhost:8000/health
```

### PRD Endpoints

#### Parse PRD
```bash
# Parse markdown PRD
curl -X POST http://localhost:8000/api/prd/parse \
  -H "Content-Type: application/json" \
  -d '{
    "content": "# My Feature\n\n## Features\n\n### User Login\n**Description:** Allow users to login.",
    "format": "markdown"
  }'
```

#### Get PRD
```bash
# Get parsed PRD by ID
curl http://localhost:8000/api/prd/{prd_id}
```

#### Analyze PRD
```bash
# Analyze PRD for ambiguities and quality
curl -X POST http://localhost:8000/api/prd/{prd_id}/analyze
```

### Ticket Endpoints

#### Preview Tickets
```bash
# Preview ticket drafts without creating in Jira
curl -X POST http://localhost:8000/api/tickets/preview \
  -H "Content-Type: application/json" \
  -d '{
    "prd_id": "uuid-here",
    "project_key": "PROJ"
  }'
```

#### Create Tickets
```bash
# Create tickets in Jira (requires OAuth)
curl -X POST http://localhost:8000/api/tickets/create \
  -H "Content-Type: application/json" \
  -d '{
    "prd_id": "uuid-here",
    "project_key": "PROJ"
  }'
```

#### Get Batch Status
```bash
# Get batch creation status
curl http://localhost:8000/api/tickets/batch/{batch_id}
```

### OAuth Endpoints

#### Check OAuth Status
```bash
# Check Jira OAuth connection status
curl http://localhost:8000/api/oauth/jira/status
```

## API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## Architecture

```
src/specflow/api/
├── main.py           # FastAPI app factory and health check
├── schemas.py        # Request/response Pydantic models
├── routes/
│   ├── prd.py       # PRD parsing and analysis endpoints
│   ├── tickets.py   # Ticket preview and creation endpoints
│   └── oauth.py     # OAuth authentication endpoints
```

## Features

- ✅ CORS middleware configured
- ✅ Request/response validation with Pydantic
- ✅ Auto-generated OpenAPI documentation
- ✅ Error handling with HTTP exceptions
- ✅ In-memory storage (replace with database for production)

## Testing

```bash
# Run API tests
pytest tests/test_api/ -v

# Run with coverage
pytest tests/test_api/ --cov=src/specflow/api --cov-report=term-missing
```

## Production Deployment

Before deploying to production:

1. Replace in-memory storage with database (PostgreSQL/SQLite)
2. Configure CORS origins for your domain
3. Set up OAuth credentials for Jira
4. Add authentication middleware
5. Configure rate limiting
6. Set up logging and monitoring
