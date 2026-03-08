# State Analysis Evaluator Contract

Purpose: define the evaluator-state structure that `state_analysis.py` consumes, record the currently observed evaluator-state shape, and keep future fixes aligned with the original analysis contract instead of silently weakening it.

---

## Working Doc Policy

This file is the single evolving document for the `state_analysis.py` versus evaluator-state compatibility issue.

Use it to track:

- the expected consumer contract
- the currently observed producer structure
- confirmed mismatches
- approved fixes
- validation outcomes

Rule:
- keep the evolution of this issue here first
- link to this file from trackers rather than duplicating detailed technical drift notes elsewhere

---

## Evolution Log

### 2026-03-06 - Baseline contract captured

- Recorded the evaluator payload that `state_analysis.py` expects.
- Recorded the currently observed Paper 12 / Paper 8 evaluator-state shape.
- Confirmed that current extraction failures are reproducible against real saved evaluator states.

### 2026-03-06 - First confirmed regression signal

- Confirmed that the same extractor can produce either partial success or zero rows depending on scenario iteration order.
- Confirmed that this behavior is caused by `env_experiments['n/a']` being present while `evaluation_results['scenarios_results']['n/a']` is absent.

### 2026-03-06 - Mini contract tests added

- Added `Dynamic_Routing_Eval_Framework/tools/tests/test_state_analysis_evaluator_contract.py`.
- Added two small checks:
  - evaluator contract smoke test
  - placeholder-scenario tolerance test

### 2026-03-06 - Mini test baseline recorded

- `test_evaluator_contract_smoke`: pass
- `test_placeholder_scenario_tolerance`: fail

Recorded baseline failures:

- `MultiRunEvaluator_4000-Default_All_All-4000_2000_5_S1T_paper2.pkl`
  - extractor rows: `0`
  - tolerant expected rows: `125`
- `MultiRunEvaluator_1500-Default_All_All-1500_500_5_S1T_paper12.pkl`
  - extractor rows: `0`
  - tolerant expected rows: `125`
- `MultiRunEvaluator_8000-Default_All_All-4000_2000_5_S2T_paper8.pkl`
  - extractor rows: `0`
  - tolerant expected rows: `125`

Interpretation:

- the real scenario contract is still present
- the current break is extraction-time brittleness, not absence of the real scenario payload

### 2026-03-06 - P-001 applied and validated

Decision:

- keep the old extraction approach
- improve it in place by treating `n/a` as a non-analysis placeholder instead of weakening the real scenario contract
- do not rerun notebooks and do not rewrite `.pkl` files for this mismatch

Implementation:

- updated `hybrid_variable_framework/state_analysis.py`
- the extractor now skips placeholder scenarios that have no matching scenario-summary payload
- the extractor no longer mutates scenario summary dictionaries in place just to remove large list fields

Validation:

- `test_evaluator_contract_smoke`: pass
- `test_placeholder_scenario_tolerance`: pass

Interpretation:

- current Paper 2 / Paper 12 / Paper 8 evaluator states contain the real scenario payload needed by `state_analysis.py`
- the confirmed break for this phase was extractor brittleness, not missing evaluator content

### 2026-03-06 - Producer-side scenario contamination diagnosed

Observation:

- the extractor guard explains why current contaminated states can still be read
- it does **not** explain why `n/a` entered saved evaluator states in the first place

Confirmed producer-side drift in `MultiRunEvaluator`:

- `ExperimentConfiguration` defaults `attack_type` to `n/a`
- `MultiRunEvaluator.__init__` calls `self.update_configs(runs, models, attack_type, scenarios, attack_intensity)`
  - this swaps `attack_type` and `scenarios`
- `MultiRunEvaluator.update_configs(...)` forwards arguments to `self.configs.update_configs(...)` in the wrong order
  - current code drops `attack_type`
  - current code passes `attack_rate` twice
- several other `MultiRunEvaluator.update_configs(...)` call sites also use the wrong positional order

Effect:

- the evaluator can seed `env_experiments['n/a']` before real scenarios are configured
- real scenarios later run and generate summaries only for `self.configs.test_scenarios`
- saved evaluator states become structurally contaminated:
  - real scenario summaries exist
  - stray `n/a` experiment buckets also exist

Engineering interpretation:

- the extractor guard is a backward-compatibility measure for already-saved contaminated states
- the root fix belongs in the evaluator/config update path

### 2026-03-06 - Contract boundary clarified

Clarification:

