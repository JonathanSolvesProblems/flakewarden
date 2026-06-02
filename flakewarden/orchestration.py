"""Triage orchestration: the Maestro-equivalent control flow.

In the live solution this logic is a UiPath Maestro process that coordinates the
deterministic scorer (a coded service), the Agent Builder classifier agent, the
Healing Agent, and an Action Center human-review task. Here it is expressed as a
plain pipeline so it is runnable and testable offline; SETUP.md maps each step to
its Maestro / Test Cloud counterpart.

Invariants (the governance gates):
  1. No test is ever quarantined or healed automatically. Every FLAKY verdict
     produces a *proposed* fix that lands in a human-review task.
  2. A REAL_DEFECT verdict is always escalated, never silenced.
  3. When the system cannot confidently explain a failure, it escalates as a
     potential defect (fail safe), so a real regression is never hidden.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from . import scorer
from .classifier import Prediction, get_classifier
from .schema import Label, TestHistory


class Action(str, Enum):
    ESCALATE_DEFECT = "escalate_defect"          # open/keep a defect; notify owning team
    PROPOSE_HEAL = "propose_heal"                # draft a selector/logic fix for human review
    FLAG_ENVIRONMENT = "flag_environment"        # re-run on clean infra; flag platform team
    HOLD_FOR_REVIEW = "hold_for_review"          # low confidence; queue for a human to decide


# Whether each action requires a human to approve before anything changes.
REQUIRES_APPROVAL = {
    Action.ESCALATE_DEFECT: False,   # escalation is safe-by-default (surfacing, not mutating)
    Action.PROPOSE_HEAL: True,       # never auto-applies a heal
    Action.FLAG_ENVIRONMENT: False,
    Action.HOLD_FOR_REVIEW: True,
}

# Below this confidence the classifier's verdict is not trusted on its own.
MIN_AUTONOMOUS_CONFIDENCE = 0.55


@dataclass
class TriageDecision:
    test_id: str
    test_name: str
    label: Label
    action: Action
    flake_score: float
    decided_by: str               # "deterministic-scorer" or "grounded-classifier"
    requires_human_approval: bool
    confidence: float
    rationale: str
    proposed_fix: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "label": self.label.value,
            "action": self.action.value,
            "flake_score": round(self.flake_score, 4),
            "decided_by": self.decided_by,
            "requires_human_approval": self.requires_human_approval,
            "confidence": round(self.confidence, 3),
            "rationale": self.rationale,
            "proposed_fix": self.proposed_fix,
        }


def _action_for(label: Label, proposed_fix: Optional[str]) -> Action:
    if label == Label.FLAKY:
        return Action.PROPOSE_HEAL
    if label == Label.ENVIRONMENT:
        return Action.FLAG_ENVIRONMENT
    return Action.ESCALATE_DEFECT


def triage(history: TestHistory, classifier=None) -> TriageDecision:
    """Run one failure through scorer -> (maybe) classifier -> governed action."""
    s = scorer.score(history)

    # Confident deterministic bands resolve without spending the LLM.
    if s.band == scorer.Band.FLAKY:
        fix = "Add an explicit wait synchronizing on the awaited UI state before the assertion."
        return TriageDecision(
            test_id=history.test_id, test_name=history.test_name,
            label=Label.FLAKY, action=Action.PROPOSE_HEAL, flake_score=s.flake_score,
            decided_by="deterministic-scorer", requires_human_approval=True,
            confidence=s.flake_score, rationale=s.rationale, proposed_fix=fix,
        )
    # A confident-low flake score only tells us the failure is NOT flaky. It does
    # not tell us defect-vs-environment -- that needs the logs. So we auto-resolve
    # as a real defect ONLY when there is a positive defect fingerprint (a selector
    # change exactly at the break). Otherwise we fall through to the grounded
    # classifier, which reads the runner logs to separate a genuine regression from
    # an infrastructure/environment failure.
    if s.band == scorer.Band.REAL_DEFECT and s.features.selector_change_at_break >= 1.0:
        return TriageDecision(
            test_id=history.test_id, test_name=history.test_name,
            label=Label.REAL_DEFECT, action=Action.ESCALATE_DEFECT, flake_score=s.flake_score,
            decided_by="deterministic-scorer", requires_human_approval=False,
            confidence=1.0 - s.flake_score, rationale="selector change at break -> " + s.rationale,
        )

    # Ambiguous band (or a non-flaky failure with no defect fingerprint) -> hand the
    # messy context to the grounded classifier.
    clf = classifier or get_classifier()
    pred: Prediction = clf.classify(history)

    if pred.confidence < MIN_AUTONOMOUS_CONFIDENCE:
        # Fail safe: low-confidence verdicts go to a human, defaulting to defect framing.
        return TriageDecision(
            test_id=history.test_id, test_name=history.test_name,
            label=Label.REAL_DEFECT, action=Action.HOLD_FOR_REVIEW, flake_score=s.flake_score,
            decided_by="grounded-classifier", requires_human_approval=True,
            confidence=pred.confidence,
            rationale=f"low-confidence classifier verdict ({pred.label.value}): {pred.rationale}",
        )

    action = _action_for(pred.label, pred.proposed_fix)
    return TriageDecision(
        test_id=history.test_id, test_name=history.test_name,
        label=pred.label, action=action, flake_score=s.flake_score,
        decided_by="grounded-classifier",
        requires_human_approval=REQUIRES_APPROVAL[action],
        confidence=pred.confidence, rationale=pred.rationale, proposed_fix=pred.proposed_fix,
    )
