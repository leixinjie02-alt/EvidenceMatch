# Evaluation: what was measured and how to read the files

## Design

1. `make_eval_plan.py` (seed 6201) picked **10 held-out postings** before any v2.3 model call and wrote them to `eval_plan.json`: 4 Chinese postings and 6 English summaries, from intern to senior, including one deliberate mismatch.
2. `JD19` is the posting the prompt was revised on. It is a development check and is never pooled with the held-out set.
3. `ADV01` is one prompt-injection probe.
4. Each posting was run once with `openai/gpt-4o`. I then reviewed the output by hand.

## Metrics

| Metric | Definition |
|---|---|
| Unsupported Claim Rate (UCR) | Bullets I judged unsupported or unclear ÷ bullets reviewed. Null until every bullet is reviewed |
| Requirement label agreement | Share of extracted requirements where the model's Strong / Partial / Missing equals mine |
| Rule baseline | A token-overlap rule scored on the same requirements |
| Majority baseline | Always guessing my most common label |
| Validator pass rate | Runs whose quotes, numbers and structure passed the deterministic checks |
| Abstention | Runs where the model declined to write bullets |
| Flag precision / recall | Automatic overclaim flags against my verdicts |
| Cost | Provider-reported USD per run |

## Folders

- `pilot_v21/` — the first live run (prompt v2.1, one posting, 3 bullets, 1 unclear).
- `run_v23/` — the 12 live runs of the current version: one JSON record per run, my review files, `evaluation_report.json` with every metric, and the untouched browser export. Its README lists the caveats.

## Results and limits

The numbers are in the `README.md`. In short: UCR 0 of 15 held-out bullets (95% upper bound 20.4%), label agreement 45 of 50, validator pass rate 6 of 10. One reviewer, who is also the author; the model's label was visible during review; one run per posting.

## Reproduce

`python -m unittest discover -p "test_*.py"` checks the metric code against a mocked API. Re-running the live evaluation needs an OpenRouter key and a résumé, and will not give identical outputs.
