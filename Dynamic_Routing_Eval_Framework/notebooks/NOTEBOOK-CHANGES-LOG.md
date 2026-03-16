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

## 2026-03-15

### Verification hub — RQ3c proof snapshot evidence bundle finalized
- **Issue:** the proof snapshot exporter prefixes filenames (`data__*`, `agg_used__*`). The initial RQ3c evidence objects were named with `data__...` / `agg__...`, causing double-prefixed exports (e.g., `data__data__rq3c_...`, `agg_used__agg__rq3c_...`) and making the evidence checks fail by pattern.
- **Fix:** rewrote the RQ3c approved-branch proof-snapshot cell to use neutral variable names (`rq3c_approved_branch`, `rq3c_approved_allocator_*`), so exports land as:
  - `data__rq3c_approved_branch.csv`
  - `agg__rq3c_approved_branch.csv` + pivot variants
  - `agg_used__rq3c_approved_allocator_scenario.csv`
  - `agg_used__rq3c_approved_allocator_summary.csv`
- **Evidence:** proof snapshot written to `paper_validation/snapshots/20260315_001835/`.

### Verification hub — `Win Share` severity assessment added
- **Added:** a notebook section that separates correction priority from manuscript blast radius
- **Finding:** `TABLE VI` `Win Share (%)` is high priority for correctness, but low-scope in terms of paper impact because the surrounding RQ2 prose does not materially rely on that numeric column

### Verification hub — RQ1 `TABLE V` high-priority semantics made explicit
- **Task:** make the RQ1 `TABLE V` audit semantics explicit directly in the notebook so review does not depend on implied meanings.
- **Meaning:** “Pending high tasks” is a mismatch-severity indicator for specific model/run items (not a statement about overall claim support).
- **Before:** manuscript `TABLE V` reported values for the listed model/run items.
- **After:** pandas-recomputed values from the validated master slice used to reconstruct `TABLE V`.

### Verification hub — RQ1 pending-high Before/After table fixed and rendered
- **Issue:** the pending-high mini table initially expected `Status` and `Δ` columns, but the `TABLE V` audit tables expose discrepancy via `B - A` (and do not necessarily carry `Status`).
- **Fix:** normalized the mini table to derive `Δ` from `B - A`, injected a simple `Status = pending (high)` label when absent, and included `Priority` for audit severity visibility.
- **Result:** the notebook now renders an explicit “Before (Expected) vs After (Actual)” table directly under the RQ1 analysis summary.

### Paper patch — RQ1 `TABLE V` values updated to match approved audit
- **Task:** apply the approved “Before vs After” corrections to the compiled paper table.
- **Paper file:** `GA Papers/QuantumFaultTolerant/main.tex` (`tab:rq1masterstochastic`).
- **Changes applied (one-decimal rounding):**
  - `GNeuralUCB` 3-run `85.2 → 86.2` (Avg `85.9 → 86.3`).
  - `EXPNeuralUCB` 5-run `83.8 → 80.9` (Avg `83.1 → 81.5`).
  - `iCPursuit` 3-run `68.7 → 67.2`, 5-run `69.0 → 67.5` (Avg `68.9 → 67.4`).
- **Source of truth:** the notebook’s rendered `RQ1 Pending-High — Before (Expected) vs After (Actual)` table.

## 2026-03-14

### Verification hub — RQ3c “Before/After” semantics made explicit
- **Issue:** the RQ3c section already had `Task / Meaning / Before / After`, but it was still easy to read the discrepancy tables as a generic “paper vs dataset” comparison without a clear mapping to the `Expected/Actual` columns.
- **Fix:** updated the RQ3c scope markdown to explicitly define:
  - `Expected` = paper-as-written values (**Before**)
  - `Actual` = pandas-computed values (**After**, only for the approved branch)
- **Added:** a short `Status (Pending vs Solved)` block so readers can see what is “doc-only solved” vs what still requires manuscript alignment + snapshot evidence.

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

### Verification hub — validation error-rate columns now use absolute magnitude
- **Issue:** signed error-rate columns were making the validation tables noisier than necessary.
- **Fix:** converted the notebook’s validation-rate columns to absolute magnitude:
  - `|Δ| / Expected (%)` in the RQ2 metric audits
  - `|Δ| vs Paper Win Dominance` in the RQ2 winner-accounting tables
- **Rule:** keep the raw `Δ` column signed where present, but make the normalized error-rate columns absolute for easier validation review.

### Verification hub — RQ3a source-first audit added
- **Added:** a full `RQ3a` section to `H-MABs_MasterDataset_VerificationHub.ipynb` covering:
  - caption-faithful source scope
  - caption-faithful reconstruction of `tab:rq3a_informative`
  - source-backed statement checks
  - manuscript-vs-source audit
  - provenance diagnostic search
