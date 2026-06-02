# Honest limitations & path to production

A solution that hides its gaps reads as immature. Here is exactly what FlakeWarden
does *not* yet solve and what production would require.

## What is real

- The deterministic scorer, the orchestration/governance logic, the grounded
  classifier interface, the eval harness, and the negative-control gate are all
  real, runnable, and tested.
- The 95.3% accuracy / 0% safety-false-positive numbers are produced by running the
  pipeline over the corpus, not asserted.
- The Maestro process and Agent Builder definitions are structured exactly as the
  deployed solution needs them.

## What is synthetic

- **The corpus is synthetic-but-adversarial.** `corpus/generate_corpus.py` seeds 150
  labeled failures with realistic histories and deliberately planted near-boundary
  cases. A solo builder cannot ship a real enterprise's months of proprietary CI
  history. The corpus is honest about its construction and is designed so the
  metrics are not a rigged 100%.
- **The offline classifier is rule-based.** It genuinely reads the grounded context
  (not the label), but it is a baseline. The live Agent Builder / Claude classifier
  is expected to do better on long-tail ambiguous cases; that should be measured,
  not assumed.

## What production requires

1. **Live data.** Connect the Test Manager results API (`uip testcloud
   export-history`) instead of the seeded suite. The downstream pipeline is
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
