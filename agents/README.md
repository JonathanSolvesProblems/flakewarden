# FlakeWarden agents

FlakeWarden uses two narrowly-scoped agents, both authored in **UiPath Agent
Builder** and orchestrated by **Maestro**. They follow Taqi Jaffri's
single-responsibility / "small in scope, big in impact" principle: each agent
does one thing, is grounded in trusted data, and is gated by a human.

| Agent | Responsibility | Grounding (context grounding / RAG) | Output |
|---|---|---|---|
| **Triage Classifier** | Classify an *ambiguous* failure as real_defect / flaky / environment | Test Manager stack traces, DOM/selector diffs, commit messages, runner logs | structured verdict + confidence + (flaky only) proposed fix |
| **Repair Agent** | Draft a selector/synchronization repair for a confirmed flaky test | The test's object repository / selectors + the proposed fix | a *draft* PR-style patch sent to Action Center |

> Naming note: the **Repair Agent** is FlakeWarden's own Agent Builder agent that
> *drafts* a fix for human review. It is distinct from UiPath's GA **Healing
> Agent™** (a platform feature that performs runtime self-healing of UI
> automations). After a reviewer approves the draft, FlakeWarden can hand off to
> UiPath's Healing Agent to apply it. We do not claim to have built UiPath's
> Healing Agent.

The Triage Classifier is invoked only on failures the deterministic flake-scorer
could not confidently bucket, so the model is spent only where it adds value.

## Files

- [`classifier_prompt.txt`](classifier_prompt.txt) — the system prompt. The local
  `AnthropicClassifier` and the UiPath Agent Builder agent use the **same** prompt
  text, so behaviour is identical between local eval and the deployed agent.
- [`classifier_agent.json`](classifier_agent.json) — Agent Builder definition
  (model, inputs, grounded sources, output schema, eval set, guardrails).
- [`healing_agent.json`](healing_agent.json) — Repair Agent definition.

## Evaluation-driven development

Per Taqi Jaffri's evaluation-driven-development principle, the classifier ships
with an eval set (`../corpus/failures.jsonl`) and a pass threshold. The release
gate is: **safety false-positive rate must stay at 0%** (no real defect
classified as flaky/environment) and overall accuracy ≥ 90%. The current build
measures 90.7% accuracy / 0% safety-FP (see [`../eval/report.md`](../eval/report.md)).
In Agent Builder these same cases load as the agent's evaluation set so the agent
cannot be published if it regresses below threshold.
