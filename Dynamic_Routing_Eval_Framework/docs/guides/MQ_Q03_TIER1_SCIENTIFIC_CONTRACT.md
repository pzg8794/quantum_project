# M-Q Q-03 — Frozen F-08 Tier-1 Scientific Contract

**Stage:** DESIGN FROZEN — owner execution authorization received September 27, 2026  
**Foundation:** PR #2 at `d97dbde30241cd04b561cdd187a3b622a35b7592`  
**Workflow source:** `notebooks/H-MABs_Eval-Testbed-Paper8-PaperRunConfig.ipynb` at `96b327de7e3571ad3cbf05bbeee02cfb922ca2c3`, blob `599bb49b58a41fc98ff7d6f10c4077c941507269`, SHA-256 `714eefbd1eafc3c66347fc6b0460e6aaf706ad25b1ea411bcc89ac317a4711c9`

This contract freezes the first reviewer-required medium-scale experiment. It reuses the last proven Colab execution pattern: one allocator notebook executes the complete configured threat spectrum and is retained as evidence. It does not introduce a new experiment framework or change the core architecture.

## Scientific question

How does the performance hierarchy exposed by the primary matched evaluation behave on the reviewer-required 15-node, 10-route primary-form anchor?

The experiment may show persistence, compression, reversal, threat-conditional ranking, or an inconclusive result. It is not designed to prove that a preferred policy wins.

## Frozen Tier-1 anchor

- Topology family: `layered-primary-form-v1`.
- Scale parameter: `m=3`, producing 15 nodes and 10 distinct three-hop routes.
- Endpoints: source 0 and destination 14.
- Route coverage: all 15 nodes represented; exactly ten distinct route profiles.
- Physical budget: 90 qubits total, nine per route for the fixed allocator.
- Within-route actions: every nonnegative three-link integer allocation summing to nine; 55 actions per route and 550 route-action pairs.
- Reward semantics: inherited primary product-form expected payoff with `entanglement_success_factor=100` and the ten distinct profiles formed from combinations of `{1e-4, 1.5e-4, 2e-4}`.
- This synthetic anchor co-varies node and route count and does not establish hardware or physical-topology resilience.

## Frozen experimental matrix

### Policies

1. `Oracle` — privileged reference.
2. `CEpsilonGreedy` — simpler contextual learner.
3. `EXPNeuralUCB` with the registry's explicit `mode='hybrid'` — neural/adversarial stress condition.

### Threat spectrum

Every notebook run contains all five existing scenario keys, preserving their established notebook order:

1. `stochastic`
2. `markov`
3. `adaptive`
4. `onlineadaptive`
5. `none`

Scenario implementations and parameters are resolved from `ExperimentConfiguration`; the scale layer does not redefine or subset them.

### Repeats, horizon, replay, and seeds

- Three predeclared paired blocks: `0`, `1`, `2`.
- 6,000 frames per policy × threat × block cell.
- Replay anchor: `T_b`.
- Replay scale: `2`.
- Replay capacity: 12,000.
- Base seed: 12,345.
- Domain-separated deterministic seed derivation and immutable run identity from PR #2.
- Valid zero/poor runs are retained. No performance-triggered retries or favorable reruns are allowed.

The fixed-allocator Tier-1 run therefore contains `3 policies × 5 threats × 3 blocks = 45` required cells.

## Allocator axis and execution order

Each allocator is represented by a separate copied Colab notebook. A notebook is complete evidence only when its full five-threat matrix is complete and its referenced immutable bundles validate.

1. **Default/fixed allocator — Tier-1 authorized.** It has a source-verified static catalog contract and is the first complete run.
2. **Random allocator — conditional expansion.** Execute only if Q-04 demonstrates deterministic allocator-seed provenance and faithful one-time catalog construction without changing core architecture.
3. **DynamicUCB and ThompsonSampling — HOLD.** Their history-dependent reallocation requires a versioned dynamic-catalog/action-space update interface and cadence. Do not reduce them to initialization-only labels or fabricate adaptive behavior.

The execution layer may parallelize independent policy × threat × block cells in separate processes. Parallel execution must preserve identical run identities, seeds, outputs, and completion validation relative to serial execution.

## Evidence and metrics

Each cell must retain:

- exact manifest and run identity;
- topology, route, action, observation, physics, and realized-availability artifacts;
- phase-ordered event stream;
- completion marker and file hashes;
- final cumulative continuous payoff and mean continuous payoff per frame;
- policy, threat, block, allocator, replay, horizon, seed, and code provenance.

After all cells complete, derive only from validated bundles:

- Oracle-normalized efficiency by block and threat;
- across-block mean and dispersion/intervals;
- threat-specific policy ranking and robustness floor;
- convergence/regret summaries only where the recorded quantities support them.

Allocator sensitivity is not claimable from the fixed-allocator run alone.

## Acceptance and interpretation rules

- A notebook passes only when all 45 required cells validate; partial notebooks remain incomplete evidence.
- Any missing scenario, policy, or block is a failed/incomplete run, not a reduced matrix.
- A hierarchy **persists** only when its direction is consistent across paired blocks with uncertainty reported.
- **Compression** means effect separation narrows relative to the established primary result; it is not failure by itself.
- **Reversal** is reported when the paired ordering changes; it is not discarded or rerun.
- Mixed or unstable evidence is reported as threat-conditional or inconclusive.
- No causal claim about node count, topology, or allocator interaction follows from this single anchor.

## Q-04 readiness gates

Before scientific execution:

1. required PR #2 regression suite passes;
2. all 15 policy × threat combinations pass a bounded medium-anchor preflight;
3. notebook JSON, scenario coverage, matrix size, external output root, and provenance cells validate;
4. serial/parallel equivalence passes on a bounded fixture;
5. no raw bundle is written inside the source repository;
6. the execution commit is pushed before runs begin.

## Explicitly unchanged

- Core model, environment, allocator, threat, topology, and reward architecture.
- Manuscript and historical result corpus.
- F-10 100-node diagnosis.
- Tier-2 scale-spectrum expansion.

Implementation debt discovered during execution is recorded separately and does not authorize architectural refactoring.
