# Seeded test suite

A small UI-style suite with deliberately planted behaviours, standing in for a real
UiPath Test Cloud suite so the pipeline can be demoed end-to-end on freshly
generated data.

| Test | Planted behaviour |
|---|---|
| `stable_login`, `stable_search` | always pass (control — must never be flagged) |
| `flaky_add_to_cart` | non-deterministic stale-element failures, recovers on retry |
| `flaky_promo_banner` | timing/animation failures, intermittent |
| `regressed_checkout` | a **real defect** introduced at run index 8 (assertion + selector change) |

Determinism is keyed on `(test, run_index)` via a hash, never wall-clock, so runs
are reproducible.

## Use

```bash
python seeded_suite/run_history.py --runs 14            # only currently-failing tests
python seeded_suite/run_history.py --runs 14 --all      # include passing tests
python -m flakewarden.cli triage seeded_suite/history.jsonl
```

Expected: the regression is **escalated** as a real defect (caught by the
deterministic scorer via selector-change-at-break), and the flaky test produces a
**proposed heal** behind the human-review gate. In production this script is
replaced by a pull from the Test Manager results API; everything downstream is
unchanged.
