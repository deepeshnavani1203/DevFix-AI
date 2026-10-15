import logging
from typing import Dict, Any
from agents.state import DebugState
from mcp_server.client import mcp_client

logger = logging.getLogger("rag_agent")

def rag_debugging_agent(state: DebugState) -> Dict[str, Any]:
    """Agent 2: RAG Debugging Agent
    Retrieves related documentation, official patterns, and verified previous debugging fixes from Qdrant.
    """
    error_type = state.get("error_type", "")
    error_msg = state.get("error_message", "")
    root_cause = state.get("root_cause", "")
    code = state.get("code", "")
    mcp_calls = list(state.get("mcp_calls_made", []))
    logs = list(state.get("workflow_logs", []))

    logs.append(f"RAG Debugging Agent: Querying Qdrant for similar cases matching '{error_type}'...")

    # Formulate rich search query
    query = f"{error_type} {root_cause}\n{error_msg[:200]}\n{code[:200]}"

    # Real MCP tool call: search_debug_knowledge
    references = mcp_client.search_debug_knowledge(query=query, limit=3)
    mcp_calls.append("search_debug_knowledge")

    logs.append(f"RAG Debugging Agent: Retrieved {len(references)} verified references from Qdrant.")

    return {
        "rag_references": references,
        "mcp_calls_made": mcp_calls,
        "workflow_logs": logs,
    }
