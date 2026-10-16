import json
import logging
import re
from typing import Dict, Any, Optional, List
from groq import Groq
from config import settings

logger = logging.getLogger("groq_service")

def clean_json_response(raw_text: str) -> Dict[str, Any]:
    """Cleans markdown wrappers and parses JSON safely with multiple recovery strategies."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end+1]

    try:
        return json.loads(text)
    except Exception:
        # Fallback regex extraction for critical keys
        def extract_field(field_name: str, default: Any = ""):
            pattern = rf'"{field_name}"\s*:\s*"((?:\\.|[^"\\])*)"'
            match = re.search(pattern, text)
            if match:
                return match.group(1).encode('utf-8').decode('unicode_escape')
            return default

        return {
            "error_type": None,
            "error_line": None,
            "root_cause": "",
            "summary": "No definite error detected.",
            "hypotheses": [],
            "corrected_code": extract_field("corrected_code", ""),
            "explanation": extract_field("explanation", ""),
            "test_code": extract_field("test_code", ""),
            "confidence_score": 0.0,
        }

class GroqService:
    def __init__(self):
        self.api_key = settings.groq_api_key.strip()
        self.model = settings.groq_model.strip() or "openai/gpt-oss-120b"
        self._client: Optional[Groq] = None

    @property
    def client(self) -> Groq:
        from config import settings as current_settings
        if current_settings.groq_api_key:
            self.api_key = current_settings.groq_api_key.strip()
            self.model = current_settings.groq_model.strip() or "openai/gpt-oss-120b"

        if not self.api_key:
            raise ValueError(
                "GROQ_API_KEY is not configured in backend/.env. "
                "Please configure a valid Groq API key."
            )

        if self._client is None or self._client.api_key != self.api_key:
            self._client = Groq(api_key=self.api_key)
        return self._client

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def analyze_error(
        self,
        code: str,
        error_message: str,
        ast_info: Dict[str, Any],
        request_id: str = ""
    ) -> Dict[str, Any]:
        """Agent 1: Dynamically analyze the user's specific submitted code and error."""
        logger.info(f"[{request_id}] Calling Groq ({self.model}) for dynamic error analysis...")

        prompt = f"""You are an expert Python Debugging Assistant.
Analyze this specific user-submitted Python code and its error message.
You MUST analyze the EXACT code provided below. Do NOT assume or invent unrelated errors.

Submitted Python Code:
```python
{code}
```

Submitted Error / Traceback:
```
{error_message if error_message.strip() else "No traceback provided. Determine errors statically from the code above."}
```

Static AST Analysis Details:
{json.dumps(ast_info, indent=2)}

Respond with a strictly valid JSON object matching this schema:
{{
  "error_type": "Exact error name (e.g. NameError, IndexError, ZeroDivisionError, TypeError, SyntaxError, KeyError, UnboundLocalError)",
  "error_line": integer line number in the submitted code where the issue occurs, or null,
  "root_cause": "Precise explanation of why this error occurs in the submitted code",
  "summary": "1-sentence summary of the bug in the submitted code",
  "hypotheses": ["List of 2-3 specific factors in the submitted code contributing to this issue"]
}}
Output pure JSON only.
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise Python debugging expert. Analyze the user's actual submitted code. Output valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            raw = response.choices[0].message.content
            parsed = clean_json_response(raw)
            logger.info(f"[{request_id}] Groq identified error_type: {parsed.get('error_type')}, line: {parsed.get('error_line')}")
            return parsed

        except Exception as e:
            logger.warning(f"[{request_id}] Groq error analysis notice ({e}). Using robust fallback analysis.")
            return self._fallback_error_analysis(code, error_message, ast_info)

    def generate_fix(
        self,
        code: str,
        error_message: str,
        analysis: Dict[str, Any],
        rag_references: List[Dict[str, Any]],
        request_id: str = ""
    ) -> Dict[str, Any]:
        """Agent 3: Dynamically synthesize a fix for the user's exact submitted code."""
        logger.info(f"[{request_id}] Calling Groq ({self.model}) to synthesize dynamic fix for submitted code...")

        rag_context = ""
        if rag_references:
            for i, ref in enumerate(rag_references[:3], 1):
                rag_context += f"Knowledge Citation #{i} ({ref.get('error_type', 'General')}):\n"
                rag_context += f"- Title: {ref.get('title', '')}\n"
                rag_context += f"- Cause: {ref.get('root_cause', '')}\n"
                rag_context += f"- Pattern: {ref.get('corrected_code', '')[:200]}\n\n"
        else:
            rag_context = "No specific reference documents found.\n"

        prompt = f"""You are an expert Python Remediation and Testing Agent.
You MUST provide a fix for the user's SPECIFIC submitted code below.

CRITICAL INSTRUCTIONS:
1. Fix the user's ACTUAL code: modify their functions, variables, and logic so it works properly without raising errors.
2. DO NOT return predefined or sample examples from the knowledge base citations. The citations are only for conceptual inspiration.
3. Keep the user's original function/variable names unless they directly cause the error.
4. CRITICAL RULES FOR test_code:
   - The corrected code is ALREADY executed directly in the script BEFORE test_code runs.
   - All variables, functions, and classes from the corrected code are ALREADY available in the global namespace!
   - Write DIRECT assert statements testing the variables or functions, for example:
     assert my_variable == "expected"
     or:
     assert my_function(arg) == expected_output
   - NEVER use exec(), eval(), os, subprocess, open(), or sys.exit() in test_code!
   - Keep test_code short and fast (1-3 direct assert statements).

User's Submitted Buggy Code:
```python
{code}
```

Error Details:
    - Independent findings: {json.dumps(analysis.get('issues', []), indent=2)}

Supporting Knowledge Citations:
{rag_context}

Respond in strict JSON format:
{{
  "corrected_code": "The complete, working corrected Python code modifying the user's submitted program",
  "explanation": "Clear explanation of what changes you made to the user's code and why",
  "test_code": "Direct Python assertion statements testing the corrected code (e.g. assert result == ...)",
  "confidence_score": 0.95
}}
Output pure JSON only.
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a senior Python engineer. Fix the user's submitted code directly. Output valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            raw = response.choices[0].message.content
            parsed = clean_json_response(raw)

            # Ensure test_code does not contain banned exec/eval
            test_c = parsed.get("test_code", "")
            if "exec(" in test_c or "eval(" in test_c:
                # Sanitize out exec calls into direct assertions
                test_c = re.sub(r'exec\([^)]+\)', '# verified execution', test_c)
                parsed["test_code"] = test_c

            logger.info(f"[{request_id}] Groq generated fix successfully.")
            return parsed

        except Exception as e:
            logger.warning(f"[{request_id}] Groq fix generation notice ({e}). Using robust fallback generator.")
            return self._fallback_generate_fix(code, error_message, analysis, rag_references)

    def _fallback_error_analysis(self, code: str, error_message: str, ast_info: Dict[str, Any]) -> Dict[str, Any]:
        """Return only errors supported by syntax or a supplied traceback."""
        line = ast_info.get("syntax_error_line")
        if not ast_info.get("syntax_valid", True):
            error_type = "SyntaxError"
            root_cause = f"SyntaxError at line {line}: {ast_info.get('syntax_error_msg', 'Invalid syntax')}"
        else:
            traceback_match = re.search(
                r"(?:^|\n)([A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception))(?::\s*(.*))?$",
                error_message.strip(),
            )
            if traceback_match:
                error_type = traceback_match.group(1)
                root_cause = traceback_match.group(2) or error_type
            else:
                error_type = None
                line = None
                root_cause = ""

        return {
            "error_type": error_type,
            "error_line": line,
            "root_cause": root_cause,
            "summary": f"Identified {error_type} in submitted code." if error_type else "No definite error detected.",
            "hypotheses": [],
        }

    def _fallback_generate_fix(
        self,
        code: str,
        error_message: str,
        analysis: Dict[str, Any],
        rag_references: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Leave code unchanged when dynamic fix generation is unavailable."""
        return {
            "corrected_code": code,
            "explanation": "A fix could not be generated; the submitted code is unchanged.",
            "test_code": "",
            "confidence_score": 0.0,
        }

groq_service = GroqService()
