# Paper 8 Master Dataset Report Workflow

This note defines the exact workflow for taking the Paper 8 paper-config run corpus, turning it into a master dataset, and integrating the resulting evidence into `GA Papers/QuantumFaultTolerant/main.tex`.

The purpose is simple:

1. use the dataset we already have without re-deriving intent from filenames,
2. update the report tables and narrative in a controlled way,
3. keep the generation/integration procedure reusable for future testbeds.

## Source Artifacts

- Report: `GA Papers/QuantumFaultTolerant/main.tex`
- Extraction script: `hybrid_variable_framework/state_analysis.py`
- Paper-config notebook: `hybrid_variable_framework/Dynamic_Routing_Eval_Framework/notebooks/H-MABs_Eval-Testbed-Paper8-PaperRunConfig.ipynb`
- Standardized notebook: `hybrid_variable_framework/Dynamic_Routing_Eval_Framework/notebooks/H-MABs_Eval-Testbed-Paper8-StandardizedRunConfig.ipynb`
- Current paper-config master dataset: `Validated_Logs/Master_Dataset_1000_1000_1_paper8.csv`

## Dataset Slice Definition

For Paper 8, the current report-ready slice is the original paper-config corpus defined by the run envelope:

- `base_frames = 1000`
- `frame_step = 1000`
- `runs = 1`

Use the envelope as the discriminator. Do not infer meaning from `T`/`Tb`.

The extraction pattern should follow the exact style already used in `state_analysis.py`:

```python
key = "1000_1000_1"
output_path = f"/Users/pitergarcia/DataScience/Semester4/GA-Work/Validated_Logs/Master_Dataset_{key}_paper8.csv"
convert_key_state_files_to_csv(path, output=output_path, keyword=fr"(?=.*MultiRunEvaluator)(?=.*{key}_S.*T_paper8\\.pkl)")
```

## What the Current Dataset Contains

The current file `Validated_Logs/Master_Dataset_1000_1000_1_paper8.csv` contains:

- `300` rows
- `5` models:
  - `ORACLE`
  - `GNEURALUCB`
  - `EXPNEURALUCB`
  - `CPURSUITNEURALUCB`
  - `ICPURSUITNEURALUCB`
- `4` allocators:
  - `Default`
  - `Dynamic`
  - `Random`
  - `ThompsonSampling`
- `5` threat scenarios:
  - `NONE`
  - `STOCHASTIC`
  - `MARKOV`
  - `ADAPTIVE`
  - `ONLINEADAPTIVE`
- `1` experiment per allocator-scenario configuration
- `scale = 1.0`
- `cap_type = T`

The Paper 8 notebook configuration for this corpus is:

- topology: `20` nodes, `19` edges
- routing paths: `8`
- total qubits: `35`
- minimum qubits per route: `2`

That means the usable Paper 8 evidence today is a valid external-testbed paper-config slice, but not yet the standardized cross-testbed corpus.

## Report-Ready Summaries From the Dataset

### All-Allocator Aggregate Means

Use these values when adding Paper 8 to the cross-testbed table and surrounding narrative:

| Model | Avg Reward | Avg Efficiency (%) | Avg Gap (%) |
|---|---:|---:|---:|
| `GNEURALUCB` | `183038.7972` | `61.65` | `38.35` |
| `EXPNEURALUCB` | `186656.1295` | `61.93` | `38.07` |
| `CPURSUITNEURALUCB` | `182011.6324` | `61.42` | `38.58` |
| `ICPURSUITNEURALUCB` | `210418.9742` | `67.85` | `32.15` |
| `ORACLE` | `300540.1887` | `n/a` | `n/a` |

Experiment-winner counts across the `20` allocator-scenario configurations:

- `EXPNeuralUCB`: `10`
- `CPursuitNeuralUCB`: `5`
- `GNeuralUCB`: `4`
- `iCPursuitNeuralUCB`: `1`

### Default-Only Aggregate Means

Use these values only if Paper 8 is added to the model-family comparison table, since that table is already normalized to the `Default` allocator:

| Model | Avg Reward | Avg Efficiency (%) | Avg Gap (%) |
|---|---:|---:|---:|
| `GNEURALUCB` | `184444.5856` | `61.81` | `38.19` |
| `EXPNEURALUCB` | `194951.0732` | `62.08` | `37.92` |
| `CPURSUITNEURALUCB` | `183594.3395` | `61.65` | `38.35` |
| `ICPURSUITNEURALUCB` | `210853.1004` | `67.41` | `32.59` |
| `ORACLE` | `301055.1512` | `n/a` | `n/a` |

Default-only scenario winner counts (`5` scenario-experiment configurations):

- `EXPNeuralUCB`: `2`
- `CPursuitNeuralUCB`: `2`
- `iCPursuitNeuralUCB`: `1`

## Implementation Status

