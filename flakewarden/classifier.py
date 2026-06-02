"""Generative classifier for ambiguous failures (the Agent Builder layer).

This is the GenAI half of the deterministic-vs-generative split. It is only
invoked on failures the deterministic scorer could not confidently bucket. It is
*grounded*: it reasons over the messy FailureContext (stack trace, DOM diff,
commit message, runner logs) rather than the raw test code, which mirrors how the
UiPath Agent Builder agent is grounded via context grounding / RAG over the
Test Manager artifacts.

Two backends:
  * RuleBasedClassifier  - deterministic, offline, no API key. Genuinely reads the
    grounded context (not the label). Used for reproducible eval and CI.
  * AnthropicClassifier  - calls a Claude model with the grounded prompt. Used in
    the live UiPath deployment (Agent Builder wires the same prompt to the model).

Both return the same Prediction shape so the orchestrator and eval harness are
backend-agnostic.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Optional

from .schema import Label, TestHistory

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "agents", "classifier_prompt.txt")


@dataclass
class Prediction:
    label: Label
    confidence: float          # 0..1, the classifier's self-reported confidence
    rationale: str
    proposed_fix: Optional[str] = None  # populated only when label == FLAKY and a heal is safe

    def as_dict(self) -> dict:
        return {
            "label": self.label.value,
            "confidence": round(self.confidence, 3),
            "rationale": self.rationale,
            "proposed_fix": self.proposed_fix,
        }


class RuleBasedClassifier:
    """Transparent, deterministic classifier over the grounded context text.

    It keys off well-understood failure fingerprints. This is the offline backend
    and the honest baseline the LLM is measured against, not a stand-in that peeks
    at the label.
    """

    ENV_PATTERNS = [
        r"connection refused", r"timeout", r"timed out", r"503", r"502",
        r"dns", r"socket", r"econnreset", r"out of memory", r"no space left",
        r"could not resolve host", r"rate limit",
    ]
    FLAKY_PATTERns = [
        r"stale element", r"element not interactable", r"element click intercepted",
        r"race condition", r"not yet (visible|present)", r"animation",
        r"implicit wait", r"detached from the dom",
    ]
    DEFECT_PATTERNS = [
        r"assertion(error)?", r"expected .* but (got|was)", r"nullreference",
        r"http 400", r"validation failed", r"unexpected status",
    ]

    def classify(self, history: TestHistory) -> Prediction:
        ctx = history.context
        blob = " ".join([
            ctx.stack_trace, ctx.recent_dom_diff, ctx.commit_message, ctx.runner_logs
        ]).lower()

        env_hits = sum(1 for p in self.ENV_PATTERNS if re.search(p, blob))
        flaky_hits = sum(1 for p in self.FLAKY_PATTERns if re.search(p, blob))
        defect_hits = sum(1 for p in self.DEFECT_PATTERNS if re.search(p, blob))

        # A selector/DOM change paired with a feature-bearing commit message is a
        # strong real-defect signal even if the runtime looks jittery.
        selector_touched = bool(ctx.recent_dom_diff.strip())
        feature_commit = bool(re.search(r"(refactor|rename|redesign|migrate|update .* (id|selector|class)|remove)", ctx.commit_message.lower()))

        scores = {
            Label.ENVIRONMENT: env_hits * 1.0,
            Label.FLAKY: flaky_hits * 1.0,
            Label.REAL_DEFECT: defect_hits * 1.0 + (1.5 if (selector_touched and feature_commit) else 0.0),
        }
        best = max(scores, key=scores.get)
        total = sum(scores.values())
        if total == 0:
            # No fingerprint at all: stay conservative, defer to real-defect (never
            # silently quarantine something we cannot explain).
            return Prediction(
                label=Label.REAL_DEFECT,
                confidence=0.40,
                rationale="No recognizable flaky/environment fingerprint in the grounded context; "
                          "defaulting to real-defect so a real regression is never hidden.",
            )
        confidence = min(0.5 + scores[best] / (total + 1), 0.97)
        fix = None
        if best == Label.FLAKY:
            fix = self._propose_fix(blob)
        return Prediction(
            label=best,
            confidence=confidence,
            rationale=f"grounded-context fingerprints -> env:{env_hits} flaky:{flaky_hits} "
                      f"defect:{defect_hits} (selector+feature-commit bonus="
                      f"{'yes' if selector_touched and feature_commit else 'no'})",
            proposed_fix=fix,
        )

    @staticmethod
    def _propose_fix(blob: str) -> Optional[str]:
        if "stale element" in blob or "detached" in blob:
            return "Wrap the locator in an explicit wait-for-element-stable; re-resolve the selector after navigation."
        if "not interactable" in blob or "click intercepted" in blob:
            return "Add a wait-for-clickable guard and scroll-into-view before the interaction."
        if "race" in blob or "not yet" in blob or "animation" in blob:
            return "Replace the implicit sleep with an explicit wait on the awaited application state."
        return "Add an explicit wait synchronizing on the awaited UI state before the assertion."


class AnthropicClassifier:
    """Live backend: sends the grounded prompt to a Claude model.

    Mirrors what the UiPath Agent Builder agent does at runtime. Requires
    ANTHROPIC_API_KEY. Falls back is the caller's responsibility.
    """

    def __init__(self, model: str = "claude-opus-4-8"):
        self.model = model

    def classify(self, history: TestHistory) -> Prediction:
        import json
        from anthropic import Anthropic  # imported lazily so offline eval needs no dep

        client = Anthropic()
        system = _load_prompt()
        user = json.dumps({
            "test_name": history.test_name,
            "stack_trace": history.context.stack_trace,
            "recent_dom_diff": history.context.recent_dom_diff,
            "commit_message": history.context.commit_message,
            "runner_logs": history.context.runner_logs,
        }, indent=2)
        msg = client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = msg.content[0].text
        data = json.loads(_extract_json(text))
        return Prediction(
            label=Label(data["label"]),
            confidence=float(data.get("confidence", 0.7)),
            rationale=data.get("rationale", ""),
            proposed_fix=data.get("proposed_fix"),
        )


def _load_prompt() -> str:
    try:
        with open(os.path.abspath(PROMPT_PATH), encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        return "You are a flaky-test triage classifier. Return JSON with keys label, confidence, rationale, proposed_fix."


def _extract_json(text: str) -> str:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return m.group(0) if m else text


def get_classifier():
    """Pick the live backend if an API key is present, else the offline one."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            import anthropic  # noqa: F401
            return AnthropicClassifier()
        except ImportError:
            pass
    return RuleBasedClassifier()
