# FlakeWarden deployment runbook (UiPath Automation Cloud)

A time-boxed, priority-ordered runbook to get FlakeWarden **running on the UiPath
platform** before the AgentHack deadline. Each step is independently demoable, so
even a partial build shows the solution running on UiPath (the hard submission
requirement). Do them in order; stop-and-demo at any point.

> Track 3 (Test Cloud). The non-negotiable: the demo video must show the solution
> running on UiPath, not a local Python script. Steps 1-2 alone satisfy that.

## Pre-flight: validate units & services (do this first)

UiPath Labs is pre-provisioned, so you should not need to buy/redeem anything. But
verify before building (Agent Builder / Maestro fail quietly without units):

- [ ] Logged into the **Labs tenant** from the access email (correct region).
- [ ] **Admin → Licenses / Agentic units:** AI units and agent units allocated, non-zero.
- [ ] Services enabled: **Studio Web (Agent Builder)**, **Maestro**, **Test Cloud /
      Test Manager**, **Action Center**, **AI Trust Layer** (a model is available).
- [ ] Can create a new project in Studio Web.

If anything is zero/disabled, raise it on the AgentHack forum thread immediately.

## Priority ladder (build top-down; each row is a valid stopping point)

| # | Build | Satisfies | Effort | Priority |
|---|---|---|---|---|
| 1 | **Triage Classifier** as an Agent Builder agent (Studio Web), grounded, with eval set | "runs on platform" + Platform Usage + AI-native headline | 3-4h | MUST |
| 2 | Connect **Test Manager / Test Cloud** as the data source; stage a red run | Track-3 fit (it's literally Test Cloud) | 2-3h | MUST |
| 3 | **Coded Agent** = the deterministic scorer + orchestration (Python SDK) published to the tenant | coded + low-code blend; reuses existing code | 3-4h | SHOULD |
| 4 | **Maestro** process: scorer (coded agent) → classifier (low-code) → **Action Center** approval | orchestration + human-in-the-loop story | 4-5h | SHOULD |
| 5 | Capture a real **`uip` CLI** coding-agent session (build/analyze/deploy) | coding-agent BONUS (must be shown on video) | 1-2h | SHOULD |
| 6 | Repair Agent + governed write-back (quarantine / open defect) | closes the loop | 2-3h | NICE |

Minimum viable submission = rows 1 + 2 + 5. Strong submission = 1-5. Full = 1-6.

---

## Step 1 — Triage Classifier in Agent Builder (Studio Web)  [MUST]

1. Studio Web → New → **Agent**. Name it `FlakeWarden Triage Classifier`.
2. **System prompt:** paste [`agents/classifier_prompt.txt`](../agents/classifier_prompt.txt) verbatim.
3. **Inputs:** `test_name`, `stack_trace`, `recent_dom_diff`, `commit_message`,
   `runner_logs` (all string). Match [`agents/classifier_agent.json`](../agents/classifier_agent.json).
4. **Output schema:** object with `label` (enum real_defect|flaky|environment),
   `confidence` (number), `rationale` (string), `proposed_fix` (string|null).
5. **Context Grounding:** add an index over the Test Manager results / a sample of
   `corpus/failures.jsonl` so retrieval is real, not free-association.
6. **Evaluations:** create an eval set from `corpus/failures.jsonl` (label is the
   expected output). Set the gate: accuracy >= 0.88, and watch the real_defect rows
   never come back flaky/environment. Run it; screenshot the eval results.
7. **Publish** the agent. Run it live on 3-4 inputs (one real_defect, one flaky, one
   environment, one conflict case) and screenshot the grounded verdicts.

> This step alone makes the submission compliant (an agent running on UiPath) and
> scores Platform Usage + AI Factor. If time collapses, ship just this.

## Step 2 — Test Cloud / Test Manager as the data source  [MUST]

1. In **Test Manager**, create a project `FlakeWarden`.
2. Import the seeded suite results as test cases / executions, OR connect a small
   real suite. Goal: a **red run with several failures** the demo can point at.
3. Note the results API / export path; this is what feeds the classifier inputs.
4. Screenshot the failing run in Test Cloud (the demo opens here).

## Step 3 — Deterministic scorer as a Coded Agent (Python SDK)  [SHOULD]

Your scorer/orchestration is already plain Python, so wrap it as a Coded Agent:

```bash
npm install -g @uipath/cli
uip login
uip skills install --agent claude        # UiPath skills for Claude Code (bonus)
uip codedagent init flakewarden-scorer    # scaffold a coded-agent project
# expose flakewarden.scorer:score and flakewarden.orchestration:triage as entrypoints
uip codedagent publish
```

Confirm exact flags with `uip codedagent --help`. This gives you the coded + low-code
blend the bonus explicitly rewards.

## Step 4 — Maestro process (orchestration + human gate)  [SHOULD]

Recreate [`maestro/flakewarden.process.json`](../maestro/flakewarden.process.json) in
the Maestro BPMN designer:

1. **Trigger:** a Test Cloud run with failures.
2. **Service/coded task:** the deterministic scorer (Step 3) → emits a band.
3. **Gateway:** confident flaky → repair; confident defect (selector at break) →
   escalate; ambiguous → classifier.
4. **Agent task:** the Triage Classifier (Step 1), wrapped by the AI Trust Layer.
5. **User task (Action Center):** "FlakeWarden: review proposed test change," 24h
   timer escalating to the lead. Approve/reject/edit.
6. **Write-back task:** quarantine / promote baseline / open defect, guarded so it
   only runs after approval.

Demo the reject-then-approve to land the governance point.

## Step 5 — Capture the coding-agent session  [SHOULD, for the bonus]

Record (asciinema or screen capture) Claude Code driving the `uip` CLI:

```bash
uip rpa analyze ./flakewarden            # Workflow Analyzer
# ... fix a finding with Claude Code ...
uip rpa analyze ./flakewarden            # clean
uip solution pack    --output ./FlakeWarden.zip
uip solution publish ./FlakeWarden.zip
uip solution deploy run "FlakeWarden Triage" --folder Shared
```

The bonus only counts if the video shows this. An un-evidenced "built with Claude
Code" does not score.

## Step 6 — Repair Agent + governed write-back  [NICE]

Build the Repair Agent from [`agents/healing_agent.json`](../agents/healing_agent.json)
to draft a selector fix on approval; optionally hand off to UiPath's GA Healing
Agent. Keep it behind the human gate.

---

## What to screen-capture for the demo (collect as you go)

- [ ] Test Cloud red run (Step 2)
- [ ] Maestro process graph executing (Step 4)
- [ ] Agent Builder classifier: grounded sources + eval set + a live verdict (Step 1)
- [ ] Action Center approval task: reject one, approve one (Step 4)
- [ ] `uip` CLI build/analyze/deploy loop (Step 5)
- [ ] Local `python eval/harness.py` (90.7% / 0% safety) and `negative_control.py`

## Reference links per step

Official docs/entry points. Deep links can shift between platform releases; if one
404s, start at `https://docs.uipath.com` and search the title.

**Pre-flight (units & services)**
- Automation Cloud admin / licensing: https://docs.uipath.com/automation-cloud/automation-cloud/latest/admin-guide
- AI Trust Layer (models, governance): https://docs.uipath.com/automation-cloud/automation-cloud/latest/admin-guide/about-ai-trust-layer

**Step 1 — Agent Builder (Triage Classifier)**
- Build an agent in Studio Web: https://docs.uipath.com/agents/automation-cloud/latest/user-guide/building-an-agent-in-studio-web
- Agent evaluations (eval sets + gates): https://docs.uipath.com/agents/automation-cloud/latest/user-guide/evaluations-agent-builder
- Context Grounding (hybrid RAG): https://docs.uipath.com/automation-cloud/automation-cloud/latest/admin-guide/about-context-grounding
- Webinar recording — "Connector Corner: Agent Builder: Create, test, and deploy enterprise AI agents" (May 27, in the AgentHack resources hub)

**Step 2 — Test Cloud / Test Manager**
- Test Cloud product: https://www.uipath.com/product/test-cloud
- How Test Cloud enables agentic QA (framing for the pitch): https://www.uipath.com/blog/product-and-updates/how-uipath-test-cloud-paves-way-for-agentic-autonomous-qa
- Autopilot for Testers: https://www.uipath.com/platform/agentic-testing/autopilot-for-testers
- Test Manager docs: https://docs.uipath.com/test-manager

**Step 3 — Coded Agents (Python SDK)**
- UiPath CLI on npm: https://www.npmjs.com/package/@uipath/cli
- CLI command reference: https://docs.uipath.com/uipath-cli/standalone/latest/user-guide/command-reference
- Coding agents with the CLI: https://docs.uipath.com/uipath-cli/standalone/latest/user-guide/coding-agents
- Webinar recording — "Dev Dives: Empower coding agents to enhance the RPA SDLC" (May 28)

**Step 4 — Maestro + Action Center**
- Maestro docs hub: https://docs.uipath.com/maestro
- Maestro overview: https://docs.uipath.com/maestro/automation-cloud/latest/user-guide/overview
- Understanding process implementation: https://docs.uipath.com/maestro/automation-cloud/latest/user-guide/understanding-process-implementation
- Introducing Maestro Case (blog): https://www.uipath.com/blog/product-and-updates/introducing-maestro-case-new-uipath-capability
- Action Center product: https://www.uipath.com/product/action-center
- Action Center app tasks & agents: https://docs.uipath.com/action-center/automation-cloud/latest/user-guide/quick-start-guide-for-app-actions-and-agents
- Webinar — "Connector Corner: UiPath Maestro: Enterprise Orchestration with Case Management" (June 23)

**Step 5 — UiPath for Coding Agents (the bonus)**
- uip solution pack: https://docs.uipath.com/uipath-cli/standalone/latest/user-guide/uip-solution-pack
- uip solution publish: https://docs.uipath.com/uipath-cli/standalone/latest/user-guide/uip-solution-publish
- UiPath skills for coding agents (GitHub): https://github.com/UiPath/skills
- Webinar — "Dev Dives: Troubleshoot any automation failure with UiPath for Coding Agents" (June 25)

**Step 6 — Repair / Healing**
- UiPath Healing Agent (the GA platform feature): https://docs.uipath.com/agents/automation-cloud/latest/user-guide-ha/what-is-healing-agent

**General ramp-up**
- UiPath Academy: https://academy.uipath.com
- UiPath Python SDK + samples (GitHub): https://github.com/UiPath

## Fallback if access is delayed past day 3

Ship Step 1 only (the classifier agent running live on the platform) + the local
orchestration + the coding-agent loop, and state clearly in the video/deck what is
deployed vs reimplemented. A small genuine platform footprint beats zero.
