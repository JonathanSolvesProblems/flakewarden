"""Unit tests for the governance invariants in the triage orchestration."""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flakewarden.orchestration import Action, triage
from flakewarden.schema import CorpusCase, Label

CORPUS = os.path.join(os.path.dirname(__file__), "..", "corpus", "failures.jsonl")


def _load():
    with open(CORPUS, encoding="utf-8") as fh:
        return [CorpusCase.from_dict(json.loads(l)) for l in fh if l.strip()]


def test_no_real_defect_is_ever_healed():
    """The core safety invariant: a real defect is never routed to a heal."""
    for c in _load():
        if c.label == Label.REAL_DEFECT:
            d = triage(c)
            assert d.action != Action.PROPOSE_HEAL, f"{c.test_id} would be healed"


def test_every_heal_requires_human_approval():
    for c in _load():
        d = triage(c)
        if d.action == Action.PROPOSE_HEAL:
            assert d.requires_human_approval is True


def test_safety_false_positive_rate_is_zero():
    """Release gate: no real defect classified as flaky/environment."""
    misses = 0
    reals = 0
    for c in _load():
        if c.label == Label.REAL_DEFECT:
            reals += 1
            if triage(c).label != Label.REAL_DEFECT:
                misses += 1
    assert reals > 0
    assert misses == 0, f"safety false-positive rate = {misses}/{reals}"


def test_accuracy_meets_release_gate():
    cases = _load()
    correct = sum(1 for c in cases if triage(c).label == c.label)
    assert correct / len(cases) >= 0.90