- `state_analysis.py` does **not** evaluate experiments
- `state_analysis.py` analyzes evaluator-produced summary payloads
- the evaluator owns:
  - scenario execution
  - scenario winners
  - scenario summary metrics
  - plotting-ready aggregate structures

Implication:

- changing `state_analysis.py` to compensate for missing evaluator summaries is a bug
- the correct fix path is to restore evaluator summary generation and scenario hygiene at the producer boundary
- analysis-side tolerance is allowed only for backward compatibility with already-saved contaminated states

### 2026-03-06 - Producer-side repair applied and validated

Implemented:

- fixed `MultiRunEvaluator.update_configs(...)` forwarding to `ExperimentConfiguration.update_configs(...)`
- replaced bad positional `update_configs(...)` calls in `MultiRunEvaluator` with keyword calls
- added evaluator-side scenario normalization so non-configured buckets such as `n/a` are pruned from:
  - `env_experiments`
  - `runner_qubit_caps`
  - `evaluation_results`
  - `scenarios_stats`
- added evaluator-side summary repair so, when raw experiment results exist for configured scenarios, missing/stale summaries are rebuilt by the evaluator itself
- added `AllocatorRunner` post-run summary-contract verification so orchestration now forces the evaluator object to persist valid summaries before plotting/cleanup

Validation:

- `python3 -m py_compile` passed for:
  - `daqr/evaluation/multi_run_evaluator.py`
  - `daqr/evaluation/allocator_runner.py`
  - `tools/tests/test_state_analysis_evaluator_contract.py`
- small contract tests now pass:
  - `test_evaluator_contract_smoke`
  - `test_placeholder_scenario_tolerance`
  - `test_evaluator_summary_repair_and_normalization`

Interpretation:

- summary generation remains evaluator-owned
- `AllocatorRunner` now verifies that the evaluator persisted that contract
- old contaminated states remain readable
- fresh states should no longer persist stray `n/a` scenario buckets

---

## Contract Owner

- **Consumer / regression harness**: `hybrid_variable_framework/state_analysis.py`
- **Producer / contract provider**: `MultiRunEvaluator` state saved under `daqr/config/framework_state/`
- **Golden references**:
  - `Validated_Logs/Master_Dataset_Hybrid.csv`
  - `Validated_Logs/Master_Dataset_EXP3.csv`
  - `Validated_Logs/Master_Dataset_iCMABs.csv`
  - `Validated_Logs/Master_Dataset_paper2_4000_2000_5_ST.csv`
  - `Validated_Logs/Master_Dataset_paper7_50_50_5_ST.csv`
  - `Validated_Logs/Master_Dataset_paper12_1500_500_5_ST.csv`

Principle:
- `state_analysis.py` is not the place where evaluator semantics are redefined.
- If evaluator payload changes, compatibility must be preserved or migrated.
- Analysis-only attributes must be improved compatibly, not deleted.
- `state_analysis.py` consumes evaluator summaries; it does not create them.

---

## Expected Evaluator Structure

`state_analysis.py` expects a saved evaluator pickle to expose, at minimum, the following top-level keys:

- `env_experiments`
- `evaluation_results`
- `runner_qubit_caps`
- `key_attrs`
- `capacity`
- `t_scale`
- `is_base_t`
- `runs_id`
- `base_frames`
- `frame_step`
- `file_name`

### Scenario-level contract

For each real scenario (`none`, `stochastic`, `markov`, `adaptive`, `onlineadaptive`), the evaluator is expected to provide:

1. `env_experiments[scenario_name]`
   Purpose: experiment-by-experiment model payloads used to flatten rows.

2. `evaluation_results["scenarios_results"][scenario_name]`
   Expected summary keys:
   - `win_counts`
   - `total_experiments`
   - `all_model_metrics`
   - `overall_winner`
   - `winner_efficients`
   - `oracle_avg_reward`
   - `avg_gap`
   - `avg_reward`
   - `winner_avg_metrics`
   - `avg_efficiency`

3. `evaluation_results["scenarios_results"][scenario_name]["winner_avg_metrics"]`
   Expected nested keys:
   - `avg_reward`
   - `avg_gap`
   - `efficiency_list`
   - `wins`
   - `avg_efficiency`
   - `reward_list`
   - `creward_list`

4. `runner_qubit_caps[scenario_name]`
   Purpose: scenario/run allocation metadata used by the flattened dataset.

### Summary ownership contract

The evaluator is expected to generate summary payloads through its own execution path:

- `test_stochastic_environment(...)`
- `run_scenarios_model_evaluation(...)`
- `calculate_scenarios_winner(...)`
- `calculate_scenarios_performance(...)`