- **Locked caption-faithful scope:** `Hybrid`, `Default`, `T`, `s=2`, `6000` horizon, runs `3` and `5`, all five scenarios.
- **Finding:** the caption-faithful reconstruction does **not** support the manuscript RQ3a claims. The strongest mismatch is the paper’s reported `+18.3 pp` OnlineAdaptive lift; the audited source result under the stated caption scope is `-0.807 pp`.
- **Provenance diagnostic:** the best source match to the manuscript table is the same deployment with `runs = 3` only, which reproduces the paper’s directional claims and yields the nearest value match (`MAE ≈ 1.805`). This suggests the current caption and the underlying derivation are inconsistent.

### Verification hub — RQ3a alternative 6K horizon branch and priority notes added
- **Added:** an explicit RQ3a diagnostic branch for the user-raised `6K horizon = 4K base + 6K base+step` interpretation under:
  - `Hybrid`
  - `Default`
  - `T`
  - `scale = 2.0`
  - `runs = 3`
  - frames aggregated over `4000` and `6000`
- **Result:** this branch improves provenance plausibility over the caption-faithful `3+5` mean, but it is still weaker than the `6000 / runs=3 only` candidate (`MAE 3.206` vs `1.805`).
- **Priority notes recorded in notebook:** high priority on:
  - the `CV_scen` claim
  - the `iCPursuitNeuralUCB / OA = 99.1` manuscript value
  - the overall caption/derivation mismatch itself

### Verification hub — RQ3a `Tb` provenance branches added
- **Added:** the same RQ3a provenance checks under `Tb`:
  - `6000 / runs 3+5 mean`
  - `6000 / runs 3 only`
  - `6000 / runs 5 only`
  - `4000+6000 / runs 3 only`
- **Finding:** none of the `Tb` branches outperforms the best `T` provenance candidate.
- **Best `Tb` branch:** `Tb / 6000 / runs 3 only`
  - `OA lift = +0.911 pp`
  - `Avg lift = -0.017 pp`
  - `MAE vs paper = 4.534`
- **Implication:** the current RQ3a manuscript values are not being explained by an accidental `Tb` source choice; `T / 6000 / runs 3 only` remains the strongest provenance candidate.

### Verification hub — RQ3a paper correction applied from the validated 3-run branch
- **Decision:** patch the paper from the strongest source-backed provenance branch rather than the unsupported caption-faithful `3+5` mean.
- **Applied paper branch:** `6K`, `Fixed`, `T`, `s=2`, `runs = 3`.
- **Applied corrections:** the paper now uses the 3-run suite wording in the RQ3a setup sentence and caption, updates the two table rows to the validated source values, and makes the high-priority dispersion claim explicit as `CV_scen: 6.5 -> 3.3` while preserving the validated `+18.3 pp` OnlineAdaptive lift.

### Verification hub — RQ3b source-first audit added
- **Added:** a full `RQ3b` section to `H-MABs_MasterDataset_VerificationHub.ipynb`.
- **Clarified purpose:** `RQ3b` is being treated as an expansion of `RQ3a` under the same fixed-deployment claim, with scale as the only intended variable.
- **Notebook wording updated:** the notebook now states explicitly that the table/caption semantics govern the audit purpose, and that any stray `Random` wording is legacy residue and not the controlling interpretation.
- **Approved interpretation anchor (final):** `Hybrid`, `Default` (fixed deployment interpretation), `Tb`, `6K`, `runs = 3`, scenarios `Bl/Sh/Mk/Ag`.
- **Result (manuscript/table claim):** under this anchor, both pursuit-based hybrids show an intermediate bump at `s=1.5` followed by regression at `s=2.0` (i.e., replay capacity is not a monotone “more is better” knob).
- **Proof bundle exported:** `paper_validation/snapshots/20260314_224936/` (row slice + pandas aggregations/pivots used for the manuscript table).
- **Provenance gap recorded:** under `T` anchoring at `6K` with `Default (=Fixed)`, the validated master is missing the full `s=1.5` grid; RQ3b is therefore reported using `Tb` until the master is repaired.
- **High-priority wording patch status:** completed. RQ3b narrative remains anchored to fixed/default deployment interpretation; `Random` is no longer treated as an interpretive anchor.
- **Paper sync status:** completed. Matching RQ3b wording in `GA Papers/QuantumFaultTolerant/main.tex` now uses the same fixed/default deployment anchor language.
- **Task:** remove stray `Random` anchor wording from the RQ3b key finding and keep interpretation anchored to fixed/default deployment.
- **Meaning:** RQ3b interpretation is deployment-anchor based (`Default/Fixed`), not `Random`-allocator based.
- **Before:** manuscript wording used `allocator fixed (Random)` in the RQ3b key-finding sentence.
- **After:** manuscript wording now uses `deployment anchor fixed (Default/Fixed)` in that same sentence.
- **Before/after solution steps:**
  1. locate the inconsistent RQ3b key-finding sentence in `main.tex`
  2. replace `Random` anchor wording with `Default/Fixed` anchor wording
  3. sync the same interpretation note into paper trackers and notebook log
  4. verify the updated phrase exists in manuscript and trackers

### Verification hub — discrepancy severity summaries added for RQ3a and RQ3b
- **Added:** a notebook-wide discrepancy severity key:
  - `High`: `|B - A| >= 1.0` percentage point
  - `Medium`: `0.5 <= |B - A| < 1.0` percentage point
  - `Low`: `0 < |B - A| < 0.5` percentage point
