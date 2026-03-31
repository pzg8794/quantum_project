# Master Dataset Validation Hub Plan

This note defines the plan for a source-backed validation notebook that reproduces or validates the paper findings directly from the master datasets.

Purpose:

1. create one notebook that acts as the paper-validation hub,
2. validate the findings in `GA Papers/QuantumFaultTolerant/main.tex` directly from `Validated_Logs/Master_Dataset_*.csv`,
3. keep the workflow explicit and reusable for future papers and future master datasets.

## Canonical Source Hierarchy

Use this hierarchy in order:

1. **Paper source of truth**
   - `GA Papers/QuantumFaultTolerant/main.tex`
2. **Master datasets**
   - `Validated_Logs/Master_Dataset_*.csv`
3. **Existing validation scripts**
   - `Validated_Logs/validate_paper.py`
   - `Validated_Logs/validate_full_paper.py`
   - `Validated_Logs/internal_table_data.py`
4. **Validation notebook target**
   - `hybrid_variable_framework/Dynamic_Routing_Eval_Framework/notebooks/`

Rule:

- if a table or figure is backed by a master dataset, the notebook should compute or verify it from the dataset before we trust the manuscript value
- if an artifact is not backed by a master dataset, mark it `TBD` and defer it

## Proposed Notebook Placement

Recommended location:

- `hybrid_variable_framework/Dynamic_Routing_Eval_Framework/notebooks/`

Recommended notebook role:

- one PhD-level validation notebook that functions as a **validation hub**
- not an exploratory scratch notebook
- not a paper-writing notebook
- a reproducible evidence notebook tied to the master datasets

Recommended notebook name:

- `H-MABs_MasterDataset_VerificationHub.ipynb`

Rationale:

- this keeps the notebook with the other framework notebooks
- it keeps the evidence workflow close to the framework/testbed execution flow
- it avoids scattering paper-validation logic into `Validated_Logs/*.py` scripts only

## Scope Policy

### Include Now

Artifacts that are backed directly by master datasets:

- `tab:rq1masterstochastic`
- `fig:context_capacity_effects`
- `tab:rq2_adversarial`
- `fig:scenario_penalties`
- `fig:capacity_all`
- `fig:threat_rules`
- `tab:rq3a_informative`
- `tab:rq3b_capacity_scaling`
- `tab:rq3c_allocators`
- `tab:testbed_comparison`
- `tab:model_family_comparison`

### Mark as TBD

Artifacts that are not currently cleanly backed by the master datasets:

- `fig:convergence_hybrid`

TBD rule:

- leave a clearly labeled section in the notebook
- state why it is deferred
- identify what data would be required to validate it later

## Artifact Inventory (Step 1 Complete)

### Internal-Corpus Artifacts

1. `tab:rq1masterstochastic`
   - source datasets:
     - `Validated_Logs/Master_Dataset_CMABs.csv`
     - `Validated_Logs/Master_Dataset_iCMABs.csv`
     - `Validated_Logs/Master_Dataset_Hybrid.csv`
     - `Validated_Logs/Master_Dataset_EXP3.csv`
   - status:
     - directly reproducible

2. `fig:context_capacity_effects`
   - source datasets:
     - same four internal master datasets
   - status:
     - reproducible from aggregated scenario-family means

3. `tab:rq2_adversarial`
   - source datasets:
     - `Validated_Logs/Master_Dataset_CMABs.csv`
     - `Validated_Logs/Master_Dataset_iCMABs.csv`
     - `Validated_Logs/Master_Dataset_EXP3.csv`
   - status:
     - directly reproducible

4. `fig:scenario_penalties`
   - source datasets:
     - same RQ2 datasets
   - status:
     - reproducible from baseline-minus-threat penalty calculations

5. `fig:capacity_all`
   - source dataset:
     - `Validated_Logs/Master_Dataset_Hybrid.csv`
   - status:
     - reproducible

6. `fig:threat_rules`
   - source dataset:
     - `Validated_Logs/Master_Dataset_Hybrid.csv`
   - status:
     - reproducible

7. `tab:rq3a_informative`
   - source dataset:
     - `Validated_Logs/Master_Dataset_Hybrid.csv`
   - status:
     - directly reproducible

8. `tab:rq3b_capacity_scaling`
   - source dataset:
     - `Validated_Logs/Master_Dataset_Hybrid.csv`
   - status:
     - directly reproducible

9. `tab:rq3c_allocators`
   - source dataset:
     - `Validated_Logs/Master_Dataset_Hybrid.csv`
   - status:
     - directly reproducible

### External-Testbed Artifacts

10. `tab:testbed_comparison`
    - source datasets:
      - `Validated_Logs/Master_Dataset_paper2_4000_2000_5_ST.csv`
      - `Validated_Logs/Master_Dataset_paper7_50_50_5_ST.csv`
      - `Validated_Logs/Master_Dataset_paper12_1500_500_5_ST.csv`
      - `Validated_Logs/Master_Dataset_1000_1000_1_paper8.csv`
    - status:
      - directly reproducible

11. `tab:model_family_comparison`
    - source datasets:
      - all four internal master datasets
      - all four external testbed master datasets
    - status:
      - directly reproducible

### Deferred Artifact

12. `fig:convergence_hybrid`
    - current status:
      - `TBD`
    - reason:
      - caption already identifies it as illustrative
      - not currently backed by a clean master-dataset derivation path

## Incremental Execution Protocol

We will build this notebook in small validated stages:

