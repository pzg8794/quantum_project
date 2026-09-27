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