- **Added:** row highlighting for the RQ3a and RQ3b discrepancy tables using light severity colors with black text for readability.
- **Added:** end-of-analysis summary blocks that state:
  - whether the claims are supported by the data
  - the high-priority discrepancies
  - the medium-priority discrepancies
  - the low-priority discrepancies
- **Updated:** the summary tables now show both:
  - signed point change `B - A`
  - absolute point change `|B - A|`
  - normalized ratio `|B - A| / Expected`
- **Decision:** severity is now driven by absolute point change, not the normalized ratio, because paper-facing replacement decisions are easier to defend in percentage-point terms.

### Verification hub — discrepancy styling expanded across all audited tables
- **Expanded coverage:** the shared discrepancy key and row-highlighting helpers now drive:
  - `RQ1 TABLE V` flat and tiered audits
  - `RQ2` runner/evaluator/per-run winner diagnostics
  - `RQ2 Partial TABLE VI` metric audits plus `Win Dominance (%)`
  - `RQ3a` raw audit table
  - `RQ3b` best table-match audit
- **Added:** end-of-analysis summary blocks for `RQ1` and `RQ2` so every completed artifact section now ends with:
  - whether the claims are supported
  - high-priority discrepancies
  - medium-priority discrepancies
  - low-priority discrepancies
- **Added:** explicit high-task status lines after every completed analysis:
  - `🔴 Pending high tasks`
  - `🟢 Solved high tasks`
- **Purpose:** make full-pass review of prior audit work consistent before moving on to additional tables/figures.

### Verification hub — RQ3c allocator audit added
- **Added:** source-first `RQ3c` sections for:
  - source aggregation scope
  - source-backed statement checks
  - manuscript-faithful reconstruction
  - provenance diagnostic
  - analysis summary with discrepancy tiers and task-status lines
- **Caption-faithful branch tested:** `CPursuitNeuralUCB / Tb / s=2 / 6K / runs=3+5 / all5`
- **Result:** the printed allocator table is not source-backed under the caption-faithful branch.
- **Answer-text branch tested:** `iCPursuitNeuralUCB / Tb / s=2 / 6K / runs=3 / all5`
- **Result:** the allocator-direction claim is supported there:
  - `Fixed` is best on average and floor
  - `Thompson` is strongest in `Adaptive` but drops hard in `Baseline` / `Stochastic`
- **High-priority issue isolated:** the table caption names `CPursuitNeuralUCB`, while the answer text argues about `iCPursuitNeuralUCB`.
- **High-priority issue isolated:** no tested `6K / s=2` branch reproduces the printed allocator table well; best tested table-match is still weak (`MAE = 13.971`).

### Verification hub — capacity-type option summaries added for non-aggregated RQ3 sections
- **Added:** two explicit option tables at the end of the notebook:
  - `T Option Summary`
  - `Tb Option Summary`
- **Coverage:** `RQ3a`, `RQ3b`, and `RQ3c`
- **Purpose:** record, per section, whether `T` or `Tb` is closer to:
  - the claims
  - the reported paper data
- **Use:** these tables are now the quick reasoning ledger before making capacity-type decisions in paper fixes.

### Verification hub — RQ3d deployment-rule audit added
- **Added:** source-first `RQ3d` sections for:
  - source aggregation scope
  - static-default audit
  - switching-rule audit
  - analysis summary with discrepancy tiers and task-status lines
- **Strongest coherent branch identified:** `iCPursuitNeuralUCB / Fixed / T / s=2 / 6K / runs=3`
- **Result:** the static-default identity is source-backed and stays above `85%` across all five scenarios.
- **Mismatch:** the reported `95.5% / 88.5%` static-default metrics are not source-backed on that coherent branch; source-backed values are `96.0%` average and `92.8%` floor.
- **Switching breakdown:** mostly source-backed on the same coherent `3-run` branch.
- **Adaptive exception:** the reported `Thompson + (Tb, s=1.5)` row is absent from the coherent `3-run` branch but present on the `5-run` slice at `95.7%`; the reported `+2.9 pp` gain aligns with the `3-run` default baseline, so this row is now flagged as the top-priority mixed-run provenance issue and a rerun/correction candidate.

### Verification hub — Table X cross-testbed audit added
- **Added:** source-first `Table X` sections for:
  - source aggregation scope
  - per-testbed source tables
  - reconstructed cross-testbed table
  - source-backed claim checks
  - manuscript-vs-source audit
  - analysis summary with task-status lines
- **Scope lock:** Papers 2, 7, and 12 use `runs=5`, `cap_type=T`, `s in {1.0, 1.5, 2.0}` across all five scenarios and 4 allocators; Paper 8 uses the paper-config `1K/1K/1R`, `runs=1`, `cap_type=T`, `s=1.0`.
- **Result:** the printed cross-testbed table is source-backed under the manuscript scope.
- **Claims:** the nearby cross-testbed observations are source-backed, including the Paper 8 EXP-vs-iCP split and the Paper 12 broad winner overlap.
- **Priority:** no new high-priority discrepancies were introduced; remaining drift is limited to low rounding noise.
- **Process correction:** each testbed now has its own source table and winner-layer diagnostics before the combined `Table X` view, so the notebook shows where the cross-testbed rows come from testbed by testbed.
- **Validation structure correction:** the claim checks and manuscript-vs-source audits are now split per testbed (`Paper 2`, `Paper 7`, `Paper 12`, `Paper 8`) instead of one giant combined audit table.

