# QUICK START – Copy & Paste Ready Code

### Use these snippets directly – aligned with the current framework APIs


## SNIPPET 1: Paper #2 Style Quick Test (Single Run)

Run a **Paper 2–style** stochastic experiment using the built‑in `PAPERCONFIGS` and `MultiRunEvaluator`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/f977fe86-d826-41c1-abb0-166453ab4b46/multi_run_evaluator.py)

```python
from daqr.config.experimentconfig import ExperimentConfiguration
from daqr.evaluation.multirunevaluator import MultiRunEvaluator

# Paper 2 testbed (Huang et al. 2023) is testbedid=2 in PAPERCONFIGS
config = ExperimentConfiguration(
    runs=1,
    envtype="stochastic",
    attacktype="stochastic",      # stochastic random failures
    attackintensity=0.25,
    models=["Oracle", "EXPNeuralUCB"],
    testbedid=2,                  # Paper 2 testbed entry
    verbose=True
)

paper2_cfg = config.gettestbedconfig()  # {'name', 'narms', 'totalframes', 'modelparams', ...}
total_frames = paper2_cfg["totalframes"]  # e.g., 1400

evaluator = MultiRunEvaluator(
    configs=config,
    baseframes=total_frames,
    framestep=total_frames       # single block for this quick test
)

results = evaluator.run_multi_model_evaluation()
print("✅ Paper #2 quick test complete")
```


## SNIPPET 2: Quick Sweep Across Paper Testbeds

Loop over all defined paper-style testbeds in `PAPERCONFIGS` (2, 5, 7, 8, 12) and run a tiny stochastic experiment on each. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)

```python
from daqr.config.experimentconfig import ExperimentConfiguration
from daqr.evaluation.multirunevaluator import MultiRunEvaluator

paper_ids = [2, 5, 7, 8, 12]
common_models = ["Oracle", "EXPNeuralUCB"]

for pid in paper_ids:
    print("=" * 60)
    print(f"Running quick test on Paper #{pid} testbed...")
    print("=" * 60)

    cfg = ExperimentConfiguration(
        runs=1,
        envtype="stochastic",
        attacktype="stochastic",
        attackintensity=0.25,
        models=common_models,
        testbedid=pid,
        verbose=False
    )

    paper_cfg = cfg.gettestbedconfig()
    total_frames = paper_cfg.get("totalframes", 1000)

    evaluator = MultiRunEvaluator(
        configs=cfg,
        baseframes=total_frames,
        framestep=total_frames
    )

    _ = evaluator.run_multi_model_evaluation()
    print(f"✅ Paper #{pid} testbed run finished\n")
```


## SNIPPET 3: Inspect Built‑In PAPERCONFIGS

Use `ExperimentConfiguration.PAPERCONFIGS` and `gettestbedconfig()` to see how each paper testbed is parameterized (arms, frames, modelparams). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)

```python
from pprint import pprint
from daqr.config.experimentconfig import ExperimentConfiguration

# Create a config object; PAPERCONFIGS is attached to the instance
cfg = ExperimentConfiguration(
    runs=1,
    envtype="stochastic",
    attacktype="stochastic",
    attackintensity=0.25,
    verbose=False
)

print("Available PAPERCONFIGS keys:", list(cfg.PAPERCONFIGS.keys()))

# Paper 2 configuration
cfg.testbedid = 2
paper2 = cfg.gettestbedconfig()
print("\nPaper #2 config:")
pprint(paper2)

# Paper 7 configuration
cfg.testbedid = 7
paper7 = cfg.gettestbedconfig()
print("\nPaper #7 config:")
pprint(paper7)
```


## SNIPPET 4: Notebook Cell – Clean Paper #2 Physics (Advanced)

In the **clean testbed notebook** (`H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb`), you have a helper `getphysicsparams(...)` that builds Paper‑specific physics (topology, noise, fidelity, external rewards). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9fdf19ed-1342-4075-a957-3e8584ca76cc/quantum_physics.py)

This cell shows how to run a **Paper 2 physics‑accurate experiment** using that helper:

```python
from daqr.config.experimentconfig import ExperimentConfiguration
from daqr.evaluation.multirunevaluator import MultiRunEvaluator

# Import the helper from the notebook or a shared helper module
from H_MABs_Eval_T_XQubit_Alloc_XQRuns import getphysicsparams  # adjust import path as needed

# Core experiment config (stochastic Paper 2 style)
config = ExperimentConfiguration(
    runs=1,
    envtype="stochastic",
    attacktype="stochastic",
    attackintensity=0.25,
    models=["Oracle", "EXPNeuralUCB"],
    verbose=True
)

current_frames = 4000
base_seed = 12345

# Build Paper 2 physics (topology, noise, fidelity, external contexts/rewards)
noisemodel, fidelitycalc, topo, contexts, rewards = getphysicsparams(
    physicsmodel="paper2",
    currentframes=current_frames,
    baseseed=base_seed,
    qubitcap=None   # or a specific qubit allocation tuple
)

# Tell ExperimentConfiguration to use this custom environment
config.setenvironment(
    qubitcap=(8, 9, 8, 10),       # example capacity per path; adapt as needed
    framesno=current_frames,
    seed=base_seed,
    attackintensity=0.25,
    envtype="stochastic",
    attacktype="stochastic",
    noisemodel=noisemodel,
    fidelitycalculator=fidelitycalc,
    externaltopology=topo,
    externalcontexts=contexts,
    externalrewards=rewards,
)

evaluator = MultiRunEvaluator(
    configs=config,
    baseframes=current_frames,
    framestep=current_frames
)

results = evaluator.run_multi_model_evaluation()
print("✅ Paper 2 physics-accurate run complete")
```


## SNIPPET 5: Minimal Script – Paper #2 & #7 Testbeds

Create `test_papers_2_7.py` to quickly validate that both Paper 2 and Paper 7 testbeds run end‑to‑end with your research models. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

```python
#!/usr/bin/env python
"""Quick test for Paper #2 and Paper #7 style testbeds."""

from daqr.config.experimentconfig import ExperimentConfiguration
from daqr.evaluation.multirunevaluator import MultiRunEvaluator

print("=" * 70)
print("PAPER #2 & #7 QUICK TEST (FRAMEWORK TESTBEDS)")
print("=" * 70)

# -------------------------
# Paper #2 testbed (id=2)
# -------------------------
print("\n[Paper #2] Running stochastic testbed with Oracle + EXPNeuralUCB...")

cfg2 = ExperimentConfiguration(
    runs=1,
    envtype="stochastic",
    attacktype="stochastic",
    attackintensity=0.25,
    models=["Oracle", "EXPNeuralUCB"],
    testbedid=2,
    verbose=True
)
p2 = cfg2.gettestbedconfig()
frames2 = p2.get("totalframes", 1400)

eval2 = MultiRunEvaluator(
    configs=cfg2,
    baseframes=frames2,
    framestep=frames2
)
_ = eval2.run_multi_model_evaluation()
print("  ✓ Paper #2 testbed run finished")

# -------------------------
# Paper #7 testbed (id=7)
# -------------------------
print("\n[Paper #7] Running stochastic testbed with Oracle + EXPNeuralUCB...")

cfg7 = ExperimentConfiguration(
    runs=1,
    envtype="stochastic",
    attacktype="stochastic",
    attackintensity=0.25,
    models=["Oracle", "EXPNeuralUCB"],
    testbedid=7,
    verbose=True
)
p7 = cfg7.gettestbedconfig()
frames7 = p7.get("totalframes", 2000)

eval7 = MultiRunEvaluator(
    configs=cfg7,
    baseframes=frames7,
    framestep=frames7
)
_ = eval7.run_multi_model_evaluation()
print("  ✓ Paper #7 testbed run finished")

print("\n" + "=" * 70)
print("✓ All tests passed! Ready for full evaluation")
print("=" * 70)
```

Run with:

```bash
python test_papers_2_7.py
```


## SNIPPET 6: Build a Simple Comparison Table from Results

Once you have aggregated metrics (e.g., from logs or post‑processed pickles), you can build a quick markdown comparison table with pandas. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

