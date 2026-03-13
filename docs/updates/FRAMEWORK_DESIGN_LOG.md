## Framework Design Log (Decisions + Protocol)

Purpose: capture **design decisions, working protocol, and framing** that guide future changes.

This log is intentionally lightweight:
- record decisions/agreements (not raw chat)
- use dated entries
- link to the doc(s) that define the current contract

---

### 2026-03-05 — Ownership narrative + “framework of frameworks” protocol

**Narrative model (shared vocabulary)**
- `configs` = **the sun** (shared context; visible everywhere; not uniquely “owned”).
- Allocator = **world** (defines routing/qubit-allocation conditions; worlds differ).
- Threat scenarios = **shared aerospace** (same scenario suite across worlds for fair comparison).
- Evaluator = **continent** (evaluates/aggregates performance across experiments under one scope).
- Runner = **country** (one experiment instance; must be consistent across models).
- Models = **workers** (operate inside the same country; fairness requires shared environment instance).

Source: `docs/guides/STATE_LAYERS_AND_RESUME.md`

**Working protocol (non-negotiable)**
- No code changes until design intent is confirmed with the system designer (Piter).
- For any fix that changes behavior, first identify the **owner object** and its **contract**.
- Prefer the smallest localized change; avoid refactors unless explicitly requested.
- Keep code short + reusable; do not duplicate state-discovery logic across layers.

**Environment vs ownership**
- The environment “resides” wherever we instantiate/call it.
- “Ownership” can be defined at two levels:
  - **Implementation owner (current):** where the behavior lives today (e.g., `QuantumEnvironment` + physics helpers).
  - **Conceptual ownership:** intentionally left open; validated by results as the framework evolves.

**Entanglement phase (language to use)**
- We can implement entanglement-related behavior inside current modules, but we do not claim final conceptual ownership yet.
- Stability first; entanglement architecture decisions are deferred until evidence constrains the right boundary.

### 2026-03-06 — Evaluator-state consumer contract must be preserved

**Decision**
- Treat `state_analysis.py` as a regression harness for evaluator-state compatibility.
- Do not weaken the consumer contract just because producer payload drifted.
- Improve or migrate evaluator payloads compatibly; do not delete analysis-only attributes that downstream tooling still depends on.

**Observed issue**
- Current evaluator states include placeholder `env_experiments["n/a"]`, while `evaluation_results["scenarios_results"]` does not contain `n/a`.
- The active extractor then fails on `all_model_metrics` depending on scenario iteration order.

**Canonical reference**
- `docs/guides/STATE_ANALYSIS_EVALUATOR_CONTRACT.md`

### 2026-03-12 — Plotting helpers must use explicit semantic arguments

**Decision**
- Plotting helpers with multiple optional parameters must be called with explicit keyword arguments when the arguments have different semantics.
- Do not rely on positional calls where a scenario-data key can be misread as a reward-type selector.

**Observed issue**
- `plot_scenarios_comparison(...)` called `_plot_reward_evolution(...)` positionally and passed `scenario_data` into the `reward_type` slot.
- Result: per-scenario robustness plots lost the reward-evolution panel even though the main comparison plot rendered it correctly.

**Applied protocol**
- use `reward_type='reward_list'` and `scen_data=...` explicitly
- make helper methods validate semantic selectors and fail safe
- keep plot metadata (titles) consistent with output filenames and allocator context

### 2026-03-12 — Paper validation should be notebook-first and source-backed

**Decision**
- The paper-validation workflow should be centered on one notebook in `Dynamic_Routing_Eval_Framework/notebooks/`, not scattered only across ad hoc scripts.
- Only artifacts backed directly by `Validated_Logs/Master_Dataset_*.csv` enter phase 1 of the validation hub.
- Anything not source-backed by the master datasets is marked `TBD` until its derivation path is formalized.

**Canonical reference**
- `docs/guides/MASTER_DATASET_VALIDATION_HUB_PLAN.md`

### 2026-03-12 — RQ1 stochastic table must surface source ambiguity, not hide it

