# AGENTS.md

This file applies to the entire `hybrid_variable_framework/` tree.

## Working style

- Ask before making code changes that alter experiment workflow, resume behavior, notebook execution order, or state-handling behavior.
- Documentation, tests, notes, and analysis are usually safe to add without advance approval, but code-path changes should be discussed first.
- Do not invent new experiment workflows when an older notebook or paper-specific pattern already exists. Check prior paper notebooks/configs and stay consistent unless explicitly asked to redesign.

## Framework intent

The framework was intentionally designed with layered resumability:

1. `model_state/`: resume individual models
2. `framework_state/QuantumExperimentRunner_*`: resume an experiment runner
3. `framework_state/MultiRunEvaluator_*`: resume evaluator-level progress
4. Planned / broader layer: allocator-runner state across evaluators

These layers are backups for one another. If a higher layer is missing or corrupted, lower layers should still help recover work when appropriate.

## Resume and state rules

- Evaluator states are resumable regardless of how many runs they contain.
- When resuming from another evaluator state with the same settings but a different run count, keep the current run settings untouched.
- Only copy the run data that is actually needed:
  - If current target is 5 runs and a matching 8-run state exists, reuse only up to 5 runs.
  - If current target is 5 runs and only a matching 3-run state exists, reuse those 3 runs and run the missing 2.
- Never silently replace the current evaluator's intended run count with the saved state's run count.
- Missing attributes in older saved states should be handled compatibly; older subsets of metadata should not cause needless resume rejection.
- If a runner state is incomplete and model sets do not fully match, model-level resume may be used only if all required model states exist.
- Registry updates are important. State saves should keep the local registry current so later resume passes can discover saved work.

## Fairness / experiment consistency

- Be careful with partial resume behavior when fairness comparisons depend on consistent runs across models.
- If resume behavior could create an unfair or inconsistent comparison, stop and ask before changing logic.
- Historically, if models were missing from a runner in a way that broke comparison fairness, the user preferred starting a new runner rather than silently mixing incompatible partial states.

## Notebook and run-order expectations

- Do not assume the user wants mixed run counts like 3 and 5 executed back-to-back per scale unless that exact workflow is already established.
- For trend analysis, prefer the established notebook/paper workflow rather than adding extra run schedules.
- Before changing notebook execution plans, compare against older paper notebooks and follow the same structure when possible.

## Practical preference

- Preserve working code paths when possible.
- Fix the smallest thing that restores the intended behavior.
- If a proposed change touches resume/state logic, explain the reason first.

## Drive migration handoff

When resuming Drive work inside `Dynamic_Routing_Eval_Framework`, read this file first:

- `Dynamic_Routing_Eval_Framework/STATE-DRIVE-MIGRATION-PLAN.md`

Current Drive contract:

- Only valid remote storage roots:
  - `quantum_data_lake/framework_state/`
  - `quantum_data_lake/model_state/`
- Keep using the existing Drive implementation; improve it, do not replace it with alternate storage paths.
- Prefer object/file-based data-management workflows, not inline terminal Python.
- Primary operator entrypoint for pattern-based Drive management:
  - `Dynamic_Routing_Eval_Framework/tools/state/manage_drive_pattern.py`
- Do not add a new script workflow unless the user explicitly approves a temporary one-off script.
- Do not rename state files during migration work.
- Use the full saved filename as the state key.
- Pattern matching is only for selecting local files to manage.
- Drive upload/check/download operations must use the full exact filename for both components.
- Do not introduce separate filename-matching logic for `model_state`; only the component changes.
- Tag rule:
  - the final suffix is the tag
  - no suffix/tag means `hybrid`

Current upload guard already implemented in:

- `Dynamic_Routing_Eval_Framework/daqr/config/gd_backup_manager.py`

Expected behavior:

- upload object state only when the remote file is missing, or when the remote file exists but is smaller than the local file
- otherwise skip overwrite

Regression coverage for that behavior:

- `Dynamic_Routing_Eval_Framework/tools/tests/test_task2d_drive_upload_size_guard_behavior.py`
- `Dynamic_Routing_Eval_Framework/tools/tests/test_task2d_drive_upload_size_guard_static.py`

Process reminder for risky changes in this area:

- task
- before
- after
- reason
- wait for approval
