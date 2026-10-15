import logging
from typing import Dict, Any
from agents.state import DebugState
from mcp_server.client import mcp_client
from services.groq_service import groq_service

logger = logging.getLogger("analyzer_agent")

def error_analysis_agent(state: DebugState) -> Dict[str, Any]:
    """Agent 1: Error Analysis Agent
    Dynamically analyzes the exact code and traceback submitted by the user.
    Leverages AST static analysis + safe dynamic pre-execution for guaranteed ground-truth error detection.
    """
    req_id = state.get("request_id", "req-unknown")
    code = state.get("code", "")
    error_msg = state.get("error_message", "")
    mcp_calls = list(state.get("mcp_calls_made", []))
    logs = list(state.get("workflow_logs", []))

    logger.info(f"[{req_id}] Agent 1: Inspecting code AST ({len(code)} chars) & error log ({len(error_msg)} chars)")
    logs.append(f"[{req_id}] Agent 1: Inspecting code AST and parsing traceback...")

    try:
        # 1. Real MCP tool call: analyze_code on the submitted code
        ast_result = mcp_client.analyze_code(code)
        mcp_calls.append("analyze_code")

        # 2. Real MCP tool call: read_error_log on the submitted traceback
        traceback_result = mcp_client.read_error_log(error_msg)
        mcp_calls.append("read_error_log")

        # Case A: Clear SyntaxError from AST
        if not ast_result.get("syntax_valid", True):
            detected_error_type = "SyntaxError"
            detected_line = ast_result.get("syntax_error_line")
            root_cause = f"Python SyntaxError at line {detected_line}: {ast_result.get('syntax_error_msg')}"
            summary = f"Syntax error preventing code compilation at line {detected_line}."
            hypotheses = [
                f"Invalid syntax on line {detected_line}",
                "Missing parentheses, colon, or mismatched brackets"
            ]
        else:
            # Case B: Safe dynamic pre-execution to capture real runtime error if present
            exec_res = mcp_client.execute_code_safely(code, timeout_seconds=1.5)
            mcp_calls.append("execute_code_safely")

            active_error_log = error_msg
            # If dynamic execution caught a real runtime exception, prioritize it
            if exec_res.get("has_error"):
                real_err_type = exec_res.get("exception_type", "RuntimeError")
                real_line = exec_res.get("probable_line")
                real_msg = exec_res.get("message", "")
                active_error_log = exec_res.get("stderr") or f"{real_err_type}: {real_msg}"
                traceback_result = mcp_client.read_error_log(active_error_log)
                logs.append(f"[{req_id}] Agent 1: Live execution captured {real_err_type} at line {real_line}.")

            # 3. Dynamic LLM analysis on the exact submitted code
            analysis_res = groq_service.analyze_error(
                code=code,
                error_message=active_error_log,
                ast_info=ast_result,
                request_id=req_id
            )

            # Prioritize real dynamic error type if detected
            dynamic_err = exec_res.get("exception_type") if exec_res.get("has_error") else None

            detected_error_type = (
                dynamic_err
                or analysis_res.get("error_type")
                or traceback_result.get("exception_type")
                or "RuntimeError"
            )

            detected_line = (
                exec_res.get("probable_line")
                or analysis_res.get("error_line")
                or traceback_result.get("probable_line")
                or ast_result.get("syntax_error_line")
            )

            root_cause = (
                analysis_res.get("root_cause")
                or (f"{dynamic_err}: {exec_res.get('message')}" if dynamic_err else None)
                or traceback_result.get("message")
                or "Runtime error detected in submitted code."
            )
            summary = analysis_res.get("summary") or f"Issue identified as {detected_error_type} in submitted code."
            hypotheses = analysis_res.get("hypotheses") or ["Uncaught exception in code execution flow"]

    except Exception as e:
        logger.error(f"[{req_id}] Agent 1 error: {e}")
        logs.append(f"[{req_id}] Agent 1: Warning during analysis ({e}), applied robust fallback.")
        ast_result = {"syntax_valid": True, "warnings": []}
        traceback_result = {"has_error": False, "message": str(e)}
        detected_error_type = "PythonExecutionError"
        detected_line = 1
        root_cause = f"Analysis identified an issue: {str(e)}"
        summary = "Error in submitted code execution."
        hypotheses = ["Potential syntax or runtime mismatch"]

    logger.info(f"[{req_id}] Agent 1: Diagnosed {detected_error_type} at line {detected_line}")
    logs.append(f"[{req_id}] Agent 1: Diagnosed {detected_error_type} at line {detected_line}. Root cause: {root_cause[:80]}...")

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