- `2026-03-09`: completed the first report-integration step by adding Paper 8 to the external testbed inventory in `main.tex` and updating the section wording from three to four external testbeds.
- `2026-03-09`: completed the second report-integration step by extending `tab:testbed_comparison` with a Paper 8 block and updating the table caption/legend so the Paper 8 `1K/1K/1R` paper-config slice is not misrepresented as a `5`-run, `3`-scale corpus.
- `2026-03-09`: completed the third report-integration step by updating the cross-testbed narrative and key-observation bullets so Paper 8 is discussed as part of the findings section rather than only appearing in the inventory and table.
- `2026-03-09`: completed the fourth report-integration step by extending the model-family comparison section and table with the Paper 8 `Default`-allocator slice, including corpus-specific note updates for its `1K/1K/1R`, `s=1.0` regime.
- `2026-03-09`: completed the fifth report-integration step by updating the standardized-testing future-work text to include Paper 8, replacing `standardized run protocol` with `standardized run configurations`, and removing the `apples-to-apples` phrasing from those future-work references.
- `2026-03-09`: completed the sixth report-integration step by updating the top-level summary wording to reflect four external testbeds, include Paper 8 in the cross-testbed contribution summary, and remove the `apples-to-apples` phrasing from the key contributions section.

## Integration Steps For `main.tex`

### Step 1 — Update the External Testbed Inventory

In the `Cross-Testbed Validation` section:

- change references from “three external testbeds” to “four external testbeds”
- add a Paper 8 bullet to the existing testbed inventory list
- describe it as the current paper-config slice, not the standardized corpus

Paper 8 inventory fields to state explicitly:

- `20N, 19E, 8P`
- `1K/1K/1R`
- `4` allocators
- `5` threat scenarios
- `scale = 1.0`
- `cap_type = T`

### Step 2 — Extend `tab:testbed_comparison`

Add a Paper 8 block to the cross-testbed table using the all-allocator aggregate means above.

Important:

- Paper 8 should be labeled as a paper-config slice
- do not present it as directly standardized against Papers 2, 7, and 12
- if space is tight, add a short footnote or caption qualifier noting the `1K/1K/1R` paper-config regime

### Step 3 — Update the Narrative Around the Table

Revise the text surrounding the table so it no longer claims:

- only three external testbeds
- only the Paper 2 / Paper 7 / Paper 12 result set

The narrative should now state:

- we currently have four external testbeds represented in the report
- Paper 8 is included as an original paper-config corpus
- strict apples-to-apples standardized comparison for Paper 8 remains a separate follow-up

### Step 4 — Decide Whether Paper 8 Enters the Model-Family Comparison Table

If Paper 8 is added to the model-family table:

- use the `Default`-allocator slice only
- use the default-only means listed above
- keep the table condition aligned with the existing “Default allocator” constraint

If Paper 8 is not added there yet:

- still add it to the cross-testbed validation table
- leave the model-family table unchanged until the standardized Paper 8 corpus is finalized

### Step 5 — Update the Cross-Testbed Observations

After Paper 8 is added to the table, refresh the observation bullets to account for:

- Paper 8’s lower/higher efficiency relative to Papers 2, 7, and 12
- the fact that `iCPursuitNeuralUCB` has the strongest aggregate efficiency on the Paper 8 slice
- the fact that `EXPNeuralUCB` wins the most allocator-scenario configurations in this specific corpus

Do not claim final cross-testbed ranking equivalence until the standardized Paper 8 campaign is ready.

## Recommended Integration Order

1. Generate or regenerate the Paper 8 paper-config master dataset with the `1000_1000_1` envelope key.
2. Verify the dataset dimensions:
   - `300` rows
   - `5` models
   - `4` allocators
   - `5` scenarios
   - `1` experiment
3. Compute:
   - all-allocator aggregate means
   - default-only aggregate means
   - experiment-winner counts
4. Add Paper 8 to the testbed inventory paragraph/list in `main.tex`.
5. Add the Paper 8 block to `tab:testbed_comparison`.
6. Update the surrounding “three external testbeds” language.
7. Decide whether to extend the model-family table now or defer that until standardized Paper 8 results are ready.
8. Update the key-observations bullets only after the table values are finalized.

## Guardrails

- Use the run envelope (`1000_1000_1`) to identify the current Paper 8 paper-config corpus.
- Do not infer paper-config vs standardized meaning from `T` / `Tb`.
- Do not merge Paper 8 into the standardized-testing claims until the standardized Paper 8 corpus is complete and validated.
- Keep the dataset-generation snippet in the same style as the existing `state_analysis.py` workflow.

## Future Reuse Template

For any new testbed master dataset, repeat the same process:

1. identify the corpus by its actual run envelope,
2. extract the master dataset with that envelope key,
3. validate row/model/allocator/scenario counts,
4. compute report-ready aggregates,
5. update the testbed inventory text,
6. extend the cross-testbed table,
7. extend any allocator-normalized comparison tables only when the slice conditions match.
