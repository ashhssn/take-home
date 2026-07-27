## Part A

`run_prompt.py` sends the unchanged 12 messages from the PDF to Ollama using each
versioned prompt in `prompts/`. Raw responses are saved in `results/`.

```bash
ollama pull qwen2.5:0.5b-instruct
python3 task-a/run_prompt.py --version v8 --max-tokens 64
```

Settings: temperature `0`, seed `42`, and `num_predict` `64` for the final run.
The local Ollama chat endpoint is used with `stream: false`.

`v8` is the selected final prompt with a manual score of `9/12`.
Failures: a5, a9, and a12.

### Evaluation assumptions

- The PDF lists 12 messages; all 12 are tested.
- No HR policy source is supplied, so no policy fact can be verified.
- Assumed domain tags are `HR-POL-LV`, `HR-POL-MC`, `HR-POL-TC`, and `HR-POL-WH`.
- Policy facts require the matching tag. Refusals have no tag.
- A pass requires relevant semantic handling without invented facts.
- Case 2's travel part may receive a generic answer redirected to HR; its AI part
  must be refused.
- Cases 4, 5, 6, 8, 10, 11, and 12 must be refused.
- Cases 1, 3, 7, and 9 may receive a generic answer redirected to HR.
- Concrete policy facts require a matching tag. Refusals do not.
- Grading is manual done by me. `sentence_count` in result JSON is only a diagnostic.

The final prompt refuses unknown policy details because no published policy text is
available. This is safer than fabricating policy details.
