# Data and evaluation

## Provenance and sampling

Collected on 2026-10-04 SGT from employer public Greenhouse board APIs: SimplifyNext (6), Temus (10), OKX (8), AppLovin (4), Intrinsic (2). Each of the 30 selected IDs was present with nonempty description in the employer board response. Each record preserves its employer's application URL, API endpoint, job ID, source update timestamp and SHA-256 of the original HTML field. Board availability at retrieval does not guarantee a vacancy remains open later. The release distributes original concise paraphrases of requirements, not copied full descriptions. Full source HTML is not bundled. Source URLs are recorded per row in both JSON and CSV.

The first 18 records preserve the prior A1 corpus and still lack original per-record source URLs. They have not been independently reverified. The combined 48-record set mixes Chinese user-supplied text and English summaries, two different formats and geographical/role distributions. Always report the two cohorts separately. A summary can omit requirements; measurement on summaries cannot establish full-JD extraction performance. Senior, specialized and eligibility-restricted roles deliberately test gap identification; this is not a personalized job recommendation list.

## Candidate data

The user uploads their own résumé. Extraction is local to the Colab runtime. Lines containing an email address or phone number are removed, then each bullet or entry heading becomes one evidence unit in its source wording (no LLM rewriting) with its section and parent entry. The user confirms the printed units before any model call. The full confirmed set is sent, because lexical retrieval across Chinese evidence and English job text can miss relevant units. A résumé is candidate-supplied evidence, not independent proof of a qualification.

## Evaluation

The design, metrics and limitations are in the README. Definitions: Strong = direct evidence fully supports that requirement; Partial = related evidence with a named gap; Missing = no supporting evidence supplied (which does not mean the skill is absent). Unsupported and unclear bullets both count against UCR. Rates are null until every generated bullet is reviewed, and null when no bullets were generated. The lexical baseline thresholds (0.55, 0.15) were fixed before any run and are not calibrated. A blocked or failed run is reported as such and contributes no bullets.

## Operational measurements

Each run retains timestamp, prompt version/hash, candidate evidence hash, JD hash, requested/returned model, response ID, token usage, elapsed request time, finish reason, validation and raw model response. Reported provider cost is recorded when returned; otherwise it remains null. A separate token-price estimate is explicitly an estimate and can differ because of caching or provider pricing. Cost sums include counts of records with actual cost available. API key and request headers are never serialized. Successful local/mock tests do not imply successful live model runs.

## References

- Job links and API endpoints: `jd_additional_30.csv`.
- OpenRouter request/usage format: https://openrouter.ai/docs/api_reference/overview
- Public model catalogue: https://openrouter.ai/api/v1/models
- GPT-4o model: https://openrouter.ai/openai/gpt-4o