1. inventory artifacts
2. map one artifact group to exact dataset logic
3. implement one notebook section
4. verify that section against the paper
5. document the result in `.md` files
6. move to the next artifact group

This protocol is mandatory because:

- discrepancies are expected
- we need to troubleshoot them before they propagate
- the notebook must become a durable validation reference, not just a one-off script

## Planned Notebook Section Structure

1. Title and objective
2. Reproducibility setup
3. Data inventory
4. Artifact validation map
5. Internal-corpus tables
6. Internal-corpus figures
7. External-testbed tables
8. Deferred/TBD artifacts
9. Validation summary and discrepancy log
10. Next actions

## Existing Helper Scripts We Should Reuse

These scripts already contain useful validation logic and should be mined before we rewrite formulas:

- `Validated_Logs/validate_paper.py`
- `Validated_Logs/validate_full_paper.py`
- `Validated_Logs/internal_table_data.py`

Use policy:

- reuse the logic
- do not blindly trust the current outputs
- make the notebook cells explicit enough that each computation is auditable

## Documentation Requirements

Whenever we advance this notebook work:

1. update this plan
2. update `docs/INDEX.md`
3. update the relevant change/design logs
4. keep references hierarchical so the notebook, datasets, scripts, and paper can be navigated quickly

## Current Next Step

Step 3:

- resolve and lock the neural-row source choice for `tab:rq1masterstochastic`
- then scaffold the first notebook section only for the RQ1 stochastic table

No notebook scaffolding should happen before the source ambiguity is recorded.

## Step 2 Complete — `tab:rq1masterstochastic`

### Target artifact

- label:
  - `tab:rq1masterstochastic`
- paper location:
  - `GA Papers/QuantumFaultTolerant/main.tex`
- expected rendered shape:
  - `13` model rows
  - columns: `Model`, `3 Runs`, `5 Runs`, `Avg. Eff.`
  - plus three narrative tier separators:
    - `Top tier (viable under stochastic)`
    - `Mid-tier (degraded)`
    - `Collapsed (structural failure)`

### Source datasets

- `Validated_Logs/Master_Dataset_CMABs.csv`
- `Validated_Logs/Master_Dataset_iCMABs.csv`
- `Validated_Logs/Master_Dataset_Hybrid.csv`
- `Validated_Logs/Master_Dataset_EXP3.csv`

### Core filters

Apply these filters before any aggregation:

- `scenario == 'STOCHASTIC'`
- `runs in {3, 5}`
- `model != 'ORACLE'`
- include all allocators present in the corpus
- include replay scales `1.0`, `1.5`, `2.0`
- include both capacity semantics:
  - `T`
  - `Tb`

### Aggregation rule

For each retained model row:

1. filter to the relevant source dataset
2. filter to the target `runs` value (`3` or `5`)
3. compute the arithmetic mean of `eff_pct`
4. round for presentation to one decimal place

For the `Avg. Eff.` column:

1. take the unrounded `3`-run and `5`-run means for the model
2. compute their arithmetic mean
3. round for presentation to one decimal place

### Stable source mapping

These rows map cleanly to one source dataset today:

- `CPURSUIT` → `Master_Dataset_CMABs.csv`
- `CEPSILONGREEDY` → `Master_Dataset_CMABs.csv`
- `CTHOMPSONSAMPLING` → `Master_Dataset_CMABs.csv`
- `CEXP4` → `Master_Dataset_CMABs.csv`
- `CEPOCHGREEDY` → `Master_Dataset_CMABs.csv`
- `ICEPSILONGREEDY` → `Master_Dataset_iCMABs.csv`
- `ICPURSUIT` → `Master_Dataset_iCMABs.csv`
- `ICTHOMPSONSAMPLING` → `Master_Dataset_iCMABs.csv`
- `ICEXP4` → `Master_Dataset_iCMABs.csv`
- `ICEPOCHGREEDY` → `Master_Dataset_iCMABs.csv`
- `EXPUCB` → `Master_Dataset_EXP3.csv`

### Unresolved source mapping

The neural rows are not source-stable yet:

- `GNEURALUCB`
- `EXPNEURALUCB`

Current evidence:

- `Validated_Logs/validate_full_paper.py` treats the RQ1 table as a direct stochastic mean over the source corpus, but the hardcoded row map is internally inconsistent:
  - `GNeuralUCB`: `('Hybrid', 86.3)  # or EXP3?`
  - `EXPNeuralUCB`: `('Hybrid', 83.8)`
- `Validated_Logs/validate_paper.py` later treats the neural family summary differently and associates both `GNEURALUCB` and `EXPNEURALUCB` with the EXP3-family validation block.
- The current master datasets do not reproduce the paper values for the neural rows from one clean family-wide stochastic mean:
- `GNEURALUCB` from `Master_Dataset_EXP3.csv` gives `86.2` (`3` runs) and `85.5` (`5` runs)
- `EXPNEURALUCB` from `Master_Dataset_EXP3.csv` gives `77.8` (`3` runs) and `82.0` (`5` runs)
- `GNEURALUCB` from `Master_Dataset_Hybrid.csv` gives `79.1` (`3` runs) and `81.2` (`5` runs)
- `EXPNEURALUCB` from `Master_Dataset_Hybrid.csv` gives `77.8` (`3` runs) and `80.9` (`5` runs)

### Validation posture for the notebook

For `tab:rq1masterstochastic`, the notebook should:

