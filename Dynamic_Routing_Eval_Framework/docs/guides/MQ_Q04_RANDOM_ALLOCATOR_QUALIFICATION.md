# M-Q Q-04 Random Allocator Qualification

**SDLC stage:** INDEPENDENT REVIEW

**Verdict:** **HOLD**

**Reviewed branch:** `codex/mq-q03-scientific-contract`

**Corrective-review baseline:** `472b04bf5c096995395c2acf1c05ab451474e2aa`

**Scope:** Read-only qualification of `RandomQubitAllocator` under the proven `AllocatorRunner` notebook workflow for the frozen 15-node / 10-route medium experiment.

## 1. Decision

`RandomQubitAllocator` is deterministic for a fixed seed and call order, conserves the configured budget, and does not depend on route statistics. It is valid for allocations to differ across experiments, threats, policies, or blocks when that variability follows the declared Random-allocation semantics and the corresponding RNG identity is preserved.

The initial review incorrectly treated cross-result allocation variability as a defect and proposed freezing one allocation across all threats and policies in a block. That requirement is withdrawn.

The current verdict nevertheless remains **HOLD** for a narrower reason: within one result, the proven notebook workflow can use one allocation to construct the action/context/reward catalog, record a second allocation in evaluator metadata, and install a third allocation in the environment. This is a within-result provenance mismatch, not an objection to native Random variability across results.

The Random allocator must remain **HOLD** until a bounded execution-layer correction and the qualification tests in Section 7 pass. No core-architecture change is required or authorized by this review.

## 2. Allocation semantics

`RandomQubitAllocator` declares stochastic capability and creates a private seeded NumPy `RandomState`:

- `daqr/core/qubit_allocator.py:122-138`

Every call to `allocate()` advances that generator and may produce a new allocation. With the proven configuration defaults (`epsilon=1.0`, `epsilon_decay=1.0`), every call takes the random branch:

- `daqr/core/qubit_allocator.py:140-167`

`route_stats` is not read anywhere in the Random allocator. The only inputs affecting a draw are allocator state, epsilon settings, total budget, route count, minimum route budget, and the RNG state. The `timestep` affects only epsilon decay when `epsilon_decay < 1.0`.

The environment contains an allocation-update method that would regenerate contexts and rewards, but no active Python call site invokes it:

- definition and regeneration behavior: `daqr/core/network_environment.py:229-241`

The reviewed workflow therefore uses Random as a **setup-time stochastic allocator**, not an online per-frame allocator.

## 3. Exact workflow call trace

The same mutable Random allocator is invoked at several setup layers.

1. `AllocatorRunner.create_allocator()` consumes a validation draw:
   - `daqr/evaluation/allocator_runner.py:273-339`
2. `AllocatorRunner.run()` consumes another draw and passes that allocation to the notebook physics/context helper:
   - `daqr/evaluation/allocator_runner.py:528-547`
3. `MultiRunEvaluator` special-cases Random by initially keying the shared environment with its deterministic baseline, not the realized random allocation:
   - `daqr/evaluation/multi_run_evaluator.py:91-115`
4. Each scenario/run consumes and records another draw in `runner_qubit_caps`:
   - `daqr/evaluation/multi_run_evaluator.py:1437-1473`
5. `QuantumExperimentRunner.__init__()` consumes another draw before constructing its environment:
   - `daqr/evaluation/experiment_runner.py:82-91`
6. `ExperimentConfiguration.set_environment()` deep-copies the allocator into the environment parameters:
   - `daqr/config/experiment_config.py:1034-1056`
7. The environment constructor calls that copied allocator again and installs the resulting allocation:
   - `daqr/core/network_environment.py:111-123`

The `qubit_cap` argument passed to `QuantumExperimentRunner.run_experiment()` is accepted but is not applied to rebuild or replace the already-constructed environment:

- `daqr/evaluation/experiment_runner.py:903-943`

These calls are not invalid merely because they produce different allocations. The defect arises when one result combines artifacts derived from different draws without recording their separate roles or establishing which draw governs the result.

## 4. Per-result catalog and evidence alignment

The proven Paper8 notebook constructs external allocation contexts from the allocation supplied to `get_physics_params()`:

