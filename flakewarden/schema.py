"""Data models for FlakeWarden.

These mirror the shape of data exported from UiPath Test Manager / Orchestrator
execution history. In a live deployment the `TestHistory` objects are built from
the Test Cloud results API; for development and the eval corpus they are loaded
from JSONL.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


class Outcome(str, Enum):
    PASS = "pass"
    FAIL = "fail"


class Label(str, Enum):
    """Ground-truth classification of a failure (the target the system predicts)."""

    REAL_DEFECT = "real_defect"   # a genuine regression introduced by a code change
    FLAKY = "flaky"               # non-deterministic failure; code is fine
    ENVIRONMENT = "environment"   # infra/data/timeout issue external to the test


@dataclass
class TestRunResult:
    """One execution of one test case in a pipeline run."""

    run_index: int                 # monotonically increasing ordinal of the pipeline run
    outcome: Outcome
    duration_s: float
    commit_sha: str
    # Outcome after the CI auto-retry, if a retry happened. None => no retry.
    retry_outcome: Optional[Outcome] = None
    # Normalized error fingerprint (exception type + first stack frame), if failed.
    error_signature: Optional[str] = None
    # True if the selectors/locators this test depends on changed in this run's commit.
    selectors_changed: bool = False

    @staticmethod
    def from_dict(d: dict) -> "TestRunResult":
        return TestRunResult(
            run_index=d["run_index"],
            outcome=Outcome(d["outcome"]),
            duration_s=float(d["duration_s"]),
            commit_sha=d["commit_sha"],
            retry_outcome=Outcome(d["retry_outcome"]) if d.get("retry_outcome") else None,
            error_signature=d.get("error_signature"),
            selectors_changed=bool(d.get("selectors_changed", False)),
        )


@dataclass
class FailureContext:
    """Unstructured, messy context handed to the generative classifier (RAG inputs).

    The deterministic scorer never reads these free-text fields; only the grounded
    Agent Builder classifier does. Keeping them separate is the deterministic-vs-
    generative boundary.
    """

    stack_trace: str = ""
    recent_dom_diff: str = ""       # selector/DOM changes since last green run
    commit_message: str = ""        # message of the commit that first turned this red
    runner_logs: str = ""           # environment / infra log excerpt

    @staticmethod
    def from_dict(d: dict) -> "FailureContext":
        d = d or {}
        return FailureContext(
            stack_trace=d.get("stack_trace", ""),
            recent_dom_diff=d.get("recent_dom_diff", ""),
            commit_message=d.get("commit_message", ""),
            runner_logs=d.get("runner_logs", ""),
        )


@dataclass
class TestHistory:
    """The recent execution window for a single test, newest run last."""

    test_id: str
    test_name: str
    runs: list[TestRunResult] = field(default_factory=list)
    context: FailureContext = field(default_factory=FailureContext)

    @property
    def latest(self) -> TestRunResult:
        return self.runs[-1]

    @property
    def currently_failing(self) -> bool:
        return self.runs and self.latest.outcome == Outcome.FAIL

    @staticmethod
    def from_dict(d: dict) -> "TestHistory":
        return TestHistory(
            test_id=d["test_id"],
            test_name=d.get("test_name", d["test_id"]),
            runs=[TestRunResult.from_dict(r) for r in d["runs"]],
            context=FailureContext.from_dict(d.get("context")),
        )


@dataclass
class CorpusCase(TestHistory):
    """A TestHistory plus its ground-truth label, used only for evaluation."""

    label: Optional[Label] = None

    @staticmethod
    def from_dict(d: dict) -> "CorpusCase":
        h = TestHistory.from_dict(d)
        return CorpusCase(
            test_id=h.test_id,
            test_name=h.test_name,
            runs=h.runs,
            context=h.context,
            label=Label(d["label"]) if d.get("label") else None,
        )

    def to_dict(self) -> dict:
        out = {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "runs": [asdict(r) | {"outcome": r.outcome.value,
                                  "retry_outcome": r.retry_outcome.value if r.retry_outcome else None}
                     for r in self.runs],
            "context": asdict(self.context),
        }
        if self.label:
            out["label"] = self.label.value
        return out
