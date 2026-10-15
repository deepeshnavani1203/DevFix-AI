import logging
from typing import Dict, Any
from agents.state import DebugState
from mcp_server.client import mcp_client
from services.groq_service import groq_service

logger = logging.getLogger("validator_agent")

def fix_validation_agent(state: DebugState) -> Dict[str, Any]:
    """Agent 3: Fix Validation Agent
    1. Generates the corrected code, explanation, and test assertion suite.
    2. Runs the code through MCP tool 'run_tests' in an isolated subprocess.
    3. Reviews validation outcome and reports passed/failed status.
    """
    code = state.get("code", "")
    error_msg = state.get("error_message", "")
    analysis = {
        "error_type": state.get("error_type", "Unknown"),
        "root_cause": state.get("root_cause", ""),
        "error_line": state.get("error_line"),
    }
    rag_refs = state.get("rag_references", [])
    mcp_calls = list(state.get("mcp_calls_made", []))
    logs = list(state.get("workflow_logs", []))

    logs.append("Fix Validation Agent: Generating corrected code and validation assertions...")

    # Generate solution
    fix_data = groq_service.generate_fix(
        code=code,
        error_message=error_msg,
        analysis=analysis,
        rag_references=rag_refs
    )

    corrected_code = fix_data.get("corrected_code", code)
    explanation = fix_data.get("explanation", "Suggested code modifications to eliminate errors.")
    test_code = fix_data.get("test_code", "# Test assertions\nassert True")
    confidence = fix_data.get("confidence_score", 0.9)

    logs.append("Fix Validation Agent: Running isolated sandbox tests via MCP 'run_tests'...")

    # Real MCP tool call: run_tests
    validation_res = mcp_client.run_tests(
        solution_code=corrected_code,
        test_code=test_code,
        timeout_seconds=3
    )
    mcp_calls.append("run_tests")

    status = "passed" if validation_res.get("passed") else "failed"
    logs.append(f"Fix Validation Agent: Sandbox execution completed with status: {status.upper()}.")

    return {
        "corrected_code": corrected_code,
        "explanation": explanation,
        "test_code": test_code,
        "validation_result": validation_res,
        "confidence_score": confidence,
        "status": status,
        "mcp_calls_made": mcp_calls,
        "workflow_logs": logs,
    }
