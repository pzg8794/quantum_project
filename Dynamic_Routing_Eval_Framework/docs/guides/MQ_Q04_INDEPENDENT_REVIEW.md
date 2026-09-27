# M-Q Q-04 Independent Scientific/Execution Review

**Decision:** REJECT/REVISE  
**Reviewed branch:** `codex/mq-q04-notebook-execution`  
**Reviewed commit:** `2cadcc76ed40726cec6f177a7823d1dddd6aab0d`  
**Review scope:** Notebook-runner fidelity to the owner-required proven Colab workflow  

## Required execution boundary

The owner required Q-04 to copy and adapt the last proven running Colab notebook workflow rather than introduce a new execution architecture. The pinned source is:

- `notebooks/H-MABs_Eval-Testbed-Paper8-PaperRunConfig.ipynb`
- source commit `96b327de7e3571ad3cbf05bbeee02cfb922ca2c3`
- source blob `599bb49b58a41fc98ff7d6f10c4077c941507269`
- SHA-256 `714eefbd1eafc3c66347fc6b0460e6aaf706ad25b1ea411bcc89ac317a4711c9`

That workflow imports and invokes `daqr.evaluation.allocator_runner.AllocatorRunner` with `ExperimentConfiguration`, and one allocator notebook covers the complete five-threat spectrum. Execution-level acceleration is permitted, but it must preserve that runner and scientific path.

## Findings

### P0 — The notebook uses a shadow runner

`daqr/campaigns/medium_scientific.py` defines a new class named `AllocatorRunner`. The new notebook imports this class from `daqr.campaigns.medium_scientific`, not the existing `daqr.evaluation.allocator_runner.AllocatorRunner` used by the proven notebook.

The replacement path is:

`medium_scientific.AllocatorRunner` → `run_scientific_matrix` → `execute_scientific` → `run_policy`

The proven path is:

`daqr.evaluation.allocator_runner.AllocatorRunner` → existing evaluator workflow

The new class is therefore not a thin acceleration wrapper around the proven runner. It shadows the established name while selecting a scientifically different execution path. Q-04 cannot be accepted for scientific execution on this basis.

### P0 — The eight-cell notebook is newly constructed, not a minimal copy

`tools/build_medium_tier1_notebook.py` constructs a new eight-cell notebook from a newly declared `cells` list. It copies the pinned source notebook's metadata, but it does not preserve and minimally adapt the source notebook's 16-cell execution flow.

The new notebook consequently preserves provenance labels and familiar class names without preserving the required runner import or invocation contract. It is a new notebook runner rather than the requested minimal configuration adaptation of the proven notebook.

### P1 — Passing tests do not establish workflow fidelity

Independent targeted rerun:

```text
tests/test_medium_scientific_notebook.py
4 passed in 28.30s
```

This passing result is bounded. The notebook test checks that the generated source contains the strings `ExperimentConfiguration` and `AllocatorRunner`, but it does not assert that `AllocatorRunner` comes from `daqr.evaluation.allocator_runner`.

The serial/process equivalence fixture also compares executions within the new path using one policy, two threats, and two frames. It does not compare the accelerated path with the proven `daqr.evaluation.allocator_runner.AllocatorRunner` workflow. Passing these tests therefore validates internal consistency of the substitute path, not scientific identity with the owner-required workflow.

## Correct elements that do not cure the rejection

Within the new path, the following appear internally coherent:

- five-threat ordering;
- 45-cell matrix construction;
- deterministic block/seed pairing;
- process isolation;
- immutable attempt bundles and exact-completion reuse;
- complete-matrix validation.

These properties are useful, but they do not establish equivalence with the required proven runner.

## Minimum correction

1. Start from an actual copy of the pinned source notebook and preserve its executable cell flow.
2. Retain the exact import `from daqr.evaluation.allocator_runner import AllocatorRunner` and the existing `ExperimentConfiguration` plus runner interface.
3. Change only the frozen medium-scale scientific settings required by Q-03: topology/route anchor, policy set, threat set, blocks, horizon, replay settings, output location, and approved run controls.
4. If process acceleration is retained, give the outer coordinator a distinct name and make it invoke the existing runner; do not redefine or shadow `AllocatorRunner`.
5. Add a test that asserts the exact runner module and invocation path.
6. Add bounded serial-versus-accelerated equivalence through the existing runner across the complete five-threat set and all three frozen policies.
7. Do not begin scientific execution from commit `2cadcc76ed40726cec6f177a7823d1dddd6aab0d`.

