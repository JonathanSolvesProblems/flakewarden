"""Robustness / edge-case tests (feasibility & versatility criterion).

These exercise the ugly inputs a real Test Manager export will eventually throw
at the pipeline: short histories, missing optional context, all-failing windows,
and a malformed JSONL row.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flakewarden import scorer  # noqa: E402
from flakewarden.classifier import RuleBasedClassifier  # noqa: E402
from flakewarden.orchestration import triage  # noqa: E402
from flakewarden.schema import CorpusCase, FailureContext, Outcome, TestHistory, TestRunResult  # noqa: E402


def _run(i, outcome="fail", **kw):
    return TestRunResult(run_index=i, outcome=Outcome(outcome), duration_s=1.0,
                         commit_sha=f"{i:07d}", **kw)


def test_single_run_history_does_not_crash():
    h = TestHistory(test_id="T", test_name="T", runs=[_run(0)])
    r = scorer.score(h)
    assert 0.0 <= r.flake_score <= 1.0
    d = triage(h)
    assert d.label is not None


def test_empty_context_is_handled():
    h = TestHistory(test_id="T", test_name="T",
                    runs=[_run(i, "pass") for i in range(5)] + [_run(5)],
                    context=FailureContext())
    pred = RuleBasedClassifier().classify(h)
    # No fingerprint at all -> must default to the safe direction (real_defect).
    assert pred.label.value == "real_defect"
    assert pred.confidence < 0.6


def test_all_failing_window():
    h = TestHistory(test_id="T", test_name="T", runs=[_run(i) for i in range(10)])
    r = scorer.score(h)
    assert r.features.failing_streak == 10
    assert triage(h).label is not None


def test_missing_optional_fields_via_from_dict():
    # only the required fields present; everything optional omitted
    row = {"test_id": "T", "test_name": "T",
           "runs": [{"run_index": 0, "outcome": "fail", "duration_s": 2.0, "commit_sha": "abc"}]}
    c = CorpusCase.from_dict(row)
    assert c.runs[0].error_signature is None
    assert triage(c).label is not None


def test_malformed_jsonl_row_raises_cleanly(tmp_path):
    p = tmp_path / "bad.jsonl"
    p.write_text('{"not":"a valid case"}\n', encoding="utf-8")
    with pytest.raises(KeyError):
        CorpusCase.from_dict(json.loads(p.read_text(encoding="utf-8").strip()))