- reproduce all stable rows directly from the master datasets
- compute the neural-row candidate values from both plausible source datasets
- flag the neural rows as a reconciliation checkpoint instead of silently forcing one source choice

This keeps the notebook defensible:

- source-backed where the mapping is stable
- explicit about the unresolved source ambiguity where it is not

### Current reconciliation result

- status:
  - `partially verified`
- verified now:
  - all non-neural rows

### RQ1 redesign lock

The verification order for `TABLE V` is now locked as:

1. aggregate each source independently
2. inspect the source tables directly in the notebook
3. reconstruct the paper-facing `TABLE V` structure (`Top tier`, `Mid-tier`, `Collapsed`)
4. only then compare `Expected` vs `Actual`, one run-count at a time

Applied notebook state:

- the notebook now shows per-source aggregation tables for:
  - `CMABs`
  - `iCMABs`
  - `Hybrid`
  - `EXP3`
- the earlier direct `Expected` vs `Actual` comparison phase for RQ1 has been removed from the active notebook flow until the paper-facing table is reconstructed from those source tables
- `EXPUCB` is rendered as `EXP3/UCB` in the source tables for clarity

### Reconstructed RQ1 table state

After the source tables were approved, the notebook now also contains:

- a `TABLE V` row map showing:
  - `Tier`
  - `Paper label`
  - `Source dataset`
  - `Source model`
- a reconstructed paper-facing `TABLE V` built from those approved source aggregates
- source-backed statement checks for the surrounding RQ1 narrative

This means the next remaining RQ1 step is now narrower:

- compare manuscript values against the reconstructed `TABLE V`, one run-count at a time

### Current RQ1 audit state

That manuscript comparison step is now present in the notebook.

The notebook now shows:

- `TABLE V Audit — 3 Runs`
- `TABLE V Audit — 5 Runs`

Both audit tables use:

- `Model`
- `Status`
- `Expected`
- `Actual`
- `Δ`
- `Source`
- `Note`

And the `Actual` side is explicitly taken from the reconstructed source-backed `TABLE V`.

Presentation state:

- the notebook keeps the flat audit tables
- and also adds tiered audit tables for the same two run-counts
- the tiered view follows the paper order:
  - `Top tier`
  - `Mid-tier`
  - `Collapsed`
- still unresolved:
  - `GNEURALUCB`
  - `EXPNEURALUCB`
- reason:
  - no single stable source contract in the current master datasets reproduces the paper values for both neural rows

### Low-priority manuscript follow-up

The collapsed-tier statement is source-supported and numerically stable:

- all three collapsed rows remain tightly clustered around `37%`
- this is a low-priority manuscript cleanup item, not an active verification blocker

Planned follow-up:

- later, tighten the paper wording so the collapsed-tier summary reflects the stronger source-backed finding that the rows average to roughly `37%`

## Next table in progress: `TABLE VI` / `tab:rq2_adversarial`

Current state:

- the notebook now includes the source-first setup for RQ2
- source mapping is locked as:
  - `CPursuit` → `CMABs`
  - `iCEpsilonGreedy` → `iCMABs`
  - `EXPNeuralUCB` → `EXP3`
  - `EXPUCB` → `EXP3`
- caption scope is locked as:
  - `MARKOV`, `ADAPTIVE`, `ONLINEADAPTIVE`
  - `Default` allocator
  - runs `3`, `5`
  - scales `1.0`, `1.5`, `2.0`
  - `T`, `Tb`

Current notebook outputs:

- per-source RQ2 tables for `CMABs`, `iCMABs`, and `EXP3`
- source-backed values for:
  - `Avg Eff. (%)`
  - `CV (%)`
  - `Floor (%)`
  - raw win counts / raw config counts

Still unresolved before reconstructing `TABLE VI`:

- the denominator for `Win Share (%)`

Roughly completed before that denominator step:

- the notebook now validates the three nearby RQ2 narrative claims directly from source
- current source-backed conclusions:
  - `CPursuit` remains stronger on average than `EXPNeuralUCB` and `EXPUCB`
  - `EXPNeuralUCB` remains the unstable/fragile adversarial baseline
  - `iCEpsilonGreedy` remains the most stable informed baseline with the strongest floor
  - `iCEpsilonGreedy` retains `100%` in-family win rate within the iCMAB adversarial slice

## RQ2 partial data validation now active

After the source-first statement validation, the verification hub now includes a partial `TABLE VI` reconstruction for the source-locked columns only:
- `Avg Eff. (%)`
- `CV (%)`
- `Floor (%)`

Those columns are now audited against the manuscript values directly from the approved source mapping:
- `CPursuit` → `CMABs`
- `iCEpsilonGreedy` → `iCMABs`
- `EXPNeuralUCB` → `EXP3`
- `EXPUCB` → `EXP3`

`Win Share (%)` remains deliberately unresolved and is displayed as `TBD` until the denominator is proven from source.

### RQ2 clarification: manuscript `Win Share (%)` values are known

The RQ2 notebook section no longer uses `TBD` for `Win Share (%)` in the reconstructed `TABLE VI` view.
The manuscript values are now shown explicitly from the paper:
- `CPursuit = 31.5`
- `iCEpsilonGreedy = 25.0`
- `EXPNeuralUCB = 11.1`
- `EXPUCB = 0.0`

Only the source reproduction of that column remains unresolved.

### RQ2 logic support table added

Before resolving `Win Share (%)`, the verification hub now includes a dedicated RQ2 diagnostics table that makes the comparison scope explicit for each `TABLE VI` row:
- source dataset
- source model
- threat suite
- allocator
- run suites
- raw experiment wins under the locked scope

