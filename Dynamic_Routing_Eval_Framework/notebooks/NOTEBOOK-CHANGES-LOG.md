# Notebook Changes Log

This log records **surgical notebook changes** (issues encountered, what was changed, and why), to avoid accidental “extra” modifications.

## 2026-03-01

### Paper 7 — Standardized run configuration notebook created
- **New file:** `H-MABs_Eval-Testbed-Paper7-StandardizedRunConfig.ipynb` (copied from `H-MABs_Eval-Testbed-Paper7.ipynb`)
- **Goal:** run Paper 7 testbed under our standard run configuration (base `4000` frames, `2000` step, runs `3` and `5`).
- **Change (run config only):** replaced the dev settings (`50` frames / `50` step / `5` experiments / runs `[5]`) with:
  - `current_frames = FRAMEWORK_CONFIG['base_frames']`
  - `frame_step = FRAMEWORK_CONFIG['frame_step']`
  - `current_experiments = FRAMEWORK_CONFIG['exp_num']`
  - `RUNS = [3, 5]`

### Notebook KeyError fix — `FRAMEWORK_CONFIG['intensity']`
- **Issue:** some cells referenced `FRAMEWORK_CONFIG['intensity']` but intensity is stored in `FRAMEWORK_CONFIG['env_attrs']['intensity']`.
- **Fix:** added a compatibility alias immediately after `FRAMEWORK_CONFIG` is defined:
  - `FRAMEWORK_CONFIG['intensity'] = FRAMEWORK_CONFIG['env_attrs']['intensity']`
- **Applied in:** `H-MABs_Eval-Testbed-Paper2.ipynb`, `H-MABs_Eval-Testbed-Paper2-StandardizedRunConfig.ipynb`, `H-MABs_Eval-Testbed-Paper7.ipynb`, `H-MABs_Eval-Testbed-Paper12.ipynb`.

### Notebook NameError fix — `test_scenarios`
- **Issue:** evaluator/runner cells call `scenarios=test_scenarios` but `test_scenarios` was never defined in Paper 7 / Paper 12 notebooks.
- **Fix:** added a single shared `test_scenarios = {...}` dict right after `FRAMEWORK_CONFIG` is defined (in the same config cell).
- **Applied in:** `H-MABs_Eval-Testbed-Paper7.ipynb`, `H-MABs_Eval-Testbed-Paper7-StandardizedRunConfig.ipynb`, `H-MABs_Eval-Testbed-Paper12.ipynb`.

### Paper 7 — Fix path-count mismatch (prevents GNeuralUCB index error)
- **Issue:** Paper 7 config had `num_paths=4`, but the Paper 7 path generator used `k=5` and `n_qisps=3`, which yields `5 * C(3,2) = 15` paths/contexts/rewards. Models infer `num_groups = len(reward_list)`, so they could select a path index ≥4 while the allocator/attack arrays are sized for 4 paths → runtime errors like `index 4 is out of bounds for axis 0 with size 4`.
- **Fix (settings only):** set `paper7.k=4` and `paper7.n_qisps=2` so the generator produces exactly 4 paths (matching `num_paths=4`).
- **Applied in:** `H-MABs_Eval-Testbed-Paper7.ipynb`, `H-MABs_Eval-Testbed-Paper7-StandardizedRunConfig.ipynb`.

### Paper 12 — Standardized run configuration notebook created
- **New file:** `H-MABs_Eval-Testbed-Paper12-StandardizedRunConfig.ipynb` (copied from `H-MABs_Eval-Testbed-Paper12.ipynb`)
- **Goal:** run Paper 12 testbed under our standard run configuration (base `4000` frames, `2000` step, runs `3` and `5`).
- **Change (run config only):** replaced the QuARC dev settings (e.g., `1500` frames / `500` step / `1` experiment / runs `[5]`) with:
  - `current_frames = FRAMEWORK_CONFIG['base_frames']`
  - `frame_step = FRAMEWORK_CONFIG['frame_step']`
  - `current_experiments = FRAMEWORK_CONFIG['exp_num']`
  - `RUNS = [3, 5]`

