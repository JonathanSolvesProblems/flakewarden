"""Deterministic flake score.

Combines the features into a single 0..1 flake score with a fixed, documented,
auditable weighting. The score drives a three-band routing decision:

  score >= HIGH_BAND    -> high-confidence FLAKY      (auto-route to healing review)
  score <= LOW_BAND     -> high-confidence REAL_DEFECT (auto-escalate as a defect)
  in between            -> AMBIGUOUS                   (hand to the grounded LLM classifier)

The bands exist so the LLM is only spent on genuinely ambiguous failures. That
is the deterministic-vs-generative division of labor: exact math decides the
clear cases; the agent reasons over the messy middle.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .features import Features, extract
from .schema import TestHistory

# Weights for the flakiness-leaning signals. Documented and version-controlled so
# any score can be reproduced and audited. Tuned on the labeled corpus (see eval/).
WEIGHTS = {
    "flip_rate": 0.28,
    "failure_isolation": 0.22,
    "pass_after_retry_rate": 0.30,
    "error_signature_entropy": 0.12,
    "runtime_instability": 0.08,  # derived: min(runtime_zscore / 3, 1)
}

# A selector change exactly at the break is a strong defect signal: it caps the
# flake score so a genuine UI-break can never auto-route as flaky.
SELECTOR_BREAK_CAP = 0.35

HIGH_BAND = 0.62   # >= => confident flaky
LOW_BAND = 0.38    # <= => confident real defect


class Band(str, Enum):
    FLAKY = "flaky"
    REAL_DEFECT = "real_defect"
    AMBIGUOUS = "ambiguous"


@dataclass
class ScoreResult:
    flake_score: float
    band: Band
    features: Features
    rationale: str

    def as_dict(self) -> dict:
        return {
            "flake_score": round(self.flake_score, 4),
            "band": self.band.value,
            "features": self.features.as_dict(),
            "rationale": self.rationale,
        }


def _raw_score(f: Features) -> float:
    runtime_instability = min(f.runtime_zscore / 3.0, 1.0)
    score = (
        WEIGHTS["flip_rate"] * f.flip_rate
        + WEIGHTS["failure_isolation"] * f.failure_isolation
        + WEIGHTS["pass_after_retry_rate"] * f.pass_after_retry_rate
        + WEIGHTS["error_signature_entropy"] * f.error_signature_entropy
        + WEIGHTS["runtime_instability"] * runtime_instability
    )
    return min(max(score, 0.0), 1.0)


def score(history: TestHistory) -> ScoreResult:
    f = extract(history)
    raw = _raw_score(f)

    capped = raw
    notes = []
    if f.selector_change_at_break >= 1.0:
        capped = min(raw, SELECTOR_BREAK_CAP)
        notes.append(
            f"selector change coincided with the break -> flake score capped at "
            f"{SELECTOR_BREAK_CAP} (defect-leaning)"
        )

    if capped >= HIGH_BAND:
        band = Band.FLAKY
    elif capped <= LOW_BAND:
        band = Band.REAL_DEFECT
    else:
        band = Band.AMBIGUOUS

    notes.append(
        f"flip_rate={f.flip_rate:.2f}, isolation={f.failure_isolation:.2f}, "
        f"retry_recovery={f.pass_after_retry_rate:.2f}, "
        f"err_entropy={f.error_signature_entropy:.2f}, "
        f"runtime_z={f.runtime_zscore:.2f}, streak={f.failing_streak}"
    )

    return ScoreResult(
        flake_score=capped,
        band=band,
        features=f,
        rationale="; ".join(notes),
    )
