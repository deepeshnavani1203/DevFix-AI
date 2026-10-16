import logging
from typing import Any, Dict

from agents.state import DebugState
from mcp_server.client import mcp_client
from services.groq_service import groq_service

logger = logging.getLogger("validator_agent")


def fix_validation_agent(state: DebugState) -> Dict[str, Any]:
    """Generate and validate a fix only when analysis found an issue."""
    req_id = state.get("request_id", "req-unknown")
    code = state.get("code", "")
    issues = state.get("issues", [])
    calls = list(state.get("mcp_calls_made", []))
    logs = list(state.get("workflow_logs", []))

    if not issues:
        return {
            "corrected_code": code,
            "explanation": "Your Python code passed the available static checks. No definite errors were detected.",
            "test_code": "",
            "validation_result": {"status": "not_run", "passed": None, "tests_configured": False},
            "confidence_score": 1.0,
            "status": "no_issues_detected",
            "mcp_calls_made": calls,
            "workflow_logs": logs,
        }

    primary = issues[0]
    analysis = {
        "error_type": primary.get("error_type"),
        "root_cause": primary.get("explanation", ""),
        "error_line": primary.get("line"),
        "issues": issues,
    }
    logger.info("[%s] Generating a request-specific fix for %d issue(s).", req_id, len(issues))
    try:
        fix_data = groq_service.generate_fix(
            code=code,
            error_message=state.get("error_message", ""),
            analysis=analysis,
            rag_references=state.get("rag_references", []),
            request_id=req_id,
        )
        corrected_code = fix_data.get("corrected_code") or code
        explanation = fix_data.get("explanation") or "No generated correction is available; the submitted code is unchanged."
        test_code = fix_data.get("test_code") or ""
        if "\\n" in corrected_code and "\n" not in corrected_code:
            corrected_code = corrected_code.replace("\\n", "\n").replace("\\t", "\t")
        if "\\n" in test_code and "\n" not in test_code:
            test_code = test_code.replace("\\n", "\n").replace("\\t", "\t")

        validation_result = mcp_client.run_tests(
            solution_code=corrected_code,
            test_code=test_code,
            timeout_seconds=3,
        )
        calls.append("run_tests")
        validation_result["tests_configured"] = bool(test_code.strip())
        validation_result["executed"] = validation_result.get("status") not in {"security_block", "syntax_error", "error"}
        status = "passed" if validation_result.get("passed") else "failed"
        logs.append(f"[{req_id}] Generated-code validation status: {status}.")
        return {
            "corrected_code": corrected_code,
            "explanation": explanation,
            "test_code": test_code,
            "validation_result": validation_result,
            "confidence_score": fix_data.get("confidence_score", 0.0),
            "status": status,
            "mcp_calls_made": calls,
            "workflow_logs": logs,
        }
    except Exception as exc:
        logger.exception("[%s] Fix generation or validation failed.", req_id)
        logs.append(f"[{req_id}] Fix generation or validation failed: {exc}")
        return {
            "corrected_code": code,
            "explanation": "Analysis found an issue, but fix generation or validation failed. The submitted code is unchanged.",
            "test_code": "",
            "validation_result": {"status": "analysis_failed", "passed": False, "tests_configured": False},
            "confidence_score": 0.0,
            "status": "analysis_failed",
            "mcp_calls_made": calls,
            "workflow_logs": logs,
        }