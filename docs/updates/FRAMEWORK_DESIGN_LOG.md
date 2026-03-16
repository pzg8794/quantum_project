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

### 2026-03-13 — Validation-rate columns should be absolute-magnitude by default

**Decision**
- In the verification hub, normalized error-rate columns should use absolute magnitude unless the sign is itself analytically meaningful.

**Applied result**
- The RQ2 audit tables now use `|Δ| / Expected (%)`.
- The RQ2 winner-accounting tables now use `|Δ| vs Paper Win Dominance`.
- Raw `Δ` remains signed where it is still useful to see direction.

### 2026-03-13 — RQ3a must be validated against the caption-faithful scope before provenance guessing

**Decision**
- `tab:rq3a_informative` must follow the same source-first workflow used for `TABLE V` and `TABLE VI`:
  1. lock the caption-faithful source scope
  2. reconstruct the paper-facing table from source
  3. validate the surrounding statements from that reconstruction
  4. only then run a provenance diagnostic if the paper values do not match

**Applied result**
- The verification notebook now contains an RQ3a section that does exactly that.
- The caption-faithful reconstruction from `Hybrid / Default / T / s=2 / 6000 / runs 3+5 mean` does not support the current manuscript values or the `+18.3 pp` OnlineAdaptive claim.
- The provenance diagnostic identifies `runs = 3` only as the closest matching source candidate, which strongly suggests a caption/derivation mismatch in the paper.

### 2026-03-13 — RQ3a needs an explicit alternative 6K horizon diagnostic

**Decision**
- Because the paper text says `6K horizon` while the source corpus is organized as `4K base` with `2K` stepping, the verification hub must preserve an explicit alternative diagnostic branch for `4000 + 6000`, `runs = 3`, even if that branch is not the best provenance match.

**Applied result**
- The notebook now includes that branch and compares it directly against:
  - the caption-faithful `6000 / runs 3+5 mean` reconstruction
  - the best provenance candidate `6000 / runs 3 only`
- The branch does not fully resolve the mismatch, but it is kept because it is a plausible interpretation of the paper wording and it narrows the provenance search cleanly.

### 2026-03-13 — RQ3a also needs a `Tb` exclusion check

**Decision**
- Before correcting the paper, the RQ3a provenance search must also exclude the possibility that the table was accidentally drawn from `Tb` rather than `T`.

**Applied result**
- The notebook now contains the same branch search under `Tb`.
- None of the `Tb` branches beats the best `T` candidate.
- This narrows the likely source further:
  - not `T / 6000 / runs 3+5 mean`
  - not `Tb`
  - strongest current candidate remains `T / 6000 / runs 3 only`

### 2026-03-13 — RQ3a paper patch must follow the strongest source-backed provenance branch

**Decision**
- Correct `tab:rq3a_informative` using the strongest validated provenance branch instead of the caption-faithful but unsupported `3+5` mean.
- For the current manuscript, that branch is:
  - `Hybrid`
  - `Default` / paper wording `Fixed`
  - `T`
  - `s = 2`
  - `frames = 6000`
  - `runs = 3` only

**Applied result**
- The paper now uses the 3-run suite wording in the RQ3a setup sentence and caption.
- The two table rows were updated to the validated source values for that branch.
- The high-priority claim fixes are now explicit:
  - `OnlineAdaptive` lift remains `+18.3 pp`
  - cross-scenario dispersion is stated as `CV_scen: 6.5 -> 3.3`

### 2026-03-15 — pandas is correct; workflow regression was in notebook structure and formatting

**Decision**
- Keep pandas as the canonical manipulation layer in the verification hub.
- Restore and preserve the review workflow on top of pandas:
  - discrepancy color coding
  - `B - A` / `|B - A|` severity tracking
  - end-of-analysis summaries
  - `🔴 Pending high tasks` / `🟢 Solved high tasks`

**Finding**
- The current GitHub notebook variant had regressed in two ways:
  1. it removed the audit formatting/status layer
  2. it also dropped the later source-first sections for `RQ3a`, `RQ3b`, `RQ3c`, `RQ3d`, `Table X`, and `Table XI`

**Applied result**
- The current notebook file again exposes the workflow layer for the sections still present (`RQ1`, `RQ2`).
- The notebook also now states explicitly that the later sections are missing and require restoration, so notebook state is not silently overstated relative to `main.tex` and the markdown logs.

### 2026-03-15 — validated `RQ3` / `Table X` / `Table XI` notebook sections restored from snapshot exports

**Decision**
- Restore the missing notebook sections on top of pandas using the approved validation snapshot bundle, rather than reintroducing pre-pandas logic or silently leaving the notebook incomplete.

**Applied result**
- Recovered `RQ3a`, `RQ3b`, `RQ3c`, `RQ3d`, `Table X`, and `Table XI` into `H-MABs_MasterDataset_VerificationHub.ipynb`.
- Kept the same workflow layer across the restored sections:
  - discrepancy color coding
  - severity tracking via `B - A` / `|B - A|`
  - end-of-analysis summaries
  - `🔴 Pending high tasks` / `🟢 Solved high tasks`
