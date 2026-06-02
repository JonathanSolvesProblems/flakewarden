"""Deterministically generate the FlakeWarden labeled evaluation corpus.

Produces `failures.jsonl`: ~150 failing-test histories, each hand-labeled
real_defect / flaky / environment, resembling UiPath Test Manager execution
exports (a window of pipeline runs with outcomes, durations, retries, error
fingerprints, selector-change flags, plus unstructured context).

DESIGN FOR HONEST METRICS (this matters):
  1. `selectors_changed` is a NOISY signal, not an oracle. Only ~65% of real
     defects carry a selector-change-at-break (logic/pricing/API defects do not),
     and ~10% of flaky tests carry a spurious, unrelated selector change. So the
     deterministic scorer's selector heuristic is a real signal that can be wrong,
     not a planted label proxy.
  2. The error-message vocabulary here is DECOUPLED from the classifier's
     patterns: messages are paraphrased surface forms, and a deliberate fraction
     use wording outside the classifier's keyword set, so some cases are genuinely
     misclassified. Accuracy is earned by semantic overlap, not string identity.
  3. CONFLICT cases are injected: real defects whose run-history statistics look
     flaky (retry recovery + jitter, no selector change), where only the grounded
     context reveals the regression. These are exactly the cases the deterministic
     scorer alone gets wrong and the generative layer must catch -- they justify
     the LLM's existence and stress the safety contract.

Because of (1)-(3) the measured accuracy is intentionally below 100% and the
safety false-positive rate is measured, not designed to be zero. See
../docs/limitations.md for replacing this with a real Test Cloud export.

Run:  python corpus/generate_corpus.py
"""

from __future__ import annotations

import json
import os
import random

SEED = 20260601
N_PER_CLASS = {"real_defect": 50, "flaky": 55, "environment": 45}
OUT = os.path.join(os.path.dirname(__file__), "failures.jsonl")

# Surface forms are deliberately varied and NOT identical to the classifier's
# keyword patterns. Some entries (marked) sit outside the classifier vocabulary so
# they are honestly hard.
DEFECT_ERRORS = [
    "Expected order total 128.40, received 142.00",
    "Assertion failed: confirmation banner was not shown",
    "Field 'taxId' rejected by API with status 400",
    "Computed discount differs from expected by 13.60",
    "Final price mismatch after pricing change",          # harder: 'mismatch' only
]
DEFECT_COMMITS = [
    "refactor: rename submit button id to #checkout-submit",
    "redesign: move confirmation banner into a modal",
    "update: change tax field rules and validation",
    "migrate pricing service to v2 rounding",
    "feature: new promotional pricing engine",
]
FLAKY_ERRORS = [
    "Element reference went stale mid-interaction",
    "Click did not register; overlay still fading in",     # harder: no obvious keyword
    "Locator resolved before hydration completed",
    "Intermittent: widget not yet rendered within 2s",
    "Detached node encountered during retry",
]
FLAKY_COMMITS = [
    "chore: bump lint config",
    "docs: update README",
    "test: add coverage for promo codes",
    "style: reformat with prettier",
]
ENV_ERRORS = [
    "Could not establish connection to db-staging:5432",
    "Upstream payments-gw returned 503 after 30s",
    "Identity provider unavailable during deploy window",
    "Runner agent out of disk space",
    "Host orders-api.internal could not be resolved",
]
ENV_LOGS = [
    "runner agent-7 reported 96% disk; staging db restarted at 02:14 UTC",
    "payments-gw health check flapping; SRE incident INC-4821 open",
    "identity-provider returned 503 for 4m during deploy window",
    "network partition on staging vlan; retries exhausted",
]
HEALTHY_LOGS = [
    "all services healthy; single runner; nothing flagged",
    "clean run; nominal runner load",
]
NEUTRAL_LOGS = [
    "parallel shard; elevated runner load; no service incidents",
    "standard shard; no infra alerts",
]


def _runs(rng, n, pattern, durs, err_pick, selector_break=False, retry_recovery=0.0):
    """pattern: list of 'p'/'f' per run (newest last)."""
    runs = []
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
                "run_index": i, "outcome": "pass",
                "duration_s": round(base * rng.uniform(0.92, 1.08), 2),
                "commit_sha": f"{rng.randrange(16**7):07x}",
            })
        else:
            retry = "pass" if rng.random() < retry_recovery else "fail"
            runs.append({
                "run_index": i, "outcome": "fail",
                "duration_s": round(base * rng.uniform(0.9, 1.6), 2),
                "commit_sha": f"{rng.randrange(16**7):07x}",
                "retry_outcome": retry,
                "error_signature": err_pick(),
                "selectors_changed": bool(selector_break and break_index is not None and i == break_index),
            })
    return runs


