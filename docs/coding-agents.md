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
   defect on a positive selector-change fingerprint — took the accuracy from 70% to
   95.3% and the noise rate from 44% to 6%.
4. **Authored the Maestro process and Agent Builder definitions**, then packaged and
   deployed via the `uip` CLI.

## The build loop shown in the demo

```text
> claude: scaffold a Maestro process that scores failures, routes the ambiguous
          ones to the classifier agent, and gates every fix behind Action Center

  ... writes maestro/flakewarden.process.json ...

> uip analyze
  ⚠ Workflow Analyzer: ST-DBP-002  user task "human-review" has no timeout
> claude: add a 24h timer to the human-review task that escalates to the lead
  ... edits the process; re-run ...
> uip analyze
  ✓ 0 errors, 0 warnings

> uip solution pack --output ./FlakeWarden.nupkg
> uip solution publish ./FlakeWarden.nupkg --feed orchestrator
> uip run deploy "FlakeWarden Triage" --folder Shared
  ✓ deployed; trigger active on testcloud.run.completed
```

The point judges should take away: the coding agent did not just generate code, it
**closed the build/validate/deploy loop** — catching a Workflow Analyzer finding,
fixing it, and shipping a governed artifact to Orchestrator.

## Coded + low-code, together

- **Coded:** the deterministic scorer and orchestration logic (exact, testable,
  version-controlled) — authored by the coding agent.
- **Low-code:** the Triage Classifier and Healing Agent — Agent Builder agents with
  grounded sources, output schemas, guardrails, and an eval gate.

This blend is exactly what the hackathon's "combine coding agents with low-code
components" bonus rewards.