This is the table used to reason toward the final win-share denominator instead of guessing it.

### RQ2 diagnostics corrected to use concrete totals

The RQ2 diagnostics table now exposes the totals needed for the `Win Share (%)` reasoning step:
- `Total threats`
- `Total runs`
- `Total wins`

This replaces the earlier distinct-value count view, which was mechanically true but not useful for the paper logic.

### RQ2 future expansion noted

The current `TABLE VI` scope follows the manuscript caption and therefore uses only the three adversarial threats:
- `MARKOV`
- `ADAPTIVE`
- `ONLINEADAPTIVE`

Follow-up work is explicitly needed to expand this analysis to the broader threat suite, because additional patterns may be hidden when `STOCHASTIC` and/or the full five-scenario set are excluded.

Priority:
- `mid-high`

Reason:
- the current table is valid for the paper as written
- but a broader threat-scope validation may expose additional ranking and stability patterns that are not visible in the narrower adversarial-only slice

### RQ2 diagnostics table simplified for high-level reasoning

The RQ2 diagnostics table now stays at the high-level view needed for the win-share walkthrough:
- per-model wins
- ratio column of `Wins / Scope wins`
- final total-wins row for the shown models

This replaces the heavier scope table that exposed repeated denominator totals on every row.

### RQ2 diagnostics ratio corrected

The RQ2 diagnostics table now computes the ratio directly instead of displaying a string form.

Current ratio column:
- `Wins / All wins (%)`

Definition:
- `model wins / total shown-model wins * 100`

### RQ2 researched win-share formulas added

To move the `Win Share (%)` question out of guesswork, the notebook now evaluates three literature-backed candidate formulas on the locked `TABLE VI` scope:

- **Micro share:** global share of total wins across the displayed models.
- **Macro threat-balanced share:** equal-weighted average of within-threat win shares.
- **Dirichlet-smoothed share:** Jeffreys-smoothed global share using a symmetric Dirichlet prior.

Current source-backed result:
- none of these formulas reproduces the manuscript `Win Share (%)` values for `CPursuit`, `iCEpsilonGreedy`, `EXPNeuralUCB`, and `EXPUCB`
- therefore the paper values are now treated as **known manuscript values with unresolved source-side provenance**, not as a missing notebook calculation

### RQ2 winner-accounting tables added

The notebook now separates the winner layers explicitly before any further `Win Share (%)` reasoning:

- **Runner wins summary**
  - experiment-level `winner`
  - `Wins (runner)`
  - `Total Wins (runner)`
  - `Wins / Total Wins (runner) (%)`

- **Evaluator wins summary**
  - aggregated `scenario_winner`
  - `Wins (evaluator)`
  - `Total Wins (evaluator)`
  - `Wins / Total Wins (evaluator) (%)`

- **Evaluator wins by run suite**
  - `3`-run view
  - `5`-run view
  - `Wins (per run)`
  - `Total Wins (per run)`
  - `Wins / Total Wins (per run) (%)`

### RQ2 audits now include normalized percent deviation

The RQ2 manuscript-vs-source audits now expose:
- `Δ = actual - expected`
- `Δ / Expected (%) = (actual - expected) / expected * 100`

This keeps the audit aligned with the paper-validation convention already used elsewhere in the project.

### RQ2 winner tables now include normalized deviation against the paper win-share values

The winner-accounting tables now expose the paper-facing comparison directly:
- `Paper Win Share (%)`
- `Δ vs Paper Win Share`

Formula:
- `(paper_share - actual_share) / actual_share`

Important edge case:
- when the actual share is `0.0`, the notebook now forces the normalized deviation to `0.0` to match the current review convention

### Paper-side `Win Share` usage is now explicitly recorded

The notebook now distinguishes two manuscript uses of win-share language:

- **`fig:global_win_share`**
  - has an explicit source-side rule in the LaTeX comment
  - default allocator
  - global paper-suite scope

- **`tab:rq2_adversarial` / TABLE VI**
  - shows `Win Share (%)`
  - does **not** define the denominator in the caption or nearby prose

This distinction is now part of the verification record because it explains why the figure is defensible from source while TABLE VI is still unresolved.

### `Win Share` severity is now split into correctness vs manuscript impact

The notebook now records a two-part severity assessment:

- **Correctness severity:** high
  - TABLE VI contains a numeric `Win Share (%)` column without a defensible source-backed denominator

- **Manuscript impact severity:** localized
  - the abstract, contribution bullets, and related-work framing do not depend on `Win Share`
  - the RQ2 prose relies primarily on `Avg Eff.`, `CV`, `Floor`, and the in-family winner statement

This means the column should be corrected quickly, but the required manuscript rewrite should be small.

### Recommended `TABLE VI` replacement is now documented

Current recommendation:
- replace `Win Share (%)` with `Configuration Win Rate (%)`

Definition:
- one unit = one unique `(scenario, runs, scale, cap_type)` configuration under `Default`
- winner = evaluator-level `scenario_winner`
- value = `wins / total unique configurations * 100`

Why this replacement was selected:
- it uses the aggregated evaluator winner rather than raw repeated experiment wins
- it keeps the denominator explicit
- it matches benchmark-style task/configuration win-rate reasoning more closely than an undefined pooled share

### Final `TABLE VI` decision (supersedes the earlier win-rate recommendation)

