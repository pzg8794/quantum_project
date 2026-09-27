# Q-02 scenario code/config inspection

**Checkpoint:** PR #2 head `d97dbde30241cd04b561cdd187a3b622a35b7592`
**Branch:** `codex/mq-q02-code-inspection`
**Scope:** read-only inspection of production code/config and existing tests; this file is the only repository modification.
**Boundary:** bounded technical tests only; no F-09 scientific run, production-code change, architecture change, manuscript edit, or test edit.

## Verdict

**Q-02 is not scientifically closed.** The strict PR #2 path correctly resolves every configured scenario, supports causal history without same-frame action lookahead, derives deterministic threat seeds, and records substantial configuration/trajectory provenance. However, the three implementation semantics do not collectively implement the proposed F-08 study definitions:

- `Markov` is a per-route two-state symmetric toggle, not the proposed 25% four-state process.
- `Adaptive` has compatible history-frequency machinery, but its default window is 100 rather than 50 and no scientific configuration freezes the missing exact targeting parameters.
- `OnlineAdaptive` is a response-delay/global-burst/last-route process; it has no `gamma=0.97` or softmax targeting implementation.
- `Adaptive` and `OnlineAdaptive` are policy-reactive, so a shared threat seed does not produce the contract's shared exogenous threat trajectory across policies.

These are scientific-semantic blockers, not failures of the bounded causal execution tests.

## Authority inspected

- Board Q-02 requires exact reconciliation of `Markov`, `Adaptive`, and `OnlineAdaptive`, freezes PR #2 architecture, and stops before F-09: `/tmp/Fall-2026-Semester-Master-Plan-MQ/CAMPAIGNS/2026-09-26-MEDIUM-SCALE/SDLC-EXECUTION-BOARD-2026-09-27.md:143`, `:144`, `:215`, `:224`.
- Proposed contract requires the complete approved configured scenario axis, resolved IDs/parameters in the launch manifest, paired seeds, and no silent drop or substitution: `/tmp/Fall-2026-Semester-Master-Plan-MQ/CAMPAIGNS/2026-09-26-MEDIUM-SCALE/PROPOSED-SCIENTIFIC-CONTRACT.md:24`, `:26`, `:31`, `:33`, `:37`, `:39`, `:102`.
- Proposed F-08 study-design semantics are: `Markov` = 25% four-state structured disruption; `Adaptive` = 25% high-usage targeting over `w=50`; `OnlineAdaptive` = 25% adaptive targeting with `gamma=0.97` and softmax selection: `/Users/pitergarcia/DataScience/Semester4/GA-Work/GA Papers/QuantumFaultTolerant/ICNP_VENUE_PREP/STUDY_DESIGN_VALIDATED_STAGING.tex:147`, `:148`, `:149`, `:150`, `:151`.
- The manuscript taxonomy further distinguishes temporally correlated, route-history-informed, and continually reactive availability processes while stating that exact process parameters must come from data-producing provenance: `/Users/pitergarcia/DataScience/Semester4/GA-Work/GA Papers/QuantumFaultTolerant/ICNP_2026_venue_draft.tex:318`, `:334`, `:335`, `:336`, `:340`.

## Exact selection and execution path

