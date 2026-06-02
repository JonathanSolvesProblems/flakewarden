"""Run the seeded suite N times and emit FlakeWarden execution history.

Produces JSONL in the same schema as the eval corpus (minus labels), so the live
pipeline can be demoed end-to-end on freshly generated data:

    python seeded_suite/run_history.py --runs 14 --out seeded_suite/history.jsonl
    python -m flakewarden.cli triage seeded_suite/history.jsonl

In production this script is replaced by a pull from the Test Manager results
API; downstream stages are unchanged.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from seeded_suite import SUITE  # noqa: E402

CONTEXT = {
    "flaky_add_to_cart": {
        "stack_trace": "StaleElementReferenceException: element is detached from the DOM\n  at CartWidget.add (cart.spec:54)",
        "recent_dom_diff": "",
        "commit_message": "test: add coverage for promo codes",
        "runner_logs": "parallel shard; high runner load; no service incidents",
    },
    "flaky_promo_banner": {
        "stack_trace": "TimeoutError: element not yet visible after 2s (animation in progress)\n  at Banner.show (promo.spec:31)",
        "recent_dom_diff": "",
        "commit_message": "style: format with prettier",
        "runner_logs": "no incidents; animation timing varies",
    },
    "regressed_checkout": {
        "stack_trace": "AssertionError: expected total '128.40' but was '142.00'\n  at CheckoutPage.submit (checkout.spec:88)",
        "recent_dom_diff": "- #submit-btn\n+ #checkout-submit",
        "commit_message": "migrate pricing service to v2 rounding",
        "runner_logs": "all services healthy; no infra alerts",
    },
}


def build_history(n_runs: int):
    histories = {name: {"test_id": f"SEED-{name}", "test_name": name, "runs": [],
                        "context": CONTEXT.get(name, {})}
                 for name in SUITE}
    for run_index in range(n_runs):
        for name, fn in SUITE.items():
            r = fn(run_index)
            run = {"run_index": run_index, "outcome": r.outcome,
                   "duration_s": round(r.duration_s, 2), "commit_sha": f"{run_index:07x}"}
            if r.outcome == "fail":
                run["error_signature"] = r.error_signature
                run["retry_outcome"] = r.retry_outcome
                run["selectors_changed"] = r.selectors_changed
            histories[name]["runs"].append(run)
    # Only emit tests that are currently failing (what triage actually sees).
    return [h for h in histories.values() if h["runs"][-1]["outcome"] == "fail"]


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--runs", type=int, default=14)
    p.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "history.jsonl"))
    p.add_argument("--all", action="store_true", help="emit all tests, not just currently-failing")
    args = p.parse_args(argv)

    hist = build_history(args.runs)
    if args.all:
        # rebuild including passing tests
        full = {name: {"test_id": f"SEED-{name}", "test_name": name, "runs": [],
                       "context": CONTEXT.get(name, {})} for name in SUITE}
        for run_index in range(args.runs):
            for name, fn in SUITE.items():
                r = fn(run_index)
                run = {"run_index": run_index, "outcome": r.outcome,
                       "duration_s": round(r.duration_s, 2), "commit_sha": f"{run_index:07x}"}
                if r.outcome == "fail":
                    run["error_signature"] = r.error_signature
                    run["retry_outcome"] = r.retry_outcome
                    run["selectors_changed"] = r.selectors_changed
                full[name]["runs"].append(run)
        hist = list(full.values())

    with open(args.out, "w", encoding="utf-8") as fh:
        for h in hist:
            fh.write(json.dumps(h) + "\n")
    print(f"Wrote {len(hist)} test histories over {args.runs} runs to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