### Verification hub — Table XI model-family audit added
- **Added:** source-first `Table XI` sections for:
  - source aggregation scope
  - per-source source tables
  - per-source claim checks
  - per-source manuscript-vs-source audits
  - inter-family claim checks
  - analysis summary with pending/solved high-task lines
- **Process:** validation is split by source world (`CMABs`, `iCMABs`, `EXP3-based`, `Hybrid Neural`, `Paper 2`, `Paper 7`, `Paper 12`, `Paper 8`) instead of one combined audit table.
- **Supported:** claim 1, claim 3, claim 4, and claim 5 in the nearby inter-family analysis are source-backed.
- **Applied fix:** claim 2 now uses Oracle-relative aggregate gap reduction instead of literal experiment-winner wording.
- **Applied fix:** the `Paper 8` floor values in `Table XI` were corrected to the source-backed values (`44.1 / 23.9 / 36.0 / 35.2`).
- **Interpretive note:** the main scientific shift is `EXPNeuralUCB`'s `Paper 8` floor (`35.1 -> 23.9`), which strengthens the framework-level argument that narrow-scope success does not guarantee robust performance under broader variability.
- **Medium-priority follow-up:** clarify in the paper that “best overall” should refer to aggregate cross-threat robustness / gap-reduction behavior under quantum variability, not to winning every evaluation setting individually.
- **Gap-reduction proof added:** for `Hybrid Neural`, `Paper 2`, `Paper 7`, `Paper 12`, and `Paper 8`, the notebook now shows Oracle-relative gap tables with:
  - all allocators aggregated across threats
  - allocator-by-allocator aggregate gap tables
- **Gap-reduction result:** `iCPursuitNeuralUCB` has the lowest Oracle-relative aggregate gap in every checked source world and in every allocator slice within those source worlds.
- **Claim implication:** the intended aggregate gap-reduction interpretation is source-backed and is now the correct paper-facing formulation for claim 2.
- **Low-priority follow-up:** add claim-to-artifact traceability so the final paper wording can link each claim back to the exact validated notebook/table/figure artifact that supports it.

### Verification workflow — paper numeric include-file automation noted
- **Recorded backlog item:** move paper-facing table/plot numbers out of hardcoded LaTeX and into generated text/TeX include files.
- **Recorded workflow dependency:** `state_analysis.py` should refresh those generated numeric files, run the dependent reports, and leave the paper repo ready for a controlled commit/push after validation.

### Verification hub — RQ3d deployment-rule block corrected
- **Patched paper values/configs:** updated the RQ3d static-default metrics to the source-backed `96.0% / 92.8%` values and corrected the `Adaptive` switching rule to `Thompson + (T, s=1)`.
- **Clarified provenance:** the paper now states that the deployment-rule block uses the coherent 6K `3-run` branch.
- **Notebook sync:** updated the RQ3d expected values/configs in the verification hub and re-executed the notebook under `.quantum`.

### Verification hub — pandas workflow retained, audit formatting restored, notebook coverage regression identified
- **Confirmed engine choice:** pandas remains the canonical data-manipulation layer for the verification hub. The issue was not pandas; the issue was that a later rewrite removed the audit workflow layer that made review tractable.
- **Restored in the current notebook file:** discrepancy color coding, `B - A` / `|B - A|` severity presentation, end-of-analysis summaries, and the `🔴 Pending high tasks` / `🟢 Solved high tasks` status lines for the sections currently present.
- **Coverage finding:** the current GitHub notebook variant only contains the restored `RQ1` and `RQ2` sections. The richer source-first sections previously tracked here for `RQ3a`, `RQ3b`, `RQ3c`, `RQ3d`, `Table X`, and `Table XI` are not currently present in the notebook file.
- **Ledger correction:** the notebook now explicitly marks those later artifacts as `restore required` instead of pretending they are still implemented in this file.
- **Paper/doc check:** `GA Papers/QuantumFaultTolerant/main.tex` still carries the later approved paper-side fixes (`Win Dominance (%)`, RQ3 wording fixes, Table XI claim/floor fixes). The mismatch is notebook coverage parity, not a rollback in the paper text.

### Verification hub — missing validated `RQ3` / `Table X` / `Table XI` sections restored on top of pandas
- **Recovery source:** rebuilt the missing notebook sections from the approved snapshot bundle under `paper_validation/snapshots/20260315_001835`.
- **Restored sections:** `RQ3a`, `RQ3b`, `RQ3c`, `RQ3d`, `Table X`, and `Table XI`.
- **Workflow preserved:** the restored sections keep the same pandas-first audit layer used in `RQ1`/`RQ2`:
  - discrepancy color coding
  - `B - A` / `|B - A|` severity presentation
  - end-of-analysis summaries
  - `🔴 Pending high tasks` / `🟢 Solved high tasks`