1. `ExperimentConfiguration.test_scenarios` is the scenario-axis source. The constructor's legacy default contains only `stochastic` and `none`; no medium scientific preset exists: `daqr/config/experiment_config.py:27`, `:55`, `:59`, `:67`, `:96`, `:97`.
2. The strict resolver iterates every configured key, calls `resolve_attack_strategy`, validates the lifecycle, and records class/source hash, realized constructor parameters, capability, and raw configured spec. It derives every scale/block/scenario/policy cell without filtering: `daqr/config/execution_contract.py:38`, `:54`, `:65`, `:66`, `:67`, `:72`, `:73`, `:74`, `:114`, `:122`.
3. A structured spec must be exactly `{"strategy": ..., "parameters": ...}` and directly constructs the registry class with those parameters. A string description instead uses legacy scalar construction through `set_attack_strategy`: `daqr/config/experiment_config.py:1099`, `:1104`, `:1105`, `:1111`, `:1115`, `:1117`, `:1120`.
4. The standalone `create_attack_strategy` helper is not called by the medium path (or elsewhere in executable source); the strict path uses `resolve_attack_strategy` and `STRATEGY_REGISTRY`: `daqr/core/attack_strategy.py:282`, `:288`, `:304`, `:307`, `:309`.
5. `build_scenario` resolves the strategy, derives a scenario-key-qualified threat seed, creates `Generator(PCG64(seed))`, and opens a `ScenarioSession`: `daqr/campaigns/medium_spec.py:92`, `:94`, `:95`, `:96`, `:97`.
6. Static strategies are fully realized at session construction. Causal strategies call `availability_at(t, history[0:t], state, rng, ...)` before policy selection and append the selected route only after outcome/update: `daqr/core/scenario_execution.py:13`, `:18`, `:19`, `:21`, `:41`, `:44`, `:45`, `:46`, `:51`, `:54`, `:55`; `daqr/campaigns/medium_runner.py:161`, `:163`, `:169`, `:180`, `:184`.
7. The strict runner rejects a policy that lacks causal-scenario support and never substitutes a random mask: `daqr/campaigns/medium_runner.py:144`, `:146`, `:147`, `:148`, `:149`; `daqr/config/execution_contract.py:95`, `:96`, `:97`.

## Current scenario semantics

### Markov

**Parameters and overrides**

- Constructor defaults are `attack_rate=0.25`, `p_stay=0.7`; both can be overridden by a structured scenario spec: `daqr/core/attack_strategy.py:148`, `:149`, `:150`, `:152`; `daqr/config/experiment_config.py:1115`, `:1120`.
- A string-valued scenario does **not** use `ExperimentConfiguration.attack_rate`; it passes `attack_intensity` as `MarkovAttack.attack_rate` and leaves `p_stay=0.7`. The configuration defaults are `attack_rate=0.25` and `attack_intensity=1.0`: `daqr/config/experiment_config.py:27`, `:59`, `:67`, `:1144`.

**State and behavior**

- Each route has one local Boolean `is_attacked`; routes evolve independently: `daqr/core/attack_strategy.py:157`, `:159`, `:160`.
- For every frame, the implementation first stays with probability `p_stay` or toggles with probability `1-p_stay`, then emits availability 0/1: `daqr/core/attack_strategy.py:162`, `:163`, `:166`, `:168`.
- Therefore `attack_rate` initializes an unobserved pre-transition state. The first emitted attacked probability is `a*p_stay + (1-a)*(1-p_stay)` (0.40 for `a=.25,p_stay=.7`), and the symmetric two-state chain tends to 0.50 attacked when it mixes. `attack_rate` is not a 25% stationary disruption rate.
- It uses neither route-selection history nor current action. Its complete mask is precomputed before policy construction: `daqr/core/attack_strategy.py:146`, `:154`; `daqr/core/scenario_execution.py:21`, `:28`.

**Configuration-driven status:** partially/fully configuration-driven only under a structured spec. The legacy string path exposes the base rate indirectly through `attack_intensity` and retains the constructor transition default.

### Adaptive

**Parameters and overrides**

- Constructor defaults are `attack_rate=0.25`, `adaptation_window=100`, and `adaptation_strength=0.5`; a structured spec can override all three: `daqr/core/attack_strategy.py:185`, `:186`, `:187`, `:188`, `:192`; `daqr/config/experiment_config.py:1115`, `:1120`.
- A string-valued scenario passes `attack_intensity` as `attack_rate` and cannot carry window/strength, so it retains 100/0.5: `daqr/config/experiment_config.py:1145`.

**State and behavior**

- At frame `t`, the strategy requires exactly `t` completed selections and slices only the trailing configured window: `daqr/core/attack_strategy.py:194`, `:195`, `:197`.
- At `t=0`, every route is independently attacked at the base rate: `daqr/core/attack_strategy.py:198`, `:199`.
- Later, it computes each route's selection share in the trailing window and independently attacks route `p` with probability `min(attack_rate + adaptation_strength*share[p], 0.9)`: `daqr/core/attack_strategy.py:202`, `:203`, `:204`, `:205`.
- It has no additional persistent strategy state; `ScenarioSession.history` is the evolving state. It never receives the current action, reward, policy internals, or future selections: `daqr/core/scenario_execution.py:18`, `:45`, `:54`.
- Missing/short history raises rather than falling back to random behavior: `daqr/core/attack_strategy.py:195`, `:215`, `:216`.

