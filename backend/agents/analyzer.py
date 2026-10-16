import logging
from typing import Any, Dict, List

from agents.state import DebugState
from mcp_server.client import mcp_client
from services.groq_service import groq_service

logger = logging.getLogger("analyzer_agent")


def error_analysis_agent(state: DebugState) -> Dict[str, Any]:
    """Analyze only the submitted code and report findings with direct evidence."""
    req_id = state.get("request_id", "req-unknown")
    code = state.get("code", "")
    error_msg = state.get("error_message", "")
    calls = list(state.get("mcp_calls_made", []))
    logs = list(state.get("workflow_logs", []))
    logs.append(f"[{req_id}] Inspecting submitted code with AST and isolated execution.")

    ast_result = mcp_client.analyze_code(code)
    calls.append("analyze_code")
    traceback_result = mcp_client.read_error_log(error_msg)
    calls.append("read_error_log")
    issues: List[Dict[str, Any]] = list(ast_result.get("issues", []))
    if traceback_result.get("has_error") and traceback_result.get("exception_type") != "Unknown":
        issues.append({
            "error_type": traceback_result.get("exception_type"),
            "line": traceback_result.get("probable_line"),
            "severity": "medium",
            "confirmed": False,
            "explanation": traceback_result.get("message") or "A supplied traceback reports this exception.",
            "suggested_fix": "Verify that this traceback belongs to the current submitted source and inspect its reported operation.",
            "evidence": "Exception reported by the user-supplied traceback; current execution has not confirmed it.",
        })
    execution_result = {
        "executed": False,
        "has_error": False,
        "status": "not_run",
        "stdout": "",
        "stderr": "",
    }

    if not ast_result.get("syntax_valid", True):
        issues.append({
            "error_type": "SyntaxError",
            "line": ast_result.get("syntax_error_line"),
            "severity": "high",
            "confirmed": True,
            "explanation": ast_result.get("syntax_error_msg", "Python could not parse this source."),
            "suggested_fix": "Correct the syntax at the reported location, then rerun analysis.",
            "evidence": ast_result.get("syntax_error_text", "AST parsing failed."),
        })
        execution_result["status"] = "not_run_syntax_error"
    else:
        execution_result = mcp_client.execute_code_safely(code, timeout_seconds=1.5)
        calls.append("execute_code_safely")
        if execution_result.get("executed") and execution_result.get("has_error"):
            error_type = execution_result.get("exception_type") or "RuntimeError"
            issue = {
                "error_type": error_type,
                "line": execution_result.get("probable_line"),
                "severity": "high",
                "confirmed": True,
                "explanation": execution_result.get("message") or error_type,
                "suggested_fix": "Correct the operation identified by the runtime traceback and validate the affected input.",
                "evidence": execution_result.get("stderr") or execution_result.get("message"),
            }
            matching = next((item for item in issues
                             if item.get("error_type") == error_type
                             and (item.get("line") == issue["line"] or item.get("line") is None
                                  or issue["line"] is None)), None)
            if matching:
                matching.update(issue)
            else:
                issues.append(issue)

    if issues and groq_service.is_configured():
        try:
            reasoning = groq_service.analyze_error(
                code=code,
                error_message=error_msg or execution_result.get("stderr", ""),
                ast_info=ast_result,
                request_id=req_id,
            )
            for issue in issues:
                same_issue = issue.get("error_type") == reasoning.get("error_type")
                same_line = not issue.get("line") or not reasoning.get("error_line") or issue.get("line") == reasoning.get("error_line")
                if same_issue and same_line and reasoning.get("root_cause"):
                    issue["reasoning"] = reasoning["root_cause"]
        except Exception as exc:
            logger.warning("[%s] Optional Groq reasoning unavailable: %s", req_id, exc)

    unique_issues = []
    seen = set()
    for issue in issues:
        key = (issue.get("error_type"), issue.get("line"), issue.get("evidence"))
        if key not in seen:
            seen.add(key)
            unique_issues.append(issue)

    primary = next((issue for issue in unique_issues if issue.get("confirmed")),
                   unique_issues[0] if unique_issues else None)
    error_type = primary.get("error_type") if primary else None
    error_line = primary.get("line") if primary else None
    root_cause = primary.get("explanation", "") if primary else ""
    summary = (f"{len(unique_issues)} issue(s) identified in the submitted code."
               if unique_issues else "No definite errors were detected by the available checks.")
    logs.append(f"[{req_id}] Analysis found {len(unique_issues)} evidence-backed issue(s).")

    return {
        "ast_analysis": ast_result,
        "traceback_details": traceback_result,
        "execution_result": execution_result,
        "issues": unique_issues,
        "error_type": error_type,
        "error_line": error_line,
        "root_cause": root_cause,
        "error_summary": summary,
        "hypotheses": [],
        "analysis_mode": "static_analysis_and_execution" if execution_result.get("executed") else "static_analysis",
        "mcp_calls_made": calls,
        "workflow_logs": logs,
        "status": "issues_detected" if unique_issues else "no_issues_detected",
    }