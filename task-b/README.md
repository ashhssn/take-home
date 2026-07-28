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

- Default score: exact text match after trimming outer whitespace only. Exact matches score `1.0`.
- For non-exact outputs, deterministic atomic-fact coverage contributes the score: matched required facts / total required facts. Full coverage can therefore pass despite different wording.
- Embedding models are not used as they are from non-standard Python libraries
- Optional `--judge true` runs the same local model as a binary LLM judge for non-exact outputs. Exact matches skip the judge. The report retains both `default_score` and judge-selected `score`.
- Same-model judging is included only as an optional comparison: generator and evaluator are circular, and a 0.5B model is not a dependable independent judge. Treat judge results as supplementary, not authoritative.
- `temperature=0`, `seed=42`, `max_tokens=96`: deterministic short answers reduce variance and runaway output.
- Malformed endpoints, non-positive timeouts, HTTP errors, and empty/malformed responses are recorded as per-case errors; remaining cases still run.

Run both scoring methods:

```bash
python3 task-b/evaluate.py --output task-b/results-default.json
python3 task-b/evaluate.py --judge true --output task-b/results-judge.json
```

The recorded local run produced `0/3` default passes and `3/3` judge-selected passes. The judge result is visibly unreliable here: it marked clearly unrelated answers correct. This demonstrates why the deterministic default remains the primary score.
