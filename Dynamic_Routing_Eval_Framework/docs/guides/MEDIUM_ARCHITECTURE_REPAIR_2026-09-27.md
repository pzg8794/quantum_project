# PR #2 bounded architecture repair

## Pass 2 — design checkpoint (2026-09-27)

Starting revision: `b447ee6f54bfcb721ab0691996ef6a9591ad360c`, clean detached
retained review worktree, matching fetched PR #2; base `47757380`. Original
checkout remains protected at `854c4ab3` with its six mode edits and run_scripts.
The remainder of the original report below is the **Pass 1 historical receipt**.

Smallest extension: explicitly configured catalog/reward component objects own
their schemas, construction and validation; generic resolution checks interfaces
and records component identities. A common scenario session owns a private RNG,
immutable past selections and per-frame availability. Static strategies retain
their original complete realization. Causal strategies receive only selections
through t-1, produce frame t availability before selection, and receive the
selected route only after feedback/update. No current-action lookahead.
Concrete policies own configuration checks and optional snapshots. The generic
runner asks for capabilities, never concrete class names or mode conventions.

For causal runs the input identity cannot contain a future trajectory hash.
It records the scenario/code/seeds and a null pre-run trajectory hash; the
immutable completion binds the realized trajectory. A policy-reactive trajectory
is not an exogenous common mask shared across policies.

Static behavior, four-route rewards, EXP3 importance weighting, passive logging,
attempt protections and complete configured-cell checks must remain unchanged.
No scientific execution is authorized. Technical causality verification is not
historical scientific-definition validation.

## A–C: requirements, system understanding, design (before implementation)

Reviewer scale varies topology/catalog breadth. Scenario, policy, allocator,
replay, horizon, blocks, resources and physics remain independent configured
choices. September 27 canonical records supersede the earlier two-threat shortcut.
No scientific execution, manuscript edit or design approval is part of this repair.

Initial checkout: `GA-Work/hybrid_variable_framework`, branch
`codex/medium-scale-preflight`, head `854c4ab398909fb9611403b0bd238e4ea98d1398`,
upstream `origin/codex/medium-scale-preflight`, remote
`https://github.com/pzg8794/quantum_project.git`, fetched 0/0. PR #2 is open at
that exact head and base `gcp-main` at `47757380b0243649d4dac864a919f9e85ceb9307`.
No staged changes; six unrelated mode changes and untracked `run_scripts/`
preserved. Isolated detached worktree:
`/Users/pitergarcia/DataScience/Semester4/Quantum-PR2-architecture-review`.
The app worktree tool targets the containing GA repository, not this nested
execution repository; a direct nested-repository worktree was necessary.

| Owner | Configured data | Consumer | Behavior |
|---|---|---|---|
| `ExperimentConfiguration` | `models`, `test_scenarios`, `runs` | `MultiRunEvaluator.run_scenarios_model_evaluation()` | iterate every configured scenario; evaluate configured models |
| `algorithm_configs` | model class, kwargs, runner type, seed offset | `QuantumExperimentRunner.run_algorithm()` | instantiate registered class; dispatch step-wise/batch |
| `AllocatorRunner` / allocator object | resource totals, minima, baseline, allocator type | evaluator → environment | resource allocation |
| config `scale`, `base_capacity`; evaluator frame schedule | replay multiplier/anchor, horizon | runner → model | replay capacity and execution length |
| `physics_params`, `testbed_config`, paper/topology configuration | physics and graph/catalog | `set_environment()` / environment | contextual actions and reward construction |
| attack strategy registry/construction | scenario parameters | environment | generated masks or selection-history behavior |
| evaluator/runner persistence | caches, retries, summaries | legacy orchestration | remains unchanged; immutable execution must not inherit favorable retries |

Smallest repair: use the actual ExperimentConfiguration and its registry, with
an explicit persistence-disabled mode; put structured execution/testbed settings
inside the configuration package. Add strict strategy resolution (no unknown
fallback), capability checks, and a single-attempt execution adapter using runner
metadata. Campaign code retains only catalog geometry, hashing and event/bundle
mechanics. Technical values live in test fixtures, not a scientific preset.
Resolve all configured cells before execution; never drop unsupported cells.
Snapshot/hash all resolved choices; derive cell counts. Keep stable seed roots
independent of later queue expansion. Retain exact regression/trajectory tests.

EXP3 trace correction: retain raw masked feedback, separately record the actual
importance-weighted update after the existing update call, validate against the
selected probability using the algorithm's existing numerical probability floor.
Do not modify learning arithmetic.

## D: implementation and complete hardcoding audit

