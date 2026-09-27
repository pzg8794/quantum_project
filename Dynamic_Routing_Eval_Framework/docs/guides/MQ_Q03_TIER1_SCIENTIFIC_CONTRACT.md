# M-Q Q-03 Tier-1 Scientific Contract

**SDLC stage:** DESIGN FROZEN — ready for independent review
**Frozen framework baseline:** `d97dbde30241cd04b561cdd187a3b622a35b7592` (`origin/codex/medium-scale-preflight`)
**Scientific authority:** `QuantumFaultTolerant@0bcc913bc5a28b1e1116245cf692989a9ec98aae` F-08 records
**Execution-board authority:** `Fall-2026-Semester-Master-Plan@6315b42edaabb25d7415b36aa73f63e0405eacfb`
**Canonical notebook:** `Dynamic_Routing_Eval_Framework/notebooks/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb`
**Canonical notebook SHA-256:** `127d04a2666867125f4e9ad04d3c3e2bdbde96b655dda68cafd3e4f3a570278c`

## 1. Scientific question and scope

Tier 1 asks:

> How does the policy-performance pattern exposed by the primary matched evaluation appear at the reviewer-required 15-node / 10-route primary-form anchor under the complete existing five-scenario notebook workflow?

This is the mandatory medium anchor requested by Reviewer C. It is exploratory evidence from three paired blocks, not a hardware result, a causal node-count result, a complete controlled scale curve, or the separate F-10 diagnosis of the 100-node external result.

Piter has authorized execution after Q-04 readiness passes. This record freezes the scientific contract only; it changes no code or notebook and runs no experiment.

## 2. Frozen Tier-1 matrix

| Axis | Frozen value |
|---|---|
| Topology family | `layered-primary-form-v1` |
| Scale point | `scale_m=3` only |
| Topology | 15 nodes: source, seven first-layer relays, six second-layer relays, destination |
| Route catalog | 10 distinct seeded three-hop routes covering all 15 nodes |
| Route budget | 9 qubits per route; 90 qubits total |
| Action space | 55 complete nonnegative three-hop allocations per route; 550 route-action pairs |
| Physics/reward | Existing primary-form route-local rates, selected-route availability gate, and product-form expected payoff with `entanglement_success_factor=100` |
| Rate profiles | The ten distinct unordered length-three profiles from `{1e-4, 1.5e-4, 2e-4}`, assigned by frozen seeded route rank |
| Policies | `Oracle`, `CEpsilonGreedy`, `EXPNeuralUCB` |
| Required EXP mode | `EXPNeuralUCB(mode='hybrid')` |
| Scenarios | `stochastic`, `markov`, `adaptive`, `onlineadaptive`, `none` |
| Horizon | 6,000 frames |
| Replay | `T_b` anchor, scale `s=2`, resolved capacity 12,000 |
| Blocks | Three paired blocks: `0`, `1`, `2` |
| Base seed | `12345` |
| Execution kind | `scientific` |
| Persistence | Immutable bundles; no legacy overwrite, best-attempt selection, or performance-triggered reruns |

The notebook scenario keys above are the exact existing full-spectrum workflow keys and remain in their existing insertion order. Q-04 must resolve and record their effective classes and parameters from the pinned code. It must not rename, omit, substitute, or silently fall back from a configured scenario.

## 3. Policy roles

- `Oracle` is the mask-aware privileged reference used for normalization; it is not a deployable learner or a competitor in winner counts.
- `CEpsilonGreedy` is the simpler contextual comparator, using its pinned configured implementation.
- `EXPNeuralUCB` is the neural/adversarial hybrid comparator and must resolve with `mode='hybrid'` from the pinned registry.

The two learners use their configured implementation-specific feedback and update rules. Tier 1 compares these configured policies; it does not claim one isolated common-feedback algorithm experiment, a pursuit-family result, or a broad ranking over the manuscript's full policy corpus.

## 4. Allocator disposition

Allocator is an experimental axis only when the frozen execution contract can represent it faithfully.

| Notebook allocator | Frozen-code capability | Q-03 disposition |
|---|---|---|
| `Default` / `QubitAllocator` | Static route budgets; explicit `(9, ..., 9)` baseline is compatible with the immutable medium catalog | **EXECUTABLE** |
| `Random` / `RandomQubitAllocator` | Stochastic allocation requires catalog/action/reward regeneration semantics not present in the strict path | **HOLD** |
| `Dynamic` / `DynamicQubitAllocator` | Dynamic history-driven allocation requires a qualified update cadence and regeneration interface | **HOLD** |
| `ThompsonSampling` / `ThompsonSamplingAllocator` | History-dependent allocation requires the same missing dynamic interface and qualified feedback semantics | **HOLD** |

Tier 1 therefore launches first with the static `Default` allocator only. A HOLD allocator may enter later only after a minimal correction is independently tested and reviewed. It must never be represented by a one-time initial allocation while being labeled dynamic.

Current executable unit count:

`1 allocator × 3 blocks × 5 scenarios × 3 policy roles = 45 required cells`.

Every later-qualified allocator adds exactly 45 cells and remains a separate allocator evidence package.

## 5. Pairing and deterministic identity

- Blocks `0`, `1`, and `2` are predeclared and may not be replaced because of poor outcomes.
- Topology and physics identities are paired within a block across policies and scenarios.
- Policy seeds are domain-separated by policy identity; scenario seeds are domain-separated by scenario identity; queue expansion must not reseed existing Tier-1 cells.
- `none`, `stochastic`, and `markov` use the same realized exogenous availability path across paired policies within a block.
- `adaptive` and `onlineadaptive` use common deterministic scenario innovations but produce policy-conditioned realized availability from each policy's completed routing history. Their realized traces and hashes belong to each policy-run identity.
- Seed derivation must use the existing SHA-256 domain-separated rule, never Python `hash()`.