These summaries are then consumed by:

- plotting/visualization
- notebook robustness analysis cells
- `state_analysis.py`

Therefore:

- if evaluator summaries are absent or contaminated, that is a producer defect
- `state_analysis.py` should not be repurposed to replace evaluator summary generation

### Naming/output contract

- Internal corpora:
  - `Hybrid` = catch-all for evaluator files that do **not** end in an explicit corpus suffix pattern such as `EXP3`, `iCMABs`, or `iCMABs2`.
- Testbed master datasets:
  - `Master_Dataset_paper2_4000_2000_5_ST.csv`
  - `Master_Dataset_paper7_50_50_5_ST.csv`
  - `Master_Dataset_paper12_1500_500_5_ST.csv`
- `ST` means the master dataset aggregates **all scales** for that run configuration. It is not a standalone `T`.

---

## Current Observed Structure (2026-03-06)

Representative evaluator states inspected directly:

- `MultiRunEvaluator_1500-Default_All_All-1500_500_5_S1T_paper12.pkl`
- `MultiRunEvaluator_8000-Default_All_All-4000_2000_5_S2T_paper8.pkl`
- `MultiRunEvaluator_6000-Default_All_All-4000_2000_5_S1_5Tb_paper8.pkl`

### Top-level keys observed

All inspected states still expose the main evaluator structure:

- `scenarios_stats`
- `env_experiments`
- `evaluation_results`
- `frame_step`
- `base_frames`
- `models`
- `run_state`
- `key_attrs`
- `runner_qubit_caps`
- `capacity`
- `t_scale`
- `is_base_t`
- `runs_id`
- `allocator_id`
- `env_id`
- `attack_id`
- `cap_id`

Additional observed drift:

- Paper 12 state includes `physics_params`
- One Paper 8 state includes `_target_runs` and `_target_models`

### Structural mismatch currently present

Observed in both current Paper 12 and Paper 8 states:

- `env_experiments` includes a placeholder scenario: `n/a`
- `evaluation_results["scenarios_results"]` does **not** include `n/a`

Example observed scenario sets:

- `env_experiments`: `['n/a', 'none', 'stochastic', 'markov', 'adaptive', 'onlineadaptive']`
- `scenarios_results`: `['none', 'stochastic', 'markov', 'adaptive', 'onlineadaptive']`

This means the extractor currently iterates into a non-analysis placeholder that has no summary payload.

### Extractor behavior observed with current states

Running the active `extract_data_from_state_file(...)` against current evaluator states produced:

- Paper 12 `S1T` state:
  - `KeyError: 'all_model_metrics'`
  - `0` rows extracted
- Paper 8 `S2T` state:
  - `KeyError: 'all_model_metrics'`
  - `0` rows extracted
- Paper 8 `S1_5Tb` state:
  - partial recovery only
  - `50` rows extracted, then `KeyError: 'all_model_metrics'`

Interpretation:

- the contract-breaking trigger is the placeholder `n/a` scenario entering the extractor loop
- whether rows are recovered first depends on dictionary iteration order
- this is why some files look partially readable while others look empty

---

## Diagnostic Conclusion

The current failure is not evidence that Paper 8 alone is malformed.

The stronger conclusion is:

- the consumer contract still expects a real summary payload for every iterated scenario
- current evaluator states now include a placeholder `n/a` scenario in `env_experiments`
- the active extractor is brittle against that new placeholder and fails before or during flattening

This is a compatibility problem between the evaluator-state producer and the analysis consumer.

---

## Confirmed Mismatches

### M-001 - Placeholder scenario drift

Status: confirmed

- `env_experiments` now includes `n/a`
- `evaluation_results['scenarios_results']` does not include `n/a`
- current extractor iterates `env_experiments` directly and assumes a matching scenario summary exists

Effect:

- some files partially extract rows, then fail
- some files fail immediately with `KeyError: 'all_model_metrics'`
- behavior depends on dictionary iteration order rather than stable evaluator semantics

### M-002 - Command-block drift in active script

Status: confirmed

- the active `hybrid_variable_framework/state_analysis.py` no longer has the clean corpus-oriented `__main__` flow as the working base
- its `__main__` block drifted into ad hoc paper-specific execution

Effect:

- the operational workflow is harder to inspect and reproduce
- testbed dataset generation commands are no longer explicit in the active file

### M-003 - `convert_key_state_files_to_csv(...)` ignores `root_dir`

Status: confirmed

