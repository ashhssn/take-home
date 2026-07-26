# Task B — Local model evaluation

## What it does

`evaluate.py` calls local Ollama with the three test cases (in jsonl) and writes per-case evidence plus a structured summary. It uses the required `qwen2.5:0.5b-instruct` model by default.

```bash
python3 task-b/evaluate.py --output task-b/results.json
```

Requires Ollama running locally and:

```bash
ollama pull qwen2.5:0.5b-instruct
```

## Scoring and assumptions

The PDF supplies expected answers but no HR policy context. The default run is therefore a **closed-book baseline**: expected answers are never placed in the prompt. A low score is valid evidence that the model does not know these organisation-specific facts; it is not silently treated as a tool failure.

- Primary score: exact text match after trimming outer whitespace only.
- Secondary diagnostic: deterministic atomic-fact coverage for each case. It reports matched and missing facts but does not turn partial credit into a pass.
- Same-model LLM-as-judge is intentionally not used: the generator and evaluator would be circular, and a 0.5B model is not a dependable independent judge.
- `temperature=0`, `seed=42`, `max_tokens=96`: deterministic short answers reduce variance and runaway output.
- Malformed endpoints, non-positive timeouts, HTTP errors, and empty/malformed responses are recorded as per-case errors; remaining cases still run.