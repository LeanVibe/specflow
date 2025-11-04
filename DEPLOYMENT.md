# SpecFlow Deployment Guide

## Quick Start

### Local Development

```bash
# Install dependencies
make install

# Run API server
make run-api

# Run CLI
make run-cli
```

### Docker Deployment

```bash
# Build and run with single command
make deploy-local

# Or step by step:
make docker-build
make docker-up

# View logs
make docker-logs

# Stop services
make docker-down
```

## Deployment Options

### 1. Docker Compose (Recommended)

**Production deployment:**
```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys

# Deploy
docker-compose up -d

# Check health
curl http://localhost:8000/health
```

**Development deployment:**
```bash
# Run with hot reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Or use make command
make deploy-dev
```

### 2. Docker Only

```bash
# Build image
docker build -t specflow:latest .

# Run container
docker run -d \
  -p 8000:8000 \
  -e OPENAI_API_KEY=your_key \
  -e JIRA_CLIENT_ID=your_id \
  -e JIRA_CLIENT_SECRET=your_secret \
  --name specflow-api \
  specflow:latest

# Check logs
docker logs -f specflow-api
```

### 3. Native (No Docker)

```bash
# Install with UV
uv sync

# Set environment variables
export OPENAI_API_KEY=your_key
export JIRA_CLIENT_ID=your_id
export JIRA_CLIENT_SECRET=your_secret

# Run API server
uvicorn specflow.api.main:app --host 0.0.0.0 --port 8000

# Or use CLI
specflow parse prd.md
```

## Environment Configuration

### Required Variables

```bash
# AI Provider (choose one or use multiple)
AI_PROVIDER=openai  # Options: openai, anthropic, gemini
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# GEMINI_API_KEY=...

# Jira OAuth
JIRA_CLIENT_ID=your-client-id
JIRA_CLIENT_SECRET=your-client-secret
JIRA_BASE_URL=https://your-company.atlassian.net
JIRA_REDIRECT_URI=http://localhost:8000/api/oauth/jira/callback
```

### Optional Variables

```bash
# Notion Integration
NOTION_API_KEY=secret_...

# Google Docs Integration
GOOGLE_DOCS_CREDENTIALS_FILE=/path/to/credentials.json

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

## Service Endpoints

After deployment, access:

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Parse PRD**: POST http://localhost:8000/api/prd/parse
- **Analyze PRD**: POST http://localhost:8000/api/prd/{id}/analyze
- **Preview Tickets**: POST http://localhost:8000/api/tickets/preview
- **OAuth Flow**: GET http://localhost:8000/api/oauth/jira/authorize

## Production Deployment

### Cloud Platforms

#### AWS ECS/Fargate

```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker build -t specflow .
docker tag specflow:latest <account>.dkr.ecr.us-east-1.amazonaws.com/specflow:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/specflow:latest

# Deploy via ECS task definition
# (See AWS console or use terraform)
```

#### Google Cloud Run

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/PROJECT_ID/specflow
gcloud run deploy specflow \
  --image gcr.io/PROJECT_ID/specflow \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

#### Azure Container Instances

```bash
# Build and push to ACR
az acr build --registry <registry-name> --image specflow:latest .

# Deploy container instance
az container create \
  --resource-group <resource-group> \
  --name specflow-api \
  --image <registry-name>.azurecr.io/specflow:latest \
  --dns-name-label specflow \
  --ports 8000
```

### Kubernetes

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: specflow
spec:
  replicas: 3
  selector:
    matchLabels:
      app: specflow
  template:
    metadata:
      labels:
        app: specflow
    spec:
      containers:
      - name: specflow
        image: specflow:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: specflow-secrets
              key: openai-api-key
---
apiVersion: v1
kind: Service
metadata:
  name: specflow-service
spec:
  selector:
    app: specflow
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

## Monitoring & Observability

### Health Checks

```bash
# Docker health check (automatic)
HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost:8000/health || exit 1

# Manual check
curl http://localhost:8000/health
# Response: {"status": "healthy", "version": "0.1.0"}
```

### Logging

```bash
# Docker logs
docker-compose logs -f specflow-api

# Filter by level
docker-compose logs specflow-api | grep ERROR

# Last 100 lines
docker-compose logs --tail=100 specflow-api
```

### Performance Monitoring

Add performance monitoring tools:

```python
# Example: Add Sentry for error tracking
# pip install sentry-sdk
import sentry_sdk
sentry_sdk.init(dsn="your-sentry-dsn")
```

## Scaling

### Horizontal Scaling

```yaml
# docker-compose.yml
services:
  specflow-api:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 1G
```

### Load Balancing

Use nginx as reverse proxy:

```nginx
upstream specflow {
    server specflow-api-1:8000;
    server specflow-api-2:8000;
    server specflow-api-3:8000;
}

server {
    listen 80;
    location / {
        proxy_pass http://specflow;
    }
}
```

## Troubleshooting

### Common Issues

**Container won't start:**
```bash
# Check logs
docker logs specflow-api

# Check environment
docker exec specflow-api env

# Verify health
docker inspect --format='{{.State.Health}}' specflow-api
```

**API returns 500 errors:**
```bash
# Check API keys are set
curl http://localhost:8000/health

# View detailed logs
docker-compose logs -f

# Test locally first
make run-api
```

**Port already in use:**
```bash
# Change port in docker-compose.yml
ports:
  - "8080:8000"  # Use 8080 instead of 8000
```

## Security Best Practices

1. **Never commit secrets**: Use environment variables
2. **Use secrets management**: AWS Secrets Manager, GCP Secret Manager
3. **Enable HTTPS**: Use reverse proxy with SSL
4. **Regular updates**: Keep dependencies updated
5. **Scan images**: Use `docker scan specflow:latest`

## Backup & Recovery

```bash
# Backup data volumes
docker run --rm -v specflow_data:/data -v $(pwd):/backup ubuntu tar czf /backup/data-backup.tar.gz /data

# Restore data
docker run --rm -v specflow_data:/data -v $(pwd):/backup ubuntu tar xzf /backup/data-backup.tar.gz -C /
```

## Development Workflow

```bash
# 1. Make code changes
vim src/specflow/api/routes/prd.py

# 2. Run tests
make test-fast

# 3. Lint code
make lint

# 4. Test in Docker
make docker-build
make docker-up-dev

# 5. Full validation
make validate

# 6. Deploy
make deploy-local
```

## Support

- **Documentation**: See README.md
- **Issues**: https://github.com/LeanVibe/specflow/issues
- **API Docs**: http://localhost:8000/docs (when running)
