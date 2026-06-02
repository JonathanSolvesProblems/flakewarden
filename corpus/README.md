# Evaluation corpus

`failures.jsonl` is the labeled evaluation corpus: 150 failing-test histories, each
tagged `real_defect`, `flaky`, or `environment`. It is the moat — the thing a
weekend "build me a flaky-test detector" clone does not have, because it is what
lets FlakeWarden quote a measured accuracy and false-positive rate.

## Regenerate

```bash
python corpus/generate_corpus.py
```

Deterministic (seed `20260601`), so the corpus and therefore the published metrics
are reproducible. Class balance: 50 real_defect / 55 flaky / 45 environment.

## Record shape

```json
{
  "test_id": "TC-RD-007",
  "test_name": "Checkout_E2E_007",
  "runs": [
    {"run_index": 0, "outcome": "pass", "duration_s": 4.1, "commit_sha": "a1b2c3d"},
    {"run_index": 11, "outcome": "fail", "duration_s": 6.0, "commit_sha": "9f8e7d6",
     "retry_outcome": "fail", "error_signature": "AssertionError: expected ...",
     "selectors_changed": true}
  ],
  "context": {
    "stack_trace": "...", "recent_dom_diff": "- #submit-btn\n+ #checkout-submit",
    "commit_message": "refactor: rename submit button id", "runner_logs": "..."
  },
  "label": "real_defect"
}
```

`runs` is the structured history the deterministic scorer reads. `context` is the
messy free-text the grounded classifier reads. `label` is used only for evaluation,
never at inference time.

## Why synthetic

A solo builder cannot ship an enterprise's proprietary CI history. The generator
plants realistic signals **and** deliberate near-boundary/adversarial cases (e.g. a
real defect that recovered once on retry, a flaky test that clustered into a short
streak) so the measured accuracy is honest rather than a rigged 100%. See
[`../docs/limitations.md`](../docs/limitations.md) for replacing this with a real
Test Cloud export.
