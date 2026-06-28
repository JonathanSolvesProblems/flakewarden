# Setup & deployment

Two paths: **(A) run locally** (no UiPath account, fully offline) and
**(B) deploy on UiPath Automation Cloud** via the `uip` CLI.

## Prerequisites

- Python 3.10+
- (Path B) A UiPath Automation Cloud / UiPath Labs tenant with Test Cloud,
  Maestro, Agent Builder, Action Center, and Orchestrator enabled
- (Path B) Node.js 18+ and the UiPath `uip` CLI (UiPath for Coding Agents)
- (optional) `ANTHROPIC_API_KEY` to run the live grounded classifier locally

## Path A — run locally (offline)

```bash
python corpus/generate_corpus.py                 # build the labeled corpus
python eval/harness.py --report eval/report.md    # accuracy + false-positive rate
python eval/negative_control.py                   # safety invariants (gates CI)
python seeded_suite/run_history.py --runs 14      # emit fresh execution history
python -m flakewarden.cli triage seeded_suite/history.jsonl
python -m pytest -q                               # unit tests
```

To route the ambiguous band through a real Claude model locally:

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-...        # PowerShell: $env:ANTHROPIC_API_KEY="sk-..."
python -m flakewarden.cli triage seeded_suite/history.jsonl
```

## Path B — deploy on UiPath Automation Cloud

> Working against the AgentHack deadline? Follow the time-boxed, priority-ordered
> [`docs/deploy-runbook.md`](docs/deploy-runbook.md) instead — it includes a
> pre-flight units/license check and a stop-and-demo ladder.

The flow below is driven by **Claude Code + the `uip` CLI** (UiPath for Coding
Agents). [`docs/coding-agents.md`](docs/coding-agents.md) shows the prompts.

> **Verify commands against your CLI version.** UiPath's CLI is `uip`
> (`@uipath/cli`). Subcommands evolve; run `uip --help` and `uip <tool> --help` to
> confirm flags. The commands below use the real tool names (`login`, `skills`,
> `agent`, `maestro`, `solution`, `tm`, `rpa`, `codedagent`) but exact flags may
> differ on your tenant. The **Maestro BPMN** ([`flakewarden-maestro/`](flakewarden-maestro/))
> is real and CLI-authored: it passes `uip maestro bpmn validate` and runs end-to-end in
> the Maestro designer. The JSON sketch in [`maestro/`](maestro/) and the Agent Builder
> JSON in [`agents/`](agents/) are the **specs** (shape, schema, grounding, guardrails);
> the live agent is authored in Agent Builder from that spec and published with the CLI.

### 1. Install the CLI and the coding-agent skills

```bash
npm install -g @uipath/cli
uip login                                # opens browser; pick your Labs tenant
uip skills install --agent claude        # installs the UiPath skills for Claude Code
```

### 2. Author the Agent Builder agents

Create the **Triage Classifier** and **Repair Agent** in Agent Builder. Use
[`agents/classifier_prompt.txt`](agents/classifier_prompt.txt) as the system
prompt and the schemas/guardrails in [`agents/*.json`](agents/) as the spec.
Configure inside Agent Builder: **Context Grounding** indexes over Test Manager
results, the object repository, and SCM commits; the **output schema**; and an
**evaluation set** loaded from `corpus/failures.jsonl` with the release gate
`safety_false_positive_rate == 0` and `accuracy >= 0.88`. Then publish:

```bash
uip agent publish                        # publish the agent package to the tenant
```

### 3. Register the deterministic scorer as a coded agent/activity

The scorer and orchestration are plain Python, packaged as a coded agent:

```bash
uip codedagent init flakewarden          # scaffold a coded-agent project
# entrypoints: flakewarden.scorer:score and flakewarden.orchestration:triage
uip codedagent publish
```

### 4. Open the Maestro BPMN

The Maestro BPMN already exists in this repo:
[`flakewarden-maestro/flakewarden-maestro.bpmn`](flakewarden-maestro/flakewarden-maestro.bpmn),
authored through the `uip` CLI and passing `uip maestro bpmn validate`. It encodes:
Start (failing test) → Triage Classifier (agent task) → verdict extraction → exclusive
gateway on the label → three routed branches (flaky → human-gated heal, real_defect →
escalate, environment → re-run). The [`maestro/flakewarden.process.json`](maestro/flakewarden.process.json)
sketch maps each step to its UiPath component. Open the BPMN in the Maestro designer to
wire the live agent job-argument envelope and the Action Center user task, then set the
start trigger to fire on a Test Cloud run with failures.

### 5. Validate, pack, publish, deploy

```bash
uip rpa analyze ./flakewarden            # Workflow Analyzer — fix findings before packing
uip solution pack    --output ./FlakeWarden.zip
uip solution publish ./FlakeWarden.zip
uip solution deploy run "FlakeWarden Triage" --folder Shared
```

> In the demo video, step 5 is where the coding-agent build loop shows: `uip rpa
> analyze` reports a finding, Claude Code fixes it, and the re-run passes — capture
> a **real** session here (see the note in `docs/coding-agents.md`).

### 6. Configure the human gate

In Action Center, assign the **"FlakeWarden: review proposed test change"** queue
to your QA reviewers. No quarantine, heal, or baseline promotion executes until a
reviewer approves the task.

## Replacing synthetic data with real Test Cloud history

For a production accuracy study, export real failing-test history via the `uip tm`
tool / Test Manager APIs into the same JSONL shape as `corpus/failures.jsonl`, have
QA leads label a sample, then re-run `python eval/harness.py`. See
[`docs/limitations.md`](docs/limitations.md) for the prospective-study plan.
