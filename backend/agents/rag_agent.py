import logging
from typing import Dict, Any
from agents.state import DebugState
from mcp_server.client import mcp_client

logger = logging.getLogger("rag_agent")

def rag_debugging_agent(state: DebugState) -> Dict[str, Any]:
    """Agent 2: RAG Debugging Agent
    Retrieves supporting reference patterns and documentation from Qdrant matching the submitted error.
    """
    req_id = state.get("request_id", "req-unknown")
    error_type = state.get("error_type", "")
    error_msg = state.get("error_message", "")
    root_cause = state.get("root_cause", "")
    code = state.get("code", "")
    mcp_calls = list(state.get("mcp_calls_made", []))
    logs = list(state.get("workflow_logs", []))

    logger.info(f"[{req_id}] Agent 2: Querying Qdrant for supporting knowledge on '{error_type}'")
    logs.append(f"[{req_id}] Agent 2: Querying Qdrant knowledge base for '{error_type}'...")

    # Formulate focused query from submitted code context
    query = f"{error_type} {root_cause}\n{error_msg[:150]}\n{code[:150]}"

    # Real MCP tool call: search_debug_knowledge with defensive error handling
    try:
        references = mcp_client.search_debug_knowledge(query=query, limit=3)
        mcp_calls.append("search_debug_knowledge")
    except Exception as e:
        logger.warning(f"[{req_id}] Agent 2: Qdrant query warning ({e}), continuing without citations.")
        references = []

    logger.info(f"[{req_id}] Agent 2: Retrieved {len(references)} supporting citations from Qdrant")
    logs.append(f"[{req_id}] Agent 2: Retrieved {len(references)} supporting citations from Qdrant vector database.")

    return {
        "rag_references": references,
        "mcp_calls_made": mcp_calls,
        "workflow_logs": logs,
    }
