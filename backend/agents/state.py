from typing import TypedDict, List, Dict, Any, Optional

class DebugState(TypedDict, total=False):
    # Request tracking
    request_id: str

    # User inputs
    code: str
    error_message: str

    # Agent 1 (Error Analysis) outputs
    ast_analysis: Dict[str, Any]
    traceback_details: Dict[str, Any]
    error_type: str
    root_cause: str
    error_summary: str
    error_line: Optional[int]
    hypotheses: List[str]
    issues: List[Dict[str, Any]]
    execution_result: Dict[str, Any]
    analysis_mode: str

    # Agent 2 (RAG Retrieval) outputs
    rag_references: List[Dict[str, Any]]

    # Agent 3 (Fix & Validation) outputs
    corrected_code: str
    explanation: str
    test_code: str
    validation_result: Dict[str, Any]
    confidence_score: float

    # System telemetry
    mcp_calls_made: List[str]
    workflow_logs: List[str]
    status: str