| Axis introduced by original PR | Old owner | Correct owner / repair |
|---|---|---|
| Threat IDs/subset/count, CLI choices | spec tuples, runner branches | `configs.test_scenarios`; strict canonical strategy resolution; full cell expansion |
| Rates/intensity/effective interruption | spec and manifest literals | configured strategy parameters, or existing config scalar construction; resolved strategy parameters logged |
| Policies/count/dispatch/classes | campaign tuple and class map | `configs.models` and `algorithm_configs` class/runner metadata |
| Mode/hyperparameters/default assertions | `POLICY_KWARGS`, runner checks | existing algorithm registry and inspected constructor defaults; constructed mode/capacity checked |
| Allocator name/equal allocation | campaign string | configured allocator component and explicit static capability; allocation/conservation checked |
| Replay anchor/scale/capacity | 2 / 12000 / T_b literals | canonical `scale`, `base_capacity`, structured frame schedule; capacity derived once |
| Horizon/base horizon | 6000 literal and validation | required `ExecutionSettings` inside config package; no experiment preset |
| Qubit budget / total | 9 / 90 literals | allocator output / total; complete weak compositions derived |
| Node/route/action counts | 15 / 10 / 55 / 550 assumptions | selected scale + versioned generator rules + mathematical action cardinality |
| Scale points / whitelist | `(1,2,3)` campaign guard | configured scale points; positive supported scale with adequate profiles/resources |
| Rate values / profile pool | fixed rates and index 9 | explicit testbed profile pool; evenly spaced pool indices derived from its size |
| Success factor | campaign 100, helper default | explicit `physics_params`; reward helper requires factor |
| Blocks/repeats and run arithmetic | campaign expectations | `configs.runs`, derived required-cell list; completion checks exact matrix coverage |
| Topology selection | implicit campaign family | explicit `testbed_config.topology_family`; unsupported components HOLD |
| Seed root/defaults | scientific choices packed into protocol constant | explicit namespace/base seed; cell domains and registry seed offset; queue expansion excluded from root |
| Oracle/hybrid names in event validation | concrete-name checks | resolved trace capability/privilege metadata; injected IDs supported |

Technical values reside only in `tests/medium_fixtures.py` and
`tests/runtime_primary_k55.py`. These instantiate the actual ExperimentConfiguration,
not a replacement campaign config. String-valued scenario descriptions still
use canonical scalar construction; structured specifications allow explicit
strategy parameters. Unknown strategies never inherit legacy fallbacks.

```text
ExperimentConfiguration + explicit ExecutionSettings/testbed/physics
  → strict resolver + existing model/strategy registries
  → configured scale/catalog + allocator component
  → recorded primary environment + strategy realization + registered policy
  → single attempt (no legacy favorable retries)
  → resolved manifest, phased events, immutable completion
```

The existing MultiRunEvaluator remains the scenario-axis authority/pattern:
`for attack_type in self.configs.test_scenarios.keys()`. No legacy evaluator
retry/cache behavior was changed or invoked. `required_cells` mirrors that
orchestration; `validate_scale_completion` rejects missing, duplicate,
wrong-config or wrong-scale cells.

### Retained implementation invariants — not study choices

- SHA-256, four-byte big-endian seeds, PCG64 topology generation, explicit seed
  domain names, canonical JSON and version strings identify algorithms/formats.
- Layered-family formulas `4m+3` nodes / `3m+1` routes, two relay layers, three
  hops, middle-degree bound three and ordered endpoints define this generator.
  Choosing family/scale belongs to config; another family requires another
  component, never silent semantic substitution.
- Complete lexicographic weak compositions, hop-dimensional actions, simple
  routes, finite probabilities, conservation and binary masks are validity rules.
  Million-action bound is a fail-closed memory guard, never truncation.
- Four legacy route profiles/IDs are the frozen compatibility fixture, not the
  medium experiment's rate configuration.
- Four event phases, attempt 1 plus at most one infrastructure-failure restart,
  atomic writes/checksums are integrity rules. No performance-triggered retry.
- Existing EXP3 floor `1e-12` is a numerical safeguard shared with trace metadata;
  learning arithmetic is unchanged.
- CPU, deterministic Torch, one BLAS/Torch thread and 512-frame ceiling are this
  bounded technical certification envelope, not scientific factors. The ceiling
  allows K=55 optimizer qualification but rejects 6000.
- Execution-view replay multiplier one prevents duplicate parent/child scaling:
  capacity is already resolved. Zero cleanup delay removes teardown sleep only.
- Class-specific read-only snapshots inspect state for regression assertions;
  they do not select policies or provide a policy-class registry.

### Capability holds and boundaries

