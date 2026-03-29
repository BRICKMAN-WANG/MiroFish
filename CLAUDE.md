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

# Install only Python backend dependencies
npm run setup:backend
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
# Run Python test scripts (example: profile format validation)
cd backend
python scripts/test_profile_format.py
```

There is no formal test suite or linting configuration. Testing is currently done via individual Python scripts.

### Docker Deployment

```bash
# Build and start with Docker Compose
docker compose up -d

# View logs
docker compose logs -f
```

The Docker image is available at `ghcr.io/666ghj/mirofish:latest`.

## Architecture and Structure

### High-Level Architecture

MiroFish follows a **5-step workflow**:

1. **Graph Building**: Extract real-world seeds, inject individual/collective memory, build GraphRAG
2. **Environment Setup**: Entity relationship extraction, persona generation, agent configuration
3. **Simulation**: Twitter/Reddit dual-platform parallel simulation
4. **Report Generation**: ReportAgent with rich toolset for deep interaction
5. **Deep Interaction**: Chat with any agent in the simulated world

### Frontend (Vue.js 3)
- **Location**: `/frontend/`
- **Framework**: Vue 3 + Vue Router + Vite
- **Key Components**:
  - `src/views/MainView.vue` - Main application layout with 5-step workflow
  - `src/components/Step1GraphBuild.vue` through `Step5Interaction.vue` - Step components
  - `src/components/GraphPanel.vue` - D3.js graph visualization
  - `src/api/` - API service layer for backend communication
- **Build**: Vite-based, output to `frontend/dist/`

### Backend (Python/Flask)
- **Location**: `/backend/`
- **Framework**: Flask with Flask-CORS
- **Package Manager**: uv (modern Python package manager)
- **Key Services**:
  - `app/services/graph_builder.py` - GraphBuilderService for knowledge graph construction
  - `app/services/simulation_manager.py` - SimulationManager for Twitter/Reddit parallel simulation
  - `app/services/oasis_profile_generator.py` - Profile generation for OASIS simulation
  - `app/services/report_agent.py` - ReportAgent for prediction reports and interaction
  - `app/services/ontology_generator.py` - Ontology generation from seed materials
  - `app/services/text_processor.py` - Document processing (PDF, MD, TXT)
- **API Endpoints**: `app/api/` (graph.py, simulation.py, report.py)
- **Configuration**: `app/config.py` loads from root `.env` file
- **Entry Point**: `run.py` validates config and starts Flask app

### Key Dependencies
- **LLM Integration**: OpenAI SDK-compatible APIs (recommended: Alibaba Qwen-plus via Bailian Platform)
- **Memory/Graph**: Zep Cloud for entity memory and graph storage
- **Simulation Engine**: OASIS (Open Agent Social Interaction Simulations) from CAMEL-AI
- **File Processing**: PyMuPDF for PDFs, charset detectors for encoding detection

## Configuration Requirements

### Essential Environment Variables
Create `.env` from `.env.example` with:

```env
# LLM API (OpenAI SDK-compatible)
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1  # For Alibaba Qwen
LLM_MODEL_NAME=qwen-plus

# Zep Cloud (memory/graph storage)
ZEP_API_KEY=your_zep_api_key_here
```

**Note**: Both `LLM_API_KEY` and `ZEP_API_KEY` are required for the application to start.

### Optional Configuration
- `FLASK_DEBUG` - Enable/disable Flask debug mode (default: True)
- `FLASK_HOST` / `FLASK_PORT` - Override default host/port (0.0.0.0:5001)
- `OASIS_DEFAULT_MAX_ROUNDS` - Simulation rounds (default: 10)
- `REPORT_AGENT_MAX_TOOL_CALLS` - Report agent interaction limit (default: 5)

## Workflow Integration Points

### Graph Building Phase
- **Input**: Text documents (PDF, MD, TXT) via file upload
- **Process**: Text chunking → ontology generation → Zep graph construction
- **Output**: Graph ID and entity statistics

### Simulation Phase
- **Platforms**: Twitter (CSV profiles) and Reddit (JSON profiles)
- **Agents**: Generated from graph entities with personas
- **Execution**: Parallel simulation via OASIS framework

### Report Phase
- **Interaction**: ReportAgent queries simulation environment using tools
- **Output**: Structured prediction report with evidence citations
- **Deep Dive**: Direct conversation with simulated agents

## File Organization

```
MiroFish/
├── frontend/                 # Vue.js frontend application
│   ├── src/
│   │   ├── views/           # Application views (Home, Process, Simulation, Report, Interaction)
│   │   ├── components/      # Step components and UI widgets
│   │   ├── api/             # API service layer
│   │   └── router/          # Vue Router configuration
│   └── package.json         # Frontend dependencies
├── backend/                  # Python Flask backend
│   ├── app/
│   │   ├── api/             # Flask API endpoints (graph, simulation, report)
│   │   ├── services/        # Core business logic services
│   │   ├── models/          # Data models and task management
│   │   ├── utils/           # Utility functions (LLM client, logger, retry)
│   │   └── config.py        # Configuration management
│   ├── uploads/             # User uploads and simulation data
│   ├── scripts/             # Utility scripts (simulation runners, tests)
│   ├── run.py               # Application entry point
│   └── pyproject.toml       # Python dependencies (uv)
├── static/                   # Static assets (logos, screenshots)
├── docker-compose.yml        # Docker Compose configuration
├── Dockerfile               # Multi-stage Docker build
├── package.json             # Root npm scripts for development
└── .env.example             # Environment configuration template
```

## Development Notes

### API Communication
- Frontend communicates with backend at `http://localhost:5001`
- API endpoints follow REST patterns with JSON request/response
- Graph visualization uses D3.js with data from `/api/graph` endpoints

### Task Management
- Backend uses async task pattern for long-running operations (graph building, simulation)
- Task status is tracked via `TaskManager` in `app/models/task.py`
- Frontend polls for task completion status

### Error Handling
- Backend validates configuration on startup via `Config.validate()`
- Required APIs (LLM, Zep) must be configured or application exits
- File uploads limited to 50MB with allowed extensions (pdf, md, txt, markdown)

### Platform-Specific Considerations
- Windows: UTF-8 encoding configured in `run.py` to prevent console encoding issues
- Docker: Multi-stage build with Node.js + Python, exposes ports 3000 (frontend) and 5001 (backend)
- Development: Concurrently runs both services; production uses separate processes

## External Dependencies

### Required Services
1. **LLM API**: Any OpenAI SDK-compatible API (tested with Alibaba Bailian Qwen-plus)
2. **Zep Cloud**: Free tier available for memory and graph storage

### External Frameworks
- **OASIS**: Social simulation engine from CAMEL-AI (`camel-oasis`, `camel-ai`)
- **Zep Cloud Python SDK**: Graph and memory operations (`zep-cloud`)

### Development Tools
- **uv**: Modern Python package manager (replaces pip/venv)
- **Vite**: Frontend build tool and dev server
- **Concurrently**: Runs multiple npm commands in parallel