No code, notebook, test, scientific configuration, or experiment result was modified by this independent review.

---

## Corrective re-review

**Decision:** REJECT
**Reviewed commit:** `3704e7d55188f987669b034bae1dae0fad64b968`
**Review scope:** Proven-workflow fidelity, frozen Q-03 settings, per-result evidence integrity, and readiness to launch the Default/fixed Q-05 run

### Corrections verified

The corrective commit resolves the original workflow-architecture rejection:

- the shadow `daqr.campaigns.medium_scientific.AllocatorRunner` is removed;
- the notebook imports and invokes the established `daqr.evaluation.allocator_runner.AllocatorRunner` with `ExperimentConfiguration`;
- the frozen matrix is represented as three policies across all five threats and three 6,000-frame repetitions;
- replay scale 2 yields a 12,000-entry replay capacity under the existing runner semantics;
- the external catalog validates the 15-node, 10-route, 550-action anchor;
- persistence is directed to an external root; and
- the two-line `baseline_allocation` propagation in the existing allocator runner is bounded to the Default allocator configuration.

The targeted notebook suite passed (`5 passed`), and the expanded regression set containing the required Q-04 regression coverage passed (`96 passed`). These results establish configuration wiring and regression safety, but they do not establish scientific-launch readiness.

### Current launch blockers

#### P0 — Per-result evidence is incomplete

The restored legacy runner does not yet emit and validate the frozen Q-03 evidence package for every one of the 45 policy--threat--block results: immutable run identity and manifest, availability record, event stream, completion receipt, and hashes. The targeted dispatch test substitutes the underlying evaluator call, so it does not prove that a complete real run persists all required artifacts or that all 45 saved results can be independently validated.

#### P0 — The three repetitions do not have the frozen block identities

The catalog callback constructs the external scientific catalog with `block=0` for every repetition. Although `runs=3` produces three equal 6,000-frame executions, it does not realize the frozen Q-03 block identities `0`, `1`, and `2` or their required pairing across policies and threats.

#### P0 — Seed identity is not process-stable

The execution path derives part of its environment/policy seed from Python's process-randomized `hash()` result. The notebook does not establish a stable hash seed or replace that derivation with the frozen deterministic seed contract. A rerun in a different Colab process therefore cannot be guaranteed to reproduce the same per-result seed identity.

#### P0 — Outcome-triggered retry remains active

The inherited model-execution loop can retry an execution when total reward is non-positive. That is an outcome-conditioned rerun and conflicts with the frozen Q-03 rule against performance-triggered retries. It also prevents each saved result from representing one unambiguous predeclared attempt.

### Re-review conclusion

Commit `3704e7d55188f987669b034bae1dae0fad64b968` faithfully restores the required existing runner and correct nominal matrix settings, but the four blockers above prevent acceptance for scientific launch. Do not start the Default/fixed Q-05 run until the existing workflow produces deterministic block-specific identities, removes outcome-conditioned reruns for this campaign, persists the complete per-result evidence package, and validates one full 45-result preflight.

This corrective re-review changes documentation only. It does not modify implementation, notebooks, tests, scientific configuration, or experiment results.

---

## Final review of the causal-session TEST checkpoint

**Decision:** REJECT
**Reviewed TEST commit:** `696a3a8f93181c93ad77cecdc23420f841586f85`
**Reviewed DEV commit:** `477f6eb4`
**Intermediate valid-zero fix:** `6b5d66f6e98709cf053cfa1f5960999d46188159`
**Review scope:** Readiness to launch the authorized Default/fixed 45-cell, 6,000-frame Q-05 run under the frozen Q-03 and PR #2 evidence contracts

### Execution requirements verified