**Decision**
- The validation hub must not silently choose a source dataset when a paper row is not reproduced cleanly by the current master datasets.
- For `tab:rq1masterstochastic`, stable rows are reproduced directly; neural rows are treated as a reconciliation checkpoint until the source choice is locked.

**Observed issue**
- The current master datasets reproduce the non-neural RQ1 stochastic rows cleanly under the documented stochastic / runs / scale / capacity filters.
- The neural rows (`GNEURALUCB`, `EXPNEURALUCB`) do not reproduce from one stable family-wide source.
- Existing helper scripts disagree on the intended source mapping.

**Resolution status**
- Keep `tab:rq1masterstochastic` in a partially verified state.
- Verify stable rows now.
- Carry the neural rows as an explicit reconciliation issue until a source contract is chosen deliberately.

**Canonical reference**
- `docs/guides/MASTER_DATASET_VALIDATION_HUB_PLAN.md`

### 2026-03-12 — Verification notebook must make validation status explicit

**Decision**
- The paper-support notebook must read like a verification record, not a scratch analysis notebook.
- Each artifact section must expose verification status, source hierarchy, discrepancy posture, and environment assumptions directly in the notebook.

**Applied notebook structure**
- canonical source hierarchy
- verification standard
- artifact verification ledger
- per-artifact mapping contract
- discrepancy register

**Canonical reference**
- `Dynamic_Routing_Eval_Framework/notebooks/H-MABs_MasterDataset_VerificationHub.ipynb`

### 2026-03-12 — Verification comparisons must isolate one question at a time

**Decision**
- Do not combine multiple run counts into one audit row.
- For manuscript verification, compare one run-count at a time.
- Use only the fields needed to make the verification judgment:
  - `Model`
  - `Status`
  - `Expected`
  - `Actual`
  - `Δ`
  - `Source`
  - `Note`

**Applied result**
- `tab:rq1masterstochastic` now uses separate `3 runs` and `5 runs` audit tables in the verification notebook.

### 2026-03-12 — Master-dataset verification must aggregate sources before paper comparison

**Decision**
- For paper-facing verification, do not compare manuscript values directly against raw mixed-source aggregates.
- First aggregate each source independently.
- Then reconstruct the paper-facing artifact from those approved source tables.
- Only after that should the notebook perform `Expected` vs `Actual` checks.

**Applied result**
- The RQ1 section of `H-MABs_MasterDataset_VerificationHub.ipynb` was redesigned to show executed per-source aggregation tables for `CMABs`, `iCMABs`, `Hybrid`, and `EXP3`.
- The manuscript comparison phase for `TABLE V` is now explicitly deferred until the source aggregates are approved.

### 2026-03-12 — Narrative claims must be validated from the reconstructed source-backed table

**Decision**
- After the per-source aggregates are approved, validate the paper-facing table itself before comparing manuscript values.
- Validate nearby narrative statements directly from the reconstructed source-backed table, not from the raw master datasets in isolation.

**Applied result**
- The verification notebook now contains:
  - a row-map for `TABLE V`
  - a reconstructed source-backed `TABLE V`
  - direct statement checks for the top-tier, mid-tier, and collapsed-tier claims in the surrounding text

### 2026-03-12 — Manuscript comparison must use the reconstructed table as the actual side

**Decision**
- When auditing a paper-facing table, compare manuscript values against the reconstructed source-backed table.
- Do not compare manuscript values directly against isolated source tables once the paper-facing reconstruction exists.
- Keep the comparison one run-count at a time.

**Applied result**
- The notebook now contains:
  - `TABLE V Audit — 3 Runs`
  - `TABLE V Audit — 5 Runs`
- In both audits, the `Actual` column is populated from the reconstructed source-backed `TABLE V`.

### 2026-03-12 — Keep both flat and tiered audit views when tier structure matters

**Decision**
- When a paper table is organized by tiers, keep the flat audit table and add a tiered audit view instead of replacing one with the other.