- Preserved the source-first validation structure where it matters:
  - `Table X` split by testbed
  - `Table XI` split by source world
- Executed the full notebook successfully after recovery.

### 2026-03-15 — winner terminology now needs a paper-wide integrity pass

**Decision**
- With the numeric/table high-priority backlog cleared, the next review target is terminology consistency around `winner` / `winning` language.

**Why**
- The paper now contains several distinct winner-like concepts that are all valid, but not interchangeable:
  - global win-share figure semantics
  - `Win Dominance (%)` in `TABLE VI`
  - experiment-level winners in `TABLE X` / `TABLE XI`
  - scenario champions from `scenario_winner`
  - aggregate leadership by Oracle-relative gap reduction

**Execution rule**
- Review and, if needed, patch these locations one by one using the explicit handoff format:
  - `Task`
  - `Meaning`
  - `Before`
  - `After`
- Do not batch-edit this terminology across the paper without section-by-section review.

### 2026-03-15 — figure winner-frequency label should reflect the existing `Win Dominance` decision

**Decision**
- The winner-frequency figure should not keep the older `Global Win Share (%)` label once the paper has already standardized the RQ2 table terminology to `Win Dominance (%)`.
- `Global` is also unnecessary here because the figure scope is already clear from context.

**Applied result**
- Updated the figure y-axis label in `GA Papers/QuantumFaultTolerant/main.tex`:
  - `Global Win Share (%)` → `Win Dominance (%)`
- Updated the legend entry:
  - `Top-5 win share (default allocator)` → `Top-5 win dominance (default allocator)`

### 2026-03-15 — RQ2 in-family winner sentence should not force an unnecessary contrast

**Decision**
- The RQ2 in-family winner sentence should keep the scoped winner claim and drop the unnecessary `while iCPursuit is not` contrast.

**Applied result**
- Updated the sentence to:
  - `iCEpsilonGreedy is the consistent winner (100% in-family win rate) under the same adversarial scope.`

### 2026-03-15 — winner-type basis should be explicit in notebook validation for `Table X` and `Table XI`

**Decision**
- The notebook should not leave winner claims implicit for the cross-testbed and model-family sections.
- It now needs explicit per-instance winner-type tables that separate:
  - experiment-win-count winners
  - aggregate gap-reduction winners
  - aggregate efficiency winners
  - allocator-level aggregate gap winners where applicable

**Applied result**
- Added per-testbed winner-type tables to `Table X` in `H-MABs_MasterDataset_VerificationHub.ipynb`.
- Added per-source winner-type tables to `Table XI` in the same notebook.
- This makes the validation basis explicit before any further wording cleanup in `main.tex`.

### 2026-03-15 — `cross-layer winner` should be reserved for multi-basis winner agreement

**Decision**
- The phrase `cross-layer winner` is acceptable only when the same model wins across all relevant validated winner views for the section under discussion.
- The basis must be stated explicitly.

**Required basis examples**
- experiment wins
- aggregate gap reduction
- aggregate efficiency
- allocator-level aggregate gap winner

### 2026-03-15 — `Table X` first bullet should use `cross-layer winner` for Papers 2/7/12 and isolate Paper 8 as dominance-only

**Applied result**
- Updated the first `Table X` interpretation bullet in `GA Papers/QuantumFaultTolerant/main.tex`:
  - `iCPursuitNeuralUCB is the experiment winner on Papers 2, 7, and 12, but not on Paper 8.`
  - → `iCPursuitNeuralUCB is the cross-layer winner on Papers 2, 7, and 12, while on Paper 8 it dominates only.`

### 2026-03-15 — `Table X` second bullet should separate experiment-level dominance from threat-scenario wins

**Applied result**
- Updated the second `Table X` interpretation bullet in `GA Papers/QuantumFaultTolerant/main.tex` so it now states:
  - `Experiment threat ranking does not fully determine experiment-level dominance.`
- The supporting sentence now explicitly defines dominance as `scenario-aggregated efficiency` and threat wins as `threat scenarios` / `allocator--threat-scenario configurations`.
- Added the same `Table X` wording-decision capture to the verification notebook so the paper fix is backed by the notebook narrative, not only the markdown logs.

### 2026-03-15 — `Table X` third bullet should use threat-scenario winner language explicitly

**Applied result**
- Updated the third `Table X` interpretation bullet in `GA Papers/QuantumFaultTolerant/main.tex`.
- `winner overlap across scenarios` is now `overlap in threat-scenario winners`.
- The `Paper 7` contrast now uses `threat-scenario championship`, and the `markov` exception is explicitly tied to experiment wins.

### 2026-03-15 — `Table X` fourth bullet should frame Paper 8 as a default-allocator winner split

**Applied result**
- Updated the fourth `Table X` interpretation bullet in `GA Papers/QuantumFaultTolerant/main.tex`.
- The sentence now states that Paper 8 extends the `testbed (default allocator) winner story` and explicitly separates:
  - `EXPNeuralUCB` experiment wins
  - `iCPursuitNeuralUCB` dominance
- Non-approved shorthand (`iCP`, `EXP/iCP`) was removed.

