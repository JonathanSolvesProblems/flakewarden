"""A small UI-style test suite with deliberately seeded behaviours.

This stands in for a real UiPath Test Cloud suite. Each "test" returns pass/fail
for a given run index, with three planted behaviours so FlakeWarden has something
real to triage:

  * stable_*      -> always pass (control: must never be flagged)
  * flaky_*       -> non-deterministically fail (timing/stale-element style)
  * regressed_*   -> start passing, then fail from a known "bad" commit onward
                     (a real defect introduced at a fixed run index)

`run_history.py` executes this suite over N runs and emits execution history in
FlakeWarden's schema so the scorer/triage pipeline can consume it. In the live
solution this data comes from the Test Manager results API instead; the shape is
the same. Determinism is driven by (test, run_index), never by wall-clock, so the
suite is reproducible.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional


@dataclass
class StepResult:
    outcome: str                       # "pass" | "fail"
    duration_s: float
    error_signature: Optional[str] = None
    retry_outcome: Optional[str] = None
    selectors_changed: bool = False


def _jitter(test: str, run_index: int, lo: float, hi: float) -> float:
    h = int(hashlib.sha256(f"{test}:{run_index}".encode()).hexdigest(), 16)
    return lo + (h % 1000) / 1000.0 * (hi - lo)


def _coin(test: str, run_index: int, p_fail: float) -> bool:
    h = int(hashlib.sha256(f"coin:{test}:{run_index}".encode()).hexdigest(), 16)
    return (h % 1000) / 1000.0 < p_fail


# --- stable tests (control) ---------------------------------------------------

def stable_login(run_index: int) -> StepResult:
    return StepResult("pass", _jitter("stable_login", run_index, 1.0, 1.2))


def stable_search(run_index: int) -> StepResult:
    return StepResult("pass", _jitter("stable_search", run_index, 0.8, 1.0))


# --- flaky tests --------------------------------------------------------------

def flaky_add_to_cart(run_index: int) -> StepResult:
    if _coin("flaky_add_to_cart", run_index, 0.35):
        return StepResult("fail", _jitter("flaky_add_to_cart", run_index, 1.0, 4.0),
                          error_signature="StaleElementReferenceException: element detached from the DOM",
                          retry_outcome="pass")
    return StepResult("pass", _jitter("flaky_add_to_cart", run_index, 1.0, 2.0))


def flaky_promo_banner(run_index: int) -> StepResult:
    if _coin("flaky_promo_banner", run_index, 0.3):
        return StepResult("fail", _jitter("flaky_promo_banner", run_index, 1.5, 5.0),
                          error_signature="TimeoutError: element not yet visible after 2s (animation in progress)",
                          retry_outcome="pass" if _coin("retry_promo", run_index, 0.7) else "fail")
    return StepResult("pass", _jitter("flaky_promo_banner", run_index, 1.2, 2.2))


# --- regressed test (real defect introduced at a fixed run) -------------------

REGRESSION_AT = 8  # the "bad commit" lands at run index 8

def regressed_checkout(run_index: int) -> StepResult:
    if run_index >= REGRESSION_AT:
        return StepResult("fail", _jitter("regressed_checkout", run_index, 3.0, 4.0),
                          error_signature="AssertionError: expected total '128.40' but was '142.00'",
                          retry_outcome="fail",
                          selectors_changed=(run_index == REGRESSION_AT))
    return StepResult("pass", _jitter("regressed_checkout", run_index, 3.0, 3.6))


SUITE = {
    "stable_login": stable_login,
    "stable_search": stable_search,
    "flaky_add_to_cart": flaky_add_to_cart,
    "flaky_promo_banner": flaky_promo_banner,
    "regressed_checkout": regressed_checkout,
}