- **Structure preserved:** `Table X` is again split testbed-by-testbed for validation, and `Table XI` is again split source-by-source before the combined interpretation.
- **Validation:** executed the full notebook successfully after the recovery patch.
- **Parity result:** notebook coverage now matches the approved paper/doc state again for the validated table/breakdown artifacts.

### Verification hub — explicit solved/pending status table added to analysis summaries
- **Added:** each completed analysis summary now includes a small status table with:
  - `✅` for solved items
  - `🔴` for pending items
- **Purpose:** make it easier to scan what has already been handled versus what remains open, without relying only on the markdown summary lines.
- **Styling update:** discrepancy rows with `Priority = None` now render with an explicit white background so zero-delta / no-issue rows stay visually neutral.
- **Validation:** re-executed the full notebook successfully after the summary/status styling change.

### Verification hub — row-level discrepancy status added after `Priority`
- **Added:** audit tables now include a `Status` column immediately after `Priority`.
- **Meaning:** the row-level discrepancy status is now explicit:
  - `✅` = discrepancy resolved in the approved paper/notebook state
  - `🔴` = discrepancy still open
  - blank/white = `Priority = None` / no discrepancy to resolve
- **Styling:** the new `Status` column is color-coded independently of the severity band so resolution state and discrepancy size can be read separately.
- **Validation:** re-executed the full notebook successfully after adding the row-level status column.

### Verification hub — row highlight reverted; only target columns remain colored
- **Correction:** removed the full-row background highlighting that had been introduced during the status-column update.
- **Current behavior:** only the intended columns are color-coded:
  - discrepancy columns (`B - A`, `|B - A|`, `|B - A| / Expected`, `Priority`)
  - the row-level `Status` column
  - statement-check `Result` where applicable
- **Removed:** the extra summary status tables that were added by mistake; the notebook now keeps only:
  - the row-level `Status` column
  - the existing red/green summary lines
- **Validation:** re-executed the full notebook successfully after reverting the unintended formatting change.

### Verification hub — `Priority = None` rows now show solved status
- **Updated rule:** rows with `Priority = None` now show `Status = ✅` instead of a blank status cell.
- **Reason:** this makes the audit tables easier to scan by showing that zero-delta / no-discrepancy rows are already resolved and require no action.
- **Styling preserved:** the discrepancy columns for `None` rows remain neutral white; only the `Status` cell changes to solved.
- **Validation:** re-executed the full notebook successfully after the status-rule update.

### Verification hub — row status labels made explicit
- **Issue found during vetting:** `✅` was overloaded and could mean either:
  - no discrepancy (`Priority = None`)
  - or a previously fixed discrepancy
- **Fix:** the row-level `Status` column now uses explicit labels:
  - `✅ No issue`
  - `✅ Fixed`
  - `🔴 Open`
- **Reason:** this separates “nothing to do here” from “this used to be a discrepancy but is now resolved.”
- **Validation:** re-executed the full notebook successfully after the status-label clarification.

### Verification hub — `RQ1 / TABLE V` status remapped from tracked paper fix
- **Issue found during vetting:** `TABLE V` was still marking its historical high-delta rows as open even though the notebook log already recorded the paper patch that applied those values to `main.tex`.
- **Tracked source used:** the existing notebook log entry `Paper patch — RQ1 TABLE V values updated to match approved audit`.
- **Fix:** remapped the four approved `RQ1` high rows to `✅ Fixed`:
  - `GNeuralUCB / 3 Runs`
  - `EXPNeuralUCB / 5 Runs`
  - `iCPursuit / 3 Runs`
  - `iCPursuit / 5 Runs`
- **Result:** `RQ1` now shows:
  - `Open high priority discrepancies: None`
  - the above four rows under `Resolved high priority discrepancies`
- **Current real open-high set after vetting:** only `RQ2 / EXPNeuralUCB / CV (%)` remains open at high priority.

### Paper patch — `RQ2 / TABLE VI / EXPNeuralUCB / CV (%)` corrected
- **Task:** apply the approved `RQ2` CV correction in the manuscript table.
- **Paper file:** `GA Papers/QuantumFaultTolerant/main.tex` (`tab:rq2_adversarial`).
- **Before / After:** `EXPNeuralUCB / CV (%)` changed from `16.5` to `15.1` (paper-facing one-decimal rounding of the validated `15.08` source value).
- **Notebook sync:** updated the `RQ2` expected value in the verification hub and marked the row as fixed so it no longer appears as an open high-priority discrepancy.
- **Result:** after this patch, the vetted open-high backlog for the validated table/breakdown artifacts is cleared.

### Winner terminology review plan recorded
- **Scope:** after clearing the open high-priority table/breakdown fixes, the next review pass is a paper-wide terminology check for how `winning`, `winner`, `Win Dominance`, `Win Share`, `Exp. Winner`, `scenario_winner`, `best overall`, and `dominance` are used.
- **Reason:** these terms now span multiple distinct meanings in the paper:
  - configuration-level experiment winners
  - scenario champions
  - displayed-model winner-pool dominance
  - aggregate gap-reduction leadership
