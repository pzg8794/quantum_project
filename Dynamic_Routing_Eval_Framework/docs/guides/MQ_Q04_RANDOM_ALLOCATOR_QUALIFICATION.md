# M-Q Q-04 Random Allocator Qualification

**SDLC stage:** INDEPENDENT REVIEW

**Verdict:** **HOLD**

**Reviewed branch:** `codex/mq-q03-scientific-contract`

**Reviewed baseline:** `ee107dbbdbe6c5e9b6397bb93f0a7f76b78a821f`

**Scope:** Read-only qualification of `RandomQubitAllocator` under the proven `AllocatorRunner` notebook workflow for the frozen 15-node / 10-route medium experiment.

## 1. Decision

`RandomQubitAllocator` is deterministic for a fixed seed and call order, conserves the configured budget, and does not depend on route statistics. It could therefore serve as a setup-time stochastic inter-route allocator.

It is **not currently executable as scientific Q-04 evidence**, however, because the proven notebook workflow does not preserve one authoritative realized allocation across allocator validation, catalog construction, environment construction, and saved evidence. Multiple setup layers consume additional random draws, and the allocation recorded by the evaluator can differ from the allocation installed in the environment or used to construct external contexts.

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

There is therefore no single realized Random allocation that is consistently used and recorded across all workflow layers.

## 4. Catalog and evidence alignment

The proven Paper8 notebook constructs external allocation contexts from the allocation supplied to `get_physics_params()`:

- helper definition: `notebooks/H-MABs_Eval-Testbed-Paper8-PaperRunConfig.ipynb:459-468`
- context construction from `qubit_cap`: `notebooks/H-MABs_Eval-Testbed-Paper8-PaperRunConfig.ipynb:506`
- external contexts returned to the framework: `notebooks/H-MABs_Eval-Testbed-Paper8-PaperRunConfig.ipynb:518-523`

When external contexts are supplied, the environment retains those contexts even though its copied allocator installs a later random allocation:

- `daqr/core/network_environment.py:100-115`

For a primary-form environment without external contexts, the environment instead regenerates contexts and rewards from its installed allocation:

- `daqr/core/network_environment.py:144-165`

That primary-form catalog is internally aligned with the environment allocation, but the evaluator records an earlier draw. Random allocations are explicitly excluded from the save-time single-capacity reconciliation:

- `daqr/evaluation/multi_run_evaluator.py:354-375`
- `daqr/evaluation/experiment_runner.py:225-239`

The medium catalog producer can construct an internally consistent catalog from one allocator draw and hashes the resulting action, observation, and physics structures:

- `daqr/core/catalog_components.py:83-108`

The strict medium execution contract nevertheless rejects non-static allocators because no qualified stochastic/dynamic catalog interface has yet been admitted:

- `daqr/config/execution_contract.py:60-64`

## 5. Saved-notebook evidence

The executed canonical notebook visibly demonstrates three different allocations during the same Random workflow:

- allocation used by the notebook helper: `(14, 5, 4, 2, 2, 3, 3, 2)` at `notebooks/H-MABs_Eval-Testbed-Paper8-PaperRunConfig.ipynb:10073`
- allocation recorded for the stochastic experiment: `(3, 3, 3, 2, 7, 8, 6, 3)` at `notebooks/H-MABs_Eval-Testbed-Paper8-PaperRunConfig.ipynb:10158`
- allocation installed during the following environment construction: `(4, 2, 4, 3, 8, 6, 5, 3)` at `notebooks/H-MABs_Eval-Testbed-Paper8-PaperRunConfig.ipynb:10159`

This is direct evidence that the current workflow does not preserve allocation identity from catalog creation through recorded experiment evidence.

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

Separate processes or notebooks initialized with the same seed repeat the same stream; they are not independent merely because they run separately. Conversely, one long-lived allocator assigns successive draws to successive threats, which changes the allocator condition across the supposedly matched threat spectrum. Parallelizing those cells without an explicit allocator seed/pairing contract would change the scientific design.

## 7. Smallest bounded qualification path

Random can be admitted without changing the framework's core architecture only after the following execution-layer contract is implemented and independently tested.

1. Freeze the pairing rule: derive and record one domain-separated allocator seed per paired block.
2. Instantiate a fresh `RandomQubitAllocator` for that block and draw exactly once.
3. Freeze the realized route-budget vector across all policies and five threat settings in that block.
4. Construct action/context/reward catalogs from that exact vector and record:
   - allocator seed and seed derivation;
   - realized route budgets and allocation hash;
   - action-catalog hash;
   - observation-catalog hash;
   - physics/reward hash.
5. Pass the frozen allocation downstream as immutable input and prevent validation, runner, or environment setup from drawing again.
6. Update the strict execution manifest so the allocator seed is marked consumed and the realized allocation is part of run identity.
7. Fail closed on any extra allocator invocation, allocation mismatch, missing evidence field, or catalog/hash mismatch.

Minimum qualification tests:

1. **Seed and route-stat invariance:** same seed/call identity replays exactly; route statistics do not affect Random.
2. **Single-draw enforcement:** a spy allocator proves exactly one allocation draw per paired block.
3. **Catalog alignment:** every route action sums to its realized budget; action and reward counts align; all hashes validate.
4. **Threat/policy pairing:** every policy and threat in one block uses the identical frozen allocation; independently seeded blocks may differ.
5. **Serial/replay equivalence:** serial and isolated-process execution produce identical allocations, manifests, catalogs, results, and completion hashes.
6. **Negative integrity tests:** injected extra draws, wrong budgets, mismatched hashes, or omitted seed evidence are rejected.

A serial/replay test alone is insufficient while the workflow can consume hidden extra draws. It becomes decisive only after the one-draw and evidence-alignment invariants are enforced.

## 8. Scope boundary

- **Random:** HOLD pending the bounded correction and tests above.
- **DynamicUCB:** remains HOLD because update cadence, feedback, and catalog regeneration semantics are not qualified.
- **ThompsonSampling:** remains HOLD for the same dynamic/history-dependent reasons.

This review made no code, notebook, architecture, manuscript, configuration, or experimental-result changes.
