import logging
import uuid
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from agents.state import DebugState
from agents.analyzer import error_analysis_agent
from agents.rag_agent import rag_debugging_agent
from agents.validator import fix_validation_agent

logger = logging.getLogger("workflow")

def build_debugging_workflow():
    """Builds and compiles the multi-agent LangGraph debugging workflow."""
    workflow = StateGraph(DebugState)

    # Register the 3 agent nodes
    workflow.add_node("error_analysis", error_analysis_agent)
    workflow.add_node("rag_debugging", rag_debugging_agent)
    workflow.add_node("fix_validation", fix_validation_agent)

    # Establish linear orchestrated execution flow
    workflow.add_edge(START, "error_analysis")
    workflow.add_edge("error_analysis", "rag_debugging")
    workflow.add_edge("rag_debugging", "fix_validation")
    workflow.add_edge("fix_validation", END)

    return workflow.compile()

# Pre-compiled workflow graph
debug_workflow = build_debugging_workflow()

def run_debugging_session(code: str, error_message: str, request_id: Optional[str] = None) -> Dict[str, Any]:
    """Runs a complete debugging session through the LangGraph multi-agent orchestrator."""
    req_id = request_id or f"req_{uuid.uuid4().hex[:8]}"

    logger.info(f"[{req_id}] Starting LangGraph workflow with submitted code ({len(code)} chars)")

    initial_state: DebugState = {
        "request_id": req_id,
        "code": code,
        "error_message": error_message,
        "mcp_calls_made": [],
        "workflow_logs": [f"[{req_id}] Initiating DevFix AI Multi-Agent Workflow..."],
        "status": "in_progress",
    }
    
    final_state = debug_workflow.invoke(initial_state)
    logger.info(f"[{req_id}] LangGraph workflow completed. Final status: {final_state.get('status')}")
    return final_state
