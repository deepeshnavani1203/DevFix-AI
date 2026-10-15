import logging
from typing import Dict, Any
from agents.state import DebugState
from mcp_server.client import mcp_client
from services.groq_service import groq_service

logger = logging.getLogger("analyzer_agent")

def error_analysis_agent(state: DebugState) -> Dict[str, Any]:
    """Agent 1: Error Analysis Agent
    1. Runs MCP static code analysis (AST, functions, risky calls).
    2. Runs MCP error log analysis (tracebacks, exception type, frames).
    3. Synthesizes error type, line, root causes, and hypotheses.
    """
    code = state.get("code", "")
    error_msg = state.get("error_message", "")
    mcp_calls = list(state.get("mcp_calls_made", []))
    logs = list(state.get("workflow_logs", []))

    logs.append("Error Analysis Agent: Inspecting AST and Traceback via MCP tools...")

    # 1. Real MCP tool call: analyze_code
    ast_result = mcp_client.analyze_code(code)
    mcp_calls.append("analyze_code")

    # 2. Real MCP tool call: read_error_log
    traceback_result = mcp_client.read_error_log(error_msg)
    mcp_calls.append("read_error_log")

    # 3. LLM analysis (Groq) with fallbacks
    analysis_res = groq_service.analyze_error(
        code=code,
        error_message=error_msg,
        ast_info=ast_result
    )

    detected_error_type = (
        analysis_res.get("error_type")
        or traceback_result.get("exception_type")
        or "RuntimeError"
    )

    detected_line = (
        analysis_res.get("error_line")
        or traceback_result.get("probable_line")
        or ast_result.get("syntax_error_line")
    )

    root_cause = analysis_res.get("root_cause") or traceback_result.get("message") or "Unspecified runtime anomaly."
    summary = analysis_res.get("summary") or f"Issue identified as {detected_error_type}."
    hypotheses = analysis_res.get("hypotheses") or ["Uncaught exception in execution flow", "Missing input validation"]

    logs.append(f"Error Analysis Agent: Identified {detected_error_type} at line {detected_line}.")

    return {
        "ast_analysis": ast_result,
        "traceback_details": traceback_result,
        "error_type": detected_error_type,
        "error_line": detected_line,
        "root_cause": root_cause,
        "error_summary": summary,
        "hypotheses": hypotheses,
        "mcp_calls_made": mcp_calls,
        "workflow_logs": logs,
    }