- helper definition: `notebooks/H-MABs_Eval-Testbed-Paper8-PaperRunConfig.ipynb:459-468`
- context construction from `qubit_cap`: `notebooks/H-MABs_Eval-Testbed-Paper8-PaperRunConfig.ipynb:506`
- external contexts returned to the framework: `notebooks/H-MABs_Eval-Testbed-Paper8-PaperRunConfig.ipynb:518-523`

For the proven Paper8 workflow, that helper allocation is the **catalog-effective allocation**: it determines the feasible allocation contexts presented to the models. When external contexts are supplied, the environment retains those contexts even though its copied allocator installs a later random allocation:

- `daqr/core/network_environment.py:100-115`

Rewards are then calculated from those retained contexts and the configured physics objects, and the models receive the same contexts and reward arrays through `get_environment_info()`:

- reward construction from `self.contexts`: `daqr/core/network_environment.py:393-428`
- model inputs: `daqr/evaluation/experiment_runner.py:467-550`

Consequently, the Paper8 result computation is internally based on the earlier catalog-effective allocation, while `environment.qubit_capacities` contains a later draw. The later environment draw does not regenerate the externally supplied contexts and therefore does not become the result's action-space allocation.

For a primary-form environment without external contexts, the environment instead regenerates contexts and rewards from its installed allocation:

- `daqr/core/network_environment.py:144-165`

That primary-form catalog is internally aligned with the environment allocation. The evaluator can still record an earlier draw, however, because `runner_qubit_caps` is populated before `QuantumExperimentRunner` and its environment consume their later draws. Random allocations are explicitly excluded from the save-time single-capacity reconciliation:

- `daqr/evaluation/multi_run_evaluator.py:354-375`
- `daqr/evaluation/experiment_runner.py:225-239`

The medium catalog producer can construct an internally consistent per-result catalog from one Random draw and hashes the resulting action, observation, and physics structures:

- `daqr/core/catalog_components.py:83-108`

That path demonstrates that cross-result Random variability is compatible with coherent evidence. The strict medium execution contract nevertheless rejects non-static allocators because no qualified stochastic allocator interface has yet been admitted:

- `daqr/config/execution_contract.py:60-64`

## 5. Exact within-result mismatch

The executed canonical notebook visibly demonstrates three allocations associated with the same stochastic result:

- **Catalog-effective allocation:** `(14, 5, 4, 2, 2, 3, 3, 2)` at `notebooks/H-MABs_Eval-Testbed-Paper8-PaperRunConfig.ipynb:10073`. This draw was passed into the helper that built the external contexts used by the result.
- **Evaluator-recorded allocation:** `(3, 3, 3, 2, 7, 8, 6, 3)` at `notebooks/H-MABs_Eval-Testbed-Paper8-PaperRunConfig.ipynb:10158`. This draw was stored in `runner_qubit_caps` for the stochastic experiment.
- **Environment-installed allocation:** `(4, 2, 4, 3, 8, 6, 5, 3)` at `notebooks/H-MABs_Eval-Testbed-Paper8-PaperRunConfig.ipynb:10159`. This later draw was installed in `environment.qubit_capacities`, but did not regenerate the external contexts.

Different values across different results would be valid. These three values are problematic because they describe competing allocation identities for one result.

`QuantumExperimentRunner.save()` serializes pickleable runner fields, including its environment when pickleable, so the environment-installed allocation can be preserved indirectly in the runner state:

- runner save invocation: `daqr/evaluation/experiment_runner.py:854-870`
- save-dictionary construction: `daqr/config/experiment_config.py:1252-1264`

The catalog-effective allocation is also reconstructible from the external allocation contexts saved with the environment. It is not, however, saved as the authoritative realized allocation for the result. The evaluator-level record instead names the earlier evaluator draw. Current artifacts therefore preserve enough data to diagnose the discrepancy but do not provide one unambiguous saved allocation identity for the result.

## 6. Reproducibility and no-write probe

The allocator seed is read from framework configuration, defaulting to `42`, and passed into `RandomQubitAllocator`:

- `daqr/evaluation/allocator_runner.py:240-285`

The allocator does not retain the initial seed as a named field, and `get_config()` does not report it:

- `daqr/core/qubit_allocator.py:126-138`
- `daqr/core/qubit_allocator.py:169-173`

The environment seed is derived with Python `hash()`, which is not process-stable unless hash randomization is separately controlled:

- `daqr/evaluation/multi_run_evaluator.py:144-168`
- `daqr/evaluation/experiment_runner.py:403-427`

