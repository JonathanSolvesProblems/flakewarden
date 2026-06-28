# Honest limitations & path to production

A solution that hides its gaps reads as immature. Here is exactly what FlakeWarden
does *not* yet solve and what production would require.

## What is real

- The deterministic scorer, the orchestration/governance logic, the grounded
  classifier interface, the eval harness, and the negative-control gate are all
  real, runnable, and tested.
- The 90.7% accuracy / 0% safety-false-positive numbers are produced by running the
  pipeline over the corpus, not asserted.
- The **Triage Classifier** is a real, published Agent Builder agent, verified live
  across all three classes and deployed as an Orchestrator process. The **Maestro
  BPMN** ([`flakewarden-maestro/`](../flakewarden-maestro/)) is a real, registry-valid
  file authored entirely through the `uip` CLI: it passes `uip maestro bpmn validate`
  (Status: Valid; 1 process, 1 start event, 12 UiPath extensions) and runs end-to-end
  in the Maestro designer (the agent classifies, the `Verdict?` gateway routes, the
  instance completes successfully). What remains is the unattended-trigger and Action
  Center plumbing described under *What production requires* below, not the
  orchestration itself.

## What is synthetic

- **The corpus is synthetic-but-adversarial, and deliberately de-rigged.**
  `corpus/generate_corpus.py` seeds 150 labeled failures. Two design choices keep
  the metrics honest rather than circular: (1) `selectors_changed` is a *noisy*
  signal (only ~65% of real defects carry it; ~10% of flaky tests carry a spurious
  one), so the deterministic scorer's selector heuristic can be wrong; and (2) the
  error-message vocabulary is *decoupled* from the classifier's keyword patterns
  (paraphrased surface forms, with some wording deliberately outside the classifier
  vocabulary), so accuracy reflects semantic overlap, not string identity. ~6 of the
  real defects are *conflict cases* whose statistics look flaky and which only the
  grounded classifier can catch. That is why the accuracy is 90.7%, not 100%.
- **The 0% safety rate is enforced by a mechanism, not the data.** Real defects with
  no selector fingerprint are routed to the classifier, which tie-breaks toward
  *real defect* on split evidence; flaky-looking histories with any regression hint
  are double-checked rather than auto-healed. Remove those mechanisms and the rate
  rises — it is earned, not planted.
- **The offline classifier is rule-based.** It genuinely reads the grounded context
  (not the label), but it is a baseline. The live Agent Builder / Claude classifier
  is expected to do better on long-tail ambiguous cases; that should be measured,
  not assumed.
- **The Maestro BPMN runs end-to-end in the designer/debug, not yet fully
  unattended.** The grounded agent is published (v1.0.0) and deployed as an
  Orchestrator process, and the Maestro BPMN runs end-to-end in the designer: the
  agent classifies (flaky, confidence 0.88), the `Verdict?` exclusive gateway routes
  to the matching branch, and the instance completes Successful. The remaining
  production plumbing is wiring the deployed agent's Orchestrator job-argument
  envelope plus a serverless robot so the BPMN invokes the agent fully unattended
  (auto-triggered by a Test Cloud failure), and an Action Center action app for the
  in-Maestro human gate; see [`SETUP.md`](../SETUP.md). A local Python reimplementation
  of the same flow backs the offline eval harness.

## What production requires

1. **Live data.** Connect the Test Manager results API (via the `uip tm` tool /
   Test Manager APIs) instead of the seeded suite. The downstream pipeline is
   unchanged.
2. **A gold-standard labeled set.** Have QA leads label a few hundred real failures
   to replace the synthetic corpus, then re-measure accuracy and the safety
   false-positive rate on real data.
3. **A prospective study.** Run FlakeWarden in shadow mode for a release cycle:
   record its verdicts without acting, compare against what engineers actually
   concluded, and report prospective sensitivity/specificity before enabling
   write-back.
4. **Drift monitoring.** Re-run the eval set on a schedule; the scorer weights and
   thresholds are constants that should be re-tuned as the suite and app evolve.
   This addresses the continuous-improvement problem that is genuinely hard and
   currently only scaffolded, not solved.

## Scope boundaries (deliberate)

- FlakeWarden triages failures; it does not author new tests. That is a different
  agent and a different problem.
- It proposes heals; it never applies them. Baseline promotion is always a human
  decision. This is a feature, not a missing capability.