**Applied result**
- `TABLE V` in the verification notebook now has:
  - flat `3 Runs` and `5 Runs` audit tables
  - tiered `3 Runs` and `5 Runs` audit tables following the paper tier order

### 2026-03-12 — RQ2 adversarial scope must follow the caption, not the old helper script

**Decision**
- For `TABLE VI`, the source-backed notebook must use the manuscript caption as the scope authority.
- That means the adversarial scenario set is:
  - `MARKOV`
  - `ADAPTIVE`
  - `ONLINEADAPTIVE`
- `STOCHASTIC` is excluded from the RQ2 adversarial validation path even if older helper scripts included it.

**Applied result**
- The verification notebook now contains an RQ2 source-first section with the caption-locked scope and source mapping.
- `Avg Eff.`, `CV`, and `Floor` are computed from source under that locked scope.
- `Win Share (%)` is deferred until its denominator is proven from source.

### 2026-03-12 — Validate narrative claims before reconstructing the next table

**Decision**
- For each artifact group, validate the nearby manuscript claims from source before final table reconstruction when possible.

**Applied result**
- RQ2 now follows that rule:
  - source-backed statement checks were added before reconstructing `TABLE VI`
  - the notebook now validates the average-ordering, stability/floor claim, and iCMAB in-family correction from source

### 2026-03-12 — Partial table reconstruction is allowed once the source-locked columns are known

**Decision**
- When one paper metric remains unresolved, the verification notebook may still reconstruct and audit the source-locked columns rather than blocking the whole artifact.

**Applied result**
- `TABLE VI` now has a partial reconstruction and manuscript audit for:
  - `Avg Eff. (%)`
  - `CV (%)`
  - `Floor (%)`
- `Win Share (%)` stays explicitly `TBD` until the source denominator is identified.

### 2026-03-12 — Known manuscript values should be shown even when source reproduction is unresolved

**Decision**
- If a paper value is explicitly present in the manuscript, the verification notebook should display it rather than hiding it behind `TBD`.
- `TBD` is only acceptable for the unresolved source derivation, not for a known manuscript value.

**Applied result**
- `TABLE VI` now shows the manuscript `Win Share (%)` values directly while keeping the source derivation status separate.

### 2026-03-12 — Add scope diagnostics before reasoning about derived percentages

**Decision**
- When a paper percentage column is unresolved, the notebook should first expose the exact source scope inputs that feed that percentage.

**Applied result**
- RQ2 now includes a source scope diagnostics table with per-row source, threat, allocator, run, and raw win information before the `Win Share (%)` reasoning step.

### 2026-03-12 — Diagnostics tables should show totals used in reasoning, not just unique-value counts

**Decision**
- When a notebook table is meant to support a paper-logic walkthrough, it should expose the totals the reasoning depends on.

**Applied result**
- `RQ2 Source Scope Diagnostics` now shows `Total threats`, `Total runs`, and `Total wins` instead of just distinct threat/run counts.

### 2026-03-12 — Keep RQ2 caption-faithful now, but expand later as a separate priority

**Decision**
- `TABLE VI` validation stays caption-faithful and therefore remains restricted to `MARKOV`, `ADAPTIVE`, and `ONLINEADAPTIVE`.
- A broader follow-up analysis is still required later to test whether additional patterns appear once the threat scope is expanded.

**Applied result**
- The narrower three-threat validation remains the active paper path.
- A separate mid-high priority follow-up is now recorded to expand the threat scope later.

### 2026-03-12 — High-level reasoning tables should not repeat denominators on every row

**Decision**
- When the purpose is high-level win-share reasoning, the table should show model wins and a compact ratio, plus a final total row.

**Applied result**
- `RQ2 Source Scope Diagnostics` now uses `Wins` and `Wins / Scope wins`, with a final `Total wins (shown models)` row.

### 2026-03-12 — Reasoning tables should compute ratios, not just display ratio strings

**Decision**
- If a diagnostics column is meant to support percentage reasoning, it must contain the computed numeric value.

