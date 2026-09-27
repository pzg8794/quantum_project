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
