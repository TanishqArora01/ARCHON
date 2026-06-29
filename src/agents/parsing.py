import json
import re

def parse_json_from_llm(raw: str) -> dict | list:
    """
    Strips markdown code blocks (e.g. ```json ... ```) from LLM output
    and parses the result into a python dict or list.
    """
    raw = raw.strip()
    
    # Try to extract content inside ```json ... ``` or just ``` ... ```
    pattern = r"```(?:json)?\s*(.*?)\s*```"
    match = re.search(pattern, raw, re.DOTALL)
    if match:
        raw = match.group(1).strip()
        
    return json.loads(raw)
