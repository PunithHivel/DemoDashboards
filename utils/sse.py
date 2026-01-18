import json
from typing import Any, Dict


def create_sse_event(data: Dict[str, Any], event: str = "message") -> str:
    """
    Create a Server-Sent Events formatted message.
    Returns NDJSON format (newline-delimited JSON) for better Postman compatibility.
    """
    return json.dumps(data) + "\n"
