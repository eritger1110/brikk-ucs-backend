# Brikk UCS Backend

Universal Connector System backend for the Brikk AI workforce platform.

## Features

- **Integration Registry** - Manage 56+ pre-built integrations
- **Connector Generation Service** - AI-powered connector generation from API docs
- **Integration Execution Engine** - Runtime for executing integration API calls
- **Auto-Repair Service** - Self-healing integrations (coming soon)

## Tech Stack

- FastAPI (Python 3.11)
- OpenAI GPT-4 (LLM)
- Uvicorn (ASGI server)

## Deployment

### Railway (Recommended)

1. Click "Deploy on Railway" button below
2. Set environment variables:
   - `OPENAI_API_KEY` - Your OpenAI API key
   - `CORS_ORIGINS` - Your dashboard URL
3. Deploy!

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/new)

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY=sk-proj-...
export CORS_ORIGINS=http://localhost:3000

# Run server
uvicorn ucs_main:app --reload --port 8000
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for LLM-powered generation |
| `CORS_ORIGINS` | Yes | Comma-separated allowed origins |
| `PORT` | No | Port (Railway auto-assigns) |

## API Endpoints

### Health Check
```
GET /health
```

### Integrations
```
GET    /api/v1/integrations
GET    /api/v1/integrations/{id}
POST   /api/v1/integrations/{id}/install
DELETE /api/v1/integrations/{id}/install
POST   /api/v1/integrations/{id}/execute
```

### Connector Generation
```
POST /api/v1/ucs/generate/openapi
POST /api/v1/ucs/generate/postman
POST /api/v1/ucs/generate/url
POST /api/v1/ucs/generate/text
POST /api/v1/ucs/generate/samples
```

## Documentation

See [RAILWAY_DEPLOYMENT_GUIDE.md](https://github.com/eritger1110/brikk-platform/blob/main/RAILWAY_DEPLOYMENT_GUIDE.md) for complete deployment instructions.

## License

Proprietary - Brikk AI Platform

## Support

- Email: support@getbrikk.com
- Docs: https://docs.getbrikk.com
