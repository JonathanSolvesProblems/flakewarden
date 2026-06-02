"""FlakeWarden evaluation harness.

Runs the full triage pipeline (deterministic scorer -> grounded classifier ->
governed action) over the labeled corpus and reports the metrics the judging
rubric and both judges care about:

  * Accuracy and a per-class confusion matrix.
  * The SAFETY false-positive rate: real defects misclassified as flaky/
    environment. This is the dangerous error Ingo names -- a real regression
    quarantined as noise. We optimise to keep this near zero.
  * The NOISE false-alarm rate: flaky/environment failures escalated as real
    defects (wasted triage effort).
  * Routing: how many failures the deterministic scorer resolved alone vs how
    many needed the LLM, and how many hit the human-review gate.

Run:  python eval/harness.py
      python eval/harness.py --report eval/report.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flakewarden.orchestration import triage  # noqa: E402
from flakewarden.schema import CorpusCase, Label  # noqa: E402

LABELS = [Label.REAL_DEFECT, Label.FLAKY, Label.ENVIRONMENT]
CORPUS = os.path.join(os.path.dirname(__file__), "..", "corpus", "failures.jsonl")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return [CorpusCase.from_dict(json.loads(l)) for l in fh if l.strip()]


def evaluate(cases):
    conf = {t: {p: 0 for p in LABELS} for t in LABELS}
    routed_det = routed_llm = human_gate = 0
    rows = []
    for c in cases:
        d = triage(c)
        conf[c.label][d.label] += 1
        if d.decided_by == "deterministic-scorer":
            routed_det += 1
        else:
            routed_llm += 1
        if d.requires_human_approval:
            human_gate += 1
        rows.append((c, d))

    n = len(cases)
    correct = sum(conf[t][t] for t in LABELS)
    accuracy = correct / n

    n_real = sum(conf[Label.REAL_DEFECT].values())
    safety_fp = (conf[Label.REAL_DEFECT][Label.FLAKY] +
                 conf[Label.REAL_DEFECT][Label.ENVIRONMENT])
    safety_fp_rate = safety_fp / n_real if n_real else 0.0

    n_noise = sum(conf[Label.FLAKY].values()) + sum(conf[Label.ENVIRONMENT].values())
    noise_fp = conf[Label.FLAKY][Label.REAL_DEFECT] + conf[Label.ENVIRONMENT][Label.REAL_DEFECT]
    noise_fp_rate = noise_fp / n_noise if n_noise else 0.0

    return {
        "n": n,
        "accuracy": accuracy,
        "confusion": conf,
        "safety_fp": safety_fp,
        "safety_fp_rate": safety_fp_rate,
        "noise_fp": noise_fp,
        "noise_fp_rate": noise_fp_rate,
        "routed_deterministic": routed_det,
        "routed_classifier": routed_llm,
        "human_gate": human_gate,
        "rows": rows,
    }


def _confusion_str(conf):
    head = "actual \\ pred   " + "".join(f"{p.value:>14}" for p in LABELS)
    lines = [head]
    for t in LABELS:
        lines.append(f"{t.value:<15}" + "".join(f"{conf[t][p]:>14}" for p in LABELS))
    return "\n".join(lines)


def render(m) -> str:
    out = []
    out.append("FlakeWarden -- evaluation report")
    out.append("=" * 60)
    out.append(f"corpus size:                 {m['n']} labeled failures")
    out.append(f"overall accuracy:            {m['accuracy']*100:.1f}%")
    out.append("")
    out.append("SAFETY false-positive rate   (real defect hidden as flaky/env)")
    out.append(f"  -> {m['safety_fp']} / real defects   = {m['safety_fp_rate']*100:.1f}%   [target: ~0%]")
    out.append("NOISE false-alarm rate       (flaky/env re-escalated as defect)")
    out.append(f"  -> {m['noise_fp']} / non-defects     = {m['noise_fp_rate']*100:.1f}%")
    out.append("")
    out.append("routing (deterministic-vs-generative division of labour):")
    out.append(f"  resolved by deterministic scorer:  {m['routed_deterministic']}")
    out.append(f"  escalated to grounded classifier:  {m['routed_classifier']}")
    out.append(f"  routed to human-review gate:       {m['human_gate']}")
    out.append("")
    out.append("confusion matrix:")
    out.append(_confusion_str(m["confusion"]))
    return "\n".join(out)


def render_markdown(m) -> str:
    conf = m["confusion"]
    md = ["# FlakeWarden evaluation report", ""]
    md.append(f"- **Corpus size:** {m['n']} labeled failures")
    md.append(f"- **Overall accuracy:** {m['accuracy']*100:.1f}%")
    md.append(f"- **Safety false-positive rate** (real defect hidden as flaky/environment): "
              f"**{m['safety_fp_rate']*100:.1f}%** ({m['safety_fp']} cases) — target ~0%")
    md.append(f"- **Noise false-alarm rate** (flaky/environment re-escalated as defect): "
              f"{m['noise_fp_rate']*100:.1f}% ({m['noise_fp']} cases)")
    md.append(f"- **Routing:** {m['routed_deterministic']} resolved by the deterministic scorer, "
              f"{m['routed_classifier']} escalated to the grounded classifier, "
              f"{m['human_gate']} routed to the human-review gate")
    md.append("")
    md.append("## Confusion matrix")
    md.append("")
    md.append("| actual \\ predicted | " + " | ".join(p.value for p in LABELS) + " |")
    md.append("|---|" + "---|" * len(LABELS))
    for t in LABELS:
        md.append(f"| **{t.value}** | " + " | ".join(str(conf[t][p]) for p in LABELS) + " |")
    md.append("")
    md.append("_Generated by `python eval/harness.py --report eval/report.md`. "
              "Backend: offline rule-based classifier (deterministic, no API key). "
              "With `ANTHROPIC_API_KEY` set, the grounded Claude classifier handles the ambiguous band._")
    return "\n".join(md)


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--corpus", default=CORPUS)
    p.add_argument("--report", help="also write a markdown report to this path")
    args = p.parse_args(argv)

    m = evaluate(load(args.corpus))
    print(render(m))
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(render_markdown(m))
        print(f"\nMarkdown report written to {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
