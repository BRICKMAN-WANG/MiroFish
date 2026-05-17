# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MiroFish is a next-generation AI prediction engine powered by multi-agent technology. It creates high-fidelity parallel digital worlds by extracting seed information from real-world sources (news, policy drafts, financial signals) and simulating thousands of intelligent agents with independent personalities, long-term memory, and behavioral logic.

**Core Purpose**: "A Simple and Universal Swarm Intelligence Engine, Predicting Anything" (简洁通用的群体智能引擎，预测万物)

## Development Commands

### Setup and Installation

```bash
# Install all dependencies (Node.js + Python)
npm run setup:all

# Install only Node.js dependencies (root + frontend)
npm run setup

# Install only Python backend dependencies (uses uv)
npm run setup:backend

# Update Python dependencies after pulling new code
cd backend && uv sync
```

### Running the Application

```bash
# Start both frontend and backend concurrently (development)
npm run dev

# Start only the backend (Flask API on port 5001)
npm run backend

# Start only the frontend (Vue dev server on port 3000)
npm run frontend
```

### Building for Production

```bash
# Build frontend for production
npm run build
```

### Testing

```bash
# Run Python test scripts
cd backend && python scripts/test_profile_format.py

# Run pytest tests (if any exist in the future)
cd backend && uv run python -m pytest
```

### Docker Deployment

```bash
# Build and start with Docker Compose
docker compose up -d

# View logs
docker compose logs -f
```

The Docker image is available at `ghcr.io/666ghj/mirofish:latest`.

## Configuration

### Essential Environment Variables

Create `.env` from `.env.example` with:

```env
# LLM API (OpenAI SDK-compatible, tested with Alibaba Bailian Qwen-plus)
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_NAME=qwen-plus

# Zep Cloud (entity memory and graph storage)
ZEP_API_KEY=your_zep_api_key_here
```

### Important Config Details

- **Backend config** (`backend/app/config.py`): `JSON_AS_ASCII = False` is critical — without it, Chinese characters are rendered as `\uXXXX` in JSON responses.
- **Frontend API URL** (`frontend/src/api/index.js`): Configured via `VITE_API_BASE_URL` env var, defaults to `http://localhost:5001`.
- **Required check**: `LLM_API_KEY` and `ZEP_API_KEY` are validated at startup — app exits if missing.
- **File uploads**: Max 50MB, allowed extensions: `pdf, md, txt, markdown`.

## Architecture

### 5-Step Workflow

1. **Graph Building**: Upload seed documents → LLM generates ontology (entity/edge types) → Split text into chunks → Build GraphRAG in Zep Cloud
2. **Environment Setup**: Read entities from Zep graph → Filter by ontology types → Generate OASIS agent profiles (with LLM persona) → LLM generates simulation config (time, agents, events)
3. **Simulation**: Twitter/Reddit dual-platform parallel simulation via OASIS framework — spawned as subprocesses managed by SimulationRunner
4. **Report Generation**: ReportAgent uses Zep tools (search, entity, statistics) to query the graph and simulation DB, generates structured markdown report
5. **Deep Interaction**: Interview agents in the running OASIS environment, or chat with ReportAgent

### Backend (Python/Flask)

Located at `backend/`, uses Flask + Flask-CORS, managed via `uv` package manager.

**Application entry point**: `run.py` — validates config, creates Flask app via the app factory, starts on `0.0.0.0:5001`.

**App factory** (`app/__init__.py`): Creates Flask app, configures CORS, JSON encoding, request logging middleware, registers 3 blueprints, and registers simulation process cleanup.

**API Blueprints** (all routes return `{"success": bool, "data": ..., "error": ...}`):

| Blueprint | Prefix | File | Key Endpoints |
|-----------|--------|------|---------------|
| graph | `/api/graph` | `app/api/graph.py` | `/ontology/generate`, `/build`, `/data/<graph_id>`, `/task/<task_id>`, `/project/*` |
| simulation | `/api/simulation` | `app/api/simulation.py` | `/create`, `/prepare`, `/start`, `/stop`, `/interview`, `/entities/<graph_id>`, `/run-status` |
| report | `/api/report` | `app/api/report.py` | `/generate`, `/chat`, `/tools/search`, `/<report_id>/sections` |

**Key Services** (in `app/services/`):