- **Planned review locations in `GA Papers/QuantumFaultTolerant/main.tex`:**
  - `fig:global_win_share`
  - `TABLE VI` / `tab:rq2_adversarial`
  - RQ2 in-family winner sentence
  - `TABLE X` intro/caption/legend/bullets
  - `TABLE XI` note + inter-family claim block
  - standardized-testing / future-work winner-language carryover
- **Execution rule:** address these one by one using the agreed process:
  - `Task`
  - `Meaning`
  - `Before`
  - `After`
- **Current status:** planning/documentation only; no new paper wording changes have been applied yet for this winner-terminology pass.

### Winner terminology review — figure-level winner-frequency label aligned
- **Approved task applied:** the global winner-frequency figure now reflects the same paper decision already used for `TABLE VI`.
- **Paper file:** `GA Papers/QuantumFaultTolerant/main.tex`
- **Before:** `Global Win Share (%)`
- **After:** `Win Dominance (%)`
- **Legend aligned too:** `Top-5 win share (default allocator)` → `Top-5 win dominance (default allocator)`
- **Reason:** this was not an open terminology decision; it was a consistency propagation task from the already-documented `Win Dominance (%)` choice.

### Winner terminology review — RQ2 in-family winner sentence simplified
- **Paper file:** `GA Papers/QuantumFaultTolerant/main.tex`
- **Before:** `iCEpsilonGreedy is the consistent winner (100% in-family win rate), while iCPursuit is not.`
- **After:** `iCEpsilonGreedy is the consistent winner (100% in-family win rate) under the same adversarial scope.`
- **Reason:** the contrast against `iCPursuit` was not adding useful meaning here; the important point is the scoped in-family winner claim.

### Notebook validation — explicit winner-type tables restored for `Table X` and `Table XI`
- **Notebook file:** `hybrid_variable_framework/Dynamic_Routing_Eval_Framework/notebooks/H-MABs_MasterDataset_VerificationHub.ipynb`
- **Reason:** `Table X` and `Table XI` needed explicit validation tables showing what kind of winner is being claimed, rather than leaving the winner basis implicit.
- **Added to `Table X`:** per-testbed winner-type tables for `Paper 2`, `Paper 7`, `Paper 12`, and `Paper 8` with:
  - `Experiment winner` = highest experiment-win count
  - `Aggregate gap-reduction winner` = lowest aggregate gap
  - `Aggregate efficiency winner` = highest aggregate efficiency
- **Result for `Table X`:**
  - `Papers 2/7/12`: `iCPursuitNeuralUCB` wins all three winner types
  - `Paper 8`: `EXPNeuralUCB` is the `Experiment winner`, while `iCPursuitNeuralUCB` remains the aggregate gap/efficiency winner
- **Added to `Table XI`:** per-source winner-type tables for `Hybrid Neural`, `Paper 2`, `Paper 7`, `Paper 12`, and `Paper 8` with:
  - `Experiment winner`
  - `Aggregate gap-reduction winner`
  - `Aggregate efficiency winner`
  - `Allocator-level aggregate gap winner`
- **Result for `Table XI`:** `iCPursuitNeuralUCB` remains the aggregate gap/efficiency winner in every checked source world and within every allocator slice, while `Paper 8` still separates experiment wins from aggregate gap leadership.
- **Validation:** the new winner-type logic was checked directly against the snapshot CSVs under `paper_validation/snapshots/20260315_001835` using pandas from `.quantum`.

### Winner terminology note — `cross-layer winner` is acceptable only when the same model wins across all relevant winner views
- **Rule recorded:** use `cross-layer winner` only when the same model is winning across all relevant validated views for that section.
- **Required qualifier:** the paper/notebook should state the basis explicitly, e.g.:
  - experiment wins
  - aggregate gap reduction
  - aggregate efficiency
  - allocator-level aggregate gap winner (when applicable)
- **Reason:** without that qualifier, `cross-layer winner` is too loose and can be confused with a narrower winner layer.

### Winner terminology review — `Table X` first interpretation bullet updated
- **Paper file:** `GA Papers/QuantumFaultTolerant/main.tex`
- **Section:** first bullet under `Key Observations from Cross-Testbed Validation`
- **Before:** `iCPursuitNeuralUCB is the experiment winner on Papers 2, 7, and 12, but not on Paper 8.`
- **After:** `iCPursuitNeuralUCB is the cross-layer winner on Papers 2, 7, and 12, while on Paper 8 it dominates only.`
- **Reason:** the notebook winner-type validation now shows that Papers 2/7/12 align across experiment wins and dominance, while Paper 8 separates experiment wins from aggregate dominance.

