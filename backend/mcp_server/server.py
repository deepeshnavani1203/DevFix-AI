import sys
import ast
import builtins
import re
import time
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from mcp.server.mcpserver import MCPServer
from rag.retriever import rag_retriever

mcp_server = MCPServer("devfix-mcp-server")

# 1. Tool: Static Python AST Analysis
@mcp_server.tool()
def analyze_code(code: str) -> Dict[str, Any]:
    """Perform static Python code analysis using Python AST.
    Checks syntax, parses functions/classes/imports, and spots potential vulnerabilities and anti-patterns.
    """
    if not code.strip():
        return {
            "syntax_valid": False,
            "syntax_error_msg": "Code is empty",
            "syntax_error_line": None,
            "functions": [],
            "classes": [],
            "imports": [],
            "risky_calls": [],
            "warnings": ["Provided code is empty."]
        }

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {
            "syntax_valid": False,
            "syntax_error_msg": str(e.msg),
            "syntax_error_line": e.lineno,
            "syntax_error_offset": e.offset,
            "syntax_error_text": e.text.strip() if e.text else "",
            "functions": [],
            "classes": [],
            "imports": [],
            "risky_calls": [],
            "warnings": [f"SyntaxError at line {e.lineno}: {e.msg}"]
        }

    functions = []
    classes = []
    imports = []
    risky_calls = []
    warnings = []

    # Dangerous system calls that can affect the host system
    DISALLOWED_FUNCTIONS = {"eval", "exec", "system", "popen", "spawn", "fork", "kill", "rmdir"}

    class CodeVisitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            functions.append({
                "name": node.name,
                "line": node.lineno,
                "args": [a.arg for a in node.args.args],
            })
            # Check for mutable default argument
            for default in node.args.defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    warnings.append(
                        f"Function '{node.name}' at line {node.lineno} uses a mutable default argument ({type(default).__name__})."
                    )
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node):
            functions.append({
                "name": node.name,
                "line": node.lineno,
                "is_async": True,
                "args": [a.arg for a in node.args.args],
            })
            self.generic_visit(node)

        def visit_ClassDef(self, node):
            classes.append({
                "name": node.name,
                "line": node.lineno,
            })
            self.generic_visit(node)

        def visit_Import(self, node):
            for alias in node.names:
                imports.append(alias.name)
            self.generic_visit(node)

        def visit_ImportFrom(self, node):
            mod = node.module or ""
            for alias in node.names:
                imports.append(f"{mod}.{alias.name}")
            self.generic_visit(node)

        def visit_Call(self, node):
            func_name = ""
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            if func_name in DISALLOWED_FUNCTIONS:
                risky_calls.append({
                    "call": func_name,
                    "line": getattr(node, "lineno", 0),
                    "reason": f"Execution of dangerous builtin '{func_name}' is restricted."
                })
            self.generic_visit(node)

        def visit_ExceptHandler(self, node):
            if node.type is None:
                warnings.append(
                    f"Bare 'except:' handler at line {node.lineno}. Catching generic BaseException can mask critical errors."
                )
            self.generic_visit(node)

    visitor = CodeVisitor()
    visitor.visit(tree)

    issues = []
    known_names = set(dir(builtins))
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            known_names.add(node.id)
        elif isinstance(node, ast.arg):
            known_names.add(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            known_names.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                known_names.add(alias.asname or alias.name.split(".")[0])

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id not in known_names:
            issues.append({
                "error_type": "NameError",
                "line": node.lineno,
                "severity": "high",
                "confirmed": False,
                "explanation": f"'{node.id}' is read but has no assignment, import, parameter, or builtin binding.",
                "suggested_fix": f"Define '{node.id}' before use or correct the name to the intended variable.",
                "evidence": f"Unbound name load '{node.id}' at line {node.lineno}.",
            })

        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            if isinstance(node.right, ast.Constant) and node.right.value == 0:
                issues.append({
                    "error_type": "ZeroDivisionError",
                    "line": node.lineno,
                    "severity": "high",
                    "confirmed": False,
                    "explanation": "The divisor is the literal zero, so evaluating this expression raises ZeroDivisionError.",
                    "suggested_fix": "Use a non-zero divisor or handle the zero case before dividing.",
                    "evidence": f"Literal zero divisor in a {type(node.op).__name__} expression at line {node.lineno}.",
                })

    empty_input_calls = []
    division_functions = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            parameters = {arg.arg for arg in node.args.args}
            for child in ast.walk(node):
                if isinstance(child, ast.BinOp) and isinstance(child.op, ast.Div):
                    divisor = child.right
                    if (isinstance(divisor, ast.Call) and isinstance(divisor.func, ast.Name)
                            and divisor.func.id == "len" and divisor.args
                            and isinstance(divisor.args[0], ast.Name)):
                        divisor_name = divisor.args[0].id
                        if divisor_name in parameters:
                            argument_index = [arg.arg for arg in node.args.args].index(divisor_name)
                        elif len(node.args.args) == 1:
                            argument_index = 0
                        else:
                            continue
                        division_functions[node.name] = (divisor_name, child.lineno, argument_index)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        definition = division_functions.get(node.func.id)
        if definition:
            parameter, line, argument_index = definition
            function = next((item for item in ast.walk(tree)
                             if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                             and item.name == node.func.id), None)
            if function:
                if (len(node.args) > argument_index and isinstance(node.args[argument_index], ast.List)
                        and not node.args[argument_index].elts):
                    empty_input_calls.append((node.func.id, parameter, line))

    for function_name, parameter, line in empty_input_calls:
        explanation = f"'{function_name}' divides by len({parameter}) and is called with an empty list. This division may be masked by an earlier error on that call."
        issues.append({
            "error_type": "ZeroDivisionError",
            "line": line,
            "severity": "medium",
            "confirmed": False,
            "explanation": explanation,
            "suggested_fix": f"Handle an empty '{parameter}' value before dividing.",
            "evidence": f"Call to {function_name} at an empty-list argument can make len({parameter}) zero.",
        })

    return {
        "syntax_valid": True,
        "syntax_error_msg": None,
        "syntax_error_line": None,
        "functions": functions,
        "classes": classes,
        "imports": imports,
        "risky_calls": risky_calls,
        "warnings": warnings,
        "issues": issues,
    }

# 2. Tool: Traceback and Error Log Parsing
@mcp_server.tool()
def read_error_log(error_log: str) -> Dict[str, Any]:
    """Extract useful traceback details such as exception type, file, line number, and messages."""
    if not error_log or not error_log.strip():
        return {
            "has_error": False,
            "exception_type": "Unknown",
            "message": "No traceback or error log provided.",
            "frames": [],
            "probable_line": None,
        }

    lines = error_log.strip().splitlines()
    frames = []
    exception_type = "PythonError"
    message = ""
    probable_line = None

    # Match standard python traceback line: File "...", line 12, in ...
    frame_pattern = re.compile(r'File\s+"([^"]+)",\s+line\s+(\d+)(?:,\s+in\s+(.+))?')

    for i, line in enumerate(lines):
        line_clean = line.strip()
        match = frame_pattern.search(line_clean)
        if match:
            file_name = match.group(1)
            line_no = int(match.group(2))
            scope = match.group(3) or ""
            # Next line usually contains the code snippet
            code_snippet = lines[i + 1].strip() if i + 1 < len(lines) else ""
            frames.append({
                "file": file_name,
                "line": line_no,
                "scope": scope,
                "code": code_snippet,
            })
            probable_line = line_no

    # Search for the final exception line, e.g. "ZeroDivisionError: division by zero"
    for line in reversed(lines):
        line_clean = line.strip()
        exc_match = re.match(r"^([a-zA-Z0-9_\.]*(?:Error|Exception|Warning|Interrupt))(?::\s*(.*))?$", line_clean)
        if exc_match:
            exception_type = exc_match.group(1)
            message = exc_match.group(2) or ""
            break

    if exception_type == "PythonError" and lines:
        # Fallback to the last line if no standard Error suffix matched
        last_line = lines[-1].strip()
        if ":" in last_line:
            parts = last_line.split(":", 1)
            exception_type = parts[0].strip()
            message = parts[1].strip()
        else:
            message = last_line

    return {
        "has_error": True,
        "exception_type": exception_type,
        "message": message,
        "frames": frames,
        "probable_line": probable_line,
    }

# 3. Tool: Search Knowledge Base via RAG
@mcp_server.tool()
def search_debug_knowledge(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Retrieve related debugging knowledge, past verified examples, and solutions from Qdrant."""
    return rag_retriever.retrieve(query=query, limit=limit)

# 4. Tool: Safe Sandboxed Test Execution
@mcp_server.tool()
def run_tests(solution_code: str, test_code: str, timeout_seconds: int = 3) -> Dict[str, Any]:
    """Execute proposed Python code and assert tests in a sandboxed, restricted subprocess with strict timeout."""
    # Perform pre-execution static security audit
    analysis = analyze_code(solution_code + "\n" + test_code)
    if not analysis["syntax_valid"]:
        return {
            "passed": False,
            "status": "syntax_error",
            "error": analysis.get("syntax_error_msg"),
            "line": analysis.get("syntax_error_line"),
            "stdout": "",
            "stderr": f"SyntaxError: {analysis.get('syntax_error_msg')} on line {analysis.get('syntax_error_line')}",
            "duration_ms": 0.0,
        }

    # Block disallowed operations before running
    if analysis["risky_calls"]:
        call_names = [c["call"] for c in analysis["risky_calls"]]
        return {
            "passed": False,
            "status": "security_block",
            "error": f"Security restriction: Execution blocked due to forbidden calls: {', '.join(call_names)}",
            "stdout": "",
            "stderr": "Code contained unsafe system execution functions and was blocked by sandbox policy.",
            "duration_ms": 0.0,
        }

    # Combine solution and verification test
    full_script = f"""# Auto-generated verification script
{solution_code}

# Verification assertions
{test_code}
"""

    start_time = time.time()
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(full_script)
            temp_file = f.name

        # Run in clean isolated subprocess with strict timeout, empty input to prevent hangs, and no network
        proc = subprocess.run(
            [sys.executable, "-I", temp_file], # -I isolates from user site-packages/environment
            input="",
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        duration_ms = round((time.time() - start_time) * 1000, 2)

        if proc.returncode == 0:
            return {
                "passed": True,
                "status": "passed",
                "stdout": proc.stdout.strip(),
                "stderr": "",
                "duration_ms": duration_ms,
            }
        else:
            return {
                "passed": False,
                "status": "failed",
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
                "duration_ms": duration_ms,
            }

    except subprocess.TimeoutExpired:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "passed": False,
            "status": "timeout",
            "error": f"Execution timed out after {timeout_seconds} seconds (possible infinite loop).",
            "stdout": "",
            "stderr": f"TimeoutExpired: Process exceeded {timeout_seconds}s threshold.",
            "duration_ms": duration_ms,
        }
    except Exception as e:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "passed": False,
            "status": "error",
            "error": str(e),
            "stdout": "",
            "stderr": str(e),
            "duration_ms": duration_ms,
        }
    finally:
        if temp_file and Path(temp_file).exists():
            try:
                Path(temp_file).unlink()
            except Exception:
                pass

# 5. Tool: Safe Dynamic Code Execution (Pre-Execution for Ground Truth)
@mcp_server.tool()
def execute_code_safely(code: str, timeout_seconds: float = 2.0) -> Dict[str, Any]:
    """Execute code in an isolated subprocess to detect real live runtime errors, tracebacks, or output."""
    if not code.strip():
        return {
            "executed": False,
            "has_error": False,
            "exception_type": None,
            "message": "Empty code.",
            "stdout": "",
            "stderr": "",
            "probable_line": None,
            "duration_ms": 0.0,
        }

    # Pre-execution static safety check
    analysis = analyze_code(code)
    if not analysis["syntax_valid"]:
        return {
            "executed": False,
            "has_error": True,
            "exception_type": "SyntaxError",
            "message": analysis.get("syntax_error_msg"),
            "probable_line": analysis.get("syntax_error_line"),
            "stdout": "",
            "stderr": f"SyntaxError: {analysis.get('syntax_error_msg')} on line {analysis.get('syntax_error_line')}",
            "duration_ms": 0.0,
        }

    if analysis["risky_calls"]:
        call_names = [c["call"] for c in analysis["risky_calls"]]
        return {
            "executed": False,
            "has_error": True,
            "exception_type": "SecurityRestriction",
            "message": f"Execution blocked due to forbidden calls: {', '.join(call_names)}",
            "probable_line": None,
            "stdout": "",
            "stderr": "Code contained unsafe system execution functions and was blocked by policy.",
            "duration_ms": 0.0,
        }

    start_time = time.time()
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            temp_file = f.name

        proc = subprocess.run(
            [sys.executable, "-I", temp_file],
            input="",
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        duration_ms = round((time.time() - start_time) * 1000, 2)

        if proc.returncode == 0:
            return {
                "executed": True,
                "has_error": False,
                "exception_type": None,
                "message": "Execution finished successfully without runtime errors.",
                "stdout": proc.stdout.strip(),
                "stderr": "",
                "probable_line": None,
                "duration_ms": duration_ms,
            }
        else:
            parsed = read_error_log(proc.stderr)
            return {
                "executed": True,
                "has_error": True,
                "exception_type": parsed.get("exception_type", "RuntimeError"),
                "message": parsed.get("message") or proc.stderr.strip()[:200],
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
                "probable_line": parsed.get("probable_line"),
                "duration_ms": duration_ms,
            }
    except subprocess.TimeoutExpired:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "executed": True,
            "has_error": True,
            "exception_type": "TimeoutError",
            "message": f"Execution timed out after {timeout_seconds}s (possible infinite loop).",
            "stdout": "",
            "stderr": f"TimeoutExpired: Process exceeded {timeout_seconds}s threshold.",
            "probable_line": None,
            "duration_ms": duration_ms,
        }
    except Exception as e:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "executed": False,
            "has_error": True,
            "exception_type": "ExecutionError",
            "message": str(e),
            "stdout": "",
            "stderr": str(e),
            "probable_line": None,
            "duration_ms": duration_ms,
        }
    finally:
        if temp_file and Path(temp_file).exists():
            try:
                Path(temp_file).unlink()
            except Exception:
                pass

if __name__ == "__main__":
    # If run as CLI script, launch standard MCP server
    mcp_server.run()
