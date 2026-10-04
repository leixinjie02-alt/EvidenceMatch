# Problem Statement (updated from the 23 August 2026 version)

**Lei Xinjie · G2606932C · Section A · PE6201 End-of-Course Project**

## 1 · Working title

EvidenceMatch — checks each job requirement against my real résumé.

## 2 · The problem, and why it matters

When I tailor my résumé to a job posting with a chat assistant, it writes claims my résumé cannot support.

This is measured, not assumed. In my first live run, a plain grounded prompt produced three bullets for one posting and one of them turned an evaluation exercise into "achieving significant improvements in AI system performance". For one search in August I shortlisted 18 postings, so the risk repeats 18 times, and one inflated line that I cannot defend in an interview costs more than a weak line.

The closest existing tools are keyword-match scanners such as Jobscan, which return a match score, and general chat assistants, which rewrite text. Neither ties every generated sentence to a verbatim quote from the résumé, and a score does not say which requirement is uncovered.

Out of scope: deciding whether to apply, ranking jobs, writing cover letters, and submitting anything.

## 3 · Who it is for, and the domain

One user: a graduate job seeker applying to AI and data roles.

Persona: Xinjie, an MSc student with four projects and one internship, checking a posting at night before applying. She knows her own résumé well, has never seen a validation report, and needs to see at a glance what is proven, what is partly proven and what is missing.

What changes for her: she stops pasting her résumé into a chat window and editing the output by instinct. She gets a requirement-by-requirement table with quotes, and only adopts a bullet after checking it against the quote beside it.

Domain: graduate hiring for AI and data roles, in Singapore and China, which is my own job search.

## 4 · Why AI, and which kind

Decision: a prompted foundation model (GPT-4o) with structured JSON output. No retrieval, no agent, no trained model.

Matching the English requirement "assist deployment" to a Chinese résumé line is a language task. The non-AI baseline is a token-overlap rule. On the 50 held-out requirements I reviewed, the rule scored 40.0%, the same as always guessing the most common label, and GPT-4o scored 90.0%.

I stopped at the first rung of the ladder. My confirmed résumé is 27 evidence units and fits in one prompt, so retrieval would add a failure mode and buy nothing. One call per posting needs no tool loop.

What stays rules: removing contact lines, checking that every quote exists in the résumé, checking numbers, and every metric. The model never judges its own output.

## 5 · Proposed approach — build versus buy

| Layer | Own or rent | Named choice | Reason |
|---|---|---|---|
| Interface and serving | Own | Flask backend, single-page HTML frontend | The key stays on my machine |
| Orchestration | Own | One fixed prompt, no retry | A retry hides failures and doubles cost |
| Model | Rent | `openai/gpt-4o` through OpenRouter | No training data; strong cross-language reading |
| Data | Own | Résumé split into one evidence unit per bullet | A citation points at one claim |
| Evaluation and logs | Own | Python validator, 31 unit tests, one JSON record per run | This is what makes the output trustworthy |

Measured cost: USD 0.0184 per posting (about 3,300 input and 1,000 output tokens). One hundred applications cost about USD 1.84. Time to deploy: `pip install -r requirements.txt`, then `python app.py`.

Low-code: skipped. Verbatim-quote checking is custom logic that a workflow builder does not make simpler than one Python function.

## 6 · Data

- **Résumé:** my own, uploaded as PDF. Email and phone lines are removed automatically and I confirm the remaining 27 units before any call. A synthetic résumé of an invented person ships with the repository so that it runs without my data.
- **Job postings:** 48 in total. 18 Chinese postings I collected from LinkedIn and Boss直聘 for A1 (no per-record link). 30 English summaries of real postings from five employers' public Greenhouse boards, each with link, job id and content hash in `jd_additional_30.csv`. They are summaries, not full posting text.
- **Ground truth:** there is no label file fixed in advance, because requirements are extracted by the model. I label each extracted requirement and each generated bullet by hand. This is a single annotator who is also the candidate.
- **Leakage:** the prompt was revised on one posting only (JD19). It is reported separately and never pooled with the 10 held-out postings, which a seeded script fixed before any v2.3 call.

## 7 · Success metric and evaluation

One metric: Unsupported Claim Rate (UCR) = bullets I judge unsupported or unclear ÷ bullets reviewed. Target: 5% or lower. Baseline: 33% (1 of 3) from the v2.1 pilot.

Result on 10 held-out postings: 0 of 15 bullets judged unsupported. With 15 bullets the 95% upper bound is 20.4%, so the target is **not demonstrated**. A later re-read questioned one bullet I had passed; if upheld, UCR is 6.7%.

Abstention is built in and measured: the model may decline to write bullets. It did so for 5 of 10 held-out postings. I did not judge whether each abstention was warranted.

The automatic overclaim flags are a component, not a judge: they fired on 0 of 21 live bullets, so their precision and recall are undefined.

## 8 · Risks, limitations and responsible use

| Risk | Mitigation that is built | What remains |
|---|---|---|
| Overclaimed experience | Validator blocks any output with a non-verbatim quote or an unquoted number; every bullet needs my approval | A quote can exist and still not support the sentence |
| Silent failure: a confident wrong bullet that passes every check | Human review of every bullet; nothing is adopted automatically | My fast review passed one bullet that a re-read questioned |
| Prompt injection inside a posting (OWASP LLM01:2025) | Posting is passed as data; one probe was run and not followed | One probe only; two of nine labels still shifted |
| Personal data sent to a provider (PDPA) | Contact lines stripped; user confirms the evidence; nothing stored server-side between requests | Résumé content still reaches OpenRouter and OpenAI |
| Over-strict validator | Fails closed | 4 of 10 held-out runs were blocked with no fabricated quote |

Intended use: checking my own résumé against a posting. Not for screening or scoring other people, and not for automated submission.

## 9 · Smallest first version

One résumé, one posting, one model call, one validated table. It worked if every quote in the output is found verbatim in the résumé and I can review every bullet. That slice ran live on 4 October 2026 (JD19, 9 requirements, 3 bullets, all quotes verified).

## What changed since the August version

- The title no longer says "agent": the system is one prompted call.
- Retrieval comparison, LLM critic with retry, and PostgreSQL were cut; reasons are in the trade-off analysis.
- The 61.1% and 66.7% figures in the August version are not in my A1 notebooks and I could not reproduce them, so they are withdrawn.
- No written instructor feedback was returned on my sheet; these updates follow the course "watch-outs" guidance.