**Configuration-driven status:** the executable mechanism is configuration-driven and can accept `adaptation_window=50`, but no scientific configuration at this PR head freezes that value, the strength, or the interpretation of “25%.” The only medium fixture contains `NoAttack` and `RandomAttack`: `tests/medium_fixtures.py:10`, `:14`, `:15`, `:24`.

### OnlineAdaptive

**Parameters and overrides**

- Constructor defaults are `attack_rate=0.25`, `response_delay=5`, and `burst_probability=0.3`; a structured spec can override only those constructor parameters: `daqr/core/attack_strategy.py:233`, `:234`, `:235`, `:236`, `:240`.
- A string-valued scenario passes `attack_intensity` as `attack_rate` and retains delay/burst defaults: `daqr/config/experiment_config.py:1146`.
- There is no constructor/config field for `gamma` or softmax selection. Supplying the proposed fields through the strict constructor would raise an unexpected-keyword `TypeError` at `daqr/config/experiment_config.py:1120`.

**State and behavior**

- The only private persistent state is `state["burst_until"]`: `daqr/core/attack_strategy.py:247`, `:249`.
- Every frame first draws a global burst. On success it sets `burst_until=min(frame+10,frames)` and returns all routes unavailable: `daqr/core/attack_strategy.py:248`, `:249`, `:250`.
- Without a new burst, an active prior burst initializes all routes unavailable. Once `frame >= response_delay`, the implementation looks at prior history but targets only the most recently selected route, not a softmax distribution or frequency vector: `daqr/core/attack_strategy.py:251`, `:252`, `:254`, `:257`.
- The targeted assignment can overwrite that route's pending burst zero; then every currently available route receives another independent base-rate attack draw: `daqr/core/attack_strategy.py:245`, `:246`, `:247`, `:257`, `:258`, `:260`.
- It uses prior selections only. The current frame's route is appended after update, so “online” does not mean same-frame action access: `daqr/core/scenario_execution.py:41`, `:45`, `:51`, `:54`.
- Missing/short history raises; there is no random fallback: `daqr/core/attack_strategy.py:243`, `:271`, `:272`.

**Configuration-driven status:** its implemented delay/burst process is configuration-driven, but the proposed `gamma=0.97`/softmax process is not implemented or configurable.

## Deterministic seeds and policy coupling

- The protocol root hashes namespace, base seed, catalog version, and seed-rule version. Domain seeds use the first four SHA-256 bytes, big-endian: `daqr/campaigns/medium_spec.py:18`, `:23`, `:24`, `:27`, `:29`, `:30`, `:34`.
- Threat seed qualification uses the exact configured scenario ID and excludes policy; policy seed qualification uses policy ID plus its registry offset: `daqr/campaigns/medium_spec.py:33`, `:38`, `:39`, `:40`.
- All three strategies consume `Generator(PCG64(threat_seed))`; the resolved seed manifest records the actual threat seed and RNG name: `daqr/campaigns/medium_spec.py:41`, `:43`, `:49`, `:96`.
- `Markov` is static and policy-independent, so equal block/scale/scenario IDs yield the same complete mask across policies.
- `Adaptive` and `OnlineAdaptive` start from the same threat seed across policies, but their masks depend on each policy's prior route selections. Equal seed is therefore reproducible coupling, not an equal trajectory. Different policy histories can also alter OnlineAdaptive's subsequent RNG consumption because conditional draws depend on the current row.
- Queue expansion leaves the protocol root and domain seeds stable, as covered by `tests/test_medium_architecture.py:136`-`:144`. However, `prepare_manifest` hashes the full resolved matrix and `required_run_count` into each per-run `config_hash`, so adding configured scenarios changes existing run IDs despite unchanged seeds: `daqr/campaigns/medium_runner.py:70`, `:72`, `:73`, `:84`.