## 2026-03-02

### Paper 8 — Standardized run configuration notebook created
- **New file:** `H-MABs_Eval-Testbed-Paper8-StandardizedRunConfig.ipynb`
- **Goal:** run Paper 8 testbed under our standard run configuration (base `4000` frames, `2000` step, runs `3` and `5`) using the same `AllocatorRunner + get_physics_params(...)` flow as the other testbeds.
- **Design constraint:** Paper 8 components come from core modules (`Paper8RandomConnectedTopologyGenerator`, `Paper8NoiseModel`, `Paper8FidelityCalculator`); notebook wiring only (no framework code changes).
- **Default safety:** `SMOKE_TEST=True` (runs `[3]`, scales `[1]`) to avoid accidental long runs; set `SMOKE_TEST=False` for the full standardized sweep.

### Paper 8 — Paper-config-first notebook created (run this before standardized sweep)
- **New file:** `H-MABs_Eval-Testbed-Paper8-PaperRunConfig.ipynb`
- **Goal:** run Paper 8 testbed using the paper’s own topology/physics settings first, then run the standardized sweep later.
- **Upstream defaults captured in config cell:** `num_nodes=20`, `connection_prob=0.001`, `fidelity_range=(0.65,0.99)`, `rate_range=(0.75,1.0)`, `pur_round_range=(0,3)`, `swap_success_range=(0.23,0.8)`, `base_seed=10`.
- **Framework run settings (minimal first pass):** `BASE_FRAMES=1000`, `FRAME_STEP=1000`, `RUNS=[1]`, `SCALES=[1]`, `ALLOCATORS=['Default']`.
- **Refactor (flow only):** restructured the notebook into the same sectioned layout used by the other testbed notebooks (title → environment setup → config → helper functions → run), without changing the Paper 8 run parameters.
- **Refactor (allocator flow):** added one **run cell per allocator** (`Default`, `Dynamic`, `ThompsonSampling`, `Random`) and enabled the same plotting-ready imports (`matplotlib`) in the setup cell, matching the flow of the Paper 2/7/12 notebooks.
- **Scenario sweep:** expanded `test_scenarios` from `{none, stochastic}` to `{none, stochastic, markov, adaptive, onlineadaptive}` so the paper-config notebook runs **all threat regimes**.
- **Plotting:** restored plotting to `AllocatorRunner` (default ON) so all notebooks get plots without extra notebook cells; removed the notebook-specific plotting cell to keep the same flow as other testbeds.

## 2026-03-12

### Master-dataset verification hub notebook scaffolded
- **New file:** `H-MABs_MasterDataset_VerificationHub.ipynb`
- **Environment rule:** the notebook asserts the GA-Work `.quantum` interpreter so verification is not run from an ad hoc environment.
- **Purpose:** provide a source-backed verification record for the paper artifacts derived from `Validated_Logs/Master_Dataset_*.csv`.
- **Initial sections added:**
  - canonical source hierarchy
  - verification standard
  - artifact verification ledger
  - RQ1 mapping contract
  - RQ1 stable-row and neural-candidate computation cells
  - discrepancy register / next steps
- **Current status:** notebook is scaffolded and readable; `tab:rq1masterstochastic` is the first active verification target.

### Verification hub — RQ1 audit now shows expected vs actual and degree of change
- **Issue:** the notebook made the RQ1 discrepancy visible, but not yet in a direct paper-audit format.
- **Fix:** added an `RQ1 Expected vs Actual Audit` table that shows:
  - expected manuscript values
  - actual master-dataset values
  - signed deltas
  - absolute change magnitude
  - a `Degree of change` label
  - row status and note
- **Result:** readers can now see which rows match, which rows drift, and which rows remain unresolved because no stable source contract exists yet.