### Winner terminology review — `Table X` second interpretation bullet clarified
- **Paper file:** `GA Papers/QuantumFaultTolerant/main.tex`
- **Before:** `Scenario-aggregated ranking does not fully determine configuration-level winners. ...`
- **After:** `Experiment threat ranking does not fully determine experiment-level dominance. ...`
- **Clarifications added:**
  - `dominance` is explicitly tied to `scenario-aggregated efficiency`
  - `2/5` and `3/5` are explicitly `threat scenarios`
  - `10/20` is explicitly `allocator--threat-scenario configurations`
- **Notebook decision capture added:** the `Table X` section now includes a `Table X Wording Decisions` note that records why:
  - `cross-layer winner` is valid for `Papers 2/7/12`
  - `Paper 8` must remain separated as a split winner-type case
  - `dominance` in this section means `scenario-aggregated efficiency`

### Winner terminology review — `Table X` third interpretation bullet clarified
- **Paper file:** `GA Papers/QuantumFaultTolerant/main.tex`
- **Before:** `Paper 12 exhibits the broadest winner overlap across scenarios. ...`
- **After:** `Paper 12 exhibits the broadest overlap in threat-scenario winners. ...`
- **Clarifications added:**
  - `scenario` wording tightened to `threat scenario`
  - the `Paper 7` contrast now says `threat-scenario championship`
  - `markov` sharing is explicitly described as `markov experiment wins`

### Winner terminology review — `Table X` fourth interpretation bullet clarified
- **Paper file:** `GA Papers/QuantumFaultTolerant/main.tex`
- **Before:** `... produces a more competitive EXP/iCP split than the strong iCP dominance seen on Paper 7.`
- **After:** `... extends the testbed (default allocator) winner story: the compact 20-node, 8-path Paper 8 network splits \texttt{EXPNeuralUCB} experiment wins from \texttt{iCPursuitNeuralUCB} dominance, unlike the strong \texttt{iCPursuitNeuralUCB} cross-layer-winner pattern seen on Paper 7.`
- **Reason:** the sentence now uses approved model names, keeps the Paper 8 split explicit, and records that the testbed winner framing here is anchored to the default allocator.

### Winner terminology review — `Table X` fifth interpretation bullet clarified
- **Paper file:** `GA Papers/QuantumFaultTolerant/main.tex`
- **Before:** `\texttt{CPursuitNeuralUCB} never wins a scenario on Paper 7 yet wins 3/5 on Paper 2. ...`
- **After:** `\texttt{CPursuitNeuralUCB} never wins a threat scenario on Paper 7 yet wins 3/5 threat scenarios on Paper 2. ...`
- **Clarifications added:**
  - `scenario` wording tightened to `threat scenario`
  - `algorithm rankings` replaced with `winner structure`
  - `\texttt{iCPursuitNeuralUCB}` is explicitly named as the `cross-layer winner` on `Paper 7`

### Notebook validation — `Table XI` wording-decision note added
- **Notebook file:** `hybrid_variable_framework/Dynamic_Routing_Eval_Framework/notebooks/H-MABs_MasterDataset_VerificationHub.ipynb`
- **Added:** `Table XI Wording Decisions`
- **Captured decisions:**
  - `strongest neural model by Oracle-relative gap reduction` is valid only under the Oracle-relative gap basis
  - the notebook proof for this claim is the pair:
    - `Table XI Aggregate Gap-Reduction Proof`
    - `Table XI Allocator-Level Gap-Reduction Proof`
  - experiment-win count is not the basis for this claim
- **Validation:** notebook re-executed after adding the note

### Winner terminology review — `cross-layer winner` adopted where all winner layers align
- **Paper file:** `GA Papers/QuantumFaultTolerant/main.tex`
- **Applied replacements in `Table X`:**
  - `overall winner` → `cross-layer winner`
  - `overall-winner pattern` → `cross-layer-winner pattern`
- **Table XI adjustment:**
  - `strongest overall neural model by Oracle-relative gap reduction` → `strongest neural model by Oracle-relative gap reduction`
- **Reason:** `cross-layer winner` is now the approved term when the same model wins across all validated winner layers, while the `Table XI` claim remains specifically gap-based rather than cross-layer.

### Winner terminology review — standardized-testbed follow-up sentence aligned
- **Paper file:** `GA Papers/QuantumFaultTolerant/main.tex`
- **Before:** `... shows strong testbed dependence in both efficiency and winner structure ...`
- **After:** `... shows strong testbed dependence in both efficiency and cross-layer winning structure ...`

### Winner terminology review — future-work benchmarking sentence aligned
- **Paper file:** `GA Papers/QuantumFaultTolerant/main.tex`
- **Before:** `... testing whether pursuit-neural dominance persists ...`
- **After:** `... testing whether pursuit-neural cross-layer winning structure persists ...`

### Winner terminology review — stale figure caption fixed
- **Paper file:** `GA Papers/QuantumFaultTolerant/main.tex`
- **Before:** `Global win share under the default allocator ...`
- **After:** `Win dominance under the default allocator ...`

