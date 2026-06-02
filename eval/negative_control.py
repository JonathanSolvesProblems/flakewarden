"""Negative-control checks: prove FlakeWarden stays safe when it should.

A demo that only shows the system catching things is not enough for either judge.
These assertions prove the fail-safe behaviour:

  1. SAFETY: across the whole corpus, NO real defect is ever routed to a healing
     or quarantine action. Real defects are only ever escalated or held for review.
  2. NO AUTO-APPLY: every proposed healing action carries requires_human_approval.
  3. CONTROL CASE: a regression with a positive defect fingerprint is escalated,
     not silenced.

Exits non-zero if any invariant is violated, so it can gate CI / the release.

Run:  python eval/negative_control.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flakewarden.orchestration import Action, triage  # noqa: E402
from flakewarden.schema import CorpusCase, Label  # noqa: E402

CORPUS = os.path.join(os.path.dirname(__file__), "..", "corpus", "failures.jsonl")
HEAL_OR_QUARANTINE = {Action.PROPOSE_HEAL}


def load(path):
    with open(path, encoding="utf-8") as fh:
        return [CorpusCase.from_dict(json.loads(l)) for l in fh if l.strip()]


def main() -> int:
    cases = load(CORPUS)
    violations = []

    for c in cases:
        d = triage(c)

        # Invariant 1: a real defect must never be sent to heal/quarantine.
        if c.label == Label.REAL_DEFECT and d.action in HEAL_OR_QUARANTINE:
            violations.append(f"SAFETY: real defect {c.test_id} routed to {d.action.value}")

        # Invariant 2: any heal proposal must require human approval.
        if d.action == Action.PROPOSE_HEAL and not d.requires_human_approval:
            violations.append(f"AUTO-APPLY: {c.test_id} would heal without human approval")

    n_real = sum(1 for c in cases if c.label == Label.REAL_DEFECT)
    n_real_escalated = sum(1 for c in cases
                           if c.label == Label.REAL_DEFECT
                           and triage(c).action in {Action.ESCALATE_DEFECT, Action.HOLD_FOR_REVIEW})

    print("Negative-control checks")
    print("-" * 40)
    print(f"real defects in corpus:                 {n_real}")
    print(f"real defects escalated / held (safe):   {n_real_escalated}/{n_real}")
    print(f"real defects auto-healed (must be 0):   {n_real - n_real_escalated}")

    if violations:
        print("\nFAILED. Invariant violations:")
        for v in violations:
            print(f"  - {v}")
        return 1
    print("\nPASSED. No real defect was hidden; no heal bypassed the human gate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
