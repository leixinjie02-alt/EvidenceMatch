# Verification status (4 October 2026)

- 31 unit tests pass (`python -m unittest discover -p "test_*.py"`). They cover the validator, contact redaction,
  evidence-unit building, overclaim warnings, and a scripted pass through upload → runs → review → metrics → export
  against a mocked API. Mocked tests say nothing about model quality or real cost.
- The notebook cells were executed outside Colab with `google.colab` stubbed. The notebook has **not** been run in
  the real Colab front end by the author yet.
- 30/30 added job sources matched id and content hash on 4 October 2026 (`source_verification.json`); not rechecked since.
- 12 live v2.3 calls were made on 4 October 2026 (UTC) through the browser runner; see the `run_v23_*` files. The Colab notebook path is still unverified in real Colab.
- The browser runner was exercised end to end in Chromium against a mocked API (failure, reload, resume, review, export, import).
- The web app (`app.py` + `index.html`) was driven end to end in Chromium: real PDF upload, missing-key error, offline demo, review, metrics and the recorded-evaluation tab. Its live-key path is covered by a mocked-provider test only.