**Applied result**
- `RQ2 Source Scope Diagnostics` now uses `Wins / All wins (%)` as a real computed percentage.

### 2026-03-12 — Win-share reconciliation should use researched candidate formulas before any manuscript rewrite

**Decision**
- When a paper-facing percentage column cannot be reproduced directly from source, the notebook should evaluate a small set of researched statistical formulas before any table rewrite is considered.

**Applied result**
- The verification hub now computes and compares:
  - micro win share
  - macro threat-balanced win share
  - Jeffreys-smoothed Dirichlet win share
- All three fail to reproduce the current `TABLE VI` manuscript values, so the issue is now isolated as manuscript-side provenance rather than a missing notebook formula.

### 2026-03-12 — Winner layers must be separated before win-share reasoning

**Decision**
- When a paper table uses winner terminology at multiple levels, the notebook must expose each layer separately before attempting to reconcile a derived percentage column.

**Applied result**
- The verification hub now separates:
  - runner / experiment-level wins
  - evaluator / scenario-level wins
  - evaluator wins split by run suite

### 2026-03-12 — Paper audits should report normalized deviation against expected values

**Decision**
- For manuscript audits, percent deviation should always be normalized by the manuscript value:
  - `(actual - expected) / expected`

**Applied result**
- The RQ2 audit tables now include `Δ / Expected (%)` alongside the raw delta.

### 2026-03-12 — Winner-accounting tables should expose deviation from paper win-share values directly

**Decision**
- If the notebook is being used to reason about manuscript `Win Share (%)`, the winner-accounting tables should carry the paper win-share reference and the normalized deviation from it.

**Applied result**
- The runner, evaluator, and per-run winner tables now include:
  - `Paper Win Share (%)`
  - `Δ vs Paper Win Share`
- The normalization now treats the notebook ratio as the accepted/actual baseline:
  - `(paper_share - actual_share) / actual_share`
- For the current review pass, rows with `actual_share = 0.0` are forced to `0.0` instead of left undefined

### 2026-03-12 — Win-share provenance must be documented at the paper-usage level

**Decision**
- Before changing or replacing a paper-facing win-share column, the notebook must record exactly where the manuscript uses `Win Share` and whether each use defines its own denominator.

**Applied result**
- The verification hub now documents that:
  - `fig:global_win_share` has an explicit rule
  - `TABLE VI` does not

### 2026-03-12 — `Win Share` severity should be split into correctness risk vs manuscript blast radius

**Decision**
- A paper-facing metric can be high priority to correct while still being low-scope to rewrite if the surrounding prose does not depend on it.

**Applied result**
- The verification hub now records that `TABLE VI` `Win Share (%)` is:
  - high priority for correctness
  - localized in manuscript impact

### 2026-03-12 — Prefer configuration-level win rate over ambiguous pooled win share in TABLE VI

**Decision**
- If `TABLE VI` keeps a winner-frequency column, it should use a configuration-level win rate with an explicit denominator rather than an undefined win-share percentage.

**Applied result**
- The verification hub now recommends:
  - `Configuration Win Rate (%)`
  - based on evaluator-level `scenario_winner`
  - over unique `(scenario, runs, scale, cap_type)` configurations

### 2026-03-13 — `TABLE VI` should use `Win Dominance (%)`, not `Configuration Win Rate (%)`

**Decision**
- The earlier win-rate recommendation was too generic for what `TABLE VI` is trying to argue.
- For this table, the right source-backed quantity is **`Win Dominance (%)`**: each displayed model’s share of aggregated scenario wins among the four displayed RQ2 representatives under the locked adversarial scope.

**Applied result**
- `main.tex` `tab:rq2_adversarial` now uses `Win Dominance (%)` with an explicit caption definition.
- The source-backed values are:
  - `CPursuit = 25.6`
  - `iCEpsilonGreedy = 43.9`
  - `EXPNeuralUCB = 30.5`
  - `EXP3/UCB = 0.0`
- The literature framing remains unchanged because this is a localized table-column correction, not a change to the paper’s external positioning.
