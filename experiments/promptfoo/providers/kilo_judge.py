"""Kilo-backed completion provider used as the llm-rubric grader.

Promptfoo's model-graded assertions construct a grading prompt and send it to
a provider; without API keys for OpenAI/Anthropic this spike points rubric
grading at the same free Kilo model so judge and worker share one engine.
The rubric prompt requires a JSON verdict; we return the raw text and let
Promptfoo parse it.
"""
import json
import os
import subprocess
import sys

_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

DEFAULT_MODEL = "kilo/tencent/hy3:free"


def call_api(prompt, options, context):
    cfg = options.get("config", {})
    model = cfg.get("model", DEFAULT_MODEL)
    timeout_s = int(cfg.get("timeout_s", 300))
    workdir = cfg.get("workdir") or "/tmp/kilo"
    try:
        proc = subprocess.run(
            ["kilo", "run", "--model", model, "--format", "json", "--pure",
             prompt],
            cwd=workdir, capture_output=True, text=True,
            stdin=subprocess.DEVNULL, timeout=timeout_s,
            env=dict(os.environ, PWD=workdir))
    except Exception as exc:
        return {"output": "", "error": f"judge invocation error: {exc}"}
    parts = []
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("type") == "text":
            parts.append(obj.get("part", {}).get("text", ""))
    text = "".join(parts)
    if proc.returncode != 0 or not text.strip():
        return {"output": text,
                "error": f"judge exited {proc.returncode} or returned empty"}
    return {"output": text}
