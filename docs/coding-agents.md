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

## The build loop (actually executed)

Claude Code drove the real `uip` CLI against the live Labs tenant. These commands
were run, not illustrated:

```text
# set up UiPath for Coding Agents
npm install -g @uipath/cli            # uip 1.196.0
uip login                             # -> jonathansolvesproblems / DefaultTenant
uip skills list                       # 21 UiPath skills for coding agents
uip tools install @uipath/maestro-tool @uipath/agent-tool @uipath/solution-tool \
                  @uipath/orchestrator-tool @uipath/tasks-tool @uipath/test-manager-tool

# deploy the published Agent Builder agent as a runnable Orchestrator process
uip solution packages list            # -> Solution 1, PackageVersionKey 17d2de71...
uip agent deploy 17d2de71-24a1-4d2e-824f-dbcd313ac365 --name FlakeWardenClassifier
  -> Installed -> folder: solution_folder ; process: Solution.1.agent.Agent (ProcessType: Agent)

# author the Maestro BPMN orchestration, registry-driven
uip maestro bpmn registry pull
uip maestro bpmn registry get Orchestrator.StartAgentJob   # agent-call node template
uip maestro bpmn registry get Actions.HITL                 # human-task node template
uip maestro bpmn init flakewarden-maestro --process-id FlakeWardenTriage
  ... Claude Code authors flakewarden-maestro/flakewarden-maestro.bpmn from the
      templates + the structural-BPMN contract (Start -> agent -> verdict script
      -> exclusive gateway -> flaky/real_defect/environment branches + diagram) ...
uip maestro bpmn validate flakewarden-maestro/flakewarden-maestro.bpmn
  -> Status: Valid   (1 process, 1 start event, 12 UiPath extensions, 0 warnings)
```

The point judges should take away: the coding agent does not just generate code — it
drove the platform. It deployed a published agent to Orchestrator and authored a
registry-valid Maestro BPMN orchestration end to end through the `uip` CLI, the exact
"build, deploy, operate via natural language" loop UiPath for Coding Agents is for.

What else the coding agent verifiably did in *this* repo (visible in git history):
built the deterministic scorer, the grounded classifier, the eval harness and corpus,
then iterated when the eval surfaced a design flaw (environment failures
auto-classified as defects, 70%→90.7%) and again when a self-review caught a
circular-corpus problem.

**Honest remaining step:** running the BPMN fully unattended needs the Orchestrator
job-argument envelope for the agent process resolved and a serverless robot assigned
to `solution_folder` (the agent runs correctly today in Agent Builder; this is
deployment plumbing). The in-Maestro human gate needs an Action Center action app.

## Coded + low-code, together

- **Coded:** the deterministic scorer and orchestration logic (exact, testable,
  version-controlled) — authored by the coding agent.
- **Low-code:** the Triage Classifier and Repair Agent — Agent Builder agents with
  grounded sources, output schemas, guardrails, and an eval gate.

This blend is exactly what the hackathon's "combine coding agents with low-code
components" bonus rewards.
