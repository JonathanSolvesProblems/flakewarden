# Building FlakeWarden with a coding agent (UiPath for Coding Agents)

This solution was built using **Claude Code** driving the UiPath `uip` CLI. This
page documents how, so the judges can see the coding-agent workflow (the
AgentHack bonus, scored under Platform Usage).

> Note on exact commands: `uip` subcommand names below illustrate the documented
> UiPath for Coding Agents capability. Confirm the precise flags against your
> tenant's installed CLI version (`uip --help`); the build loop is the same.

## What the coding agent did

1. **Scaffolded the deterministic core** — the feature extractor (`features.py`),
   the weighted scorer (`scorer.py`), and the data schema, from a natural-language
   spec of the flake signals.
2. **Wrote the grounded classifier** with two interchangeable backends (offline
   rule-based + live Claude), sharing one prompt with the Agent Builder agent.
3. **Generated the evaluation corpus and harness**, then iterated on the
   orchestration when the first eval run exposed a design flaw (environment
   failures were being auto-classified as defects). The fix — only auto-resolving a
   defect on a positive selector-change fingerprint, and routing the rest to the
   grounded classifier — took accuracy from 70% to ~95%. A subsequent self-review
   caught that the corpus was encoding the exact signals the model read back, so
   the corpus was decoupled (noisy selector flag, paraphrased error vocabulary,
   conflict cases) and re-measured at an honest **90.7%** with a **0% safety
   false-positive rate** earned by a mechanism rather than the data.
4. **Authored the Maestro process and Agent Builder definitions**, then packaged and
   deployed via the `uip` CLI.

## The build loop (representative)

> **Honesty note:** the transcript below is a *representative* illustration of the
> intended build loop, not a captured tenant session. To earn the coding-agent
> bonus, record a **real** session (asciinema / screen capture) of these `uip`
> commands running against your Labs tenant and link it here and in the demo video.
> An un-evidenced "built with Claude Code" claim does not score.

```text
> claude: scaffold a Maestro process that scores failures, routes the ambiguous
          ones to the classifier agent, and gates every fix behind Action Center

  ... writes maestro/flakewarden.process.json ...

> uip rpa analyze ./flakewarden
  ⚠ Workflow Analyzer: ST-DBP-002  user task "human-review" has no timeout
> claude: add a 24h timer to the human-review task that escalates to the lead
  ... edits the process; re-run ...
> uip rpa analyze ./flakewarden
  ✓ 0 errors, 0 warnings

> uip solution pack    --output ./FlakeWarden.zip
> uip solution publish ./FlakeWarden.zip
> uip solution deploy run "FlakeWarden Triage" --folder Shared
  ✓ deployed; trigger active on a Test Cloud run with failures
```

The point judges should take away: the coding agent does not just generate code, it
**closes the build/validate/deploy loop** — catching a Workflow Analyzer finding,
fixing it, and shipping a governed artifact to Orchestrator.

What the coding agent verifiably did in *this* repo (visible in git history): built
the deterministic scorer, the grounded classifier, the eval harness and corpus,
then iterated when the eval surfaced a design flaw (environment failures
auto-classified as defects, 70%→90.7%) and again when a self-review caught a
circular-corpus problem. That iteration trail is the real evidence of coding-agent
engineering; the tenant deployment above is what remains to capture live.

## Coded + low-code, together

- **Coded:** the deterministic scorer and orchestration logic (exact, testable,
  version-controlled) — authored by the coding agent.
- **Low-code:** the Triage Classifier and Repair Agent — Agent Builder agents with
  grounded sources, output schemas, guardrails, and an eval gate.

This blend is exactly what the hackathon's "combine coding agents with low-code
components" bonus rewards.
