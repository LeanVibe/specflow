# SpecFlow

**Kill spec drift, ship faster**

Transform PRDs into production-ready Jira tickets in 15 minutes.

## Overview

SpecFlow is an AI-powered tool that converts Product Requirements Documents (PRDs) into fully structured Jira tickets with acceptance criteria, test stubs, and priority scoring. Stop wasting 4+ hours per PRD on manual ticket creation.

## Features

- **Multi-format PRD parsing**: Markdown, Notion, Google Docs
- **AI-powered extraction**: Automatically identify features, requirements, and dependencies
- **Acceptance criteria generation**: Given/When/Then format with pydantic.ai
- **Ambiguity detection**: Flag vague requirements before implementation
- **Quality scoring**: Definition of Ready scores (0-100) for each feature
- **Jira integration**: OAuth 2.0 with bulk ticket creation
- **Test stub generation**: Unit, integration, and e2e test templates
- **Web UI + CLI**: HTMX dashboard and command-line interface

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourorg/specflow.git
cd specflow

# Install with UV
uv sync

# Set up environment
cp .env.example .env
# Edit .env with your API keys (OpenAI, Jira, etc.)
```

### Usage

#### CLI

```bash
# Parse a PRD
specflow parse docs/my-prd.md

# Generate tickets
specflow generate <prd-id> --project PROJ

# Analyze quality
specflow analyze <prd-id>

# Authenticate with Jira
specflow auth jira
```

#### Web UI

```bash
# Start the server
uvicorn specflow.main:app --reload

# Open browser to http://localhost:8000
```

#### API

```python
import httpx

# Upload and parse PRD
response = httpx.post(
    "http://localhost:8000/api/prd/parse",
    json={"content": "# My PRD\n\n...", "format": "markdown"}
)
prd = response.json()

# Generate tickets
response = httpx.post(
    f"http://localhost:8000/api/tickets/generate",
    json={"prd_id": prd["prd_id"], "project_key": "PROJ"}
)
```

## Development

### Setup

```bash
# Install dev dependencies
uv sync --extra dev

# Run tests
pytest

# Run with coverage
pytest --cov=specflow

# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/

# Type checking
mypy src/
```

### Architecture

```
src/specflow/
├── models/          # Pydantic data models
├── parsers/         # PRD parsers (Markdown, Notion, GDocs)
├── intelligence/    # AI-powered analysis with pydantic.ai
├── integrations/    # Jira, Linear, Asana clients
├── api/             # FastAPI endpoints
├── ui/              # HTMX templates
└── utils/           # Configuration and logging
```

## Configuration

See `.env.example` for all configuration options.

Required environment variables:
- `OPENAI_API_KEY` - OpenAI API key for pydantic.ai
- `JIRA_CLIENT_ID` - Jira OAuth client ID
- `JIRA_CLIENT_SECRET` - Jira OAuth client secret

Optional integrations:
- `NOTION_API_KEY` - For Notion PRD parsing
- `GOOGLE_DOCS_CREDENTIALS_FILE` - For Google Docs parsing
- `LINEAR_API_KEY` - For Linear integration

## MVP Roadmap

**Week 1: Core Parsing & AI**
- [x] Project setup with UV
- [x] Pydantic data models
- [ ] Markdown parser
- [ ] Notion parser
- [ ] Google Docs parser
- [ ] Feature extraction with pydantic.ai
- [ ] Acceptance criteria generation

**Week 2: Jira Integration**
- [ ] Jira OAuth 2.0 handler
- [ ] Jira API client
- [ ] Bulk ticket creation
- [ ] FastAPI endpoints
- [ ] CLI interface

**Week 3: Intelligence & Polish**
- [ ] Ambiguity detection
- [ ] Quality scoring (Definition of Ready)
- [ ] Web UI with HTMX
- [ ] Analytics and monitoring
- [ ] Documentation

## Contributing

This is currently an MVP in active development. Contributions welcome after initial release.

## License

MIT License - see LICENSE file for details.

## Support

- GitHub Issues: https://github.com/yourorg/specflow/issues
- Email: hello@specflow.dev

---

Built with ❤️ for product teams who ship fast
