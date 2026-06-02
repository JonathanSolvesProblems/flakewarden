"""Deterministically generate the FlakeWarden labeled evaluation corpus.

Produces `failures.jsonl`: ~150 failing-test histories, each hand-labeled
real_defect / flaky / environment. The histories are synthesised to resemble
real UiPath Test Manager execution exports: a window of pipeline runs per test
with outcomes, durations, retry results, error fingerprints, selector-change
flags, plus the unstructured context (stack trace, DOM diff, commit message,
runner logs) the grounded classifier reads.

Why synthetic: a solo builder cannot ship a real enterprise's months of CI
history, and real failure data is proprietary. Seeding the corpus lets the moat
(a labeled set with a measured false-positive rate) exist and stay reproducible.
The generator injects ADVERSARIAL near-boundary cases on purpose so the reported
accuracy is honest rather than a rigged 100%. SETUP.md explains how to replace
this with a real Test Cloud export for a production accuracy study.

Run:  python corpus/generate_corpus.py
"""

from __future__ import annotations

import json
import os
import random

SEED = 20260601
N_PER_CLASS = {"real_defect": 50, "flaky": 55, "environment": 45}
OUT = os.path.join(os.path.dirname(__file__), "failures.jsonl")

DEFECT_ERRORS = [
    "AssertionError: expected total '128.40' but was '142.00'",
    "AssertionError: expected element 'confirmation-banner' to be visible",
    "ValidationError: required field 'taxId' rejected by API (HTTP 400)",
    "AssertionError: expected status 'APPROVED' but got 'PENDING'",
]
DEFECT_COMMITS = [
    "refactor: rename submit button id to #checkout-submit",
    "redesign: move confirmation banner into modal",
    "update: change tax field selector and validation rule",
    "migrate pricing service to v2 rounding",
]
FLAKY_ERRORS = [
    "StaleElementReferenceException: element is detached from the DOM",
    "ElementClickInterceptedException: other element would receive the click",
    "TimeoutError: element not yet visible after 2s (animation in progress)",
    "ElementNotInteractableException: element not interactable",
    "Error: race condition reading cart state before hydration",
]
FLAKY_COMMITS = [
    "chore: bump lint config",
    "docs: update README",
    "test: add coverage for promo codes",
    "style: format with prettier",
]
ENV_ERRORS = [
    "ConnectionRefusedError: connection refused to db-staging:5432",
    "TimeoutError: request to payments-gw timed out after 30000ms",
    "Error: HTTP 503 Service Unavailable from identity-provider",
    "OSError: no space left on device on runner agent-7",
    "Error: could not resolve host 'orders-api.internal'",
]
ENV_LOGS = [
    "runner agent-7 reported 96% disk; staging db restarted at 02:14 UTC",
    "payments-gw health check flapping; SRE incident INC-4821 open",
    "identity-provider returned 503 for 4m during deploy window",
    "network partition on staging vlan; retries exhausted",
]


def _runs(rng, n, pattern, durs, err_pick, selectors_at_break=False, retry_recovery=0.0):
    """pattern: list of 'p'/'f' per run (newest last). err_pick: callable->str."""
    runs = []
    # index of first failure in the trailing failing block, for selector flagging
    streak = 0
    for o in reversed(pattern):
        if o == "f":
            streak += 1
        else:
            break
    break_index = len(pattern) - streak if streak else None
    base = rng.uniform(*durs)
    for i, o in enumerate(pattern):
        if o == "p":
            runs.append({
                "run_index": i,
                "outcome": "pass",
                "duration_s": round(base * rng.uniform(0.92, 1.08), 2),
                "commit_sha": f"{rng.randrange(16**7):07x}",
            })
        else:
            retry = "pass" if rng.random() < retry_recovery else "fail"
            runs.append({
                "run_index": i,
                "outcome": "fail",
                "duration_s": round(base * rng.uniform(0.9, 1.6), 2),
                "commit_sha": f"{rng.randrange(16**7):07x}",
                "retry_outcome": retry,
                "error_signature": err_pick(),
                "selectors_changed": bool(selectors_at_break and break_index is not None and i == break_index),
            })
    return runs


