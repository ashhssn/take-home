# README

## Part A

### Assumptions
- No HR policy knowledge base is shared for this part. I assume my very own reference codes for four domains:
    - Leave: `HR-POL-LV`
    - Medical claim: `HR-POL-MC`
    - Travel claim: `HR-POL-TC`
    - Working hours: `HR-POL-WH`
- I treat a safe generic refusal as a PASS when no published policy fact is supplied. A generic policy answer without source text is a FAIL for speculation.
- I also assume work from home is not categorized under working hours.


### Dir structure

```text
task-a/
├── prompts/            # versioned system prompts
├── results/            # model outputs from versioned system prompts
├── run_prompt.py       # script to run the model with versioned system prompts
├── final-grid.md       # results of all test cases across final chosen versions
├── iteration-log.md    # log of iterations and observations
└── README.md           # readme for part A
```

### Usage

```bash
ollama pull qwen2.5:0.5b-instruct
python3 task-a/run_prompt.py --version v6 --max-tokens 64
```

Part A final settings: temperature `0`, seed `42`, and `num_predict` `64`.


## Part B

### Assumptions
- I assume that this part is solely for evaluating the base LLM `qwen2.5:0.5b-instruct` and no specific system prompt towards getting a response as close to the examples are allowed
- I assume generic system prompt is allowed to maintain response length and quality of LLM.

### Dir structure

```text
task-b/
├── evaluate.py         # script to evaluate the model on test cases
├── test_cases.jsonl    # test cases for evaluation
├── results.json        # model outputs from evaluation
└── README.md           # readme for part B
```

### Usage

```bash
ollama pull qwen2.5:0.5b-instruct
python3 task-b/evaluate.py --output task-b/results.json
```

## Part C

### Assumptions
- I assume the task "Identify and fix a data quality issue you find in the usable set" refers to updating the labelled `csv` file directly. This is documented in `task-c/part_c_curation_notes.md`.

### Dir structure

```text
task-c/
├── labelled_singlish pairs_Deployment Team Take Home Assignement 202607 Y0 (1).csv # labelled source dataset
├── new_examples.csv            # added examples
└── part_c_curation_notes.md    # curation notes for part C
```