### Verification hub — RQ1 audit is color-coded by change severity
- **Issue:** the audit was still hard to scan quickly.
- **Fix:** changed the styling so only the letter/color of the severity-related columns is encoded; no background wash is applied.
- **Color rule:**
  - green = within rounding tolerance
  - yellow = small drift
  - orange = moderate drift
  - red = large drift or unresolved
- **Readability correction:** removed styling from `Status`; it now stays plain text, and only `Degree of change` plus the absolute-delta columns are color-coded.

### Verification hub — RQ1 audit simplified to one run at a time
- **Issue:** the mixed audit table was conflating run counts, source ambiguity, and drift into one confusing structure.
- **Fix:** replaced it with two separate audit tables:
  - `RQ1 Audit — 3 Runs`
  - `RQ1 Audit — 5 Runs`
- **Final columns only:**
  - `Model`
  - `Status`
  - `Expected`
  - `Actual`
  - `Δ`
  - `Source`
  - `Note`
- **Result:** each run-count is validated independently, unresolved neural rows stay explicit, and stable rows are judged only as `match` or `drift`.

### Verification hub — RQ1 redesigned to aggregate each source first
- **Issue:** even the run-specific audit was still validating in the wrong order; `TABLE V` must be reconstructed from independently aggregated source tables before any manuscript comparison is attempted.
- **Fix:** removed the premature `Expected` vs `Actual` comparison section from the notebook and replaced it with per-source aggregation tables for:
  - `CMABs`
  - `iCMABs`
  - `Hybrid`
  - `EXP3`
- **Locked scope of each source table:**
  - `scenario == STOCHASTIC`
  - `runs in {3, 5}`
  - all allocators
  - scales `1.0`, `1.5`, `2.0`
  - `cap_type in {T, Tb}`
  - `model != ORACLE`
- **Clarity fix:** `EXPUCB` is now rendered as `EXP3/UCB` in the notebook tables so the source-facing model label is explicit.
- **Result:** the notebook now shows the source aggregates first, and the paper-facing `TABLE V` reconstruction is explicitly deferred to the next step.

### Verification hub — RQ1 `TABLE V` reconstructed from approved source tables
- **Task:** rebuild the paper-facing RQ1 stochastic table after the per-source aggregates were locked.
- **Fix:** added two new notebook phases:
  - a row-map table that shows each `TABLE V` row with its `Source dataset` and `Source model`
  - a reconstructed `TABLE V` table derived directly from those approved source aggregates
- **Statement validation:** added source-backed checks for the surrounding narrative claims:
  - top tier remains above the 85% viability threshold
  - several mid-tier rows fall in the 60--80% band
  - collapsed rows remain in the ~37--40% band
- **Result:** the notebook now validates the table structure and the adjacent interpretation from the source aggregates before any manuscript-value comparison is attempted.

### Verification hub — `TABLE V` now audits manuscript vs reconstructed values
- **Task:** compare the manuscript values against the reconstructed source-backed `TABLE V`, one run-count at a time.
- **Fix:** added two audit tables to the notebook:
  - `TABLE V Audit — 3 Runs`
  - `TABLE V Audit — 5 Runs`
- **Audit columns:**
  - `Model`
  - `Status`
  - `Expected`
  - `Actual`
  - `Δ`
  - `Source`
  - `Note`
- **Implementation rule:** the `Actual` side now comes from the reconstructed source-backed `TABLE V`, not from raw mixed-source aggregates.
- **Clarity note:** `EXPUCB` is annotated in the audit as the paper label for `EXP3/UCB`.

### Verification hub — `TABLE V` now has both flat and tiered audit views
- **Adjustment:** kept the flat `3 Runs` and `5 Runs` audit tables and added separate tiered views for the same audits.
- **Tier split follows the paper order:**
  - `Top tier (viable under stochastic)`
  - `Mid-tier (degraded)`
  - `Collapsed (structural failure)`
- **Result:** readers can inspect the full audit table at once or analyze the same audit by tier without losing the flat view.