After reviewing the table’s actual rhetorical use in the manuscript, the replacement decision was tightened:

- replace `Win Share (%)` with **`Win Dominance (%)`**

Definition:
- numerator = aggregated scenario wins for the displayed model under the locked RQ2 adversarial scope
- denominator = aggregated scenario wins captured by the four displayed `TABLE VI` representatives under that same scope
- reported value = `wins_i / \sum_j wins_j * 100`

Locked source-backed values:
- `CPursuit = 25.6`
- `iCEpsilonGreedy = 43.9`
- `EXPNeuralUCB = 30.5`
- `EXP3/UCB = 0.0`

Why this supersedes the earlier `Configuration Win Rate (%)` recommendation:
- `TABLE VI` is being used to show which representative dominates the winner pool under adversarial threats, not to report a corpus-wide task win rate
- `%` already conveys the share; `Win Dominance (%)` is more precise than an undefined `Win Share (%)` and more aligned with the argument than a generic `Win Rate (%)`
- the manuscript change remains localized because the surrounding RQ2 prose does not depend on the old column values

## RQ3a Validation Status

Current artifact under audit:
- `GA Papers/QuantumFaultTolerant/main.tex` `tab:rq3a_informative`

Caption-faithful source lock:
- source dataset: `Validated_Logs/Master_Dataset_Hybrid.csv`
- models: `CPURSUITNEURALUCB`, `ICPURSUITNEURALUCB`
- allocator: `Default` (paper wording: `Fixed`)
- `cap_type = T`
- `scale = 2.0`
- `frames = 6000`
- run suites: `3`, `5`
- scenarios: `NONE`, `STOCHASTIC`, `MARKOV`, `ADAPTIVE`, `ONLINEADAPTIVE`

Caption-faithful reconstruction result:
- `CPursuitNeuralUCB`: `Bl 98.29`, `Sh 92.95`, `Mk 90.65`, `Ag 92.77`, `OA 85.71`, `Avg 92.08`, `CV_scen 4.41`
- `iCPursuitNeuralUCB`: `Bl 98.10`, `Sh 86.40`, `Mk 91.60`, `Ag 93.12`, `OA 84.90`, `Avg 90.82`, `CV_scen 5.24`

Source-backed statement check outcome:
- `OnlineAdaptive lift = -0.807 pp` under the caption-faithful scope, not `+18.3 pp`
- `Avg lift = -1.250 pp` under the caption-faithful scope, so the paper’s “higher overall average” statement is not supported there
- `CV_scen delta = +0.834 pp`, so tighter cross-scenario dispersion is also not supported there
- `Markov` remains effectively unchanged (`+0.955 pp`)
- `Stochastic` does not remain effectively unchanged (`-6.553 pp`)

Provenance diagnostic:
- the closest source match to the manuscript table is:
  - `allocator = Default`
  - `cap_type = T`
  - `scale = 2.0`
  - `frames = 6000`
  - `runs = 3` only
- that candidate gives:
  - `OA lift = +18.310 pp`
  - `Avg lift = +3.666 pp`
  - `Stochastic Δ = +0.040 pp`
  - `Markov Δ = -0.035 pp`
- implication: the paper values appear to have been derived from the `3-run` suite only, while the current caption says the table is averaged across the `3-run` and `5-run` suites

Additional diagnostic branch requested during review:
- test `6K horizon` as `4K base + 6K base+step`, `runs = 3`, same `Default / T / s=2` deployment
- reconstructed result:
  - `CPursuitNeuralUCB`: `Bl 99.83`, `Sh 94.34`, `Mk 92.83`, `Ag 92.99`, `OA 89.61`, `Avg 93.92`, `CV_scen 3.56`
  - `iCPursuitNeuralUCB`: `Bl 92.99`, `Sh 94.62`, `Mk 92.80`, `Ag 92.98`, `OA 98.01`, `Avg 94.28`, `CV_scen 2.10`
- comparison summary:
  - `OA lift = +8.400 pp`
  - `Avg lift = +0.360 pp`
  - `MAE vs paper = 3.206`
- interpretation:
  - this alternative explains more of the paper’s directionality than the caption-faithful `3+5` mean, but it is still weaker than the `6000 / runs=3 only` provenance candidate

Priority classification for RQ3a:
- **High priority:** `CV_scen` claim
- **High priority:** manuscript `iCPursuitNeuralUCB / OA = 99.1`
- **High priority:** caption/derivation mismatch for `tab:rq3a_informative`

`Tb` diagnostic extension:
- checked the same provenance branches under `Tb`:
  - `6000 / runs 3+5 mean`
  - `6000 / runs 3 only`
  - `6000 / runs 5 only`
  - `4000 + 6000 / runs 3 only`
- best `Tb` branch:
  - `Tb / 6000 / runs 3 only`
  - `OA lift = +0.911 pp`
  - `Avg lift = -0.017 pp`
  - `MAE vs paper = 4.534`
- conclusion:
  - `Tb` does not explain the manuscript table better than `T`
  - `T / 6000 / runs 3 only` remains the strongest provenance candidate

RQ3a paper correction applied:
- corrected `tab:rq3a_informative` in `GA Papers/QuantumFaultTolerant/main.tex` to the strongest source-backed branch:
  - `Hybrid`
  - `Default` (`Fixed` in paper wording)
  - `T`
  - `s = 2`
  - `frames = 6000`
  - `runs = 3` only
