# Demo video script (5:00 max)

Goal: show the solution *running* on UiPath, walk the architecture, name the
agents and how they're orchestrated, and show where humans fit. Every second
earns a judging point. Keep slides to the first 30 seconds; the rest is live.

## 0:00–0:30 — The problem (one number, fast)

> "Around 16% of tests at scale are flaky. When a build goes red, an engineer
> can't tell if it's a real regression or noise, so they either waste 20 minutes
> triaging or start ignoring red builds, and a real bug ships. FlakeWarden answers
> the only question that matters: real defect, flaky, or environment? With a human
> in charge of every change."

Show the architecture diagram (README mermaid) for 8 seconds.

## 0:30–1:10 — The thesis: deterministic vs generative

> "Failures carry two kinds of evidence. Structured run history — exact, so a
> deterministic scorer handles it. And messy context — stack traces, DOM diffs,
> commits — so a grounded agent reasons over that. I spend the model only on the
> ambiguous middle."

Live: `python eval/harness.py`. Point at the screen:
- **95.3% accuracy**
- **0% safety false-positive rate** ("a real regression is never hidden")
- "70 of 150 resolved by the deterministic scorer, no LLM spent."

## 1:10–2:30 — Run it on UiPath

Switch to Automation Cloud.

1. Show the **Test Cloud** run that just went red with several failures.
2. Show the **Maestro** process firing on the `run.completed` trigger. Walk the
   graph live: scorer → gateway → classifier → healing → human gate.
3. Open the **Agent Builder Triage Classifier**: show its grounded sources and its
   evaluation set with the release gate (`safety_fp == 0`). "This agent can't be
   published if it regresses."
4. Let one **ambiguous** failure hit the classifier; show the grounded verdict and
   rationale citing the actual stack trace.

## 2:30–3:30 — The human gate (where humans fit)

1. Open **Action Center**: the "review proposed test change" task.
2. Show the flaky verdict, the Healing Agent's **proposed** selector fix, the
   rationale, the flake score.
3. **Reject** one to prove nothing auto-applies, then **approve** another, and show
   Orchestrator performing the governed write-back (quarantine / baseline promote).

## 3:30–4:15 — Negative control (it stays silent when it should)

Live: `python eval/negative_control.py`.

> "Across 150 cases, zero real defects were ever auto-healed or hidden. The system
> fails safe: when it can't explain a failure, it escalates as a potential defect
> and asks a human."

Show the planted regression in the seeded suite being **escalated**, not silenced.

## 4:15–4:50 — Built with a coding agent

Show `docs/coding-agents.md` transcript live or as a quick screen recording:

> "I built this with Claude Code driving the uip CLI. Here it catches a Workflow
> Analyzer finding — a user task with no timeout — fixes it, re-runs clean, then
> packs and deploys to Orchestrator. Coded scorer plus low-code Agent Builder
> agents, orchestrated by Maestro."

## 4:50–5:00 — Close

> "Deterministic where it must be exact, generative where the context is messy,
> measured against a real corpus, and a human in charge of every change.
> That's FlakeWarden."

## Recording checklist

- [ ] Pre-generate the corpus and report so eval runs fast on camera
- [ ] Have a red Test Cloud run staged and a populated Action Center queue
- [ ] Rehearse the reject-then-approve to land the governance point
- [ ] Keep total runtime under 5:00 (hard cutoff)