### Verification hub — RQ2 source-first section added for `TABLE VI`
- **Target artifact:** `TABLE VI` / `tab:rq2_adversarial`
- **Compiled paper anchor:** `TABLE VI`
- **Locked manuscript scope:**
  - scenarios: `MARKOV`, `ADAPTIVE`, `ONLINEADAPTIVE`
  - allocator: `Default`
  - runs: `3` and `5`
  - scales: `1.0`, `1.5`, `2.0`
  - capacity semantics: `T`, `Tb`
- **Locked source mapping:**
  - `CPursuit` → `CMABs`
  - `iCEpsilonGreedy` → `iCMABs`
  - `EXPNeuralUCB` → `EXP3`
  - `EXPUCB` → `EXP3`
- **Important correction:** the older helper script included `STOCHASTIC` in the RQ2 adversarial check; the notebook now follows the manuscript caption and excludes it.
- **Current notebook state:** per-source tables now show `Avg Eff.`, `CV`, `Floor`, plus raw win counts/config counts.
- **Deferred metric:** `Win Share (%)` remains unresolved until the correct denominator is locked from source.

### Verification hub — RQ2 narrative claims now validated from source
- **Task:** validate the narrative statements around `TABLE VI` before reconstructing the final paper-facing table.
- **Fix:** added `RQ2 Source-Backed Statement Checks` to the notebook.
- **Validated now from source:**
  - `CPursuit` remains stronger on average than both `EXPNeuralUCB` and `EXPUCB` under the locked adversarial scope
  - `EXPNeuralUCB` remains the unstable/fragile adversarial baseline while `iCEpsilonGreedy` remains the most stable informed baseline with the strongest floor
  - `iCEpsilonGreedy` has a `100%` in-family win rate within the iCMAB adversarial slice under the same scope
- **Interpretation rule:** these checks validate the manuscript statements first; table-value reconstruction still waits on the `Win Share (%)` denominator.

### Visualizer — scenario plots now show reward evolution correctly
- **Issue:** the main comparison plot (e.g., `*_stochastic_vs_baseline_comparison_*.png`) showed reward evolution across runs, but the per-scenario plots (e.g., `*_stochastic_vs_baseline_*.png`) did not.
- **Root cause:** `plot_scenarios_comparison(...)` passed `scenario_data` as the third positional argument into `_plot_reward_evolution(...)`, so it was interpreted as `reward_type` instead of `scen_data`.
- **Fix:** changed the call to use explicit keywords:
  - `reward_type='reward_list'`
  - `scen_data=scenario_data`
- **Defensive hardening:** `_plot_reward_evolution(...)` now validates `reward_type`, recovers the old accidental positional misuse case, and falls back safely instead of silently plotting nothing.
- **Applied in:** `daqr/evaluation/visualizer.py`

### Visualizer — comparison plot titles now match the allocator/output file
- **Issue:** per-scenario plot files were named correctly (e.g., `Random_onlineadaptive_vs_baseline_*.png`), but the figure title remained hardcoded as `Stochastic vs Baseline Robustness Analysis`.
- **Fix:** both comparison plot methods now build the suptitle dynamically from the allocator label, so titles follow the actual plot/output context.
- **Example:** `Random_onlineadaptive_vs_baseline_*.png` now renders the title `Quantum MAB Models: Random vs Baseline Robustness Analysis`.
- **Applied in:** `daqr/evaluation/visualizer.py`

### Verification hub — RQ2 partial `TABLE VI` reconstruction and source-locked audits
- **Task:** after validating the RQ2 narrative claims, reconstruct only the source-locked `TABLE VI` columns before resolving `Win Share (%)`.
- **Fix:** added `RQ2 Partial TABLE VI Reconstruction` and `RQ2 Partial TABLE VI Audit` sections to `H-MABs_MasterDataset_VerificationHub.ipynb`.
- **What is now shown in the notebook:**
  - source-backed `TABLE VI` rows for `CPursuit`, `iCEpsilonGreedy`, `EXPNeuralUCB`, and `EXPUCB`
  - source-backed values for `Avg Eff. (%)`, `CV (%)`, and `Floor (%)`
  - manuscript-vs-source audit views for each of those three metrics
  - `Source dataset` and `Source model` carried through the audit output
