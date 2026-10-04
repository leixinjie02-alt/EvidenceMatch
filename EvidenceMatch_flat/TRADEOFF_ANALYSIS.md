# EvidenceMatch — Project Report: Business and Technical Trade-off Analysis

**EvidenceMatch · Lei Xinjie · G2606932C · PE6201 End-of-Course Project**

EvidenceMatch labels each requirement in a job posting Strong, Partial or Missing against my real résumé, and drafts résumé bullets that must quote the résumé. On 10 held-out postings it cost USD 0.018 per posting and I judged all 15 generated bullets supported. The same run showed its safety check blocking 4 postings in 10 for harmless reasons. This analysis explains the choices behind those numbers and what each one cost.

## 1 · Which AI, and why not more

I chose one prompted GPT-4o call with structured output.

The alternative at the bottom of the ladder is a rule. I built it: a token-overlap score with fixed thresholds. On the 50 held-out requirements I reviewed, it agreed with me on 40.0%, exactly the majority-class rate. GPT-4o agreed on 90.0% (Wilson 95% interval 78.6–95.7%). Matching "assist deployment" to a Chinese résumé line needs language understanding, and the rule has none.

The alternatives above are retrieval and an agent, both in my August proposal. I cut them. My confirmed résumé is 27 evidence units and fits in one prompt, so a retriever could only lose evidence. An agent loop would add calls, cost and failure modes to a task with one step. What I gave up is scale: a ten-page CV or a library of past projects would need retrieval.

## 2 · Build versus buy

| Layer | Decision | Business reason | Technical reason |
|---|---|---|---|
| Model | Rent `openai/gpt-4o` via OpenRouter | No training cost; pay per use | Reads Chinese evidence against English postings |
| Interface | Own: Flask backend, one HTML page | Free to run locally | Key and résumé stay on the user's machine |
| Orchestration | Own: fixed prompt, no retry | Cost is predictable: one call per posting | A retry would hide a failed validation |
| Evidence data | Own: one unit per résumé bullet | Works for any résumé | A citation points at a single claim |
| Validation, metrics, logs | Own: Python, 31 unit tests, JSON records | This is the product's value | Deterministic and checkable |

Cost is measured. Twelve calls cost USD 0.2238. The 10 held-out postings averaged USD 0.0184 at about 3,300 input and 1,000 output tokens. One hundred applications cost about USD 1.84, which is negligible beside the hours of rewriting it replaces. At the scale of a careers office running 100,000 checks a year the bill is about USD 1,840, and a smaller model becomes the first thing to test. I did not test one, so I make no claim about it.

Time to deploy is two commands. I skipped low-code because verbatim-quote checking is custom logic.

## 3 · What the evaluation shows

A seeded script fixed 10 held-out postings before any call: four Chinese postings from my A1 corpus and six English summaries of real Singapore postings, from intern to senior. Each ran once.

| Measure (held-out) | Result |
|---|---|
| Unsupported Claim Rate | 0 of 15 bullets (95% upper bound 20.4%) |
| Requirement labels agreeing with mine | 45 of 50 = 90.0% |
| Token-overlap rule / majority class | 40.0% / 40.0% |
| Runs passing the validator | 6 of 10 |
| Model declined to write bullets | 5 of 10 |
| Cost per posting | USD 0.0184 |

My target was a UCR of 5% or lower. Fifteen bullets cannot demonstrate that: the interval reaches 20%. A later AI-assisted re-read also questioned one bullet I had passed, where "participated in" became "Implemented". If upheld, UCR is 1 of 15, or 6.7%.

The label figure is an upper bound. I reviewed 50 of 92 extracted requirements, with the model's label on screen. All five disagreements were the model being stricter than me.

On the posting used for prompt development, the first prompt produced 2 supported bullets of 3 and the current one 3 of 3. I claim no improvement: two things changed and n is 3.

Latency is not reported. My evaluation page stopped its timer at the response headers. The only valid figure is 9.35 seconds from the earlier pilot.

## 4 · Three trade-offs the results exposed

**Safety against usability.** The validator fails closed. It blocked 4 of 10 runs, and none held a fabricated quote. Two had a real quote under my six-character minimum ("SQL", "Linux"). One used a full-width comma. One reworded requirement text while splitting a sentence. I left the rules unchanged, because loosening them after seeing results is tuning on the test set. As it stands the check is too strict for daily use, and that is the price of never passing a made-up quote.

**Caution against usefulness.** The model declined to write for 5 of 10 postings. For chip design that is right. For a general algorithm-engineer posting with two Strong and seven Partial matches it is probably over-cautious. The prompt rules that removed overclaiming also removed output.

**Human review against automation.** Seven deterministic overclaim flags fired on none of 21 bullets and missed the one questionable bullet. So the human reviewer is the only control on meaning, and my review was fast and unwritten. Adding a model as judge would cost a second call and need its own labelled set; I judged that worse than admitting the gap.

## 5 · What was hard, and what I tuned

**What changes for the user.** Before, I pasted my résumé into a chat assistant and edited its output by instinct. Now I get a table I can check line by line, and the tool refuses to write when my résumé has nothing to say.

**Prompt tuning.** My first live prompt labelled 8 of 9 requirements Strong on one posting, including "cloud familiarity" inferred from Git and Linux, and one of three bullets overclaimed. I added rules: cite every clause, keep "assisted" and "participated", treat a degree in progress as incomplete, never infer cloud from Git. On the same posting the labels became 5 Strong and 4 Partial. It still called the cloud requirement Strong, so a prompt rule is not a guarantee.

**Evidence granularity.** The first version split my résumé into three large blocks, so a citation pointed at a third of the page. I rebuilt it as 27 units, one per bullet.

**Rough edges.** The first notebook sent my phone number and email to the model; contact lines are now stripped first. The Colab widget interface rendered blank, so I replaced it with a local web app. My latency timer was wrong and I report no v2.3 latency.

## 6 · Risk and responsible use

| Risk | Control that is built | Residual |
|---|---|---|
| Overclaimed experience | Quote and number checks; human approval per bullet | A real quote may not support the sentence |
| Silent failure | Nothing is adopted automatically | Depends on review quality |
| Prompt injection (OWASP LLM01:2025) | Posting passed as data; one probe run, not followed | One probe; two of nine labels shifted |
| Personal data (PDPA) | Contact lines stripped; user confirms evidence; server stores nothing between requests | Résumé text reaches the provider |

Intended use is checking my own résumé. It is not for screening other people.

## 7 · Limits, and what I would do next

One résumé, one model, one run per posting, one reviewer who is also the author and the candidate. The English postings are summaries.

Next: separate "quote too short" from "quote not found" in the validator and re-test on new postings; have a second person label a subset blind; run each posting three times to measure stability; test a cheaper model against the same held-out set.
