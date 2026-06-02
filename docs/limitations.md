# Honest limitations & path to production

A solution that hides its gaps reads as immature. Here is exactly what FlakeWarden
does *not* yet solve and what production would require.

## What is real

- The deterministic scorer, the orchestration/governance logic, the grounded
  classifier interface, the eval harness, and the negative-control gate are all
  real, runnable, and tested.
- The 90.7% accuracy / 0% safety-false-positive numbers are produced by running the
  pipeline over the corpus, not asserted.
- The Maestro process and Agent Builder definitions are *illustrative artifacts*
  structured the way the deployed solution needs them. They are not literal
  importable files — real Maestro processes and Agent Builder agents are authored in
  the low-code builders; see [`SETUP.md`](../SETUP.md).

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
- **The UiPath platform pieces are not yet deployed.** The orchestration runs as a
  Python reimplementation of the Maestro flow; deploying to a real tenant and
  capturing it is the top remaining task (see [`SETUP.md`](../SETUP.md)).

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
