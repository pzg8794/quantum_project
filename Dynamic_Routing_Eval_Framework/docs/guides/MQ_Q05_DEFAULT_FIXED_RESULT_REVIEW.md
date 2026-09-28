# Q-05 Default/Fixed Full-Roster Result Review

## Decision

**ACCEPT Q-05 ARTIFACTS FOR SCIENTIFIC REVIEW.**

This decision accepts the immutable evidence package and closes Q-06 artifact
validation. It does not authorize manuscript claims from the observed medium
results. The unexpectedly low efficiencies require bounded diagnosis from the
existing traces before scientific interpretation.

## Frozen execution identity

- Source revision: `f5ed371ca0e3ddd5af942d9deb992fdd82ce0b08`
- Source notebook SHA-256:
  `82fe9f6d557a3fe8666fff364f51c1f45032746b91a111e75f6ceaf7b4cd1436`
- Executed notebook SHA-256:
  `2f56ce51faa588f93f379adca8c3ec3261b94cc5fba04c950535a883e3953103`
- Campaign receipt SHA-256:
  `cfa05be491183597963c6efe3e02de28b8ee13adc01f61cfe91b9d0bbcdd0c21`
- Fresh matrix: three blocks by five threats by five models, 75 cells total
- Horizon: 6,000 frames per cell
- Allocator: Default/fixed, ten route budgets of nine qubits
- Process scheduler: two isolated threat-group workers; thread-based model
  execution disabled

The superseded 45-cell diagnostic remains separate and unchanged. Its receipt
SHA-256 is
`dee8b9fc17b2e5d670896deb85beaae8edbc7be19359a42f39cb6a90e72dbbb3`.
There is no old/new run-ID overlap and no old cell was pooled into this run.

## Independent artifact review

- Repository validation passed all 75 bundles and all 1.8 million ordered
  phase records.
- Every cell is `attempt-1`, `COMPLETE`, and marked as scientific evidence.
- Every cell contains 6,000 `PRESELECTION`, `DECISION`, `OUTCOME`, and `UPDATE`
  records.
- There are no failed cells, technical retries, or performance reruns.
- All campaign-receipt hashes match the immutable bundles on disk.
- All recorded source hashes match the execution revision.
- Threat seed records match across policies within each block/threat group.
- Static threat trajectories match across policies. Adaptive and
  OnlineAdaptive trajectories remain policy-conditioned by design.
- Independent aggregate recomputation matches the manager package with maximum
  numerical delta `0.0`.

## Descriptive results

Each entry is mean final reward / mean matched-Oracle normalized efficiency
across three blocks.

| Policy | None | Stochastic | Markov | Adaptive | OnlineAdaptive |
|---|---:|---:|---:|---:|---:|
| `GNeuralUCB` | 0.04521 / 3.814% | 0.04213 / 3.611% | 0.01679 / 1.742% | 0.02739 / 2.769% | 0.0000638 / 0.0555% |
| `EXPNeuralUCB` | 0.03703 / 3.124% | 0.03326 / 2.852% | 0.01358 / 1.407% | 0.02257 / 2.282% | 0.0001380 / 0.0662% |
| `CPursuitNeuralUCB` | 0.04584 / 3.867% | 0.04227 / 3.623% | 0.01980 / 2.054% | 0.03062 / 3.095% | 0.0000186 / 0.0072% |
| `iCPursuitNeuralUCB` | 0.03883 / 3.276% | 0.03440 / 2.948% | 0.01072 / 1.112% | 0.02251 / 2.277% | 0 / 0% |

`CPursuitNeuralUCB` has the highest three-block mean among learned policies for
None, Stochastic, Markov, and Adaptive. `EXPNeuralUCB` has the highest learned-
policy mean for OnlineAdaptive. These are descriptive rankings within this
specific medium Default/fixed run, not generalized performance claims.

## Diagnosis boundary

The package is internally coherent, but the observed efficiencies are too low
to transfer directly into manuscript conclusions.

- The medium catalog contains 270 zero-payoff allocations among 550 feasible
  allocations.
- In the Baseline traces, the learned neural policies select zero-payoff actions
  during approximately 88--90% of frames. Later-frame behavior improves, which
  is consistent with an action-space/convergence or calibration issue, but does
  not prove a cause.
- OnlineAdaptive realizes approximately 4.635% mean global availability under
  its burst mechanism. The five zero-result cells are trace-consistent: all
  three `iCPursuitNeuralUCB` blocks and `CPursuitNeuralUCB` blocks 0 and 2.
- For Adaptive and OnlineAdaptive, a matched Oracle uses the same block, threat,
  and seed contract, but not an identical realized availability trajectory;
  each causal trajectory responds to the policy's own decisions.

The next analysis must use the existing traces to quantify convergence,
zero-payoff action occupancy, and selected-route exposure. It must not silently
rerun, filter, replace, or select more favorable outcomes. No manuscript claim
is approved by this report.

## Parallel-execution conclusion

The qualified process scheduler is safe for this workflow because the unit of
parallelism is a complete threat group, not an individual model result stitched
in later. Every worker reconstructs private configuration, allocator, model,
scenario, RNG, logging, and state objects; runs all five models and three blocks
through the established evaluator with `threaded=False`; and writes disjoint
immutable bundles. The parent process only validates all 75 bundles and writes
the campaign receipt.

## Findings classification

- **BLOCKER:** none for artifact acceptance.
- **DEBT:** diagnose low efficiency and zero-payoff action occupancy before
  scientific interpretation.
- **DEBT:** preserve the causal-threat comparator qualification.
- **OPTIONAL:** none required before the bounded existing-trace analysis.
- **Not changed:** manuscript, architecture, scientific parameters, raw
  evidence, or prior diagnostic evidence.
