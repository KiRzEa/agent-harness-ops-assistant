# Ops Assistant Agent Harness

An agent harness for an operations assistant. An OpenAI model can call three mock tools; the harness
controls everything around it: tool validation, retries and timeouts, malformed-response repair,
step and time limits, human approval before `create_incident`, persisted state, and a per-run trace.

Built with Python 3.12, FastAPI, LangChain + LangGraph, OpenAI, and MongoDB (Atlas Local, including vector search).

## Run it

Requirements: Docker, [uv](https://docs.astral.sh/uv/), an OpenAI API key.

```bash
cp .env.example .env            # then set OPENAI_API_KEY
docker compose up -d            # MongoDB Atlas Local on :27017
uv sync
uv run python -m src.seed       # embeds the runbooks and creates the vector index
```

### API

```bash
uv run uvicorn src.main:app

curl -X POST localhost:8000/runs -H 'content-type: application/json' \
  -d '{"objective":"search-service looks down. Check it and open an incident if needed."}'
# status AWAITING_APPROVAL, pending_approval shows the exact incident arguments

curl -X POST localhost:8000/runs/<run_id>/approve     # or /reject
curl localhost:8000/runs/<run_id>
curl localhost:8000/runs/<run_id>/trace
```

Endpoints: `POST /runs`, `GET /runs/{id}`, `GET /runs/{id}/trace`, `POST /runs/{id}/approve`,
`POST /runs/{id}/reject`, `GET /health`. Contract: `specs/001-agent-harness/contracts/openapi.yaml`.
A Postman collection is in `postman/ops-assistant.postman_collection.json` (set `base_url`; `run_id` is saved automatically).

### CLI

```bash
uv run python -m src.cli run "Is payments-api healthy and what does the runbook say?" --trace
```

If the assistant wants to open an incident, the CLI shows the arguments and asks `Approve? [y/N]`.

## Tests

```bash
uv run pytest            # offline: scripted fake LLM, needs only the MongoDB container
uv run pytest -m live    # optional: one smoke test against the real OpenAI API
```

The tests never call OpenAI: a scripted chat model replays success, failure, malformed and looping
responses. They cover success, tool retry/timeout/permanent failure, invalid tool output, malformed
model output, approve/reject/duplicate approval/changed arguments, resume after restart, step and
time limits, trace completeness, the API, and the CLI.

## Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | | OpenAI key (never committed; requests are sent with `store=False`) |
| `OPENAI_MODEL` | `gpt-4o-mini` | Chat model |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embeddings for the knowledge base |
| `MONGODB_URI` | `mongodb://localhost:27017/?directConnection=true` | MongoDB connection |
| `MONGODB_DB` | `ops_assistant` | Database name |
| `MAX_STEPS` | `8` | Max model turns per run |
| `MAX_RUN_SECONDS` | `60` | Max active run time (time waiting for approval is not counted) |
| `TOOL_TIMEOUT_SECONDS` | `5` | Timeout per tool attempt |
| `TOOL_MAX_RETRIES` | `2` | Retries for transient errors and timeouts |
| `MAX_REPAIRS` | `2` | Corrections allowed for malformed model responses |
| `FAILURE_MODE` | `none` | Demo only: `transient`, `permanent`, `timeout` or `invalid_output` makes the mock tools fail |

## Layout

```
src/
  main.py  cli.py  bootstrap.py  seed.py
  core/        config (settings), logging, enums (run, approval, event types), exceptions
  ai_models/   chat_model (OpenAI chat, store=False), embeddings
  services/    run_service (start, approve, reject, get run, trace)
  graph/       state, nodes, routing, builder    (the LangGraph agent loop)
  tools/       schemas, registry, executor (timeout, retry, validation), mock tools, failure injection
  store/       MongoDB client, one repository per collection (runs, approvals, incidents), event log
  api/         FastAPI app routes, dependencies, schemas
data/      services.json and 16 runbook documents (the mock dataset)
tests/     unit, integration, api, live
postman/   collection
docs/      REPORT.md (approach, database design, limitations)
specs/ is kept next to this repo (Spec Kit artifacts)
```
