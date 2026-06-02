# Presentation deck outline

Fill the official AgentHack template with these slides. Mapped to the six judging
criteria so nothing is left on the table.

## Slide 1 — Title
FlakeWarden · Agentic flaky-test triage for UiPath Test Cloud · Track 3 · your name.
One-line: "Real defect, flaky, or environment? With a human in charge of every change."

## Slide 2 — The problem *(Business Impact)*
- ~16% of tests flaky at scale (Google). 5% flake on a 2,000-test suite → ~100
  spurious failures per run; 15–45 min triage each.
- The real cost: teams stop trusting red builds → a real regression ships.
- One sentence of stakes, one number. Don't over-explain.

## Slide 3 — The idea *(Creativity)*
- Triage every failure into real_defect / flaky / environment and route it.
- Uniqueness claim: *"A deterministic statistical flake-scorer + a grounded
  generative classifier that separates real defects from false positives with a
  measured false-positive rate, plus governed human-gated self-healing in Maestro —
  nothing else combines all four."*

## Slide 4 — Architecture *(Technical Execution)*
- The mermaid diagram from the README.
- Headline: **deterministic where exact, generative where messy.**
- Call out the three bands and the selector-change-at-break defect cap.

## Slide 5 — Platform usage *(Platform Usage)*
- Test Cloud (data + write-back), Maestro (orchestration), Agent Builder (2 agents),
  Context Grounding (RAG), Action Center (human gate), Orchestrator (deploy),
  AI Trust Layer (PII + audit).
- Coded scorer + low-code agents, both shown.

## Slide 6 — Measured results *(Technical Execution / Business Impact)*
- 95.3% accuracy · **0% safety false-positive rate** · 6% noise (safe direction).
- 70/150 resolved deterministically (LLM spent only where it helps).
- "These are run, not claimed — `python eval/harness.py`."

## Slide 7 — Governance & the human gate *(Business Impact / Technical Execution)*
- No autonomous mutation; every heal/quarantine is a proposal → Action Center.
- Fail-safe default to defect framing on low confidence.
- Eval-driven release gate: can't publish below threshold.
- Negative control: 0 real defects ever hidden across 150 cases.

## Slide 8 — Built with a coding agent *(Platform Usage — bonus)*
- Claude Code + uip CLI built, validated (Workflow Analyzer), packed, deployed.
- The 70%→95.3% fix that the eval loop surfaced — shows real engineering, not a
  one-shot generation.

## Slide 9 — Honest limitations & path to production *(Business Impact / feasibility)*
- Synthetic-but-adversarial corpus; live Test Manager API + gold-standard labels +
  shadow-mode prospective study for production.
- Drift monitoring scaffolded, not solved (named honestly).

## Slide 10 — Close *(Presentation)*
- Restate the one sentence. Thank you. Repo + demo links.

## Delivery notes
- Lead every technical slide with the *why*, then the *how*.
- Quote the 0% safety false-positive rate at least twice; it's the trust anchor.
- Keep jargon grounded — define "flaky" and "environment failure" once, early.
