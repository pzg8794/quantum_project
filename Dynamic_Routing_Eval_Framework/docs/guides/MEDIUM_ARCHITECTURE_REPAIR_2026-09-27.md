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


## Pass 2 — implementation and ownership audit

Implementation revision: `ae411fda35a21230747004158e7a1cf0716dbac8`.
The receipt/documentation commit that follows it does not change implementation.

```text
ExperimentConfiguration (explicit catalog_component / reward_component objects)
  → generic interface resolution + configured model / strategy registry
  → selected catalog, reward, scenario and policy components
  → capability-driven execution with passive events
  → resolved manifest
  → immutable attempt + completion (including realized trajectory hash)
```

| Sol finding | Ownership repair | Technical proof |
|---|---|---|
| Generic topology identity/schema | `LayeredPrimaryCatalog` owns family, profile schema, formulas and catalog validation; explicit config selects the object | `test_component_schemas_are_owned_by_selected_components[topology/both]`: independent two-hop component and width schema executes without generic edits |
| Generic physics schema | `PrimaryPayoff` owns factor validation and calculation; alternate reward objects own their own parameters | same test [physics/both]: constant-reward component with level schema executes |
| Static-only threat execution | `AttackStrategy.open_session` supplies common lifecycle; static realization remains immutable; causal callbacks receive past selections | static realization tests, injected causal/online probes, actual adaptive/online × three-policy fixtures |
| Adaptive random fallback | absent/short history raises; unsupported causal interface fails entire configuration before creating a bundle | missing-history, missing-interface and unsupported-policy tests; no stochastic substitution |
| Generic mode requirement | `QuantumModel` family validates its mode; generic resolver validates registry/interface only | independent `ModeFreePolicy`, with action kwarg and no mode, resolves and executes |
| Campaign concrete-policy diagnostics | optional `diagnostic_snapshot` on component; no policy class imports/branches in runner | injected snapshot and no-snapshot policies; exact existing policy-state comparisons |

The strict path consumes validated catalog contexts/payoffs directly rather than
reconstructing every injected component through the primary-only environment.
The legacy `QuantumEnvironment` and `RecordedQuantumEnvironment` remain intact,
with their exact four-route/metadata/mask regression tests. Environment RNG is
not consumed by this direct catalog path, so its derived domain seed remains in
provenance but its actual seed is null. Topology/profile seeds are supplied to
the selected catalog component; constructor/state/code identities and parameters
are recorded. Queue expansion still cannot change the protocol root.

### Exact chronology and threat scope

1. At frame t, the scenario session holds precisely t completed route selections.
2. It passes an immutable tuple of those selections, private strategy state and
   private RNG to the strategy. No reward, policy state, current selection or
   future selection is supplied.
3. The strategy fixes availability for t. Policy-side availability is read-only;
   future causal rows are unrealized sentinels, never reported as observations.
4. Nonprivileged selectors use their existing contexts/past feedback. Oracle is
   explicitly privileged and computes its existing per-frame argmax from the
   current row, without precomputing nonexistent future masks.
5. Feedback and the existing policy update occur. Only then does the session
   append the selected route for t+1.

The initial empty history at t=0 is legitimate. Empty history at t>0 is rejected.
The configured adaptive component uses its trailing selection-frequency window.
The configured online component retains the existing response-delay gating,
most-recent-selection behavior, ten-frame burst writes and subsequent targeted
path overwrite behavior. Its name does not grant same-frame action access.
Both causal implementations match an independent transcription of their
pre-Pass-2 supplied-history arithmetic under a deterministic technical fixture.
The actual three policies also match exact frozen replay of their own realized
mask, including RNG/model state. This is not a counterfactual result.

**Implementation/scientific-definition reconciliation still required:** this
pass does not establish that Markov, Adaptive or OnlineAdaptive matches a
historical manuscript/study definition. Markov's attack rate initializes state;
its transition rule remains unchanged. Online burst carry-over/overwrite and
response-delay meanings need scientific interpretation before a scientific
configuration is approved. No historical audit or scientific redesign was done.

Reactive trajectories depend on the policy. Shared strategy seed does not imply
a common exogenous availability trajectory across policies. The manifest binds
scenario parameters, seed, policy, code and chronology, with a null pre-run
trajectory hash for causal scenarios. Completion binds the actual trajectory
hash and file hash; event joins retain run/attempt identity. Static trajectories
retain their pre-run hash. Partial failed trajectories remain failed, with -1
only denoting unrealized rows; they cannot validate as complete. No mid-frame
resume, favorable retry or best-attempt selection was introduced.

### Final hardcoding audit — complete PR relative to 47757380

Reviewed the full PR diff plus new component files; searched added source lines
and current generic/campaign files for concrete names, schema keys, scientific
numeric values, mode/type dispatch, fallback, policy/scenario lists and CLI choices.