- The copied notebook continues to use `ExperimentConfiguration` and the real `daqr.evaluation.allocator_runner.AllocatorRunner`; no shadow runner is present.
- The frozen configuration remains 15 nodes, 10 routes, 550 route--action pairs, three policies, five threats in the required order, blocks `0/1/2`, 6,000 frames, replay scale 2/capacity 12,000, and base seed 12,345.
- Catalog construction is block-specific, and all three block topology identities are distinct.
- Stochastic, Markov, and Baseline use one shared static availability trajectory per block/threat across policies.
- Adaptive and OnlineAdaptive create a fresh `ScenarioSession` for each policy while preserving the same block/threat seed; realized trajectories are correctly policy-conditioned by prior route selections.
- Outcome-triggered retries are disabled for this campaign. The valid-zero correction now retains a completed zero-reward Oracle result, continues downstream policies, and records it as completed rather than raising or rerunning.
- The causal-session changes are campaign-gated execution integration. No policy algorithm, allocator, topology/reward model, or threat-strategy definition was changed.

### Independent test results

- Q-04 notebook, real tiny-horizon 45-cell evidence, and valid-zero tests: `8 passed in 58.99s`.
- Current expanded PR #2 regression command, containing the required historical 72-test gate: `121 passed in 74.99s`.
- The 6,000-frame Q-05 run was not launched.

These passing tests establish the execution matrix, causal availability behavior, valid-zero rule, and current bundle consistency. They do not cure the evidence-contract defects below because the tests currently assert the reduced two-phase evidence schema itself.

### Current launch blockers

#### P0 — Saved events do not implement the frozen PR #2 phase contract

`daqr.evaluation.campaign_evidence` reconstructs events after model execution from `path_action_list` and emits only `DECISION` and `OUTCOME`. The frozen `daqr.campaigns.medium_trace` contract is ordered `PRESELECTION` → `DECISION` → `OUTCOME` → `UPDATE` for every frame. The current Q-04 stream therefore omits the decision-time observation reference/history boundary and the learner-update record.

This is scientifically material for `EXPNeuralUCB`: the current stream records expected continuous payoff, but not its sampled Bernoulli draw, masked route feedback, route probability/importance-weighted update, within-route update target, or whether that update was applied. Consequently, the saved evidence cannot reconstruct or validate the feedback actually used to learn. A post-hoc two-phase summary is not the Q-03 phase-ordered event stream and cannot substitute for the frozen passive trace architecture.

#### P0 — Required catalog and provenance artifacts are not retained

Each new cell bundle contains `manifest.json`, `availability.json`, `events.jsonl`, `result.json`, and `completion.json`, but the evidence writer does not persist the required topology, routes, action/observation catalog, or physics artifacts either per cell or once per block under immutable hashes. The manifest carries catalog hashes without retaining the corresponding payloads. It also lacks the complete frozen code/configuration provenance required to bind policy settings, resolved replay semantics, and source commit to the result.

#### P0 — Stable seeds are not the frozen PR #2 seed identity

The new `stable_environment_seed` is process-stable, so the prior Python-`hash()` defect is fixed for the opted-in campaign. However, the scientific result identity still derives the environment/policy seed through the new campaign hash plus legacy registry offsets, while the frozen Q-03 contract requires PR #2's domain-separated `seed_manifest` identity. Static threat trajectories likewise use the legacy environment path rather than being bound to the PR #2 threat-seed manifest. Stability alone does not establish identity with the frozen seed contract.

### Minimum correction before launch

1. Thread the existing PR #2 passive `EventRecorder` semantics through the real `AllocatorRunner` execution path so every completed frame records all four phases and actual learner feedback/update fields without adding selector or RNG calls.
2. Persist the block-level topology, route, observation/action, and physics catalogs immutably, reference them from every cell, and include their hashes in completion validation.
3. Bind result identities to the frozen PR #2 domain-separated seed manifest and complete code/configuration/replay provenance; test exact identity, not only cross-process stability.
4. Repeat the real tiny 45-cell preflight and require four ordered events per frame, complete catalog/provenance artifacts, immutable hashes, and valid-zero retention before authorizing 6,000 frames.

### Final decision

The runner, matrix, causal-session behavior, valid-zero rule, and bounded tests are now materially improved, but TEST commit `696a3a8f93181c93ad77cecdc23420f841586f85` does not satisfy the frozen Q-03/PR #2 per-result evidence contract. **Do not launch the Default/fixed Q-05 run from this commit.**