- the function accepts `root_dir`
- internally it still uses the global `path` variable instead of `root_dir`

Effect:

- the function signature suggests configurable behavior that it does not actually honor
- this is structural debt in the old approach and should be improved in place

---

## Fix Set Status

- P-001: completed
  - skip non-analysis placeholder scenarios such as `n/a` during extraction without weakening the real scenario contract
- P-002: pending
  - restore a clean corpus/testbed command layout in the active `state_analysis.py`
- P-003: pending
  - make `convert_key_state_files_to_csv(...)` honor its `root_dir` parameter

### Approved producer-side fix direction

- P-004: completed
  - fix `MultiRunEvaluator.update_configs(...)` argument forwarding
- P-005: completed
  - replace positional `update_configs(...)` calls in `MultiRunEvaluator` with keyword-based calls
- P-006: completed
  - normalize evaluator scenario buckets before save so only configured test scenarios are persisted
- P-007: completed
  - rebuild evaluator summaries from raw scenario experiment results when the producer detects missing/stale summary payload
- P-008: completed
  - make `AllocatorRunner` verify and persist evaluator summary contract before plotting/cleanup

Constraint:

- these producer-side fixes must preserve evaluator-owned summaries
- they are not allowed to shift summary-generation responsibility into `state_analysis.py`

---

## Small Test Strategy

Goal: validate the contract in small steps before trusting a full `state_analysis.py` run.

### TST-001 - Evaluator contract smoke test

Checks:

- evaluator pickle loads
- required top-level keys exist
- each real scenario has a matching `scenarios_results[scenario]`
- each real scenario summary contains:
  - `all_model_metrics`
  - `winner_avg_metrics`

Pass condition:

- the state is structurally valid for analysis

### TST-002 - Placeholder scenario tolerance

Checks:

- placeholder scenarios such as `n/a` do not break extraction
- extraction result does not depend on dictionary iteration order

Pass condition:

- extractor returns the same row count regardless of where `n/a` appears

### TST-003 - Scenario flattening smoke test

Checks:

- a representative evaluator state produces rows
- the flattened rows contain expected columns
- scenario/model counts are sensible

Pass condition:

- the file is usable for master-dataset generation

### TST-004 - Command path smoke test

Checks:

- corpus/testbed commands in `state_analysis.py` point at the intended files
- `convert_key_state_files_to_csv(...)` uses the provided directory, not hidden global state

Pass condition:

- dataset generation commands are explicit and reproducible

---

## Notebook / PKL Update Policy

Preferred order:

1. fix extractor-side brittleness when the saved states already contain the required real scenario payload
2. fix producer-side contract drift only when required attributes are genuinely missing
3. rerun notebooks only if producer changes must create new evaluator states

Avoid by default:

- direct `.pkl` surgery as the first solution

Reason:

- targeted extractor fixes and small contract tests are lower risk
- state rewriting can solve today’s file but create tomorrow’s compatibility problem if the true contract is still unclear

---

## Recovery Protocol

Use the following order when restoring this pipeline:

1. Keep `state_analysis.py` as the regression harness.
2. Use working corpora (`Hybrid`, `EXP3`, `iCMABs`) and existing paper2/7/12 master datasets as the golden reference.
3. Compare one working evaluator state against one failing evaluator state key-by-key.
4. Restore evaluator compatibility first when the producer broke the contract.
5. Only add extractor-side guards for true non-analysis placeholders such as `n/a`.
6. Do not remove analysis-only attributes such as `all_model_metrics`; preserve or migrate them compatibly.

---

## Current Decision Register

- `DR-001`: use this document as the single running ledger for the `state_analysis.py` contract issue
- `DR-002`: use `Hybrid`, `EXP3`, `iCMABs`, and the existing paper2/7/12 master datasets as golden references
- `DR-003`: treat `state_analysis.py` as the regression harness, not the place to redefine evaluator semantics
- `DR-004`: for the current `n/a` mismatch, prefer extractor hardening over notebook rerun or `.pkl` rewriting
- `DR-005`: only consider notebook reruns after a producer-side fix, if a real contract attribute is actually missing
- `DR-006`: `state_analysis.py` analyzes evaluator summaries; it does not replace evaluator summary generation

---

## Related Documents

- `hybrid_variable_framework/state_analysis.py`
- `docs/guides/STATE_LAYERS_AND_RESUME.md`
- `docs/updates/FRAMEWORK_DESIGN_LOG.md`
- `GA Papers/QuantumFaultTolerant/tracking/PAPER-CHANGES-TRACKER.md`