| Classification | Matches and disposition |
|---|---|
| A — configurable choice removed from implementation ownership | topology identity/schema and ordered profile pool moved out of resolver/spec to selected catalog; physics schema/calculation to selected reward component; policy mode validation to model family; concrete snapshots to models; scenario support to lifecycle/capability contracts |
| A — canonical configuration ownership retained | models/scenarios/parameters, allocator, replay, horizon, resources, scale points and repeats resolve only from configuration; registry concrete class entries are valid component lookup, not campaign axis selection; existing constructor defaults remain in their canonical owner and are recorded |
| B — catalog component invariants | layered formulas nodes=4m+3/routes=3m+1; three-hop enumeration; middle-degree bound 3; stable ordered-route hashing/profile rank; all-node coverage; allocation conservation/weak-composition ordering; primary payoff's existing two-stage arithmetic |
| B — numerical/algorithm invariants | SHA-256, first-four-byte seed mapping, PCG64, finite/binary checks; EXP3 1e-12 floor; adaptive 0.9 rate ceiling and online ten-frame burst behavior preserved from existing algorithms, not new experimental knobs |
| B — execution/schema invariants | four event phases, two-part action contract, restart attempt limit, immutable file/hash checks, technical frame ceiling 512, unit thread qualification; static/history/online are lifecycle capabilities, not concrete strategy names |
| B — compatibility/schema identifiers | `primary-catalog-v2` retained as protocol schema token so this repair does not silently re-seed prior fixtures; it selects no component. Legacy four-route rates/order preserve compatibility only, never select medium experiment values |
| B — remaining type checks | generic mappings/tuples/integer checks, `ScenarioSession` lifecycle envelope and interruption exception handling; no scientific policy/strategy type dispatch in campaign |
| B — trace schema semantics | hybrid feedback-v2 labels and within-route NeuralUCB recipient describe an existing declared producer contract, not selection of a policy or scenario |
| C — technical fixture inputs | concrete policy/scenario IDs, .0625, 6000 replay anchor, 12000 resolved capacity, 9-qubit budget, selected scales, 55 actions and 256 cost frames appear in test inputs/receipts; no scientific CLI defaults exist |
| D — legacy outside bounded path | legacy concrete paper/testbed dispatch, constructor defaults, backup/cache/retry orchestration and legacy unknown-name fallback remain outside strict execution; strict scenario resolver rejects unknown names; directly used adaptive missing-history fallback was removed |

No campaign-owned policy/scenario tuple, numeric scenario count, fixed run total,
scale whitelist, concrete physics schema or topology-family selection remains.
Unsupported dynamic allocators/context transitions and undeclared batch trace
contracts continue to fail closed rather than silently redefine a configuration.
Those existing limits are not scientific validation or a new axis choice.

### Pass-2 files and purposes

All paths below are relative to `Dynamic_Routing_Eval_Framework/`.

| File | Purpose |
|---|---|
| `daqr/config/experiment_config.py` | explicit optional component selection; no implicit scientific component |
| `daqr/config/execution_contract.py` | generic component/policy/scenario validation and resolved component provenance |
| `daqr/core/catalog_components.py` | selected layered topology/catalog and primary reward implementations |
| `daqr/core/identity.py` | shared canonical JSON/hash primitive; components do not import campaign orchestration |
| `daqr/core/scenario_execution.py` | causal lifecycle, immutable history cutoff, read-only policy mask |
| `daqr/core/attack_strategy.py` | component-owned session behavior; preserve supplied-history algorithms; reject missing history |
| `daqr/algorithms/base_bandit.py` | family-owned validation/snapshot; causal Oracle frame preparation |
| `daqr/algorithms/neural_bandits.py` | trace-contract adapter, owned snapshot and session begin/observe hooks; learning arithmetic unchanged |
| `daqr/algorithms/predictive_bandits.py` | causal capability and owned diagnostic snapshot |
| `daqr/campaigns/medium_spec.py` | delegate catalog/reward work; derive scenario cardinality from actual catalog |
| `daqr/campaigns/medium_runner.py` | no concrete policy imports/dispatch; consume components and causal session |
| `daqr/campaigns/medium_trace.py` | component observation metadata; immutable causal trajectory completion binding |
| `tests/medium_fixtures.py` | explicitly select components in technical configuration |
| `tests/test_medium_architecture.py` | preserve fail-closed test with genuinely missing causal interface, not now-supported components |
| `tests/test_medium_architecture_pass2.py` | injected components/policies/scenarios; chronology; no fallback; equivalence and completeness |
| `docs/guides/MEDIUM_ARCHITECTURE_REPAIR_2026-09-27.md` | separate current Pass 2 from historical Pass 1; evidence and audit |
| `docs/guides/MEDIUM_SCALE_EXECUTION_PREPARATION.md` | current Pass-2 pointer without changing study choices |
| `docs/guides/MEDIUM_ARCHITECTURE_PASS2_K55_TECHNICAL_RECEIPT.json` | new cost receipt pinned to ae411fda; old receipt preserved |
| `docs/guides/MEDIUM_ARCHITECTURE_PASS2_TEST_RECEIPT.json` | exact commands, revision, test counts and known failure identities |

