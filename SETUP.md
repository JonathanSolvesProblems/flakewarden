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

The whole flow below is driven by **Claude Code + the `uip` CLI** (this is the
UiPath for Coding Agents bonus). The transcript in
[`docs/coding-agents.md`](docs/coding-agents.md) shows the exact prompts.

### 1. Install the CLI and skills

```bash
npm install -g @uipath/cli
uip auth login                          # opens browser; pick your Labs tenant
uip skills add uipath-test uipath-agents uipath-solution uipath-platform
```

### 2. Connect the data source (Test Cloud / Test Manager)

```bash
uip testcloud connect --tenant <your-tenant>
# Register the trigger that fires the Maestro process on a failed run:
uip testcloud trigger create \
    --event run.completed \
    --filter "result.failedCount > 0" \
    --target "FlakeWarden Triage"
```

### 3. Publish the Agent Builder agents

The agent definitions live in [`agents/`](agents/). Import them and wire the
grounded sources:

```bash
uip agents import agents/classifier_agent.json
uip agents import agents/healing_agent.json
uip agents ground "FlakeWarden Triage Classifier" \
    --source test-manager-results --source object-repository-diffs --source scm-commits
# Attach the evaluation set + release gate (eval-driven development):
uip agents eval set "FlakeWarden Triage Classifier" \
    --dataset corpus/failures.jsonl \
    --gate "safety_false_positive_rate==0.0" --gate "accuracy>=0.90"
```

### 4. Register the deterministic scorer as a coded activity

```bash
uip solution add-coded flakewarden/   --entry flakewarden.scorer:score
uip solution add-coded flakewarden/   --entry flakewarden.orchestration:triage
```

### 5. Import the Maestro process

```bash
uip maestro import maestro/flakewarden.process.json
```

### 6. Validate, pack, publish, deploy

```bash
uip analyze                              # Workflow Analyzer — fix any findings before packing
uip solution pack    --output ./FlakeWarden.nupkg
uip solution publish ./FlakeWarden.nupkg --feed orchestrator
uip run deploy "FlakeWarden Triage" --folder Shared
```

> In the demo video, step 6 includes a moment where `uip analyze` reports a
> Workflow Analyzer finding, Claude Code fixes it, and the re-run passes — this
> shows the coding-agent build loop, not just a green run.

### 7. Configure the human gate

In Action Center, assign the **"FlakeWarden: review proposed test change"** queue
to your QA reviewers. No quarantine, heal, or baseline promotion executes until a
reviewer approves the task.

## Replacing synthetic data with real Test Cloud history

For a production accuracy study, point the corpus loader at a real export:

```bash
uip testcloud export-history --window 15 --only-failing --out corpus/failures.jsonl
# then label a sample and re-run:
python eval/harness.py
```

See [`docs/limitations.md`](docs/limitations.md) for the prospective-study plan.
