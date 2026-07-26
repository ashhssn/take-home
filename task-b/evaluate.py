import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_ENDPOINT = "http://127.0.0.1:11434/api/chat"
DEFAULT_MODEL = "qwen2.5:0.5b-instruct"
TEMPERATURE = 0
SEED = 42
MAX_TOKENS = 96
SYSTEM_PROMPT = "Return only a concise answer to the user's question. Do not add labels or explanations."

FACTS = {
    "q1": [("14 days", r"\b14\s+days?\b"), ("annual leave", r"\bannual\s+leave\b")],
    "q2": [("Direct manager", r"\bdirect\s+manager\b")],
    "q3": [
        ("500 per employee referred", r"\b500\s+per\s+(?:employee\s+)?referred\b|\b500\s+per\s+employee\b"),
        ("no more than 2000 per quarter", r"\b(?:no\s+more\s+than|maximum\s+of|cap\s+of)\s+2000\s+per\s+quarter\b"),
        ("must pass probation", r"\b(?:must\s+)?pass\s+(?:their\s+)?probation(?:\s+period)?\b"),
        ("probation typically lasts 1 year", r"\bprobation\b.{0,40}\btypically\s+lasts?\s+(?:1|one)\s+year\b"),
    ],
}


class EvaluationError(Exception):
    pass


def load_cases(path):
    cases = []
    seen = set()
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"cannot read test file: {exc}") from exc
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {line_number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(case, dict):
            raise ValueError(f"line {line_number}: case must be an object")
        cases.append(case)
    if not cases:
        raise ValueError("test file contains no cases")
    return cases


def exact_match(output, expected):
    return output.strip() == expected.strip()


def fact_coverage(case_id, output):
    facts = FACTS.get(case_id, [])
    matched = [label for label, pattern in facts if re.search(pattern, output, re.IGNORECASE | re.DOTALL)]
    missing = [label for label, _ in facts if label not in matched]
    return {"matched": matched, "missing": missing, "score": f"{len(matched)}/{len(facts)}" if facts else None}


def parse_response(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("message"), dict):
        raise EvaluationError("response missing message object")
    content = payload["message"].get("content")
    if not isinstance(content, str) or not content.strip():
        raise EvaluationError("response content is empty or not a string")
    return content.strip()


def generate(endpoint, model, user_input, timeout):
    if timeout <= 0:
        raise EvaluationError("timeout must be greater than zero")
    body = {"model": model, "stream": False, "messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ], "options": {"temperature": TEMPERATURE, "seed": SEED, "num_predict": MAX_TOKENS}}
    try:
        request = urllib.request.Request(endpoint, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return parse_response(json.loads(response.read().decode("utf-8")))
    except urllib.error.HTTPError as exc:
        raise EvaluationError(f"HTTP {exc.code} from model endpoint") from exc
    except (ValueError, urllib.error.URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvaluationError(f"model endpoint error: {exc}") from exc


def evaluate(cases, client, endpoint, model, timeout):
    results = []
    for case in cases:
        started = time.monotonic()
        item = {"id": case["id"], "input": case["input"], "expected": case["expected"]}
        try:
            output = client(endpoint, model, case["input"], timeout)
            coverage = fact_coverage(case["id"], output)
            item.update({"status": "pass" if exact_match(output, case["expected"]) else "fail",
                         "output": output, "exact_match": exact_match(output, case["expected"]),
                         "fact_coverage": coverage})
            if item["status"] == "fail":
                item["reason"] = "output differs from expected text"
        except EvaluationError as exc:
            item.update({"status": "error", "reason": str(exc), "anomaly": "model call failed"})
        item["latency_ms"] = round((time.monotonic() - started) * 1000, 1)
        results.append(item)
    counts = {status: sum(item["status"] == status for item in results) for status in ("pass", "fail", "error")}
    return results, {"total": len(results), **counts, "pass_rate": round(counts["pass"] / len(results), 4) if results else 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate a local Ollama model against JSONL cases")
    parser.add_argument("--cases", default=str(Path(__file__).with_name("test_cases.jsonl")))
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--output", help="write full JSON report to this path")
    args = parser.parse_args(argv)
    try:
        cases = load_cases(args.cases)
    except ValueError as exc:
        parser.error(str(exc))
    results, summary = evaluate(cases, generate, args.endpoint, args.model, args.timeout)
    report = {"run_at": datetime.now(timezone.utc).isoformat(), "model": args.model, "endpoint": args.endpoint,
              "parameters": {"temperature": TEMPERATURE, "seed": SEED, "max_tokens": MAX_TOKENS},
              "system_prompt": SYSTEM_PROMPT, "summary": summary, "cases": results,
              "anomalies": [item["reason"] for item in results if item["status"] == "error"]}
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        try:
            Path(args.output).write_text(text, encoding="utf-8")
        except OSError as exc:
            parser.error(f"cannot write report: {exc}")
    print(f"Pass rate: {summary['pass_rate']:.1%} ({summary['pass']}/{summary['total']})")
    print(f"Failures: {summary['fail']}; errors: {summary['error']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
