"""Deterministic feature extraction from test execution history.

Every feature here is exact, reproducible math over the structured run history.
No LLM is involved. Given the same history window you always get the same numbers,
which is what makes the flake score auditable and defensible.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, pstdev

from .schema import Outcome, TestHistory


@dataclass
class Features:
    flip_rate: float              # fraction of adjacent run-pairs that change outcome
    failure_isolation: float      # 1.0 => failures are scattered (flaky-like), 0.0 => one contiguous tail (defect-like)
    pass_after_retry_rate: float  # fraction of failing runs that passed on auto-retry
    runtime_zscore: float         # |z| of the latest duration vs the test's own history
    error_signature_entropy: float  # normalized variety of error signatures among failures
    selector_change_at_break: float  # 1.0 if selectors changed exactly at the first red run
    failing_streak: int           # length of the current consecutive-failure tail
    n_runs: int

    def as_dict(self) -> dict:
        return {
            "flip_rate": round(self.flip_rate, 4),
            "failure_isolation": round(self.failure_isolation, 4),
            "pass_after_retry_rate": round(self.pass_after_retry_rate, 4),
            "runtime_zscore": round(self.runtime_zscore, 4),
            "error_signature_entropy": round(self.error_signature_entropy, 4),
            "selector_change_at_break": round(self.selector_change_at_break, 4),
            "failing_streak": self.failing_streak,
            "n_runs": self.n_runs,
        }


def _flip_rate(outcomes: list[Outcome]) -> float:
    if len(outcomes) < 2:
        return 0.0
    flips = sum(1 for a, b in zip(outcomes, outcomes[1:]) if a != b)
    return flips / (len(outcomes) - 1)


def _failing_streak(outcomes: list[Outcome]) -> int:
    streak = 0
    for o in reversed(outcomes):
        if o == Outcome.FAIL:
            streak += 1
        else:
            break
    return streak


def _failure_isolation(outcomes: list[Outcome]) -> float:
    """How scattered are the failures?

    A single contiguous block of failures at the tail (a clean break after a
    commit) looks like a real defect -> low isolation. Failures sprinkled
    between passes look flaky -> high isolation.

    Implemented as: number of distinct failure "runs" (maximal contiguous
    failure blocks) divided by total failures. 1.0 means every failure is its
    own isolated island; ~1/streak means one solid block.
    """
    n_fail = sum(1 for o in outcomes if o == Outcome.FAIL)
    if n_fail == 0:
        return 0.0
    blocks = 0
    prev_fail = False
    for o in outcomes:
        is_fail = o == Outcome.FAIL
        if is_fail and not prev_fail:
            blocks += 1
        prev_fail = is_fail
    return blocks / n_fail


def _pass_after_retry_rate(history: TestHistory) -> float:
    failed = [r for r in history.runs if r.outcome == Outcome.FAIL]
    if not failed:
        return 0.0
    recovered = sum(1 for r in failed if r.retry_outcome == Outcome.PASS)
    return recovered / len(failed)


def _runtime_zscore(history: TestHistory) -> float:
    durations = [r.duration_s for r in history.runs]
    if len(durations) < 3:
        return 0.0
    mu = mean(durations[:-1])
    sigma = pstdev(durations[:-1])
    if sigma == 0:
        return 0.0
    return abs((durations[-1] - mu) / sigma)


def _error_signature_entropy(history: TestHistory) -> float:
    sigs = [r.error_signature for r in history.runs
            if r.outcome == Outcome.FAIL and r.error_signature]
    if len(sigs) <= 1:
        return 0.0
    distinct = len(set(sigs))
    # Normalize: all-same => 0.0, all-distinct => 1.0
    return (distinct - 1) / (len(sigs) - 1)


def _selector_change_at_break(history: TestHistory) -> float:
    """1.0 iff selectors changed exactly at the run where the test first turned red.

    A selector/locator change coinciding with the break is the classic
    'real defect / UI change broke the test' fingerprint, not flakiness.
    """
    outcomes = [r.outcome for r in history.runs]
    streak = _failing_streak(outcomes)
    if streak == 0:
        return 0.0
    break_index = len(history.runs) - streak
    return 1.0 if history.runs[break_index].selectors_changed else 0.0


def extract(history: TestHistory) -> Features:
    outcomes = [r.outcome for r in history.runs]
    return Features(
        flip_rate=_flip_rate(outcomes),
        failure_isolation=_failure_isolation(outcomes),
        pass_after_retry_rate=_pass_after_retry_rate(history),
        runtime_zscore=_runtime_zscore(history),
        error_signature_entropy=_error_signature_entropy(history),
        selector_change_at_break=_selector_change_at_break(history),
        failing_streak=_failing_streak(outcomes),
        n_runs=len(history.runs),
    )
