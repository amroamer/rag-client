# RAGFlow Data Governance Gateway

FastAPI gateway that exposes your five RAGFlow data governance agents as a single unified REST API.

## Architecture

```
External Client / Postman
        ↓  POST /agent/run  (port 8000)
  dg-gateway  (FastAPI container)
        ↓  POST /api/v1/agents/{id}/completions
  ragflow-server  (port 80, internal Docker network)
        ↓
  Ollama  (Qwen2.5:7b)
```

## Registered Agents

| Agent Name | Description |
|---|---|
| `ndmo-classification` | NDMO 4-tier data sensitivity classification |
| `pii-detection` | PII scanning (GDPR/PDPL aligned) |
| `business-definitions` | Bilingual EN/AR business glossary |
| `report-tester` | Automated data quality validation |
| `dq-rules-generator` | Implementable DQ rules from dataset |

---

## Setup

### 1. Find your RAGFlow Docker network name

```bash
docker network ls
# Look for something like: ragflow_ragflow  or  docker_ragflow
```

If the name differs from `ragflow_ragflow`, update `docker-compose.yml`:
```yaml
networks:
  your_actual_network_name:   # ← change this
    external: true
```

And set `RAGFLOW_BASE_URL` to match the RAGFlow service name:
```bash
docker network inspect ragflow_ragflow
# Look for the container name under "Containers" — e.g. "ragflow-server"
```

### 2. Get your RAGFlow API key

RAGFlow UI → click your avatar (top right) → **API Key** → copy the key.

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your actual values:
#   RAGFLOW_API_KEY=ragflow-xxxxxxxxxxxx
#   FASTAPI_API_KEY=choose-a-strong-secret
```

### 4. Build and start

```bash
docker compose up -d --build
```

### 5. Verify

```bash
curl http://localhost:8000/health
# → {"status":"ok","agents_registered":5}
```

---

## API Usage

All endpoints except `/health` require the `X-API-Key` header.

### List available agents

```bash
curl http://localhost:8000/agents \
  -H "X-API-Key: your-secret-api-key-here"
```

### Run an agent

```bash
curl -X POST http://localhost:8000/agent/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-here" \
  -d '{
    "agent": "ndmo-classification",
    "input": "column_name: national_id\ndata_type: VARCHAR(10)\nsample_values: 1089456723\ntable_name: employees"
  }'
```

**Response:**
```json
{
  "request_id": "a1b2c3d4-...",
  "agent": "ndmo-classification",
  "agent_title": "NDMO Data Classification",
  "session_id": "abc123...",
  "answer": "{\"classifications\": [...]}",
  "output_format": "json"
}
```

### Continue a conversation (pass session_id back)

```bash
curl -X POST http://localhost:8000/agent/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-here" \
  -d '{
    "agent": "ndmo-classification",
    "input": "Now classify these columns too: ...",
    "session_id": "abc123..."
  }'
```

### PII Detection example

```bash
curl -X POST http://localhost:8000/agent/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-here" \
  -d '{
    "agent": "pii-detection",
    "input": "Scan the following data elements for PII:\n\n--- Column 1 ---\ncolumn_name: email\ndata_type: VARCHAR(255)\nsample_values: ahmed@gmail.com\ntable_name: users"
  }'
```

### Report Tester — pass raw CSV

```bash
curl -X POST http://localhost:8000/agent/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-here" \
  -d '{
    "agent": "report-tester",
    "input": "Analyze this report for data quality issues:\n\ninvoice_id,customer_name,...\nINV-001,Mohammed Al-Ghamdi,..."
  }'
```

---

## Interactive API Docs

Once running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## Troubleshooting

**`503 Cannot reach RAGFlow`**
- Check that `RAGFLOW_BASE_URL` uses the Docker service name, not `localhost`
- Run `docker network inspect ragflow_ragflow` to confirm the service name

**`504 Gateway Timeout`**
- Increase `RAGFLOW_TIMEOUT` in `.env` (default 120s)
- Ollama may be loading the model cold — retry once

**`502 RAGFlow returned HTTP 401`**
- Your `RAGFLOW_API_KEY` is wrong or expired — regenerate in RAGFlow UI

**`403 Invalid API key`**
- The `X-API-Key` header value doesn't match `FASTAPI_API_KEY` in `.env`

---

## Updating Agent IDs

If you recreate agents in RAGFlow, update the IDs in `agents.py`:

```python
AGENT_REGISTRY = {
    "ndmo-classification": {
        "id": "your-new-agent-id-here",
        ...
    },
    ...
}
```

Then rebuild: `docker compose up -d --build`