### Applied the medium-priority `RQ2` average-efficiency correction for `EXPNeuralUCB`
- **Paper file:** `GA Papers/QuantumFaultTolerant/main.tex`
- **Before:** `EXPNeuralUCB & 82.4 & 15.1 & 18.0 & 30.5`
- **After:** `EXPNeuralUCB & 83.1 & 15.1 & 18.0 & 30.5`
- **Reason:** this row was already approved earlier (`82.4 -> 83.12` is a small but real source-backed difference), but the manuscript had not been updated.
- **Notebook sync:** re-executed the verification notebook so the `RQ2 / EXPNeuralUCB / Avg Eff. (%)` medium discrepancy is no longer open.

### Applied the approved `RQ1` medium-fix group for 3-run values
- **Paper file:** `GA Papers/QuantumFaultTolerant/main.tex`
- **Applied rows:**
  - `EXPUCB / 3 Runs`: `76.2 -> 75.5`
  - `CEXP4 / 3 Runs`: `70.1 -> 69.2`
  - `CThompsonSampling / 3 Runs`: `66.6 -> 65.7`
  - `iCThompsonSampling / 3 Runs`: `66.5 -> 65.7`
- **Notebook sync:** updated the `RQ1` expected values and marked these four discrepancies as fixed in `H-MABs_MasterDataset_VerificationHub.ipynb`.
- **Validation:** re-executed the notebook after the sync.

### Applied the remaining approved `RQ1` medium-fix group
- **Paper file:** `GA Papers/QuantumFaultTolerant/main.tex`
- **Applied rows:**
  - `iCEXP4 / 3 Runs`: `37.4 -> 36.9`
  - `iCEpsilonGreedy / 5 Runs`: `88.6 -> 87.9`
  - `GNeuralUCB / 5 Runs`: `86.3 -> 85.5`
  - `EXPUCB / 5 Runs`: `78.4 -> 77.8`
  - `CEXP4 / 5 Runs`: `70.2 -> 69.3`
  - `CThompsonSampling / 5 Runs`: `68.1 -> 67.3`
  - `iCThompsonSampling / 5 Runs`: `68.0 -> 67.2`
  - `iCEXP4 / 5 Runs`: `37.4 -> 36.8`
- **Notebook sync:** updated the `RQ1` expected values and marked these discrepancies as fixed in `H-MABs_MasterDataset_VerificationHub.ipynb`.
- **Validation:** re-executed the notebook after the sync.

### Final notebook sync — cleared stale open medium rows
- **Notebook file:** `hybrid_variable_framework/Dynamic_Routing_Eval_Framework/notebooks/H-MABs_MasterDataset_VerificationHub.ipynb`
- **Fix applied:** updated `rq2_expected` so `EXPNeuralUCB / Avg Eff. (%)` now uses the patched paper value `83.1` and marked that row as fixed.
- **Validation:** re-executed the notebook and confirmed there are now `0` `Medium / 🔴 Open` rows remaining in the saved notebook outputs.

### Applied the approved low-priority audit batch
- **Paper file:** `GA Papers/QuantumFaultTolerant/main.tex`
- **RQ1 low fixes applied:**
  - `CPursuit / 3 Runs`: `89.6 -> 90.0`
  - `iCEpsilonGreedy / 3 Runs`: `88.0 -> 87.8`
  - `CEpsilonGreedy / 3 Runs`: `87.5 -> 87.9`
  - `EXPNeuralUCB / 3 Runs`: `82.1 -> 82.1` (source `82.05`, no visible one-decimal change)
  - `CEpochGreedy / 3 Runs`: `37.6 -> 37.5`
  - `iCEpochGreedy / 3 Runs`: `37.5 -> 37.2`
  - `CPursuit / 5 Runs`: `90.1 -> 90.2`
  - `CEpsilonGreedy / 5 Runs`: `87.9 -> 87.8`
  - `CEpochGreedy / 5 Runs`: `37.6 -> 37.5`
  - `iCEpochGreedy / 5 Runs`: `37.5 -> 37.2`
- **RQ2 low fixes applied:**
  - `CPursuit / Avg Eff. (%)`: `88.1 -> 88.0`
  - `iCEpsilonGreedy / Avg Eff. (%)`: `86.9 -> 86.8`
  - `EXPUCB / Avg Eff. (%)`: `76.3 -> 76.4`
  - `CPursuit / CV (%)`: `5.3 -> 5.6`
  - `iCEpsilonGreedy / CV (%)`: `3.6 -> 3.7`
  - `EXPUCB / CV (%)`: `6.0 -> 6.0` (source `6.01`, no visible one-decimal change)
  - `CPursuit / Floor (%)`: `77.4 -> 77.4` (source `77.37`, no visible one-decimal change)
  - `iCEpsilonGreedy / Floor (%)`: `81.0 -> 81.0` (source `80.98`, no visible one-decimal change)
  - `EXPNeuralUCB / Floor (%)`: `18.0 -> 18.0` (source `18.01`, no visible one-decimal change)
  - `EXPUCB / Floor (%)`: `68.8 -> 68.8` (source `68.75`, no visible one-decimal change)
- **Notebook sync:** updated the expected-value cells and solved-key sets for `RQ1` and `RQ2`, re-executed the notebook, and confirmed there are now `0` `Open` rows in the saved outputs.
