"""FlakeWarden command-line entry point.

Usage:
    python -m flakewarden.cli triage corpus/failures.jsonl
    python -m flakewarden.cli score  corpus/failures.jsonl --limit 5

`triage` runs the full scorer -> classifier -> governed-action pipeline and prints
the Action Center queue that a human reviewer would see. `score` prints just the
deterministic flake scores and feature vectors.
"""

from __future__ import annotations

import argparse
import json
import sys

from . import scorer
from .orchestration import triage
from .schema import CorpusCase


def _load(path: str) -> list[CorpusCase]:
    cases = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                cases.append(CorpusCase.from_dict(json.loads(line)))
    return cases


def cmd_score(args) -> int:
    for case in _load(args.path)[: args.limit]:
        r = scorer.score(case)
        print(f"\n{case.test_name}  [{case.test_id}]")
        print(f"  flake_score={r.flake_score:.3f}  band={r.band.value}")
        print(f"  {r.rationale}")
    return 0


def cmd_triage(args) -> int:
    decisions = [triage(c) for c in _load(args.path)[: args.limit]]
    review_queue = [d for d in decisions if d.requires_human_approval]
    print(f"Triaged {len(decisions)} failing tests.")
    print(f"  -> {len(review_queue)} routed to the Action Center human-review queue.\n")
    for d in decisions:
        gate = "REVIEW" if d.requires_human_approval else "auto"
        print(f"[{gate:^6}] {d.test_name:<34} {d.label.value:<12} "
              f"{d.action.value:<18} (score={d.flake_score:.2f}, by={d.decided_by})")
        if d.proposed_fix:
            print(f"           proposed fix: {d.proposed_fix}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="flakewarden", description="Agentic flaky-test triage for UiPath Test Cloud.")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("score", help="print deterministic flake scores")
    ps.add_argument("path")
    ps.add_argument("--limit", type=int, default=10**9)
    ps.set_defaults(func=cmd_score)

    pt = sub.add_parser("triage", help="run the full governed triage pipeline")
    pt.add_argument("path")
    pt.add_argument("--limit", type=int, default=10**9)
    pt.set_defaults(func=cmd_triage)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
