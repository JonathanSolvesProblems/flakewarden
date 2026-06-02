"""Unit tests for the deterministic flake-scorer."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flakewarden import scorer
from flakewarden.schema import FailureContext, Outcome, TestHistory, TestRunResult


def _run(i, outcome, dur=2.0, retry=None, sig=None, sel=False):
    return TestRunResult(
        run_index=i, outcome=Outcome(outcome), duration_s=dur, commit_sha=f"{i:07d}",
        retry_outcome=Outcome(retry) if retry else None, error_signature=sig,
        selectors_changed=sel,
    )


def _hist(runs, ctx=None):
    return TestHistory(test_id="T", test_name="T", runs=runs, context=ctx or FailureContext())


def test_clean_break_scores_as_real_defect():
    # long green run then a contiguous failing tail with a selector change at break
    runs = [_run(i, "pass") for i in range(9)]
    runs += [_run(9, "fail", sig="AssertionError", sel=True), _run(10, "fail", sig="AssertionError")]
    r = scorer.score(_hist(runs))
    assert r.band == scorer.Band.REAL_DEFECT
    assert r.flake_score <= scorer.LOW_BAND


def test_alternating_recovering_scores_as_flaky():
    runs = []
    for i in range(12):
        if i % 2 == 0:
            runs.append(_run(i, "pass"))
        else:
            runs.append(_run(i, "fail", retry="pass", sig=f"Stale-{i}", dur=5.0))
    runs.append(_run(12, "fail", retry="pass", sig="StaleElement", dur=6.0))
    r = scorer.score(_hist(runs))
    assert r.band == scorer.Band.FLAKY
    assert r.flake_score >= scorer.HIGH_BAND


def test_selector_change_caps_flake_score():
    # even if the failure looks jittery, a selector change at the break caps the score
    runs = [_run(i, "pass") for i in range(8)]
    runs += [_run(8, "fail", retry="pass", sig="X", dur=9.0, sel=True),
             _run(9, "fail", retry="pass", sig="Y", dur=9.0)]
    r = scorer.score(_hist(runs))
    assert r.flake_score <= scorer.SELECTOR_BREAK_CAP


def test_score_is_deterministic():
    runs = [_run(i, "pass") for i in range(8)] + [_run(8, "fail", sig="AssertionError", sel=True)]
    a = scorer.score(_hist(runs)).flake_score
    b = scorer.score(_hist(runs)).flake_score
    assert a == b
