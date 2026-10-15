import logging
from typing import Dict, Any, List
from mcp_server.server import (
    analyze_code as mcp_analyze_code,
    read_error_log as mcp_read_error_log,
    search_debug_knowledge as mcp_search_debug_knowledge,
    run_tests as mcp_run_tests,
)

logger = logging.getLogger("mcp_client")

class DevFixMCPClient:
    """Client interface for agents to execute MCP tools provided by DevFix MCP Server."""

    def __init__(self):
        self.server_name = "devfix-mcp-server"

    def analyze_code(self, code: str) -> Dict[str, Any]:
        """Invoke MCP static analysis tool."""
        logger.info("MCP Client invoking tool: analyze_code")
        return mcp_analyze_code(code)

    def read_error_log(self, error_log: str) -> Dict[str, Any]:
        """Invoke MCP traceback parsing tool."""
        logger.info("MCP Client invoking tool: read_error_log")
        return mcp_read_error_log(error_log)

    def search_debug_knowledge(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Invoke MCP knowledge retrieval tool."""
        logger.info(f"MCP Client invoking tool: search_debug_knowledge with limit={limit}")
        return mcp_search_debug_knowledge(query, limit)

    def run_tests(self, solution_code: str, test_code: str, timeout_seconds: int = 3) -> Dict[str, Any]:
        """Invoke MCP sandboxed test execution tool."""
        logger.info("MCP Client invoking tool: run_tests")
        return mcp_run_tests(solution_code, test_code, timeout_seconds)

mcp_client = DevFixMCPClient()