## Trace and provenance emitted

- The manifest records the selected scenario ID, resolved class/source hash, realized constructor parameters/defaults, raw configured spec, capability, chronology, trajectory kind, all seed records, code/import hashes, and policy/config identity: `daqr/config/execution_contract.py:72`-`:74`; `daqr/campaigns/medium_runner.py:70`-`:83`.
- Static `Markov` receives a pre-run trajectory hash in identity. Causal scenarios use `threat_trajectory_hash=null` before execution and are labeled `policy-reactive-causal`: `daqr/campaigns/medium_runner.py:79`, `:80`, `:81`.
- Each event records protocol/run/attempt/block/topology/route identity, threat ID, threat/policy/environment seeds, and seed-identity hash: `daqr/campaigns/medium_trace.py:44`-`:60`.
- `PRESELECTION` records context provenance and `history_cutoff_frame=t-1` but no availability. `DECISION` records route/action and any supplied route probability. `OUTCOME` records selected-route availability and continuous/sampled feedback. `UPDATE` records the actual update channel: `daqr/campaigns/medium_trace.py:71`-`:83`, `:85`-`:105`, `:107`-`:128`.
- The full realized availability matrix is written separately. Completion records its hash and all file hashes; validation recomputes the mask and event joins: `daqr/campaigns/medium_trace.py:190`-`:197`, `:209`-`:224`, `:251`-`:269`, `:273`-`:337`.
- Scenario-internal state (`is_attacked`, selection counts, `burst_until`) is not emitted per frame. Its effects are preserved in the realized availability matrix, while reconstruction additionally relies on the recorded seed, parameters, history, source hash, and chronology.

## Discrepancy classification

### BLOCKER

1. **Markov process mismatch.** The proposed 25% four-state structured disruption cannot be represented by the current independent two-state symmetric toggle; because its `attack_rate` only initializes a pre-transition state and the chain tends toward 50% disruption, executing it would mislabel the scientific condition.
2. **Adaptive contract is not frozen.** The proposed `w=50` condition is not present in any scientific configuration, while the constructor/string path defaults to `w=100` and leaves strength/cap semantics unstated; because trajectory behavior changes with those values, Q-02 cannot accept “Adaptive” by name alone.
3. **OnlineAdaptive process mismatch.** The proposed `gamma=0.97` softmax targeting has no implementation/config fields and current behavior instead uses delay, global bursts, last-route targeting, and independent base attacks; because the intended parameters cannot be resolved through the strict constructor, the approved scenario cannot execute faithfully.
4. **Shared-trajectory contract conflicts with causal threats.** The proposed paired-block language requires one threat trajectory shared by every policy, but Adaptive/OnlineAdaptive availability is a function of each policy's past routes; because different histories produce different masks even under one threat seed, the pairing semantics must be adjudicated before F-09.
5. **No scientific scenario configuration exists at this head.** Production/config source contains no executable `w=50`, `gamma=0.97`, softmax, or complete five-scenario medium configuration, and the technical fixture intentionally includes only NoAttack/RandomAttack; because the strict runner executes exactly what it is given, source capability tests do not establish the approved F-08 axis.
6. **Legacy string resolution can silently produce the wrong severity.** Markov/Adaptive/OnlineAdaptive string specs use `attack_intensity` (default 1.0) as `attack_rate` and ignore the separate `attack_rate=0.25`; because a description-only canonical config can therefore resolve to 100% base rate, scientific launch must require explicit structured parameters or an independently verified scalar configuration.
7. **Per-run identity includes queue-level configuration.** The run `config_hash` includes all resolved scenarios/cells and required count, contrary to the proposed exclusion of campaign queue from completed-run identity; because adding a scenario changes prior run IDs despite invariant seeds, Q-03 identity freezing cannot yet satisfy the proposed contract.

### DEBT