### K=55 technical qualification

Execution/config resolution changed materially, so the cost fixture was rerun
on clean implementation revision `ae411fda35a21230747004158e7a1cf0716dbac8`.
The old Pass-1 receipt is unchanged and remains historical.

- Explicit technical fixture only: 256 frames, four routes, 55 actions/route.
- Configuration hash: `049e07746f7894850d8cb4048febf6b3ed355bc181b4424731c7919e4c8cdf28`.
- T/replay sizes: 53, 65, 75, 63; capacity 12000 from fixture configuration.
- Optimizer steps: none, 20, 40, 16; four parameter states in each trained route.
- Wall time 5.897495625 seconds; peak RSS 480690176 bytes on this macOS runtime.
- Python/package/import hashes are in the new JSON receipt. This is cost and
  code-path evidence only, not a performance result or extrapolated campaign ETA.

### Pass-2 verification receipts and handoff

Final implementation tests on `ae411fda`:

| Suite | Result |
|---|---|
| Pass-2 architecture/extensibility | 23 passed (also independently rerun: 29.55 s) |
| Pass-1 architecture/extensibility | 26 passed, unchanged test count |
| Required combined medium/primary/regression | **121 passed**, 84.09 s |
| Broader tests + state-naming suite | **138 passed, exactly 4 known failures**, 87.17 s |
| Skips / xfails / new failures | **0 / 0 / 0** |
| Diff whitespace validation | passed |

The two former tests expecting *all* adaptive/online scenarios to HOLD initially
failed because those components are now supported (77 passed / 2 failed on the
first development run). They now inject components genuinely missing the causal
interface and retain the same fail-closed/no-output assertions. No test was
skipped, xfailed, deleted or changed to conceal a regression. Real adaptive/
online success, causality and equivalence have additional positive tests.

The four unchanged broader failures are:

1. `test_standalone_migrate_files_by_pattern_deletes_verified_files_across_dates`
2. `test_standalone_migrate_files_by_pattern_reports_summary_status`
3. `test_standalone_migrate_files_by_pattern_runs_in_parallel_and_deletes_verified_local`
4. `test_expected_keys_no_qubit_suffix_for_random_runtime`

The first three legacy fake managers reject the existing `workers` kwarg.
The fourth legacy `__new__` fixture lacks `backup_registry`. None was modified.

Exact final commands (framework root; task temp paths recorded for reproduction):

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR=/tmp/quantum-pass2-G4NRob/mpl /Users/pitergarcia/DataScience/Semester4/GA-Work/.quantum/bin/python -B -m pytest -p no:cacheprovider tests/test_medium_architecture_pass2.py tests/test_medium_architecture.py tests/test_primary_routes.py tests/test_medium_catalog.py tests/test_medium_preflight.py tests/test_environment_contexts.py tests/test_resume_behavior.py tests/test_runner_resume_compare.py tests/test_allocator_runner_cleanup.py tests/test_registry_update_on_save.py tests/test_drive_state_offload.py -q --tb=short --basetemp=/tmp/quantum-pass2-G4NRob/required-final --junitxml=/tmp/quantum-pass2-G4NRob/required-final.xml
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR=/tmp/quantum-pass2-G4NRob/mpl /Users/pitergarcia/DataScience/Semester4/GA-Work/.quantum/bin/python -B -m pytest -p no:cacheprovider tests tools/tests/test_state_naming_and_resume.py -q --tb=short --basetemp=/tmp/quantum-pass2-G4NRob/broad-final --junitxml=/tmp/quantum-pass2-G4NRob/broad-final.xml
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR=/tmp/quantum-pass2-G4NRob/mpl /Users/pitergarcia/DataScience/Semester4/GA-Work/.quantum/bin/python -B tests/runtime_primary_k55.py
git diff --check
```

See the retained [test receipt](MEDIUM_ARCHITECTURE_PASS2_TEST_RECEIPT.json)
and [new K=55 receipt](MEDIUM_ARCHITECTURE_PASS2_K55_TECHNICAL_RECEIPT.json).
The earlier [Pass-1 K=55 receipt](MEDIUM_ARCHITECTURE_K55_TECHNICAL_RECEIPT.json)
was not overwritten. Temporary test bundles/caches/XML are task-scoped and
removed after these receipts are retained; no scientific raw evidence exists.

No manuscript, Overleaf, course scope, scientific result or scientific contract
was changed. No merge. The original protected checkout remains at `854c4ab3`
with its pre-existing work; the detached review worktree is intentionally retained.
The remote PR branch is updated only by non-forced fast-forward push.

**NO SCIENTIFIC RUN EXECUTED**

**ARCHITECTURE REPAIR PASS 2 — READY FOR INDEPENDENT SOL RE-AUDIT**

Next action is Sol's independent architecture/source re-audit of PR #2, not
F-09 execution. Scientific threat-definition reconciliation and Piter's
substantial-execution approval remain separate gates.
## Pass 1 historical record — requirements, system understanding, design

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
