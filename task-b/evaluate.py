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
JUDGE_SYSTEM_PROMPT = "Return only JSON with one boolean field: {\"correct\": true or false}."

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


def parse_bool(value):
    value = value.lower()
    if value in {"true", "1", "yes", "y", "on"}:
        return True
    if value in {"false", "0", "no", "n", "off"}:
        return False
    raise ValueError("expected true or false")


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


def chat(endpoint, model, messages, timeout, system_prompt=SYSTEM_PROMPT, num_predict=MAX_TOKENS,
         response_format=None):
    if timeout <= 0:
        raise EvaluationError("timeout must be greater than zero")
    body = {"model": model, "stream": False,
            "messages": [{"role": "system", "content": system_prompt}, *messages],
            "options": {"temperature": TEMPERATURE, "seed": SEED, "num_predict": num_predict}}
    if response_format is not None:
        body["format"] = response_format
    try:
        request = urllib.request.Request(endpoint, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return parse_response(json.loads(response.read().decode("utf-8")))
    except urllib.error.HTTPError as exc:
        raise EvaluationError(f"HTTP {exc.code} from model endpoint") from exc
    except (ValueError, urllib.error.URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvaluationError(f"model endpoint error: {exc}") from exc


def generate(endpoint, model, user_input, timeout):
    return chat(endpoint, model, [{"role": "user", "content": user_input}], timeout)


def judge_generate(endpoint, model, judge_prompt, timeout):
    return chat(endpoint, model, [{"role": "user", "content": judge_prompt}], timeout,
                system_prompt=JUDGE_SYSTEM_PROMPT, num_predict=32,
                response_format={"type": "object", "properties": {"correct": {"type": "boolean"}},
                                 "required": ["correct"]})


def parse_judge(content):
    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        raise EvaluationError(f"judge returned invalid JSON: {exc.msg}") from exc
    if not isinstance(result, dict) or not isinstance(result.get("correct"), bool):
        raise EvaluationError("judge JSON must contain boolean field 'correct'")
    return result["correct"]


def default_score(case, output):
    if exact_match(output, case["expected"]):
        return 1.0, "exact_match", None
    coverage = fact_coverage(case["id"], output)
    total = len(FACTS.get(case["id"], []))
    score = len(coverage["matched"]) / total if total else 0.0
    return score, "fact_coverage", coverage


def make_summary(results, score_field="score"):
    total = len(results)
    counts = {"error": sum(item["status"] == "error" for item in results)}
    counts["pass"] = sum(item.get(score_field) == 1.0 for item in results if item["status"] != "error")
    counts["fail"] = total - counts["pass"] - counts["error"]
    return {"total": total, **counts, "pass_rate": round(counts["pass"] / total, 4) if total else 0}


def evaluate(cases, client, endpoint, model, timeout, use_judge=False, judge_client=None):
    results = []
    for case in cases:
        started = time.monotonic()
        item = {"id": case["id"], "input": case["input"], "expected": case["expected"]}
        try:
            output = client(endpoint, model, case["input"], timeout)
            score, source, coverage = default_score(case, output)
            item.update({"output": output, "exact_match": exact_match(output, case["expected"]),
                         "default_score": score, "default_score_source": source,
                         "score": score, "score_source": source})
            if coverage is not None:
                item["fact_coverage"] = coverage
            if use_judge and not item["exact_match"]:
                item["judge_status"] = "error"
                try:
                    if judge_client is None:
                        raise EvaluationError("judge client is not configured")
                    prompt = ("Compare expected answer and candidate answer. Decide whether candidate contains "
                              "all material facts in expected and introduces no contradiction. Ignore wording, "
                              "case, and punctuation differences. Return correct=true only if substantively correct.\n\n"
                              f"EXPECTED:\n{case['expected']}\n\nCANDIDATE:\n{output}")
                    correct = parse_judge(judge_client(endpoint, model, prompt, timeout))
                    item.update({"judge_status": "pass", "judge_correct": correct,
                                 "judge_score": 1.0 if correct else 0.0,
                                 "score": 1.0 if correct else 0.0,
                                 "score_source": "llm_judge"})
                except EvaluationError as exc:
                    item["judge_reason"] = str(exc)
            item["status"] = "pass" if item["score"] == 1.0 else "fail"
            if item["status"] == "fail":
                item["reason"] = "score below 1.0"
        except EvaluationError as exc:
            item.update({"status": "error", "reason": str(exc), "anomaly": "model call failed"})
        item["latency_ms"] = round((time.monotonic() - started) * 1000, 1)
        results.append(item)
    default_summary = make_summary(results, "default_score")
    summary = make_summary(results)
    summary["judge_enabled"] = use_judge
    summary["default_summary"] = default_summary
    summary["judge_summary"] = make_summary(results) if use_judge else None
    return results, summary


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate a local Ollama model against JSONL cases")
    parser.add_argument("--cases", default=str(Path(__file__).with_name("test_cases.jsonl")))
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--judge", type=parse_bool, default=False,
                        help="use same local model as judge for non-exact answers (true/false)")
    parser.add_argument("--output", help="write full JSON report to this path")
    args = parser.parse_args(argv)
    try:
        cases = load_cases(args.cases)
    except ValueError as exc:
        parser.error(str(exc))
    results, summary = evaluate(cases, generate, args.endpoint, args.model, args.timeout,
                                use_judge=args.judge, judge_client=judge_generate if args.judge else None)
    report = {"run_at": datetime.now(timezone.utc).isoformat(), "model": args.model, "endpoint": args.endpoint,
              "parameters": {"temperature": TEMPERATURE, "seed": SEED, "max_tokens": MAX_TOKENS},
              "system_prompt": SYSTEM_PROMPT, "judge_system_prompt": JUDGE_SYSTEM_PROMPT if args.judge else None,
              "scoring": "exact match, otherwise fact coverage; optional non-exact LLM judge" if args.judge
              else "exact match, otherwise fact coverage",
              "summary": summary, "cases": results,
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