- patched the two manuscript claims that were highest priority:
  - claim 1 (`OnlineAdaptive` lift) remains `+18.3 pp`
  - claim 3 now states the validated dispersion improvement explicitly:
    - `CV_scen: 6.5 -> 3.3`
- updated the paper table scope text and caption so they no longer claim the values are averaged across the `3-run` and `5-run` suites

## Notebook Workflow Integrity / GitHub Variant Check

- **Engine decision:** keep pandas as the canonical engine for all verification-hub data manipulation.
- **Formatting/workflow decision:** pandas adoption must not remove the audit-review layer. The verification notebook is expected to preserve:
  - discrepancy color coding
  - `B - A` / `|B - A|` severity presentation
  - end-of-analysis summaries
  - `🔴 Pending high tasks` / `🟢 Solved high tasks`
- **Current verified state:** the local notebook file now restores that workflow for the sections currently present (`RQ1`, `RQ2`).
- **Current regression still open:** the GitHub notebook variant no longer contains the richer source-first sections previously built for:
  - `RQ3a`
  - `RQ3b`
  - `RQ3c`
  - `RQ3d`
  - `Table X`
  - `Table XI`
- **Priority:** restoring notebook coverage parity with the already-approved paper/doc state is a high-priority workflow task.
- **Paper check:** `GA Papers/QuantumFaultTolerant/main.tex` still reflects the approved paper-side fixes; the current mismatch is between the notebook file and the paper/docs, not a rollback in `main.tex`.

### Recovery update

- The missing validated sections have now been restored into `H-MABs_MasterDataset_VerificationHub.ipynb` using the approved snapshot bundle under `paper_validation/snapshots/20260315_001835`.
- Restored coverage:
  - `RQ3a`
  - `RQ3b`
  - `RQ3c`
  - `RQ3d`
  - `Table X`
  - `Table XI`
- The recovery preserves the required workflow layer on top of pandas:
  - discrepancy color coding
  - `B - A` / `|B - A|`
  - end-of-analysis summaries
  - `🔴 Pending high tasks` / `🟢 Solved high tasks`
- The notebook now executes successfully again with those recovered sections present.

## Winner Terminology Review Pass

- **Trigger:** the validated table/breakdown backlog is now cleared at high priority, so the next pass is language integrity rather than numeric repair.
- **Goal:** verify that all winner-related paper language is scoped and defined correctly, without conflating:
  - experiment-level winners
  - scenario champions
  - displayed-model win-pool dominance
  - aggregate gap-reduction leadership
- **Primary review locations in `GA Papers/QuantumFaultTolerant/main.tex`:**
  1. `fig:global_win_share`
  2. `TABLE VI` / `tab:rq2_adversarial`
  3. RQ2 in-family winner sentence
  4. `TABLE X` intro / caption / legend / bullets
  5. `TABLE XI` note / inter-family claims
  6. standardized-testing and future-work wording that carries winner/dominance language forward
- **Process lock:** each location will be handled one by one under the explicit review format:
  - `Task`
  - `Meaning`
  - `Before`
  - `After`
- **Constraint:** no wording patch should be applied for this pass until that specific location has been reviewed under the above format.

## Winner-Type Validation Extension

- `Table X` and `Table XI` notebook sections now include explicit winner-type validation tables.
- `Table X` winner types are now shown per testbed:
  - `Experiment winner`
  - `Aggregate gap-reduction winner`
  - `Aggregate efficiency winner`
- `Table XI` winner types are now shown per source world:
  - `Experiment winner`
  - `Aggregate gap-reduction winner`
  - `Aggregate efficiency winner`
  - `Allocator-level aggregate gap winner`
- This extension is intended to keep the paper terminology pass grounded in the validated data rather than inferred from prose.

## Winner wording rule — `cross-layer winner`
- Use `cross-layer winner` only when the same model is validated as the winner across all relevant winner views for that section.
- Always state the basis explicitly.

## Winner wording rule — `cross-layer winner` vs gap-based leader
- Use `cross-layer winner` when the same model wins across all validated winner layers for the section.
- Use metric-specific wording when the validated basis is narrower, e.g. `strongest neural model by Oracle-relative gap reduction`.


## Review To-Do List (Reviewer Comments Queue)

These review tasks now take priority over all remaining non-validation work. Each item is frozen in the agreed format so we can address them one by one later without re-deriving the problem.

### Reviewer source map — Dan comments (March 11--13)

This queue comes directly from Dan's comments and is intentionally duplicated here in a compact map so the source, priority, and location stay visible while we work through the backlog.

| Queue ID | Dan comment date/time | Section / location | Short ask |
|---|---|---|---|
| `R-01` | 11 March, 8:21 am | Related Work | Be more explicit about how existing works differ |
| `R-02` | 13 March, 10:29 am | Introduction sentence | Replace awkward `situate` wording |
| `R-03` | 11 March, 7:30 am | Abstract | Add 1--2 sentences on why the problem matters |
| `R-04` | 13 March, 9:34 am | Early intro framing | State the primary contribution early and why readers should care |
| `R-05` | 11 March, 7:33 am | Main findings sentence | Rewrite the pursuit--neural finding and make the results concrete |
| `R-06` | 11 March, 8:21 am | Introduction | Cut intro length to about a page; move detail elsewhere |
| `R-07` | 11 March, 8:20 am | Introduction gap framing | Convert the long bullet-heavy framing into paragraphs |
| `R-08` | 11 March, 8:27 am | Key Contributions | Keep only 2--4 contributions with short explanations |
| `R-09` | 12 March, 10:34 am | Intro transition sentence | Replace `these considerations` with explicit context |
| `R-10` | 13 March, 8:54 am | Research questions | Use `\\emph{}` rather than bold |
| `R-11` | 13 March, 9:39 am | Figure captions | Shorten captions and make the takeaway explicit |
| `R-12` | 13 March, 9:55 am | Hypothesis sentence | Review whether the explicit hypothesis should be removed |
| `R-13` | 13 March, 9:56 am | Table VI caption | Shorten caption and state the main implication |