| Service | File | Purpose |
|---------|------|---------|
| TextProcessor | `text_processor.py` | Document text extraction, chunking with overlap |
| OntologyGenerator | `ontology_generator.py` | LLM-based entity/edge type extraction from documents |
| GraphBuilderService | `graph_builder.py` | Zep Cloud graph construction (create, set ontology, add text batches, wait for episodes) |
| ZepEntityReader | `zep_entity_reader.py` | Read/filter entities from Zep graph by ontology type |
| OasisProfileGenerator | `oasis_profile_generator.py` | Generate OASIS agent profiles (Twitter CSV + Reddit JSON) from entities |
| SimulationConfigGenerator | `simulation_config_generator.py` | LLM generates time config, agent behaviors, event config |
| SimulationManager | `simulation_manager.py` | Simulation CRUD, state persistence, prepare orchestration |
| SimulationRunner | `simulation_runner.py` | Spawn/manage OASIS subprocesses, action logging, run state, interview |
| ReportAgent | `report_agent.py` | Report generation with tool-calling agent (Zep search + statistics), chat |
| ZepTools | `zep_tools.py` | Tool wrappers for ReportAgent (graph search, entity lookup, statistics) |

**Key Models** (in `app/models/`):
- `task.py`: `TaskManager` singleton — thread-safe in-memory task tracking for async operations (polled by frontend)
- `project.py`: `ProjectManager` — file-based persistent project storage via JSON metadata

### Frontend (Vue.js 3)

Located at `frontend/`, uses Vue 3 + Vue Router (history mode) + Vite + axios.

**Routes** (`frontend/src/router/index.js`):

| Path | View | Purpose |
|------|------|---------|
| `/` | Home.vue | Landing page, history list |
| `/process/:projectId` | MainView.vue | 5-step workflow (graph build) |
| `/simulation/:simulationId` | SimulationView.vue | Simulation details and env setup |
| `/simulation/:simulationId/start` | SimulationRunView.vue | Run simulation (monitor rounds) |
| `/report/:reportId` | ReportView.vue | View generated report |
| `/interaction/:reportId` | InteractionView.vue | Interview agents / chat with ReportAgent |

**Key Components** (`frontend/src/components/`):
- `Step1GraphBuild.vue` through `Step5Interaction.vue` — step components
- `GraphPanel.vue` — D3.js graph visualization
- `HistoryDatabase.vue` — historical project browser

**API layer** (`frontend/src/api/`): axios instance with 5min timeout, response interceptor checks `success` field, `requestWithRetry()` helper with exponential backoff.

## Key Architectural Patterns

### Async Task Polling

Long-running operations (graph building, simulation prep, report generation) use this pattern:

1. Backend creates a `TaskManager` task with `task_id`, starts a background `threading.Thread`
2. Frontend immediately gets `{ "task_id": "task_xxx", "success": true }`
3. Frontend polls `/api/graph/task/{task_id}` or equivalent status endpoints
4. Backend updates task progress via `task_manager.update_task()` with progress %, message, and progress_detail
5. Task completes with `COMPLETED` status and `result` dict, or `FAILED` with `error`

### Simulation Process Management

- OASIS simulations run as **subprocesses** (not threads), spawned by `SimulationRunner`
- State tracked in `run_state.json` (rounds, platform status, PID)
- Actions logged to `actions.jsonl`, also mirrored to SQLite DB per platform (`twitter_simulation.db`, `reddit_simulation.db`)
- `SimulationRunner.register_cleanup()` ensures processes are killed on server shutdown
- Interview mode: after simulation completes rounds, OASIS enters "waiting for command" mode — `SimulationRunner.interview_agent()` sends queries via stdin/stdout pipes

### Zep Entity Flow

1. `GraphBuilderService` creates graph → adds text chunks → waits for Zep to process episodes
2. `ZepEntityReader.filter_defined_entities()` reads all nodes, filters by ontology-defined types (not just generic `Entity` label)
3. `OasisProfileGenerator` takes filtered entities + their edges → generates agent profiles (LLM-enriched personas)
4. `SimulationConfigGenerator` takes profiles + simulation requirement → LLM generates full config (time, agent behaviors, events)

## Important Development Notes

- **Windows encoding**: `run.py` sets UTF-8 for stdout/stderr before any imports. If adding new entry points, replicate this pattern.
- **JSON Chinese encoding**: `app/__init__.py` sets `app.json.ensure_ascii = False` — always preserve this when modifying Flask config.
- **Third-party warnings**: `resource_tracker` warnings from multiprocessing libs are suppressed in `app/__init__.py`.
- **Simulation scripts** live in `backend/scripts/` (not copied to simulation dirs) — `run_twitter_simulation.py`, `run_reddit_simulation.py`, `run_parallel_simulation.py`, `action_logger.py`.
- **OASIS version compatibility**: Uses `camel-oasis==0.2.5` and `camel-ai==0.2.78` — pinned in `pyproject.toml`.