### 2026-03-15 — `Table X` fifth bullet should use threat-scenario wording and explicit cross-layer-winner language

**Applied result**
- Updated the fifth `Table X` interpretation bullet in `GA Papers/QuantumFaultTolerant/main.tex`.
- The sentence now explicitly says:
  - `threat scenario`
  - `winner structure`
  - `\texttt{iCPursuitNeuralUCB}` as the `cross-layer winner` on `Paper 7`

### 2026-03-15 — `Table XI` wording decision should be captured in the notebook, not only in prose

**Applied result**
- Added a `Table XI Wording Decisions` note to `H-MABs_MasterDataset_VerificationHub.ipynb`.
- The note records that the `strongest neural model by Oracle-relative gap reduction` claim is supported by Oracle-relative aggregate gap reduction and allocator-level aggregate gap retention, not by experiment-win count.

### 2026-03-15 — `cross-layer winner` replaces `overall winner` where the meaning is full winner-layer agreement

**Applied result**
- Updated `Table X` wording in `GA Papers/QuantumFaultTolerant/main.tex` to use `cross-layer winner` / `cross-layer-winner pattern`.
- Narrowed the `Table XI` claim wording to `strongest neural model by Oracle-relative gap reduction` so it does not imply cross-layer proof where the validated basis is specifically gap-based.

### 2026-03-15 — standardized-testbed follow-up should use `cross-layer winning structure`

**Applied result**
- Updated the standardized-testbed follow-up sentence in `GA Papers/QuantumFaultTolerant/main.tex`.
- `winner structure` is now `cross-layer winning structure`.

### 2026-03-15 — future-work benchmarking sentence should use `cross-layer winning structure`

**Applied result**
- Updated the standardized cross-testbed benchmarking sentence in `GA Papers/QuantumFaultTolerant/main.tex`.
- `pursuit-neural dominance persists` is now `pursuit-neural cross-layer winning structure persists`.

### 2026-03-15 — stale figure caption should use `Win dominance`

**Applied result**
- Updated the figure caption in `GA Papers/QuantumFaultTolerant/main.tex`:
  - `Global win share under the default allocator ...`
  - → `Win dominance under the default allocator ...`

### 2026-03-15 — approved `RQ2` average-efficiency fix for `EXPNeuralUCB` applied

**Applied result**
- Updated `GA Papers/QuantumFaultTolerant/main.tex`:
  - `EXPNeuralUCB & 82.4 & 15.1 & 18.0 & 30.5`
  - → `EXPNeuralUCB & 83.1 & 15.1 & 18.0 & 30.5`
- This reflects the approved source-backed `83.12` value at one-decimal paper precision.

### 2026-03-15 — approved `RQ1` 3-run medium-fix group applied

**Applied result**
- Updated `GA Papers/QuantumFaultTolerant/main.tex` for the approved `RQ1 / TABLE V` medium discrepancies:
  - `EXPUCB / 3 Runs`: `76.2 -> 75.5`
  - `CEXP4 / 3 Runs`: `70.1 -> 69.2`
  - `CThompsonSampling / 3 Runs`: `66.6 -> 65.7`
  - `iCThompsonSampling / 3 Runs`: `66.5 -> 65.7`
- Synced the notebook expectations and fixed-status mapping to match.

### 2026-03-15 — remaining approved `RQ1` medium-fix group applied

**Applied result**
- Updated `GA Papers/QuantumFaultTolerant/main.tex` for the remaining approved `RQ1 / TABLE V` medium discrepancies:
  - `iCEXP4 / 3 Runs`: `37.4 -> 36.9`
  - `iCEpsilonGreedy / 5 Runs`: `88.6 -> 87.9`
  - `GNeuralUCB / 5 Runs`: `86.3 -> 85.5`
  - `EXPUCB / 5 Runs`: `78.4 -> 77.8`
  - `CEXP4 / 5 Runs`: `70.2 -> 69.3`
  - `CThompsonSampling / 5 Runs`: `68.1 -> 67.3`
  - `iCThompsonSampling / 5 Runs`: `68.0 -> 67.2`
  - `iCEXP4 / 5 Runs`: `37.4 -> 36.8`
- Synced the notebook expectations and fixed-status mapping to match.

### 2026-03-15 — final notebook sync should clear stale medium-open status rows

**Applied result**
- Updated the `RQ2` expected-value block in `H-MABs_MasterDataset_VerificationHub.ipynb` so `EXPNeuralUCB / Avg Eff. (%)` matches the patched paper value.
- Re-executed the notebook and verified that no `Medium / Open` rows remain in the saved outputs.

### 2026-03-16 — approved low-priority audit batch applied and notebook fully synced

**Applied result**
- Updated `GA Papers/QuantumFaultTolerant/main.tex` with the approved low-priority rounding-level fixes for `RQ1 / TABLE V` and `RQ2 / TABLE VI`.
- Synced `H-MABs_MasterDataset_VerificationHub.ipynb` so the expected values and solved/open status match the paper.
- Re-executed the notebook and verified that no `Open` rows remain in the saved outputs.