def gen_real_defect(rng, k):
    n = rng.randint(10, 14)
    streak = rng.randint(2, 4)
    pattern = ["p"] * (n - streak) + ["f"] * streak
    sig = rng.choice(DEFECT_ERRORS)
    commit = rng.choice(DEFECT_COMMITS)
    # ~65% of real defects have a selector change at the break; the rest are
    # logic/pricing/API defects with no selector signal.
    has_selector = rng.random() < 0.65
    dom_diff = "- #submit-btn\n+ #checkout-submit" if has_selector else ""
    # ~18% recovered once on retry (adversarial; looks slightly flaky).
    retry_recovery = 0.34 if rng.random() < 0.18 else 0.0
    runs = _runs(rng, n, pattern, (3.0, 9.0), lambda: sig,
                 selector_break=has_selector, retry_recovery=retry_recovery)
    return {
        "test_id": f"TC-RD-{k:03d}", "test_name": f"Checkout_E2E_{k:03d}", "runs": runs,
        "context": {
            "stack_trace": sig + "\n  at CheckoutPage.submit (checkout.spec.ts:88)",
            "recent_dom_diff": dom_diff, "commit_message": commit,
            "runner_logs": rng.choice(HEALTHY_LOGS),
        },
        "label": "real_defect",
    }


def gen_conflict_defect(rng, k):
    """A real defect whose HISTORY looks flaky (scattered, recovers on retry) and
    that has NO selector change. Only the grounded context (assertion + feature
    commit) reveals it. The deterministic scorer will lean flaky here; the
    classifier must catch it. This is the safety-critical hard case."""
    n = rng.randint(11, 14)
    pattern = ["f" if rng.random() < 0.4 else "p" for _ in range(n)]
    pattern[-1] = "f"
    sig = rng.choice(DEFECT_ERRORS)
    runs = _runs(rng, n, pattern, (2.5, 7.0), lambda: sig,
                 selector_break=False, retry_recovery=rng.uniform(0.4, 0.7))
    return {
        "test_id": f"TC-RDX-{k:03d}", "test_name": f"Pricing_Calc_{k:03d}", "runs": runs,
        "context": {
            "stack_trace": sig + "\n  at PricingService.total (pricing.ts:204)",
            "recent_dom_diff": "", "commit_message": rng.choice(DEFECT_COMMITS),
            "runner_logs": rng.choice(HEALTHY_LOGS),
        },
        "label": "real_defect",
    }


def gen_flaky(rng, k):
    n = rng.randint(11, 15)
    pattern = ["f" if rng.random() < 0.4 else "p" for _ in range(n)]
    if "f" not in pattern:
        pattern[rng.randrange(n)] = "f"
    # ~16% cluster into a short streak (looks defect-ish).
    if rng.random() < 0.16:
        pattern = ["p"] * (n - 2) + ["f", "f"]
    # ~10% carry a spurious, unrelated selector change (a real distractor).
    spurious_selector = rng.random() < 0.10
    dom_diff = "- .promo-old\n+ .promo-new" if spurious_selector else ""
    runs = _runs(rng, n, pattern, (1.5, 6.0), lambda: rng.choice(FLAKY_ERRORS),
                 selector_break=spurious_selector, retry_recovery=rng.uniform(0.55, 0.85))
    return {
        "test_id": f"TC-FL-{k:03d}", "test_name": f"Cart_UI_{k:03d}", "runs": runs,
        "context": {
            "stack_trace": rng.choice(FLAKY_ERRORS) + "\n  at CartWidget.update (cart.spec.ts:54)",
            "recent_dom_diff": dom_diff, "commit_message": rng.choice(FLAKY_COMMITS),
            "runner_logs": rng.choice(NEUTRAL_LOGS),
        },
        "label": "flaky",
    }


def gen_environment(rng, k):
    n = rng.randint(10, 14)
    streak = rng.randint(1, 4)
    pattern = ["p"] * (n - streak) + ["f"] * streak
    sig = rng.choice(ENV_ERRORS)
    runs = _runs(rng, n, pattern, (2.0, 8.0), lambda: sig,
                 selector_break=False, retry_recovery=rng.uniform(0.2, 0.5))
    return {
        "test_id": f"TC-EN-{k:03d}", "test_name": f"Payments_API_{k:03d}", "runs": runs,
        "context": {
            "stack_trace": sig, "recent_dom_diff": "",
            "commit_message": rng.choice(FLAKY_COMMITS), "runner_logs": rng.choice(ENV_LOGS),
        },
        "label": "environment",
    }


def main():
    rng = random.Random(SEED)
    rows = []
    # ~6 of the 50 real defects are conflict cases (flaky-looking history).
    n_conflict = 6
    for k in range(N_PER_CLASS["real_defect"] - n_conflict):
        rows.append(gen_real_defect(rng, k))
    for k in range(n_conflict):
        rows.append(gen_conflict_defect(rng, k))
    for k in range(N_PER_CLASS["flaky"]):
        rows.append(gen_flaky(rng, k))
    for k in range(N_PER_CLASS["environment"]):
        rows.append(gen_environment(rng, k))
    rng.shuffle(rows)
    with open(OUT, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    counts = {}
    for r in rows:
        counts[r["label"]] = counts.get(r["label"], 0) + 1
    print(f"Wrote {len(rows)} labeled failures to {OUT}")
    print("Class balance:", counts, f"(incl. {n_conflict} conflict real-defects)")


if __name__ == "__main__":
    main()
