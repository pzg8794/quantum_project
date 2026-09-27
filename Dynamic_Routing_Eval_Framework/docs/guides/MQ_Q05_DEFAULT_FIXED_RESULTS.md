# M-Q Q-05 — Default/Fixed Medium-Scale Reduced-Diagnostic Checkpoint

> **SUPERSEDED AS Q-05 COMPLETION EVIDENCE:** These immutable results remain valid only for the executed `Oracle` / `CEpsilonGreedy` / `EXPNeuralUCB` subset. The pinned proven workflow requires `Oracle`, `GNeuralUCB`, `EXPNeuralUCB`, `CPursuitNeuralUCB`, and `iCPursuitNeuralUCB`; therefore this 45-cell package is preserved as an additional reduced diagnostic and must not be presented as the completed full-model Tier-1 experiment. No cell from this package may be pooled into or substituted for the corrected, fresh 75-cell campaign.

**Status:** REDUCED DIAGNOSTIC PRESERVED / FULL-MODEL Q-05 ACCEPTANCE REVOKED
**Execution commit:** `fdcefee58adc8df8d802d33f8c079666d115d68d`  
**Execution mode:** Serial, proven `AllocatorRunner -> MultiRunEvaluator -> QuantumExperimentRunner` workflow  
**Started:** `2026-09-27T21:08:29Z`  
**Finished:** `2026-09-27T21:34:22Z`

## Frozen matrix executed

- Default/fixed allocator only: 90 total qubits, nine per route.
- Three predeclared blocks: `0`, `1`, `2`.
- Three policies: `Oracle`, `CEpsilonGreedy`, `EXPNeuralUCB`.
- Five threats, in frozen order: `stochastic`, `markov`, `adaptive`, `onlineadaptive`, `none`.
- 6,000 frames per cell; 45 required cells total.
- Medium anchor: 15 nodes, 10 routes, 550 route-action pairs.
- Replay scale 2 / capacity 12,000; base seed 12,345.

## Validation result

- All 45 required cells completed and passed the existing PR2 `validate_completion` checks.
- Every cell contains topology, routes, observations/actions, physics, catalog diagnostics, realized availability, result, four-phase event stream, attempt lineage, manifest, and completion hashes.
- Phase totals are 270,000 each for `PRESELECTION`, `DECISION`, `OUTCOME`, and `UPDATE` (1,080,000 phase records total).
- Static threats share one trajectory across policies within each block/threat pair. Adaptive and OnlineAdaptive retain separate policy-conditioned causal trajectories under the common block/threat seed.
- One valid zero-payoff cell was retained: `EXPNeuralUCB`, block 0, `onlineadaptive`. It was not replaced or rerun for performance.
- All cells report one technical attempt and zero performance reruns.
- The executed notebook contains no error output.

## Validated outcome summary

Values are Oracle-normalized efficiency means across the three paired blocks, with sample standard deviation in parentheses. These are results from this one medium-scale fixed-allocator anchor, not a controlled node-count curve.

| Threat | CEpsilonGreedy | EXPNeuralUCB | Non-Oracle ordering |
|---|---:|---:|---|
| Stochastic | 57.55% (11.56) | 3.70% (0.34) | CEpsilonGreedy > EXPNeuralUCB |
| Markov | 30.96% (3.77) | 2.34% (0.61) | CEpsilonGreedy > EXPNeuralUCB |
| Adaptive | 25.68% (0.56) | 3.35% (0.62) | CEpsilonGreedy > EXPNeuralUCB |
| OnlineAdaptive | 56.09% (7.97) | 0.11% (0.10) | CEpsilonGreedy > EXPNeuralUCB |
| Baseline (`none`) | 60.36% (9.55) | 3.86% (0.27) | CEpsilonGreedy > EXPNeuralUCB |

Block-level Oracle-normalized efficiencies:

| Threat | CEpsilonGreedy blocks 0/1/2 | EXPNeuralUCB blocks 0/1/2 |
|---|---|---|
| Stochastic | 59.95%, 67.73%, 44.98% | 3.46%, 3.56%, 4.09% |
| Markov | 34.99%, 30.36%, 27.52% | 2.10%, 1.90%, 3.04% |
| Adaptive | 25.04%, 26.08%, 25.91% | 3.33%, 2.75%, 3.98% |
| OnlineAdaptive | 62.08%, 47.04%, 59.14% | 0.00%, 0.15%, 0.19% |
| Baseline (`none`) | 64.55%, 67.10%, 49.43% | 3.70%, 3.71%, 4.18% |

The across-threat efficiency floor in this matrix is 25.68% for `CEpsilonGreedy` and 0.11% for `EXPNeuralUCB`.

## Bounded interpretation

Within this exact fixed-allocator medium anchor, `CEpsilonGreedy` ranks above `EXPNeuralUCB` in all five threat regimes and all 15 block/threat comparisons. This establishes the observed non-Oracle ordering for the frozen matrix. Describing it as a reversal requires an explicitly pinned prior comparator or preregistered ordering and is not established by this run alone.

This result does **not** establish that node count alone caused the observed ordering, does not test allocator sensitivity, and cannot support an inference about the established five-model roster because three required learning policies are absent. It is one reduced medium-anchor diagnostic; it must not be pooled with the corrected 75-cell campaign or with heterogeneous external testbeds as though they were one controlled scaling curve.

## Immutable evidence

- Source notebook SHA-256: `2f5f922cfdd3b4bd8dc1448a41b54bb28cc1afe8bfe8b656ae8fee7325e9accb`
- Executed notebook SHA-256: `b2765cebee8bcf253926814c851808d7b6d7cd6fe20cd804dd2120432fe0f028`
- Campaign receipt SHA-256: `dee8b9fc17b2e5d670896deb85beaae8edbc7be19359a42f39cb6a90e72dbbb3`
- Manager validation SHA-256: `08325900c5c6a88529bc4ac4b35a692af8880c330055781cee973ddbbae6f202`
- External evidence root: `/Users/pitergarcia/DataScience/Semester4/GA-Work/quantum_experiment_evidence/medium-tier1/default-fixed`

## Remaining allocator scope

- Random remains pending within-result allocation/catalog/provenance coherence under its native stochastic semantics.
- DynamicUCB and ThompsonSampling remain held until the existing workflow can represent their adaptive cadence and catalog regeneration faithfully.
- No manuscript, historical corpus, threat semantics, allocator architecture, or frozen scientific configuration changed during this run.