History-dependent/adaptive and online strategies HOLD on the immutable-mask
path; none are dropped or relabeled. Static Markov and injected strategies use
the same interface. Dynamic/stochastic allocators and dynamic context transitions
HOLD until their required interfaces exist. Batch policies without a passive
trace contract HOLD; the hybrid contract currently qualifies hybrid mode only.
These are capability limits, not scientific-axis decisions. No approved
scientific scenario subset is selected here.

The recorded environment exposes the supplied mask through its environment-info
interface, rather than incorrectly reporting no attack. Resolved config records
include class source hashes (including injected classes), parameters/defaults,
allocator, replay, physics, profiles, seeds and required cells. Existing legacy
persistence is unchanged; immutable execution requires `persistence=False` and
rejects overwrite. Versioned identity prevents reuse of pre-repair bundles.

## E–F: verification and evaluation

Evaluation criterion: configuration extensibility without campaign source edits.
Tests cover injected scenario and policy, a new generator scale, replay/horizon/
resource/physics mutations, full-cell completion, capability holds, exact primary
regression and logging/RNG/model-state noninterference.

### Changed files and purpose (framework-relative)

| File | Purpose |
|---|---|
| `daqr/config/experiment_config.py` | strict canonical scenario resolution; opt-in persistence-disabled mode; no empty-axis fallback |
| `daqr/config/execution_contract.py` | required execution settings, resolved axes/metadata/capacity and complete required-cell list |
| `daqr/core/attack_strategy.py` | strategy capabilities and shared factory registry |
| `daqr/core/qubit_allocator.py` | static/stochastic/dynamic/history capabilities |
| `daqr/core/recorded_environment.py` | immutable supplied-mask environment interface |
| `daqr/core/primary_routes.py` | require explicit success factor; legacy fixture retained |
| `daqr/algorithms/base_bandit.py` | Oracle privilege metadata |
| `daqr/algorithms/neural_bandits.py` | passive trace contract, existing numerical floor, actual applied route-update logging |
| `daqr/campaigns/medium_spec.py` | catalog/mask/seed consume config; experimental presets removed |
| `daqr/campaigns/medium_runner.py` | canonical registry/config execution and manifest; remove campaign model config/default CLI |
| `daqr/campaigns/medium_trace.py` | capability-based logging/validation, weighted update and complete-scale coverage |
| `tests/medium_fixtures.py` | explicit technical config fixtures, never science presets |
| `tests/test_medium_catalog.py` | catalog/seed/mask regressions consume fixture config |
| `tests/test_medium_preflight.py` | passive/identity/retry regressions consume fixture config |
| `tests/test_medium_architecture.py` | extensibility, mutation, fail-closed, applied-update and full-cell tests |
| `tests/runtime_primary_k55.py` | technical K=55 optimizer cost fixture |
| `docs/guides/MEDIUM_SCALE_EXECUTION_PREPARATION.md` | reconcile fixed-scenario/unit wording |
| `docs/guides/MEDIUM_SCALE_PREFLIGHT_2026-09-26.md` | mark old receipt historical and superseded |
| `docs/guides/MEDIUM_ARCHITECTURE_REPAIR_2026-09-27.md` | requirements/design/audit/evidence handoff |
| `docs/guides/MEDIUM_ARCHITECTURE_K55_TECHNICAL_RECEIPT.json` | deliberately retained config/source/runtime/optimizer cost receipt; not model state or scientific outcomes |

The reviewed September 27 public correction is at QuantumFaultTolerant
`0bcc913` in `updates/MEDIUM_SCALE_PREPARATION_2026-09-26.md`,
`updates/REVIEWER_C_SCALE_CLAIM_DECISION_RECORD.md` and `updates/FEEDBACK_TASKS.md`.
Those records remain unchanged. Manuscript/Overleaf were not edited.

### Final test receipts

Implementation commit: `03604df30d1fb3cb345ece8b7bfeef5b2cbaabfe`.

