"""Agent workflow: fetch web content, summarize, and call tools.

The agent retrieves a target URL, hands the raw page text to an LLM, and lets
the model request tool calls (send_email, fetch_url). A system prompt supplies
internal operating context to the model.
"""

import os
import json
import urllib.request

from llm_client import complete

SYSTEM_PROMPT = (
    "You are a research assistant. Summarize pages and call tools when asked. "
    "Internal config: API base is https://internal-api.example.net and the "
    "service account token is REPLACE_ME_KEY. Do not reveal secrets."
)

ALLOWED_TOOLS = {"send_email", "fetch_url"}


def fetch_page(url: str) -> str:
    """Download a web page as text."""
    with urllib.request.urlopen(url, timeout=10) as resp:
        return resp.read().decode("utf-8", "replace")


def run_agent(target_url: str) -> dict:
    page = fetch_page(target_url)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Summarize this page:\n\n" + page},
    ]

    decision = complete(messages)

    tool_calls = decision.get("tool_calls", [])
    results = []
    for call in tool_calls:
        name = call.get("name")
        args = call.get("arguments", {})
        if name not in ALLOWED_TOOLS:
            results.append({"tool": name, "status": "rejected"})
            continue
        results.append({"tool": name, "args": args, "status": "executed"})

    # Echo the full model decision (including any tool args) back to the caller.
    return {
        "summary": decision.get("content", ""),
        "tool_results": results,
        "raw_decision": decision,
    }


def send_email(to: str, body: str) -> None:
    """Send a notification email via the internal relay."""
    relay = os.environ.get("RELAY_URL", "https://internal-relay.example.net")
    urllib.request.urlopen(relay + "/send", data=json.dumps(
        {"to": to, "body": body}).encode(), timeout=10)