Every required cell must preserve the resolved configuration, source identity, topology hash, route-set hash, action-catalog hash, physics hash, observation hash, seeds, scenario identity, allocator identity, replay settings, block, code identity, attempt lineage, event records, and completion hashes.

## 6. Notebook evidence contract

The existing validated Colab notebook workflow is the execution template. Q-04 must copy it non-destructively; it must not replace it with a new runner or rewrite the core architecture.

Evidence requirements:

1. Create one copied notebook per admitted allocator.
2. Each allocator notebook must execute the complete five-key scenario spectrum, all three policy roles, and all three paired blocks.
3. A notebook is complete only when all 45 required cells have valid immutable completion bundles.
4. Preserve executed cell outputs, the exact resolved manifest, bundle locations, checksums, failures, and final completion summary in the notebook evidence package.
5. A failed or interrupted cell leaves the notebook incomplete. Valid zero or poor results remain evidence and are never rerun for performance.
6. Exact hash-verified completed bundles may be reused; no exact mid-frame resume is claimed.

Execution acceleration may parallelize independent cells or allocator notebooks only through isolated processes/runtimes with disjoint output directories. Shared-process threading that can couple global NumPy, Python, or Torch state is not approved. Parallel execution must not alter seeds, ordering identities, scenario semantics, policy semantics, or bundle contents.

## 7. Frozen metrics

For each policy/scenario/block cell, retain the complete reward trajectory and final cumulative continuous payoff.

For each learner relative to its paired Oracle:

- **Oracle-normalized efficiency:** `100 × learner final reward / Oracle final reward`.
- **Oracle gap:** `100 - Oracle-normalized efficiency`.
- **Scenario mean efficiency:** arithmetic mean of the three block efficiencies for one policy and scenario.
- **Scenario-aggregated efficiency:** arithmetic mean of the five scenario mean efficiencies.
- **Robustness floor:** minimum of the five scenario mean efficiencies in the stated allocator/policy scope.
- **Cross-scenario stability:** report the five scenario means, their standard deviation, and coefficient of variation; do not collapse robustness to this measure alone.
- **Winner count:** number of policy/scenario/block cells won by each non-Oracle learner, reported with the underlying efficiencies.
- **Convergence/regret:** report only metrics emitted with a comparable definition by the pinned workflow. Otherwise preserve trajectories and label convergence/regret unresolved rather than inventing a derived metric.

Report all three block values alongside aggregates. Three blocks are exploratory and do not justify formal interaction, universal superiority, or deployment claims.

## 8. Predeclared interpretation rules

- **Persistence:** the prespecified learner contrast retains the same direction as the compatible primary reference in every block and in the five-scenario aggregate. Report exact gaps; do not claim causal scale invariance.
- **Compression:** the direction persists, but the absolute paired gap at the medium anchor is smaller than the compatible primary reference. This is descriptive unless the reference uses matched definitions and provenance.
- **Reversal:** the paired learner contrast changes sign consistently across all three blocks relative to the compatible primary reference.
- **Threat conditionality:** scenario-specific contrast directions differ reproducibly while the paired block directions within those scenarios agree.
- **Inconclusive:** paired blocks disagree in direction, evidence is too variable for one of the preceding labels, or no compatible primary reference is available.

If a compatible primary reference cannot be established, use only **medium-anchor pattern**, **threat conditionality**, or **inconclusive**. Do not call the single Tier-1 anchor a controlled scale trend.

Because replay and topology scale are fixed, Tier 1 cannot estimate replay-capacity effects or a scale curve. Because only `Default` is currently executable, it cannot estimate allocator sensitivity. Those questions remain outside claims from this first run.

## 9. Q-04 readiness gates

Q-04 may declare READY FOR PITER GO only if all of the following pass against this exact contract:

- the copied notebook resolves the exact topology, route/action counts, policies, five scenario keys, allocator, horizon, replay capacity, blocks, and seed root;
- the static allocation is exactly ten route budgets of nine and conserves 90 qubits;
- every configured scenario executes without fallback or omission;
- deterministic replay and nonanticipation checks pass for the applicable scenarios;
- required cells derive to exactly 45 for the executable allocator;
- notebook and bundle paths are collision-free and immutable;
- a bounded preflight confirms policy mode, trace completeness, hashes, and completion validation;
- execution-level parallelism, if used, reproduces serial identities and results for the tested fixture;
- no architecture, manuscript, historical corpus, or unrelated workflow is changed.

Any failed gate is a STOP/HOLD for the affected allocator or cell, not permission to shrink the five-scenario spectrum.

## 10. Findings classification

### BLOCKER

- No blocker remains to Q-04 preparation for the static `Default` allocator, subject to the contract-specific readiness gates above.
- `Random`, `Dynamic`, and `ThompsonSampling` are blocked from scientific execution by the missing qualified dynamic catalog/context/reward regeneration interface.

### DEBT

- Historical scenario provenance remains separate from this newly pinned medium run; new evidence must not be pooled with historical rows merely because scenario labels match.
- Dynamic allocator update cadence, feedback, and action-space regeneration require later bounded engineering and review.
- Tier-2 controlled spectrum points and F-10 diagnosis remain separate work.

### OPTIONAL

- Process-isolated execution parallelism is allowed as an execution optimization after equivalence testing. It is not a scientific factor and must not change the contract.

## 11. Explicit non-changes

This DESIGN checkpoint does not modify code, notebooks, core architecture, manuscript text, historical results, or scenario definitions. It does not run Q-04 tests or Q-05/F-09 experiments.