A read-only in-memory probe against the reviewed allocator produced these results:

- same seed plus the same call order replayed exactly: **PASS**;
- empty versus populated `route_stats` produced the same sequence: **PASS**;
- four consecutive calls produced four distinct allocations;
- the modeled evaluator-recorded allocation differed from the modeled environment allocation;
- the modeled keying allocation differed from the modeled environment allocation;
- because `set_environment()` deep-copies the allocator, the environment allocation equaled the next draw that the original allocator would later produce.

Representative 15-node / 10-route probe values using 90 qubits, minimum 2 per route, epsilon 1.0, and seed 12345 were:

```text
first draw:  (5, 3, 3, 8, 8, 24, 9, 11, 9, 10)
second draw: (13, 20, 4, 9, 3, 13, 5, 10, 8, 5)
recorded:    (10, 16, 3, 4, 6, 12, 8, 7, 11, 13)
keyed:       (5, 7, 2, 4, 4, 11, 19, 3, 10, 25)
environment: (5, 3, 18, 13, 11, 7, 13, 9, 6, 5)
```

A second no-write probe launched the same six-draw Random sequence twice serially and twice in isolated subprocesses. All four streams were byte-identical:

```text
serial_replay_equal:   true
isolated_process_equal: true
draw_count:             6
stream_sha256:          da05f46860ca50d78d4bb95ace919140765b0d04e0c88a6841fe40dc177e3378
```

This qualifies the allocator's process-isolated RNG identity for a fixed explicit seed and call sequence. It does not qualify arbitrary per-result process parallelism in the current notebook because the legacy sequential workflow assigns results by advancing one long-lived stream. A process-isolated execution must preserve each result's intended seed and draw identity explicitly; restarting every result at the same seed would change the sequential stream assignment. Full-result replay also remains vulnerable to the separate Python-`hash()` environment-seed issue cited above.

## 7. Smallest bounded qualification path

Random can be admitted without changing the framework's core architecture only after the following execution-layer correction is implemented and independently tested.

1. Assign every result an explicit allocator RNG identity: initial seed plus a stable draw identity, or a domain-separated per-result seed.
2. Draw the allocation intended for that result exactly once at the authoritative execution boundary.
3. Construct that result's action/context/reward catalog from that exact allocation.
4. Pass the same realized allocation into the environment without another stochastic draw for that result.
5. Record with the result:
   - allocator seed and seed derivation;
   - draw identity when a sequential stream is retained;
   - realized route budgets and allocation hash;
   - action-catalog hash;
   - observation-catalog hash;
   - physics/reward hash.
6. Update the strict execution manifest so the allocator RNG identity and realized allocation are part of run identity.
7. Permit allocations to differ freely across results according to those recorded identities.
8. Fail closed on any within-result allocation mismatch, missing evidence field, or catalog/hash mismatch.

Minimum qualification tests:

1. **Seed and route-stat invariance:** same seed/draw identity replays exactly; route statistics do not affect Random.
2. **Per-result allocation authority:** a spy allocator proves that the result's authoritative allocation is the one passed to both catalog and environment construction.
3. **Catalog alignment:** every route action sums to that result's realized budget; action and reward counts align; all hashes validate.
4. **Saved evidence:** loading the completed result reproduces the explicit allocator RNG identity, realized budgets, and catalog hashes without inference from unrelated fields.
5. **Serial/replay equivalence:** serial and isolated-process execution preserve the declared per-result RNG identities and reproduce allocations, manifests, catalogs, results, and completion hashes.
6. **Native variability:** independently identified results may realize different valid allocations without failing qualification.
7. **Negative integrity tests:** injected extra draws within a result, wrong budgets, mismatched hashes, or omitted seed evidence are rejected.

A serial/replay test alone is insufficient while one result can refer to several different draws. It becomes decisive after the per-result allocation authority and evidence-alignment invariants are enforced.

## 8. Scope boundary

- **Random:** HOLD only for the demonstrated within-result allocation/catalog/evidence mismatch. Cross-result variability is approved native behavior.
- **DynamicUCB:** remains HOLD because update cadence, feedback, and catalog regeneration semantics are not qualified.
- **ThompsonSampling:** remains HOLD for the same dynamic/history-dependent reasons.

This review made no code, notebook, architecture, manuscript, configuration, or experimental-result changes.