```python
#!/usr/bin/env python
"""Generate a simple cross-testbed comparison table."""
import pandas as pd

# Example: fill in metrics you extracted from evaluation results/logs
results = {
    'Testbed': ['Paper2', 'Paper2', 'Paper7', 'Paper7'],
    'Algorithm': ['Oracle', 'EXPNeuralUCB', 'Oracle', 'EXPNeuralUCB'],
    'Metric': ['Efficiency', 'Efficiency', 'Efficiency', 'Efficiency'],
    'Our Model': [0.88, 0.91, 0.84, 0.89],
    'Baseline': [0.90, 0.90, 0.82, 0.82],
}

df = pd.DataFrame(results)
df['Gap'] = ((df['Our Model'] - df['Baseline']) / df['Baseline'] * 100).round(1)
df['Gap'] = df['Gap'].apply(lambda x: f"{x:+.1f}%")

print("\n" + "=" * 100)
print("CROSS-TESTBED COMPARISON TABLE")
print("=" * 100)
print(df.to_string(index=False))
print("=" * 100)

with open('comparison_results.md', 'w') as f:
    f.write("# Cross-Testbed Comparison\n\n")
    f.write(df.to_markdown(index=False))

print("\n✓ Comparison saved to comparison_results.md")
```


## SNIPPET 7: Colab Cell – Paper 2 Testbed on Shared Drive

This is a minimal **Colab** cell that mounts the shared drive, uses the default research models, and runs a Paper 2 testbed experiment, with results written to the shared quantum data lake. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)

```python
from google.colab import drive
drive.mount('/content/drive')

import sys
sys.path.insert(0, '/content/drive/Shareddrives/ai_quantum_computing/DynamicRoutingEvalFramework')

from daqr.config.experimentconfig import ExperimentConfiguration
from daqr.evaluation.multirunevaluator import MultiRunEvaluator

config = ExperimentConfiguration(
    runs=1,
    envtype="stochastic",
    attacktype="stochastic",
    attackintensity=0.25,
    models=None,         # default research models
    testbedid=2,         # Paper 2 testbed
    verbose=True
)

paper2_cfg = config.gettestbedconfig()
frames = paper2_cfg.get("totalframes", 1400)

evaluator = MultiRunEvaluator(
    configs=config,
    baseframes=frames,
    framestep=frames
)

results = evaluator.run_multi_model_evaluation()
print("✅ Colab Paper 2 run complete (results in quantum_data_lake)")
```


## SNIPPET 8: Cross-Paper Loop for Reporting

Use this pattern to **loop over multiple paper testbeds** and stash per‑testbed summaries for later comparison plots or tables. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/f977fe86-d826-41c1-abb0-166453ab4b46/multi_run_evaluator.py)

```python
from daqr.config.experimentconfig import ExperimentConfiguration
from daqr.evaluation.multirunevaluator import MultiRunEvaluator

paper_ids = [2, 5, 7, 8, 12]
summary = {}

for pid in paper_ids:
    cfg = ExperimentConfiguration(
        runs=3,
        envtype="stochastic",
        attacktype="stochastic",
        attackintensity=0.25,
        models=["Oracle", "EXPNeuralUCB"],
        testbedid=pid,
        verbose=False
    )
    pcfg = cfg.gettestbedconfig()
    total_frames = pcfg.get("totalframes", 2000)

    evalr = MultiRunEvaluator(
        configs=cfg,
        baseframes=total_frames,
        framestep=total_frames
    )
    res = evalr.run_multi_model_evaluation()
    summary[f"paper{pid}"] = res

print("Collected results keys:", list(summary.keys()))
```


***

## How to Use These Snippets

- Use **Snippet 1** to run a compact Paper 2–style experiment from any notebook or script.  
- Use **Snippet 2** to verify that all configured paper testbeds execute successfully.  
- Use **Snippet 3** to understand the exact parameters (arms, frames, modelparams) driving each paper testbed.  
- Use **Snippet 4** when you need physics‑accurate replication of Paper 2 (topology, noise, fidelity, reward).  
- Use **Snippet 5–6** to run small end‑to‑end tests and generate markdown comparison tables.  
- Use **Snippet 7–8** in Colab or scripts to automate multi‑testbed evaluation and reporting.