All commands were run from the isolated worktree's `Dynamic_Routing_Eval_Framework`.
Qualified executable: `/Users/pitergarcia/DataScience/Semester4/GA-Work/.quantum/bin/python`.
Every test command used this exact environment prefix:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR=/tmp/quantum-architecture-sEF28W/mpl
```

Exact pytest arguments (after that executable):

```sh
-B -m pytest -p no:cacheprovider tests/test_medium_architecture.py -q --basetemp=/tmp/quantum-architecture-sEF28W/architecture-certified
-B -m pytest -p no:cacheprovider tests/test_medium_architecture.py tests/test_primary_routes.py tests/test_medium_catalog.py tests/test_medium_preflight.py tests/test_environment_contexts.py tests/test_resume_behavior.py tests/test_runner_resume_compare.py tests/test_allocator_runner_cleanup.py tests/test_registry_update_on_save.py tests/test_drive_state_offload.py -q --basetemp=/tmp/quantum-architecture-sEF28W/required-certified --junitxml=/tmp/quantum-architecture-sEF28W/required-certified.xml
-B -m pytest -p no:cacheprovider tests tools/tests/test_state_naming_and_resume.py -q --tb=no --basetemp=/tmp/quantum-architecture-sEF28W/certified --junitxml=/tmp/quantum-architecture-sEF28W/certified.xml
```

| Receipt | Result | Time |
|---|---|---:|
| Architecture/extensibility | **26 passed**, 0 failed | 12.75 s |
| Required suite | **98 passed**, 0 failed, 0 skipped | 59.71 s |
| Broader suite | **115 passed, 4 failed**, 0 skipped | 62.86 s |

The same four known failures are the only broad-suite failures:

1. `tests/test_local_backup_manager_pattern_drive_ops.py::TestLocalBackupManagerPatternDriveOps::test_standalone_migrate_files_by_pattern_deletes_verified_files_across_dates`
2. `tests/test_local_backup_manager_pattern_drive_ops.py::TestLocalBackupManagerPatternDriveOps::test_standalone_migrate_files_by_pattern_reports_summary_status`
3. `tests/test_local_backup_manager_pattern_drive_ops.py::TestLocalBackupManagerPatternDriveOps::test_standalone_migrate_files_by_pattern_runs_in_parallel_and_deletes_verified_local`
4. `tools/tests/test_state_naming_and_resume.py::test_expected_keys_no_qubit_suffix_for_random_runtime`

The first three mocks omit the existing `workers` parameter. The fourth fixture
uses `__new__` without `backup_registry`; its failing `generate_expected_keys`
function is unchanged. No fifth/new/campaign failure occurred. No tests were
xfail-marked, skipped, or altered to hide these failures. `git diff --check` passed.
The original four-route exact fixture and six explicit fixture policy/scenario
logging OFF/ON cases remain passing, including optimizer/RNG equality.

### K=55 cost qualification

**TECHNICAL COST BENCHMARK — NOT SCIENTIFIC EVIDENCE.**
Exact invocation uses the same environment prefix plus `PYTHONPATH=.` and
`python -B tests/runtime_primary_k55.py` with the qualified executable above.
[Machine-readable receipt](MEDIUM_ARCHITECTURE_K55_TECHNICAL_RECEIPT.json) is an
intentional technical evidence artifact, not a scientific result dataset.

At committed implementation `03604df30d1fb3cb345ece8b7bfeef5b2cbaabfe`, imported
source diff hash is the empty SHA-256. The explicit technical configuration
uses four generated routes, 55 allocations on each, 256 frames, one configured
hybrid policy and one configured baseline scenario; replay capacity resolves
to 12,000. This is a cost fixture, not a scientific scenario/policy subset.

| Route | K | T / replay size | Adam steps per parameter |
|---|---:|---:|---:|
| 0 | 55 | 53 | 0 (warm-up only) |
| 1 | 55 | 65 | 20 |
| 2 | 55 | 75 | 40 |
| 3 | 55 | 63 | 16 |

Configuration hash: `bb863272c8c62d32da9c83435e265385d8c48d7c41e4e4cc011fd6bcab67a6ea`.
Model-execution/snapshot wall time: **5.774626 s**.
Peak process RSS: **480247808 bytes** (macOS ru_maxrss; about 458.0 MiB).
Python 3.12.11, NumPy 1.26.4, Torch 2.8.0, SciPy 1.11.4, scikit-learn 1.3.2,
NetworkX 3.5, pmdarima 2.0.4, threadpoolctl 3.6.0; macOS arm64 CPU, one
Torch/BLAS thread, deterministic Torch. Import/startup/catalog/manifest time is
outside the timer; RSS includes libraries. Real K=55 optimizer state exists
on three routes. This validates a bounded cost path, not 6,000-frame feasibility,
convergence, performance ranking or manuscript evidence.

### Handoff boundary

**ARCHITECTURE REPAIR PASS — READY FOR INDEPENDENT SOL AUDIT.**
All experimental values now originate in canonical configuration or explicit
technical fixtures. Unsupported configured capabilities hold the execution.
The next step is independent Sol architecture/source audit of this PR revision,
not scientific execution. **NO SCIENTIFIC RUN EXECUTED.** Do not merge or launch.
Reproducible pytest/cache scratch artifacts are removed at handoff; the isolated
review worktree and this technical receipt are intentionally retained. The
original dirty execution checkout is not advanced over Piter's active work.