This final review changes documentation only. It does not modify implementation, notebooks, tests, scientific configuration, or experiment results.

---

## Final independent review of the frozen PR2 evidence integration

**Decision:** ACCEPT
**Reviewed TEST commit:** `bd415be03e781e495d6967271530424700658ffd`
**Reviewed DEV commits:** `f6fc73cac68b1c2691c1feda64cbe799f2940187`, `be75b611c89f054c14f582f43fd6b5b60449cacb`
**Scientific contract:** Q-03 `7036f0d0044bac576c61093c6361fb6739dfc292`
**Frozen PR2 baseline:** `d97dbde30241cd04b561cdd187a3b622a35b7592`
**Review scope:** Default/fixed Q-05 launch readiness only; no scientific run was launched

### Acceptance findings

- The copied notebook retains the proven `ExperimentConfiguration` → `daqr.evaluation.allocator_runner.AllocatorRunner` → `MultiRunEvaluator` → `QuantumExperimentRunner` path. No shadow runner remains.
- Generic orchestration consumes typed scenario/evidence capabilities. It contains no `daqr.campaigns` import and no `Adaptive`/`OnlineAdaptive` name-based dispatch.
- The campaign adapter reuses the frozen PR2 `prepare_manifest`/`seed_manifest`, `AttemptBundle`, `EventRecorder`, `validate_completion`, and `validate_scale_completion` implementations rather than defining a replacement evidence schema.
- The frozen scientific matrix remains unchanged: 15 nodes, 10 routes, 550 route--action pairs; `Oracle`, `CEpsilonGreedy`, and `EXPNeuralUCB`; threats ordered `stochastic`, `markov`, `adaptive`, `onlineadaptive`, `none`; blocks `0/1/2`; 6,000 frames; replay scale 2/capacity 12,000; base seed 12,345; Default/fixed allocation `(9,) * 10`.
- Static threats use the same immutable trajectory across policies within each block/threat. Causal threats open a fresh `ScenarioSession` per policy with the same block/threat seed and record the policy-conditioned realized trajectory.
- The campaign path retains completed zero/poor outcomes and disables outcome-triggered reruns. Technical faults remain failures/restarts under PR2 attempt lineage, not favorable reruns.
- The branch was clean, pushed, and exactly synchronized with `origin/codex/mq-q04-notebook-execution` at the reviewed TEST commit before this review-only checkpoint.

### Independent validation

The reviewer reran the required checks using the project environment and a separate task-scoped temporary root:

```text
Focused Q-04 tests excluding the full matrix: 12 passed, 1 deselected in 35.88s
Real AllocatorRunner tiny 45-cell preflight: 1 passed in 60.42s
Expanded PR2 regression: 121 passed in 76.19s
```

Independent readback of the tiny preflight found:

- one COMPLETE campaign receipt with 45 required and 45 completed cells;
- the exact 3 × 5 × 3 policy/threat/block matrix;
- 45 independently validated `AttemptBundle` directories at code commit `bd415be03e781e495d6967271530424700658ffd`;
- topology, routes, observations/actions, physics, catalog diagnostics, realized availability, result, event stream, attempt lineage, manifest, and completion hashes in every cell;
- 180 records for each phase (`PRESELECTION`, `DECISION`, `OUTCOME`, `UPDATE`), four of each per four-frame cell;
- exact frozen seed manifests, one shared static trajectory per block/static-threat across policies, and separate causal per-policy evidence under the common block/threat seed;
- 28 valid zero-payoff outcomes retained as completed, with `performance_reruns = 0` and one technical attempt each.

### Final decision

No concrete Q-03/PR2 contract defect remains in the reviewed Default/fixed execution path. Q-04 is **ACCEPTED** for the exact reviewed implementation, and the Default/fixed Q-05 run is safe to launch under the already-authorized contract. This review does not admit Random, DynamicUCB, or ThompsonSampling, and it does not authorize any scientific-matrix change.

No implementation, notebook, test, scientific configuration, manuscript, or experiment result was modified by this review. The 6,000-frame Q-05 run was not launched.