- **Deferred metric:** `Win Share (%)` remains `TBD` until its denominator is proven from source.
- **Execution:** notebook re-executed successfully under `/Users/pitergarcia/DataScience/Semester4/GA-Work/.quantum`.

### Verification hub — RQ2 partial `TABLE VI` now shows manuscript Win Share values explicitly
- **Issue:** the notebook showed `TBD` in `Win Share (%)`, which was inaccurate because the paper values are already known from `TABLE VI`.
- **Fix:** the reconstructed RQ2 partial table now carries the manuscript `Win Share (%)` values directly:
  - `CPursuit = 31.5`
  - `iCEpsilonGreedy = 25.0`
  - `EXPNeuralUCB = 11.1`
  - `EXPUCB = 0.0`
- **Clarification:** only the source derivation of `Win Share (%)` remains unresolved; the manuscript values themselves are now displayed explicitly.

### Verification hub — RQ2 source scope diagnostics table added
- **Task:** expose the exact source reasoning inputs for `TABLE VI` before further logic on `Win Share (%)`.
- **Fix:** added `RQ2 Source Scope Diagnostics` to `H-MABs_MasterDataset_VerificationHub.ipynb`.
- **What the table shows for each `TABLE VI` model:**
  - `Model`
  - `Source`
  - `Source model`
  - `Threats`
  - `Threat count`
  - `Allocator`
  - `Runs`
  - `Run count`
  - `Wins`
- **Execution:** notebook re-executed successfully under `/Users/pitergarcia/DataScience/Semester4/GA-Work/.quantum`.

### Verification hub — RQ2 diagnostics now show totals needed for win-share reasoning
- **Fix:** replaced the misleading distinct-value counts with concrete totals in `RQ2 Source Scope Diagnostics`.
- **Added columns:**
  - `Total threats`
  - `Total runs`
  - `Total wins`
- **Kept columns:**
  - `Threats`
  - `Allocator`
  - `Run suites`
  - `Scales`
  - `Cap types`
  - `Experiments`
  - `Wins`
- **Interpretation:** `Wins` is model wins under the locked scope; `Total wins` is the total available experiment-level wins in that scope.

### Verification hub — RQ2 broader threat-scope follow-up noted
- recorded that the notebook currently validates `TABLE VI` exactly as captioned using only `MARKOV`, `ADAPTIVE`, and `ONLINEADAPTIVE`
- recorded a separate `mid-high` priority follow-up to expand this analysis later because broader threat coverage may reveal patterns not visible in the narrower adversarial-only slice

### Verification hub — RQ2 diagnostics simplified to high-level wins view
- **Fix:** simplified `RQ2 Source Scope Diagnostics` to the high-level structure used for reasoning.
- **Current columns:**
  - `Model`
  - `Source`
  - `Threats`
  - `Allocator`
  - `Run suites`
  - `Wins`
  - `Wins / Scope wins`
- **Added:** final summary row for `Total wins (shown models)`.
- **Removed:** per-row total columns that repeated the full-scope denominator on every line.

### Verification hub — RQ2 wins ratio now performs the actual division
- **Issue:** the previous RQ2 high-level diagnostics showed a string ratio instead of the computed division.
- **Fix:** replaced the string with a numeric percentage column:
  - `Wins / All wins (%)`
- **Definition:** `Wins / All wins (%) = model wins / total shown-model wins * 100`
- **Total row:** remains `100.0%` for `Total wins (shown models)`.

### Verification hub — RQ2 researched win-share formulas added
- **Added:** a new `RQ2 Win Share Candidate Formulas (researched)` section to the verification hub notebook.
- **Formulas applied:**
  - `Micro share (%) = wins_i / sum_j wins_j * 100`
  - `Macro threat-balanced share (%) = mean_t[wins_{i,t} / sum_j wins_{j,t}] * 100`
  - `Dirichlet-smoothed share (%) = (wins_i + 0.5) / (sum_j wins_j + 0.5K) * 100`
