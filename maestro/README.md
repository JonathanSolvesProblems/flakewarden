# Maestro process

[`flakewarden.process.json`](flakewarden.process.json) is the UiPath Maestro
process that orchestrates the whole triage flow. It is the single coordination
layer the hackathon asks for: it ties together a coded service (the deterministic
scorer), two low-code Agent Builder agents (classifier + repair), an Action Center
human task, and Orchestrator write-backs.

## Flow

1. **Trigger** — fires on `uipath.testcloud.run.completed` when a run has failures.
2. **pull-history** — Test Manager API → per-test execution window (retried 3×).
3. **score-loop** — the coded deterministic scorer runs over each failure in
   parallel and emits a band.
4. **route** — gateway: confident flaky → heal; confident defect (selector change at
   break) → escalate; ambiguous → classify.
5. **classify** — the grounded Agent Builder Triage Classifier, wrapped by the AI
   Trust Layer (PII redaction + audit log).
6. **confidence-gate** — verdicts below 0.55 confidence are held for a human and
   default to defect framing.
7. **heal** — the Repair Agent drafts a selector/sync fix (a proposal, never
   applied).
8. **human-review** — a mandatory Action Center approval task with a 24h timer that
   escalates to the lead on timeout.
9. **apply** — governed write-back (quarantine / promote baseline / open defect),
   guarded so it only runs after human approval.

## Why Maestro and not a single agent

A single chat agent has no durable state, no SLA timers, no parallel scoring, no
governed handoffs, and no human gate. Maestro gives the flow resumability and
auditability — the prototype-to-production properties the failure mode actually
needs. The same orchestration is expressed runnably in
[`../flakewarden/orchestration.py`](../flakewarden/orchestration.py) for local
testing.