### Queue guardrail

- We do not add new review/backlog tasks unless they are explicitly requested by the user or explicitly proposed and approved first.
- When a later sweep identifies a possible cleanup item, it remains outside the active queue unless it is explicitly approved for tracking.

### R-01 — Related Work differentiation (Dan, 11 March, 8:21 am)
- **Task:** make the differences between existing works explicit in the Related Work section.
- **Meaning:** the section should not only summarize prior work; it should say how those works differ from one another and from this paper.
- **Before:** `\section{Related Work}` remains too descriptive and does not make the comparative differences explicit enough.
- **After:** revise the section so each cited stream/paper is contrasted by assumption set, threat scope, allocation treatment, and evaluation comparability.
- **Reasoning:** readers need the comparative logic, not just a literature inventory; otherwise the value of this paper's evaluation-first contribution is harder to see.

### R-02 — Introduction wording: `situate` (Dan, 13 March, 10:29 am)
- **Task:** rewrite the sentence beginning `We situate multi-armed bandits...`.
- **Meaning:** the verb choice and sentence framing are awkward and need cleaner positioning language.
- **Before:** `We situate multi-armed bandits (MABs) as a family of uncertainty-aware sequential decision rules and use quantum entanglement routing as a stress test where stochastic noise, structured disruption, and resource constraints jointly shape performance.`
- **After:** replace this with cleaner positioning language that introduces MABs and quantum routing naturally, without the awkward `situate` construction.
- **Reasoning:** this sentence appears early and sets reader confidence; awkward phrasing there makes the paper feel less precise than the underlying work.

### R-03 — Abstract problem significance (Dan, 11 March, 7:30 am)
- **Task:** add 1--2 sentences in the abstract explaining why the stated problem matters.
- **Meaning:** the abstract identifies failing assumptions, but it still needs an explicit consequence statement.
- **Before:** `Quantum entanglement routing requires dynamic path selection and qubit allocation under noisy and adversarial conditions. Existing routing approaches often assume stationary link behavior, decouple selection from allocation, or rely on offline optimization---assumptions that can fail when link fidelities drift and disruptions adapt online.`
- **After:** extend this with 1--2 sentences that explain why these assumption failures matter for deployment, reliability, or decision quality.
- **Reasoning:** without an explicit consequence statement, the abstract explains the setup but does not yet tell the reader why the problem deserves attention.

### R-04 — Early contribution statement (Dan, 13 March, 9:34 am)
- **Task:** state the paper's primary contribution early and explain why readers should care.
- **Meaning:** the contribution and importance need to appear earlier in the paper, not be inferred later.
- **Before:** the early introduction does not contain a compact `primary contribution` statement with a clear payoff.
- **After:** add an early sentence or short block stating the primary contribution and the practical reason it matters.
- **Reasoning:** readers should not need to wait until later sections to understand what this paper contributes and what decision problem it helps solve.

### R-05 — Main findings sentence clarity (Dan, 11 March, 7:33 am)
- **Task:** rewrite the pursuit--neural finding sentence and ground it with concrete results.
- **Meaning:** the current sentence is too compressed and not concrete enough.
- **Before:** `Pursuit--neural hybrids emerge as the most robust family, outperforming non-contextual bandit baselines by 18--24 percentage points and sustaining higher worst-case performance under strategic attacks than adversarial-first designs.`
- **After:** rewrite this so the finding reads clearly and uses concrete, defensible result language.
- **Reasoning:** this is one of the paper's headline takeaways, so it needs to be both easy to read and tightly aligned with the validated evidence.

### R-06 — Introduction length reduction (Dan, 11 March, 8:21 am)
- **Task:** compress the oversized introduction block and move detail elsewhere.
- **Meaning:** the introduction is carrying too much framework/process detail and needs to be cut down to about a page.
- **Before:** the block beginning `However, existing quantum routing research often evaluates algorithms under incompatible assumptions...` is too long for the intro.
- **After:** condense this material into a tighter intro framing and move supporting detail into later sections.
- **Reasoning:** the introduction should frame the problem, gap, and stakes quickly; too much detail early hides the main message and hurts pacing.

### R-07 — Bullet-heavy gap framing (Dan, 11 March, 8:20 am)
- **Task:** convert the intro's long enumerated gap framing into tighter prose.
- **Meaning:** the current bullet/list structure is too heavy and slows the introduction.
- **Before:** the adversarial-first/stochastic-first split and the three deployment-critical gaps are presented through multiple enumerate blocks.
- **After:** rewrite this material as tighter paragraph form while preserving the three core gaps.
- **Reasoning:** paragraph form will read more like an argument than a checklist, which better supports the narrative flow of the introduction.

### R-08 — Key Contributions compression (Dan, 11 March, 8:27 am)
- **Task:** reduce the Key Contributions subsection to 2--4 contributions with 1--2 sentences each.
- **Meaning:** the contributions need to get to the point quickly.
- **Before:** `\subsection{Key Contributions}` is too long/heavy.
- **After:** present only 2--4 contributions, each stated briefly and clearly.
- **Reasoning:** a shorter contributions block helps readers retain the main claims and avoids repeating material that belongs in later sections.