def gen_real_defect(rng, k):
    name = f"Checkout_E2E_{k:03d}"
    n = rng.randint(10, 14)
    streak = rng.randint(2, 4)
    pattern = ["p"] * (n - streak) + ["f"] * streak
    sig = rng.choice(DEFECT_ERRORS)
    commit = rng.choice(DEFECT_COMMITS)
    # Adversarial: ~1 in 6 real defects also recovered once on retry (looks flaky-ish).
    retry_recovery = 0.34 if rng.random() < 0.18 else 0.0
    runs = _runs(rng, n, pattern, (3.0, 9.0), lambda: sig,
                 selectors_at_break=True, retry_recovery=retry_recovery)
    return {
        "test_id": f"TC-RD-{k:03d}",
        "test_name": name,
        "runs": runs,
        "context": {
            "stack_trace": sig + "\n  at CheckoutPage.submit (checkout.spec.ts:88)",
            "recent_dom_diff": "- #submit-btn\n+ #checkout-submit",
            "commit_message": commit,
            "runner_logs": "all services healthy; single runner; no infra alerts",
        },
        "label": "real_defect",
    }


def gen_flaky(rng, k):
    name = f"Cart_UI_{k:03d}"
    n = rng.randint(11, 15)
    # scattered failures among passes -> high flip rate, high isolation
    pattern = []
    for _ in range(n):
        pattern.append("f" if rng.random() < 0.4 else "p")
    if "f" not in pattern:
        pattern[rng.randrange(n)] = "f"
    # Adversarial: ~1 in 6 flaky tests cluster into a short streak (looks defect-ish).
    if rng.random() < 0.16:
        pattern = ["p"] * (n - 2) + ["f", "f"]
    errs = FLAKY_ERRORS
    runs = _runs(rng, n, pattern, (1.5, 6.0),
                 lambda: rng.choice(errs),
                 selectors_at_break=False, retry_recovery=rng.uniform(0.55, 0.85))
    return {
        "test_id": f"TC-FL-{k:03d}",
        "test_name": name,
        "runs": runs,
        "context": {
            "stack_trace": rng.choice(errs) + "\n  at CartWidget.update (cart.spec.ts:54)",
            "recent_dom_diff": "",
            "commit_message": rng.choice(FLAKY_COMMITS),
            "runner_logs": "parallel shard; high runner load; no service incidents",
        },
        "label": "flaky",
    }


def gen_environment(rng, k):
    name = f"Payments_API_{k:03d}"
    n = rng.randint(10, 14)
    streak = rng.randint(1, 4)
    pattern = ["p"] * (n - streak) + ["f"] * streak
    sig = rng.choice(ENV_ERRORS)
    runs = _runs(rng, n, pattern, (2.0, 8.0), lambda: sig,
                 selectors_at_break=False, retry_recovery=rng.uniform(0.2, 0.5))
    return {
        "test_id": f"TC-EN-{k:03d}",
        "test_name": name,
        "runs": runs,
        "context": {
            "stack_trace": sig,
            "recent_dom_diff": "",
            "commit_message": rng.choice(FLAKY_COMMITS),
            "runner_logs": rng.choice(ENV_LOGS),
        },
        "label": "environment",
    }


def main():
    rng = random.Random(SEED)
    rows = []
    for k in range(N_PER_CLASS["real_defect"]):
        rows.append(gen_real_defect(rng, k))
    for k in range(N_PER_CLASS["flaky"]):
        rows.append(gen_flaky(rng, k))
    for k in range(N_PER_CLASS["environment"]):
        rows.append(gen_environment(rng, k))
    rng.shuffle(rows)
    with open(OUT, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print(f"Wrote {len(rows)} labeled failures to {OUT}")
    counts = {}
    for r in rows:
        counts[r["label"]] = counts.get(r["label"], 0) + 1
    print("Class balance:", counts)


if __name__ == "__main__":
    main()