- **Scope:** `MARKOV`, `ADAPTIVE`, `ONLINEADAPTIVE`, `Default`, runs `3` and `5`, scales `1.0/1.5/2.0`, `T/Tb`
- **Finding:** none of the researched source-backed formulas reproduces the paper `Win Share (%)` column, so the manuscript values still require separate provenance clarification.

### Verification hub — RQ2 winner accounting tables added
- **Added:** three explicit winner-accounting sections for the locked `TABLE VI` scope:
  - `RQ2 Runner Wins Summary`
  - `RQ2 Evaluator Wins Summary`
  - `RQ2 Overall Wins by Run Suite`
- **Runner summary:** uses experiment-level `winner`
- **Evaluator summary:** uses aggregated `scenario_winner`
- **Per-run tables:** split evaluator wins into `3`-run and `5`-run views
- **Purpose:** make the winner layers explicit before any further `Win Share (%)` reasoning

### Verification hub — RQ2 audits now include percent deviation from expected
- **Added:** `Δ / Expected (%)` to each RQ2 audit table
- **Formula:** `(actual - expected) / expected * 100`
- **Reason:** this is the validation-normalized comparison the paper audit should use

### Verification hub — RQ2 winner tables now compare their ratios against the paper win-share values
- **Added:** `Paper Win Share (%)` and `Δ vs Paper Win Share` to:
  - `RQ2 Runner Wins Summary`
  - `RQ2 Evaluator Wins Summary`
  - `RQ2 Overall Wins by Run Suite`
- **Formula:** `(paper_share - actual_share) / actual_share`
- **Note:** rows with actual share `0.0` are now forced to `0.0` for this column, per the notebook convention used in the current review pass
- **Update:** removed the `* 100` factor from the winner-table deviation column

### Verification hub — paper-side use of `Win Share (%)` documented
- **Added:** a notebook section that records where `Win Share` is actually used in `main.tex`
- **Finding:** the global win-share figure defines its rule explicitly, but `TABLE VI` does not define the denominator for its `Win Share (%)` column
- **Implication:** `TABLE VI` remains the highest-priority provenance issue

### Verification hub — `Win Share` severity assessment added
- **Added:** a notebook section that separates correction priority from manuscript blast radius
- **Finding:** `TABLE VI` `Win Share (%)` is high priority for correctness, but low-scope in terms of paper impact because the surrounding RQ2 prose does not materially rely on that numeric column

### Verification hub — `TABLE VI` replacement recommendation added
- **Added:** a notebook recommendation section for replacing the unsupported `Win Share (%)` column
- **Recommended replacement:** `Configuration Win Rate (%)`
- **Rule:** use evaluator-level `scenario_winner` over unique `(scenario, runs, scale, cap_type)` configurations under the `Default` allocator
- **Reason:** this is the most defensible source-backed, literature-aligned replacement found during the audit

### Verification hub — final `TABLE VI` fix switched from `Win Share (%)` to `Win Dominance (%)`
- **Decision:** after reviewing the table’s argumentative purpose, the notebook superseded the earlier `Configuration Win Rate (%)` recommendation with **`Win Dominance (%)`** for `TABLE VI`.
- **Definition:** `Win Dominance (%)` is each displayed model’s share of aggregated scenario wins among the four displayed RQ2 representatives under the locked adversarial scope (`MARKOV`, `ADAPTIVE`, `ONLINEADAPTIVE`; `Default`; runs `3/5`; scales `1/1.5/2`; `T/T_b`).
- **Source-backed values:** `CPursuit = 25.6`, `iCEpsilonGreedy = 43.9`, `EXPNeuralUCB = 30.5`, `EXP3/UCB = 0.0`.
- **Paper action:** `main.tex` now uses `Win Dominance (%)` in `TABLE VI` with an explicit caption definition; this is a localized manuscript correction and does not change the literature framing.
