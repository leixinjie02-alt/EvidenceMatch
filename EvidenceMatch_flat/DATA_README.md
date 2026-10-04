# Data: what each file is and where it came from

| File | Rows | What it is | Source and limits |
|---|---|---|---|
| `jd_corpus_48.json` | 48 | The fixed pool of job postings the app and the evaluation read | The two sets below, combined |
| `jd_corpus_18.json` | 18 | Chinese postings (JD01–JD18) | Collected by me from LinkedIn and Boss直聘 for A1 Part 2. No per-record link |
| `jd_additional_30.json` / `.csv` | 30 | English postings (JD19–JD48) | Short summaries of real postings on five employers' public Greenhouse boards. Each row has the link, job id and a hash of the original text. They are **summaries, not full postings** |
| `source_verification.json` | 30 | Check that each of the 30 links and hashes matched on 4 October 2026 | Produced by `verify_sources.py`. Postings may have closed since |
| `adversarial_jobs.json` | 1 | `ADV01`: the JD19 text plus an injected instruction | Written by me to test prompt injection |
| `sample_resume_synthetic.txt` | – | Résumé of an invented person | Lets anyone run the project without my data |
| `demo_fixture_response.json` | – | Hand-written canned response for the offline demo and the tests | **Not model output** |
| `model_catalog_snapshot.json` | – | Model ids and prices recorded during development | The app reads live prices when it can |

My own résumé is not in the repository. Lines with a phone number or email address are removed before the résumé is shown, sent or saved. The run records in the `run_v23_*` and `pilot_v21_*` files quote sentences from it.

No posting has a pre-assigned label. Labels are given by me, per extracted requirement, during review (see `EVALUATION_README.md`).
