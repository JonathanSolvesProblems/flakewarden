# FlakeWarden — demo video script (voiceover + b-roll)

Record the **voiceover first** reading the top line of each beat, then lay the
b-roll named under it. Target **~4:00** (hard cap 5:00). Conversational, confident,
plain language. Criterion each beat serves is in [brackets].

---

## Beat 1 — The problem  (0:00–0:28)  [Business Impact]
**VOICEOVER:**
> "Every engineering team has the same problem. When a test goes red, you can't tell if it's a real bug or just a flaky test. Google found about 16% of their tests are flaky, and that flaky failures cause most of their red builds. So teams either burn hours triaging noise, or they start ignoring red builds, and that's when a real regression ships to production."

**B-ROLL:** Title card "FlakeWarden — agentic flaky-test triage for UiPath Test Cloud". Optionally the README hero. Keep it simple and clean.

---

## Beat 2 — The idea + the thesis  (0:28–1:02)  [Creativity & Innovation]
**VOICEOVER:**
> "FlakeWarden is an agentic triage system for UiPath Test Cloud. It looks at a failing test and answers the one question that matters: is this a real defect, a flaky test, or an environment problem? The design follows one principle. Deterministic where the math should be exact, generative where the evidence is messy. And a human stays in charge of every fix."

**B-ROLL:** `maestro-graph.mp4` — slow pan across the flow (Start → Triage Classifier → Verdict? → the three branches). This is your "here's the shape of it" shot.

---

## Beat 3 — The agent, classifying live  (1:02–2:12)  [Technical Execution / Platform Usage]
**VOICEOVER:**
> "Here's the agent running live in UiPath Agent Builder. First, a failing checkout test. The stack trace is a business-value assertion, the total is wrong, and the commit renamed a selector. The agent reasons over that evidence and calls it a real defect, 97% confident, and it proposes no fix, because you don't heal a real bug.
> Now a flaky one. A stale-element error, no real code change, just timing. It calls it flaky, and this time it does propose a fix: re-locate the element and add a wait. But that fix is a proposal for a human to approve, never applied automatically.
> And a third. A 503 from an upstream service with an open incident. Environment. Re-run on clean infrastructure, don't blame the test or the code. Same agent, three evidence-grounded calls."

**B-ROLL:** `verdict-real_defect.mp4` → `verdict-flaky.mp4` → `verdict-environment.mp4`, cut so each verdict lands as you say its label. Make sure the **label + rationale + proposed_fix** are visible on each.

---

## Beat 4 — The safety contract + measured results  (2:12–2:50)  [Business Impact / Technical Execution]
**VOICEOVER:**
> "Why would a QA lead trust this? Because of the safety contract: a real regression is never quarantined as flaky. When the evidence is split, the agent escalates instead of hiding. I measured it on a 150-case corpus, synthetic but deliberately adversarial: 90.7% accuracy, and a zero-percent safety false-positive rate. Not zero by luck. Zero by design, enforced by a check that fails the build if it ever regresses."

**B-ROLL:** `eval-numbers.mp4` — the harness output or the GitHub README results table. Hold on **90.7% accuracy** and **0% safety false-positive rate**.

---

## Beat 5 — Running on the UiPath platform  (2:50–3:25)  [Platform Usage]
**VOICEOVER:**
> "FlakeWarden runs on the UiPath platform end to end. The agent is built in Agent Builder, grounded on the test evidence, and deployed as a process on Orchestrator. UiPath Maestro orchestrates the flow: the agent classifies, and the verdict routes, flaky goes to a human-review heal, real defects escalate, environment re-runs on clean infra. The right actor on the right failure, with the human at the decision point."

**B-ROLL:** `deployed-process.mp4` (Orchestrator, Agent process Active) then back to `maestro-graph.mp4` on the three branches as you name them.

---

## Beat 6 — Built with a coding agent  (3:25–3:55)  [Platform Usage — BONUS]
**VOICEOVER:**
> "And I built the whole thing with a coding agent. Using UiPath for Coding Agents, Claude Code drove the uip CLI to deploy the agent, author the Maestro orchestration, and validate it, the full build-and-deploy loop, from the terminal, in natural language. Coded logic plus a low-code Agent Builder agent, orchestrated by Maestro."

**B-ROLL:** `coding-agent-cli.mp4` — the `uip` commands running (`uip agent list`, `uip maestro bpmn validate` returning Valid).

---

## Beat 7 — Close  (3:55–4:12)  [Presentation / Completeness]
**VOICEOVER:**
> "FlakeWarden. Deterministic where it must be exact, generative where the context is messy, measured against a real corpus, and a human in charge of every change. The agent, the orchestration, the corpus, and the setup instructions are all on GitHub under MIT. Thanks for watching."

**B-ROLL:** GitHub repo page (README top) + closing title card with the repo URL.

---

## Clip checklist (lay in this order)
1. Title card
2. `verdict-real_defect.mp4`
3. `verdict-flaky.mp4`
4. `verdict-environment.mp4`
5. `maestro-graph.mp4`
6. `eval-numbers.mp4`
7. `deployed-process.mp4`
8. `coding-agent-cli.mp4`
9. GitHub repo + closing card

## Recording tips
- Read the voiceover in one pass per beat; leave a half-second gap between beats for editing.
- Pace ~150 words/min. The narration is ~420 words ≈ 2.8 min of pure speech; with b-roll pauses it lands ~3.5–4 min, well under the 5:00 cap. You have margin, don't rush.
- Say the **0% safety false-positive rate** clearly, it's the trust anchor, and pair it with "on a synthetic corpus" once so it reads as honest, not overclaimed.
- Don't show a faulted Maestro run; the design-mode graph carries the orchestration story.
- Smile while reading the close; it comes through in the audio.

## Honesty guardrails (so nothing in the video is overclaimed)
- Agent classifying: **live and real**, show it.
- Maestro orchestration: shown as the **authored + validated design/graph**. Do not claim an unattended end-to-end run.
- Numbers: **measured on a synthetic-but-adversarial corpus** (say "synthetic" once).
- Coding agent: **real** (the CLI deployed the agent and authored/validated the BPMN).
