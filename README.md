# DevFix AI — Multi-Agent AI Debugging System

**DevFix AI** is an autonomous multi-agent debugging system for Python code. It combines static AST code analysis, traceback parsing, vector similarity retrieval (RAG) using **Qdrant**, multi-agent orchestration via **LangGraph**, **Groq** LLM inference, and safe sandboxed test execution through the official **Python Model Context Protocol (MCP)** SDK.

---

## 🏗️ Architecture & Multi-Agent Flow

```
[ User Code / Traceback ]
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│                 LangGraph Orchestrator                     │
│                                                             │
│  ┌───────────────────────┐       ┌───────────────────────┐  │
│  │ 1. Error Analysis     │       │ 2. RAG Debugging      │  │
│  │    Agent              │ ────> │    Agent              │  │
│  │    - MCP analyze_code │       │    - MCP search_debug │  │
│  │    - MCP read_log     │       │      _knowledge       │  │
│  └───────────────────────┘       └───────────────────────┘  │
│                                              │              │
│                                              ▼              │
│                                  ┌───────────────────────┐  │
│                                  │ 3. Fix Validation     │  │
│                                  │    Agent              │  │
│                                  │    - Groq Synthesis   │  │
│                                  │    - MCP run_tests    │  │
│                                  └───────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
           [ Verified Fix + Sandboxed Test Proof ]
```

### 1. Error Analysis Agent
- Calls MCP `analyze_code`: Parses the code's Python AST, identifies syntax validity, functions, classes, and flags dangerous functions (`eval`, `exec`, `os.system`).
- Calls MCP `read_error_log`: Extracts exception types, line numbers, and traceback frames.
- Analyzes root causes and formulates hypotheses using Groq.

### 2. RAG Debugging Agent
- Calls MCP `search_debug_knowledge`: Computes dense embeddings with `sentence-transformers/all-MiniLM-L6-v2` and queries Qdrant.
- Retrieves verified reference cases and official troubleshooting patterns matching the detected error.

### 3. Fix Validation Agent
- Synthesizes the corrected code and automated verification assertions.
- Calls MCP `run_tests`: Executes the fix and assertions in an isolated Python subprocess with a strict 3-second timeout and security safeguards.
- Returns verified results with stdout/stderr and execution time in milliseconds.

---

## 📁 Project Structure

```
DevFixAI/
├── frontend/                     # React + Vite Developer Dashboard
│   ├── src/
│   │   ├── App.jsx               # Dashboard UI (Studio, Knowledge, History)
│   │   ├── index.css             # Dark developer theme & glassmorphism
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── backend/
│   ├── main.py                   # FastAPI Application & Endpoints
│   ├── config.py                 # Pydantic Settings & Environment Loader
│   ├── agents/                   # LangGraph Multi-Agent Architecture
│   │   ├── state.py              # DebugState TypedDict
│   │   ├── analyzer.py           # Agent 1: Error Analysis Agent
│   │   ├── rag_agent.py          # Agent 2: RAG Debugging Agent
│   │   ├── validator.py          # Agent 3: Fix Validation Agent
│   │   └── workflow.py           # LangGraph StateGraph orchestrator
│   ├── rag/                      # Embeddings, Chunking, Retrieval
│   │   ├── embeddings.py         # sentence-transformers all-MiniLM-L6-v2
│   │   ├── chunking.py           # Document chunker & metadata mapper
│   │   └── retriever.py          # Qdrant semantic similarity search
│   ├── mcp_server/               # Official Python MCP SDK Implementation
│   │   ├── server.py             # MCPServer exposing 4 debugging tools
│   │   └── client.py             # DevFixMCPClient invoked by agents
│   ├── services/
│   │   ├── groq_service.py       # Groq API client with structured outputs
│   │   └── qdrant_service.py     # Local embedded & remote Qdrant client
│   ├── data/
│   │   └── knowledge/
│   │       ├── python_errors.json # 35 baseline verified Python error cases
│   │       └── ingest.py         # Knowledge ingestion pipeline
│   ├── tests/                    # Pytest test suite (16 tests)
│   │   ├── test_ast_analysis.py
│   │   ├── test_safe_runner.py
│   │   ├── test_rag.py
│   │   └── test_endpoints.py
│   ├── .env                      # Local environment secrets (never commit)
│   ├── .env.example              # Template environment configuration
│   └── pyproject.toml            # uv dependencies specification
├── .gitignore
└── README.md
```

---

## 🛠️ Technology Stack

- **Backend**: Python 3.12+, FastAPI, Uvicorn
- **Package Management**: `uv` exclusively
- **LLM**: Groq API (`llama-3.3-70b-versatile` / `llama-3.1-8b-instant`)
- **Agent Orchestrator**: LangGraph
- **Vector Database**: Qdrant (local persistent embedded storage or Docker)
- **Embeddings**: `sentence-transformers` (`all-MiniLM-L6-v2`, 384 dimensions)
- **MCP**: Official Python Model Context Protocol SDK (`mcp` 2.x)
- **Frontend**: React 19, Vite, Lucide React, Vanilla CSS
- **Testing**: pytest, HTTPX TestClient

---

## 🚀 Quickstart Guide (Windows PowerShell)

### Step 1: Clone and Open Project
```powershell
cd C:\DevFix-AI
```

### Step 2: Configure Environment Variables
Copy `backend/.env.example` to `backend/.env` and paste your Groq API key:
```powershell
# In backend/.env:
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
QDRANT_URL=
QDRANT_COLLECTION=devfix_knowledge
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
FRONTEND_ORIGIN=http://localhost:5173
```
> **Note on Qdrant**: When `QDRANT_URL` is left blank, DevFix AI automatically runs Qdrant in **local embedded mode** using `./backend/qdrant_storage`. No Docker or cloud account is required! If you prefer Docker, set `QDRANT_URL=http://localhost:6333`.

### Step 3: Ingest Knowledge Base
Populate the vector database with the 35 verified Python error scenarios:
```powershell
cd C:\DevFix-AI\backend
uv run python data/knowledge/ingest.py
```

### Step 4: Run Backend Tests
Run the test suite to verify AST analysis, sandbox isolation, RAG, and endpoints:
```powershell
uv run pytest
```

### Step 5: Start the Backend Server
```powershell
uv run uvicorn main:app --reload --port 8000
```
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### Step 6: Start the React Frontend
In a separate PowerShell window:
```powershell
cd C:\DevFix-AI\frontend
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🔒 Security & Privacy

1. **Sandboxed Subprocess Execution**: Code is never executed directly in the main server process. It runs inside isolated subprocesses with restricted permissions, strict 3-second timeouts, and AST pre-checks.
2. **Disallowed Operations**: Unsafe calls such as `eval()`, `exec()`, `os.system()`, and `subprocess` are blocked before execution.
3. **Privacy Sanitizer**: When opting in to save solutions to the Qdrant knowledge base, API keys, passwords, and tokens (`sk-...`, `gsk_...`, `Bearer ...`) are automatically redacted with `[REDACTED_SECRET]`.
4. **Separation of History & Knowledge**: Debugging session history is stored separately from reusable vector knowledge. User code is never saved to the knowledge base without explicit user opt-in.
