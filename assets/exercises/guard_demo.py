"""Fixture-only PreToolUse demonstration. NOT a SQL parser/security boundary."""
import json
import re
import sys


def decision(payload):
    if not isinstance(payload, dict) or payload.get("hook_event_name") != "PreToolUse":
        return False, "Malformed or unsupported demonstration payload"
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return False, "Missing tool_input"
    sql = tool_input.get("sql")
    if payload.get("tool_name") not in {"sql_execute", "snowflake_sql_execute"} or not isinstance(sql, str) or not sql.strip():
        return False, "This fixture only demonstrates SQL tool inputs"
    if re.search(r"\bPROD_SIM\b", sql, re.IGNORECASE):
        return False, "Demonstration denied: sandbox PROD_SIM marker"
    return True, "No demonstration marker found; RBAC still governs actual execution"


def main():
    try:
        payload = json.load(sys.stdin)
    except (ValueError, TypeError):
        payload = None
    allowed, reason = decision(payload)
    print(json.dumps({"decision": "allow" if allowed else "block", "reason": reason}))
    return 0 if allowed else 2


if __name__ == "__main__":
    raise SystemExit(main())