### R-09 — `these considerations` ambiguity (Dan, 12 March, 10:34 am)
- **Task:** replace the vague reference in `Motivated by these considerations...` with explicit context.
- **Meaning:** the sentence assumes context that is not explicit enough at that point.
- **Before:** `Motivated by these considerations, we study how modeling choices (\eg contextual vs.\ adversarial vs.\ predictive), allocator strategies, and capacity semantics jointly affect routing robustness under diverse threat regimes.`
- **After:** replace `these considerations` with a short explicit reminder of the considerations being referenced.
- **Reasoning:** vague referents make the sentence dependent on nearby memory rather than standalone clarity, which is exactly what Dan flagged.

### R-10 — RQ typography (Dan, 13 March, 8:54 am)
- **Task:** standardize the research-question styling to use `\emph{}` rather than bold.
- **Meaning:** the reviewer requested lighter question styling.
- **Before:** RQs are currently styled in bold.
- **After:** RQs use `\emph{}` consistently.
- **Reasoning:** this is a presentation consistency fix that improves readability and aligns the manuscript with the requested style.

### R-11 — Figure caption shortening / takeaway captions (Dan, 13 March, 9:39 am)
- **Task:** shorten long captions and make the takeaway explicit, starting with the context-vs-non-context figure.
- **Meaning:** captions should state the primary implication, not restate the full setup.
- **Before:** `\caption{Context vs.\ non-context efficiency across threat scenarios (evaluation corpus, paper-default allocator). Contextual (CMAB/iCMAB) models maintain higher Oracle-normalized efficiency than non-context EXP3 baselines under both $T$ and $T_b$ capacity semantics.}`
- **After:** shorten the caption and state the main takeaway more directly; repeat this rule for the rest of the paper captions as needed.
- **Reasoning:** captions are read quickly and should foreground interpretation; long setup-heavy captions cost space and bury the takeaway.

### R-12 — Hypothesis removal / cut-for-space review (Dan, 13 March, 9:55 am)
- **Task:** review whether the explicit hypothesis sentence should be removed.
- **Meaning:** this is a space/clarity decision, not a validation issue.
- **Before:** `We hypothesized that adversarial-first algorithms (EXP3-family, including 	exttt{EXPUCB} and 	exttt{EXPNeuralUCB}) would outperform contextual pursuit methods under structured attacks due to pessimistic exponential weighting.`
- **After:** decide whether to remove this sentence entirely or replace it with a shorter setup line.
- **Reasoning:** if the sentence is not doing important framing work, it is a good candidate to cut so the paper spends its space on evidence and implications.

### R-13 — Table VI caption shortening / implication-first wording (Dan, 13 March, 9:56 am)
- **Task:** shorten the `RQ2` table caption and make the primary implication explicit.
- **Meaning:** the caption is too long and setup-heavy.
- **Before:** `\caption{RQ2: robustness under adversarial threats (Markov/Adaptive/OnlineAdaptive) computed from the curated evaluation corpus under the 	exttt{Default} allocator. Results aggregate across horizons present, replay scales $s \in \{1,1.5,2\}$, and capacity semantics ($T$, $T_b$), summarized over 3-run and 5-run ensemble suites.}`
- **After:** use this table as the reference caption pattern for the full manuscript-wide table pass: takeaway first, compressed context second, and no setup-heavy aggregation recipe unless essential for interpretation.
- **Reasoning:** tables should tell readers what to conclude at a glance; the methodological details can be shortened or moved elsewhere when the caption is overloaded.

### Deferred later-review note — Global table consistency sweep
- **Task:** run one formatting-only sweep for table caption and table layout consistency across the manuscript.
- **Meaning:** figure-caption consistency is largely aligned after `R-11`, but tables showed a mix of takeaway-first and setup-heavy caption styles plus formatting variation.
- **Before:** several table captions remained longer and more method-heavy than the current figure-caption style (e.g., the table regions around `main.tex:1244`, `main.tex:1400`, `main.tex:1741`, `main.tex:1786`, `main.tex:1930`, and `main.tex:2000`).
- **After:** normalize table caption tone/length, sizing directives, column-header style, label/title style, and notation consistency (`T` vs `T_b`, scale notation, Oracle-normalized wording) without changing scientific claims or numerical values.
- **Reasoning:** user later explicitly pulled this into active work and merged it into the `R-13` implementation lane; keep this note as the rationale/base for that completed pass.

### Deferred later-review note — Remaining hypothesis audit
- **Task:** review the remaining non-`RQ2` hypothesis subsections and decide whether any others should be shortened or removed.
- **Meaning:** Dan explicitly flagged the `RQ2` hypothesis, and the paper still contains other hypothesis subsections that may or may not earn their space.
- **Before:** the manuscript retains hypothesis subsections outside the flagged `RQ2` case.
- **After:** in a later pass, check each remaining hypothesis subsection individually and decide whether it should stay, be shortened, or be removed for space/clarity.
- **Reasoning:** this keeps the immediate `RQ2` fix narrow while preserving a deliberate follow-up review for consistency.

## Hold Until Review Queue Is Cleared
- move paper tables/plots to generated text/TeX include files instead of hardcoded values
- update `state_analysis.py` to refresh those generated files and run dependent report generation
- automate controlled paper-repo commit/push preparation after validated report refresh
