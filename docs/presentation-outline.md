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
- Uniqueness claim (defensible version): *"Detection tools tell you a test is flaky;
  healing tools auto-repair selectors. FlakeWarden is the governance layer between
  them: a reproducible, auditable scorer that spends an LLM only on the ambiguous
  band, under a hard safety contract — a real regression is never auto-quarantined
  as flaky — with every fix a human-gated proposal written back through UiPath, not
  an autonomous mutation."*
- Position vs prior art explicitly (see [`prior-art.md`](prior-art.md)); the moat is
  the *composition + safety contract*, not any single component.

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
- 90.7% accuracy · **0% safety false-positive rate** · 12% noise (safe direction).
- 52/150 resolved deterministically; the grounded classifier carries the other 98.
- Say it first: "measured on a synthetic-but-adversarial corpus; the 0% is enforced
  by a mechanism (tie-break-to-defect + flaky-band guard), not planted in the data."
- "These are run, not claimed — `python eval/harness.py`."

## Slide 7 — Governance & the human gate *(Business Impact / Technical Execution)*
- No autonomous mutation; every heal/quarantine is a proposal → Action Center.
- Fail-safe default to defect framing on low confidence.
- Eval-driven release gate: can't publish below threshold.
- Negative control: 0 real defects ever hidden across 150 cases.

## Slide 8 — Built with a coding agent *(Platform Usage — bonus)*
- Claude Code + uip CLI built, validated (Workflow Analyzer), packed, deployed.
- The eval loop caught a real design flaw (environment failures auto-classified as
  defects, 70%→90.7%) AND a self-review caught a circular-corpus problem that was
  then fixed — shows real engineering and honest methodology, not a one-shot gen.

## Slide 9 — Honest limitations & path to production *(Business Impact / feasibility)*
- Synthetic-but-adversarial corpus; live Test Manager API + gold-standard labels +
  shadow-mode prospective study for production.
- Drift monitoring scaffolded, not solved (named honestly).

## Slide 10 — Close *(Presentation)*
- Restate the one sentence. Thank you. Repo + demo links.

## Delivery notes
- Lead every technical slide with the *why*, then the *how*.
- The 0% safety false-positive rate is the trust anchor — but every time you say it,
  pair it with "on a synthetic corpus, enforced by a mechanism" so a judge can't
  frame it as overclaiming before you do.
- Pre-empt "isn't this just Healenium / Tricentis / UiPath Autopilot?" with the
  three-beat rebuttal in [`prior-art.md`](prior-art.md). Don't wait to be asked.
- Keep jargon grounded — define "flaky" and "environment failure" once, early.
