# M-Q Q-03 — Corrected F-08 Tier-1 Scientific Contract

**Stage:** DESIGN CORRECTED — historical full-model roster restored September 27, 2026  
**Foundation:** PR #2 at `d97dbde30241cd04b561cdd187a3b622a35b7592`  
**Workflow source:** `notebooks/H-MABs_Eval-Testbed-Paper8-PaperRunConfig.ipynb` at `96b327de7e3571ad3cbf05bbeee02cfb922ca2c3`, blob `599bb49b58a41fc98ff7d6f10c4077c941507269`, SHA-256 `714eefbd1eafc3c66347fc6b0460e6aaf706ad25b1ea411bcc89ac317a4711c9`

This contract corrects the policy-roster defect in Q-03 commit `7036f0d0044bac576c61093c6361fb6739dfc292`. The pinned proven notebook sets `models = config.NEURAL_MODELS`; at that revision, the list contains the five policies below. The earlier substitution of `CEpsilonGreedy` produced a valid reduced diagnostic, but it did not reproduce the established full-model spectrum process and is not the requested Tier-1 deliverable.

The experiment continues to reuse the proven Colab execution pattern: one allocator notebook executes the complete configured model and threat spectrum through `ExperimentConfiguration -> AllocatorRunner -> MultiRunEvaluator -> QuantumExperimentRunner`. It does not introduce a new experiment framework or change the core architecture.

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

The policy roster is the pinned notebook's complete `ExperimentConfiguration.NEURAL_MODELS` list, in source order:

1. `Oracle` — privileged reference.
2. `GNeuralUCB` — Simple-UCB route/group selection with NeuralUCB within-route action selection.
3. `EXPNeuralUCB` — EXP3 route/group selection with NeuralUCB within-route action selection.
4. `CPursuitNeuralUCB` — Pursuit/CMAB route selection with NeuralUCB within-route action selection.
5. `iCPursuitNeuralUCB` — informed Pursuit/iCMAB route selection with NeuralUCB within-route action selection and the registered predictive machinery.

`CEpsilonGreedy` is a contextual CMAB policy, not a NeuralUCB policy and not a member of this pinned five-model roster. Its previously completed cells remain preserved as additional reduced-diagnostic evidence only.

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

The fixed-allocator Tier-1 run therefore contains `5 policies × 5 threats × 3 blocks = 75` required cells.

## Matched-experiment integrity

The runner builds one shared environment for each experiment and evaluates the complete configured roster within that experiment. The policies execute serially, not as simultaneous agents consuming a depleting common pool, but the shared setup, normalization, policy-conditioned causal trajectories, and comparative ranking belong to one full-roster campaign.

The corrected campaign must therefore rerun all five policies, including `Oracle` and `EXPNeuralUCB`, from a fresh campaign namespace and output root. No cell from the defective 45-cell subset may be pooled into or substituted for a corrected 75-cell result.

## Allocator axis and execution order

Each allocator is represented by a separate copied Colab notebook. A notebook is complete evidence only when its full five-model, five-threat matrix is complete and its referenced immutable bundles validate.

1. **Default/fixed allocator — Tier-1 authorized.** It has a source-verified static catalog contract and is the first complete run.
2. **Random allocator — HOLD for separate native-stochastic provenance qualification.** Changing allocations are expected; qualification must prove that each result records the allocation, catalog, environment, and random-stream identity that generated it without freezing Random into a fixed allocator.
3. **DynamicUCB and ThompsonSampling — HOLD.** Their history-dependent reallocation requires a faithful dynamic-catalog/action-space update interface and cadence. Do not reduce them to initialization-only labels or fabricate adaptive behavior.

The execution layer may parallelize independent policy × threat × block cells in separate processes only after equivalence with the serial proven path is established. The required Default campaign remains valid as a serial run.

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

- The corrected campaign is distinct from the preserved 45-cell diagnostic and writes to a separate output namespace/root.
- A notebook passes only when all 75 required core cells validate; partial notebooks remain incomplete evidence.
- Any missing core scenario, policy, or block is a failed/incomplete run, not a reduced matrix.
- A hierarchy **persists** only when its direction is consistent across paired blocks with uncertainty reported.
- **Compression** means effect separation narrows relative to the established primary result; it is not failure by itself.
- **Reversal** is reported only against an explicitly pinned prior comparator or preregistered ordering.
- Mixed or unstable evidence is reported as threat-conditional or inconclusive.
- No causal claim about node count, topology, or allocator interaction follows from this single anchor.

## Q-04 readiness gates

Before scientific execution:

1. required PR #2 regression suite passes;
2. all 25 policy × threat combinations pass a bounded medium-anchor preflight across blocks `0`, `1`, and `2` (75 cells);
3. notebook JSON, scenario coverage, matrix size, external output root, and provenance cells validate;
4. the five registered models execute through the same proven runner/evidence path without substitute implementations;
5. no raw bundle is written inside the source repository;
6. an independent reviewer confirms the complete historical roster and absence of silent substitutions;
7. the execution commit is pushed before runs begin.

## Preserved reduced diagnostic

The prior `Oracle` / `CEpsilonGreedy` / `EXPNeuralUCB` campaign remains immutable at its existing external evidence root. Its 45 cells are scientifically valid for that exact reduced roster, but they are superseded as Q-05 completion evidence and must not be pooled with, overwritten by, deleted for, or relabeled as the corrected 75-cell campaign.

## Explicitly unchanged

- Core model, environment, allocator, threat, topology, and reward architecture.
- Manuscript and historical result corpus.
- F-10 100-node diagnosis.
- Tier-2 scale-spectrum expansion.

Implementation debt discovered during execution is recorded separately and does not authorize architectural refactoring.
