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
`POST /runs/{id}/reject`, `GET /health`. Interactive API docs are served at `http://localhost:8000/docs`.
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

Expected result with MongoDB running: `74 passed, 1 deselected`.

- The deselected test is the `live` OpenAI smoke test. It is excluded by default because it needs an
  API key, network access and costs money; run it with `-m live`.
- Tests that need MongoDB skip themselves when `localhost:27017` is unreachable, so `52 skipped`
  means the container is not running (`docker compose up -d`). Each test uses its own throwaway
  database, which is dropped afterwards.
- The tests never call OpenAI: a scripted chat model replays success, failure, malformed and looping
  responses.

| Requirement | Where it is tested |
|---|---|
| Objective via API or CLI | `tests/api/` (`test_runs_api`, `test_flow`, `test_cli`) |
| LLM-tool loop, parallel tool calls | `integration/test_happy_path`, `test_mixed_calls`, `test_no_tools` |
| Input and output validation | `unit/test_schemas`, `integration/test_malformed_llm`, `test_tool_failures` |
| Tool errors, timeouts, retries | `unit/test_tool_executor`, `integration/test_tool_failures` |
| Malformed model output and repair | `integration/test_malformed_llm` |
| Step and time limits | `integration/test_limits`, `test_pause_excludes_time` |
| Approval, rejection, duplicates, changed arguments | `integration/test_approval_pause`, `test_approval_integrity` |
| Resume after restart | `integration/test_resume_after_restart` |
| Trace, logs, run state | `integration/test_trace`, `test_store`, `unit/test_config_logging` |
| Tool output treated as data, no OpenAI storage | `integration/test_untrusted_tool_output`, `unit/test_chat_model` |
| Knowledge base vector search | `integration/test_kb_vector_search`, `unit/test_tools` |

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
docs/      slide deck (Agent-Harness-Slides.pdf and .pptx)
```
