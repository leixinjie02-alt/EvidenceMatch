# Reviewed development pilot — 4 October 2026

Original v2.1 API response is preserved byte-for-byte. The user accepted the assistant-proposed verdicts in chat: supported / unclear / supported. This was assisted human review, not an independent blind assessment. The full uploaded resume informed the judgments, while model citation quality is a separate limitation. The personal resume and API key are not included.

3/3 bullets reviewed. Supported 2; definitely unsupported 0; unclear 1. Under the existing conservative definition (unsupported OR unclear), UCR = 1/3 = 33.3%. This is one development case, not an estimate of general performance. Structural checks flagged none; recall against the single unsupported-or-unclear finding was 0/1, and precision is undefined because nothing was flagged.

Actual API cost USD 0.0154775; latency 9.3528 seconds; tokens 2837. No independently prelabelled job ground truth is available; do not report classification accuracy.

Prompt v2.2 addresses clause-level citations, personal versus team contribution, in-progress education, compound requirements, and unsupported cloud/ML inference. No live v2.2 API results exist yet. Reusing this job is a development regression check, not held-out evaluation.

Update: v2.2 was never run live. v2.3 keeps the v2.2 rules and also changes how the résumé is split into evidence units (per bullet instead of three large blocks), so a v2.3 rerun of this job differs from this pilot in two ways and is not a clean prompt comparison.
