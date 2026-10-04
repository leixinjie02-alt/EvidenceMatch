# v2.3 live evaluation — 4 October 2026 (UTC)

12 GPT-4o calls made from the browser runner with my own OpenRouter key: JD19 (development regression), the 10 held-out
jobs fixed in `eval_plan.json`, and the injection probe ADV01. `browser_export_raw.json` is the untouched export
(provider responses plus my review). The other files were produced from it by `session.import_browser_run()`:
one record per run, `human_audit.json` (bullets), `requirement_audit.json`, `job_audit.json`, `evaluation_report.json`.

Read with these limits in mind:
- Review coverage: all 21 bullets; 59 of 110 requirement labels (JD19, JD03, JD06, JD08, JD14 in full, 5 of 7 for JD23); 5 of 12 job-level extraction checks.
- 58 of the 59 requirement labels were given with the model's label visible.
- The bullet review took a few minutes and has no written reasons. A later AI-assisted re-read flagged JD42 bullet B3
  ("Implemented backend development…" where the résumé says 参与, "participated in") as an ownership upgrade that the
  review passed. The recorded verdicts are unchanged; the README reports both readings.
- `latency_seconds` is null: the page stopped its timer at the response headers (`time_to_response_headers_seconds`).
- Files quote my résumé (contact lines removed). No API key is present.
