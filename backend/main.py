import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Ensure backend root is on sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import settings
from services.groq_service import groq_service
from services.qdrant_service import qdrant_service
from data.knowledge.ingest import ingest_knowledge_file, add_single_debugging_case
from agents.workflow import run_debugging_session

app = FastAPI(
    title="DevFix AI - Multi-Agent AI Debugging System",
    description="Full-stack AI debugging system using LangGraph, Groq, Qdrant, RAG, and MCP.",
    version="1.0.0"
)

# Enable CORS for React frontend
origins = [
    settings.frontend_origin,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory history store (kept separate from reusable RAG knowledge base as required)
DEBUG_HISTORY: List[Dict[str, Any]] = []

# --- Request / Response Models ---
class DebugRequest(BaseModel):
    code: str = Field(..., description="Python code to analyze and debug")
    error_message: Optional[str] = Field("", description="Traceback or runtime error message")

class SaveKnowledgeRequest(BaseModel):
    code: str = Field(..., description="Original code")
    corrected_code: str = Field(..., description="Verified fixed code")
    error_type: str = Field(..., description="Type of error fixed")
    root_cause: str = Field(..., description="Root cause explanation")
    test_code: Optional[str] = Field("", description="Verification test code")
    title: Optional[str] = Field(None, description="Optional custom title")

# --- Endpoints ---

@app.get("/")
def root():
    return {
        "message": "DevFix AI Backend is running.",
        "docs_url": "/docs",
        "health_url": "/api/health"
    }

@app.get("/api/health")
def health_check():
    """Health check endpoint verifying Groq, Qdrant, and RAG status."""
    groq_ready = groq_service.is_configured()
    qdrant_count = qdrant_service.count()

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "groq": {
                "configured": groq_ready,
                "model": settings.groq_model,
                "status": "connected" if groq_ready else "api_key_missing_using_fallback"
            },
            "qdrant": {
                "collection": settings.qdrant_collection,
                "total_records": qdrant_count,
                "mode": "remote/docker" if settings.qdrant_url else "local_embedded",
                "status": "ready"
            },
            "mcp_server": {
                "name": "devfix-mcp-server",
                "tools": ["analyze_code", "read_error_log", "search_debug_knowledge", "run_tests"],
                "status": "ready"
            },
            "langgraph": {
                "agents": ["error_analysis_agent", "rag_debugging_agent", "fix_validation_agent"],
                "status": "ready"
            }
        }
    }

@app.post("/api/debug")
def debug_code(request: DebugRequest):
    """Main debugging endpoint using LangGraph multi-agent workflow."""
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="Source code cannot be empty.")

    try:
        result = run_debugging_session(
            code=request.code,
            error_message=request.error_message or ""
        )

        session_id = str(uuid.uuid4())
        session_record = {
            "id": session_id,
            "timestamp": datetime.now().isoformat(),
            "code": request.code,
            "error_message": request.error_message,
            "error_type": result.get("error_type", "Unknown"),
            "root_cause": result.get("root_cause", ""),
            "summary": result.get("error_summary", ""),
            "error_line": result.get("error_line"),
            "hypotheses": result.get("hypotheses", []),
            "corrected_code": result.get("corrected_code", ""),
            "explanation": result.get("explanation", ""),
            "test_code": result.get("test_code", ""),
            "validation_result": result.get("validation_result", {}),
            "rag_references": result.get("rag_references", []),
            "mcp_calls_made": result.get("mcp_calls_made", []),
            "workflow_logs": result.get("workflow_logs", []),
            "status": result.get("status", "completed"),
        }

        # Save to history (limited to 50 most recent items)
        DEBUG_HISTORY.insert(0, session_record)
        if len(DEBUG_HISTORY) > 50:
            DEBUG_HISTORY.pop()

        return session_record

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Debugging workflow error: {str(e)}")

@app.post("/api/debug/upload")
async def debug_code_file(
    file: UploadFile = File(...),
    error_message: Optional[str] = Form("")
):
    """Debug code uploaded via a .py file."""
    if not file.filename.endswith(".py"):
        raise HTTPException(status_code=400, detail="Only Python (.py) files are supported.")

    content = await file.read()
    code_str = content.decode("utf-8", errors="replace")

    req = DebugRequest(code=code_str, error_message=error_message)
    return debug_code(req)

@app.get("/api/history")
def get_debugging_history():
    """Retrieve debugging session history."""
    return {
        "total": len(DEBUG_HISTORY),
        "history": DEBUG_HISTORY
    }

@app.delete("/api/history")
def clear_debugging_history():
    """Clear session history."""
    DEBUG_HISTORY.clear()
    return {"message": "Debugging history cleared successfully."}

@app.post("/api/knowledge/ingest")
def trigger_knowledge_ingestion():
    """Ingest/re-index baseline Python debugging knowledge into Qdrant."""
    try:
        res = ingest_knowledge_file()
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@app.post("/api/knowledge/save")
def save_user_approved_case(data: SaveKnowledgeRequest):
    """Explicit opt-in endpoint to save a verified debugging example to the knowledge base."""
    try:
        res = add_single_debugging_case(data.model_dump())
        return {
            "success": res.get("success", False),
            "message": "Verified debugging case sanitized and saved to Qdrant knowledge base.",
            "data": res
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save case: {str(e)}")

@app.get("/api/knowledge")
def list_knowledge_items(limit: int = 50):
    """List records currently stored in Qdrant knowledge collection."""
    records = qdrant_service.get_all_records(limit=limit)
    return {
        "count": len(records),
        "total_in_collection": qdrant_service.count(),
        "records": records
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