1. **Causal event rows retain a null trajectory hash.** Completion and `availability.json` bind the realized trajectory, but every immutable causal event keeps the pre-run null `threat_trajectory_hash`; because row-level consumers must join through run/attempt completion to obtain the realized hash, this is provenance friction rather than loss of the raw trajectory.
2. **Scenario-name aliases change threat seeds.** The exact configured scenario key is the seed qualifier, so renaming an otherwise identical scenario changes its mask; because the manifest records the ID and parameters this is reproducible, but the approved IDs must be frozen explicitly.

### OPTIONAL

1. **Internal-state diagnostics are absent.** Per-frame Markov state, adaptive frequency vector, and OnlineAdaptive `burst_until` are not traced; because complete availability, decisions, parameters, seed, chronology, and source hashes are retained, state snapshots would aid diagnosis but are not required to reproduce the configured implementation.

## Bounded verification

Repository precheck:

```text
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short --branch
git remote -v
git rev-list --left-right --count @{upstream}...HEAD
```

Result before inspection: root `/Users/pitergarcia/DataScience/Semester4/Quantum-MQ-Q02-inspection`; branch `codex/mq-q02-code-inspection`; head `d97dbde30241cd04b561cdd187a3b622a35b7592`; clean; upstream `origin/codex/medium-scale-preflight`; divergence `0 0`; origin `https://github.com/pzg8794/quantum_project.git`.

Exact bounded test command:

```text
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR="$TEST_TMP/mpl" /Users/pitergarcia/DataScience/Semester4/GA-Work/.quantum/bin/python -B -m pytest -p no:cacheprovider tests/test_medium_architecture.py::test_scenario_extensibility_and_complete_cell_counts tests/test_medium_architecture.py::test_existing_description_scenarios_use_canonical_scalar_settings tests/test_medium_architecture.py::test_seed_root_independent_of_queue_expansion tests/test_medium_architecture_pass2.py::test_injected_causal_scenario_chronology tests/test_medium_architecture_pass2.py::test_static_session_matches_original_realization tests/test_medium_architecture_pass2.py::test_causal_session_matches_existing_supplied_history_algorithm tests/test_medium_architecture_pass2.py::test_missing_history_is_never_random_fallback tests/test_medium_architecture_pass2.py::test_real_causal_policies_logging_exact_equivalence tests/test_medium_architecture_pass2.py::test_complete_matrix_includes_causal_scenarios_and_blocks tests/test_medium_architecture_pass2.py::test_causal_unsupported_policy_fails_entire_matrix -q --tb=short --basetemp="$TEST_TMP/pytest"
```

Result: `20 passed in 60.80s` (Python 3.12.11). The selected tests cover strict scenario resolution/full-cell expansion, legacy scalar resolution, queue-independent seed root, static Markov determinism, exact Adaptive/OnlineAdaptive supplied-history arithmetic, causal chronology, no missing-history fallback, all 2 causal scenarios × 3 approved technical policies with 8-frame trace/replay equivalence, matrix completeness, and fail-closed unsupported-policy behavior. These are technical regression/preflight results, not validation of the historical/proposed scientific definitions.

Inspection-only search:

```text
find Dynamic_Routing_Eval_Framework -type f \( -name '*.py' -o -name '*.json' -o -name '*.yaml' -o -name '*.yml' \) ! -path '*/config/framework_state/*' ! -path '*/config/model_state/*' ! -path '*/config/quantum_logs/*' ! -path '*/tests/*' -print0 | xargs -0 grep -nE '0\.97|adaptation_window.{0,20}50|scenarios.{0,80}(markov|adaptive|onlineadaptive)|onlineadaptive.{0,80}gamma'
```

Result: no matches in executable/config source. This does not search or alter manuscript/history files; the authoritative study-design values were read separately from the pinned local source cited above.

## Checkpoint conclusion

- Technical scenario selection/lifecycle/trace tests: **PASS (20/20)**.
- Configuration completeness for proposed F-08: **BLOCKED**.
- `Markov` scientific semantic match: **BLOCKED**.
- `Adaptive` scientific semantic match: **BLOCKED pending exact structured configuration/adjudication**.
- `OnlineAdaptive` scientific semantic match: **BLOCKED**.
- F-09 readiness: **NO — no scientific run authorized or performed**.
