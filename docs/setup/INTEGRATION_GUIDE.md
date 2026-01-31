
# INTEGRATION GUIDE: Paper Testbeds

### Running Papers #2, #5, #7, #8, #12 in Dynamic Routing Evaluation Framework

## Overview

The current framework already has **built‑in hooks** for paper-style testbeds via:

- `ExperimentConfiguration.PAPERCONFIGS` (per‑paper testbed settings). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
- Paper-specific topology generators in `daqr.core.topologygenerator`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b763d538-0411-4ab5-b724-bf4750f65ea6/topology_generator.py)
- Paper-specific physics / reward models in `daqr.core.quantumphysics`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9fdf19ed-1342-4075-a957-3e8584ca76cc/quantum_physics.py)
- Evaluation drivers (`MultiRunEvaluator`, `AllocatorRunner`) that can use these configs. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)

This guide shows how to **activate and use** those pieces rather than adding a separate `paper_testbeds.py` file.


***

## STEP 1: Enable Paper Configs in ExperimentConfiguration

`ExperimentConfiguration` already defines a `PAPERCONFIGS` dictionary keyed by paper ID. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)

Examples (abridged):

- `2`: `Paper2UCB2023` with `narms=8`, `totalframes=1400`, and model params like `nnodes=15`, `fidelitythreshold=0.582`, `synchronizedswapping=True`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
- `5`: `Paper5Feedback2025` with `narms=10`, `totalframes=2000`, `modelparams={'feedbacktype': 'combined'}`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
- `7`: `Paper7QBGP2024` with `narms=15`, `totalframes=2000`, `modelparams={'k': 5, 'nqisps': 3, 'networkscale': 'large'}`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
- `8`: `Paper8DQN2025` with `narms=8`, `totalframes=1500`, `modelparams={'learningrate': 0.01}`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
- `12`: `Paper12QuARC2024` with `narms=10`, `totalframes=2000`, `modelparams={'nclusters': 3}`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)

These are accessed through `testbedid` and `gettestbedconfig`:

```python
from daqr.config.experimentconfig import ExperimentConfiguration

# Example: configure for Paper #2 testbed
config = ExperimentConfiguration(
    runs=3,
    envtype="stochastic",          # primary environment
    attacktype="stochastic",       # or "random"
    attackintensity=0.25,
    models=None,                   # use default research models
    testbedid=2,                   # Paper #2
    verbose=True
)

paper_cfg = config.gettestbedconfig()
print(paper_cfg["name"], paper_cfg["narms"], paper_cfg["totalframes"])
```

This uses the internal `PAPERCONFIGS` mapping and tags the configuration as “Paper2UCB2023” with the right number of arms and frame budget. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)


***

## STEP 2: Use Paper-Specific Topology Generators

Topologies for Papers #2, #7, and #12 are implemented in `daqr.core.topologygenerator`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b763d538-0411-4ab5-b724-bf4750f65ea6/topology_generator.py)

- **Paper 2**: `Paper2TopologyGenerator`  
  - Random 2D placement of ~15 nodes with distance-based connectivity. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b763d538-0411-4ab5-b724-bf4750f65ea6/topology_generator.py)
  - Suggests 4 or 8 k‑shortest paths and marks the graph with `testbed='paper2'`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b763d538-0411-4ab5-b724-bf4750f65ea6/topology_generator.py)

- **Paper 7**: `Paper7ASTopologyGenerator`  
  - Loads an AS-level graph from `topologydata/as20000101.txt` (or synthetic fallback). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)
  - Keeps the largest connected component, can cap node count, and annotates `testbed='paper7'`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b763d538-0411-4ab5-b724-bf4750f65ea6/topology_generator.py)

- **Paper 12**: `Paper12WaxmanTopologyGenerator`  
  - Generates a Waxman graph with parameters `(nnodes, avgdegree, alpha, beta)` and tags `testbed='paper12'`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

You usually **won’t call these directly**; they are wrapped by physics helpers (see Step 3), but if you want raw topology:

```python
from daqr.core.topologygenerator import (
    Paper2TopologyGenerator,
    Paper7ASTopologyGenerator,
    Paper12WaxmanTopologyGenerator,
)

# Paper 2 topology
p2_topo = Paper2TopologyGenerator(numnodes=15, seed=42).generate()

# Paper 7 topology (AS graph)
p7_topo = Paper7ASTopologyGenerator(
    edgelistpath="daqr/core/topologydata/as20000101.txt",
    maxnodes=None,
    testbed="paper7"
).generate()

# Paper 12 Waxman topology
p12_topo = Paper12WaxmanTopologyGenerator(
    nnodes=100, avgdegree=6, alpha=0.4, beta=0.2, seed=42, testbed="paper12"
).generate()
```  



***

## STEP 3: Attach Paper Physics (Noise, Fidelity, Rewards)

Paper-specific physics and reward functions live in `daqr.core.quantumphysics`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9fdf19ed-1342-4075-a957-3e8584ca76cc/quantum_physics.py)

Key components:

- **Paper 2 (UCB on fiber network)**  
  - `FiberLossNoiseModel` — link error rates derived from distances and fiber attenuation. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9fdf19ed-1342-4075-a957-3e8584ca76cc/quantum_physics.py)
  - `FullPaper2FidelityCalculator` or `CascadedFidelityCalculator` — cascaded fidelity with optional gate and memory effects. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9fdf19ed-1342-4075-a957-3e8584ca76cc/quantum_physics.py)
  - `MemoryNoiseModel` and toggles `usegateerror`, `usememorydecay`, `swapmode`, `memoryT2`, `swapdelayperlink`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)
  - `Paper2RewardFunction` — piecewise, fidelity-based reward that matches your GA work. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9fdf19ed-1342-4075-a957-3e8584ca76cc/quantum_physics.py)

- **Paper 7 (QBGP over AS topology)**  
  - Uses `Paper7ASTopologyGenerator` + helper functions `generatepaper7paths` and `generatepaper7contexts` from the clean testbed notebook. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)
  - `Paper7RewardFunction` supports context-aware reward modes such as `neghop`, `negdegree`, `neglength`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

- **Paper 12 (QuARC routing with fusion)**  
  - `FusionNoiseModel`, `FusionFidelityCalculator`, `QuARCRewardFunction`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9fdf19ed-1342-4075-a957-3e8584ca76cc/quantum_physics.py)
  - `Paper12RetryFidelityCalculator` wraps the base fidelity calc with retry thresholds, attempt caps, and decay. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9fdf19ed-1342-4075-a957-3e8584ca76cc/quantum_physics.py)

The **clean testbed notebook** (`H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb`) provides a `getphysicsparams(...)` helper that builds the correct physics stack for `physicsmodel="paper2"`, `"paper7"`, or `"paper12"`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

Example pattern (simplified from that notebook):

```python
from daqr.core.quantumphysics import (
    FiberLossNoiseModel,
    CascadedFidelityCalculator,
    FullPaper2FidelityCalculator,
    MemoryNoiseModel,
    Paper2RewardFunction,
)

# Example: Paper 2 physics from topology + paths
# (In practice, you should reuse the getphysicsparams(...) helper from the notebook.)
```


***

## STEP 4: Run Paper Testbeds with MultiRunEvaluator

The framework uses `ExperimentConfiguration` + `MultiRunEvaluator` as the standard entry point. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

Import paths:

```python
from daqr.config.experimentconfig import ExperimentConfiguration
from daqr.evaluation.multirunevaluator import MultiRunEvaluator
```


You have two practical patterns:

### Pattern A: Fast Integration via Clean Testbed Notebook

In `H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb`, you:

- Define `FRAMEWORKCONFIG` with entries for `paper2`, `paper7`, and `paper12` (numpaths, totalqubits, gate errors, retry thresholds, etc.). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)
- Use `getphysicsparams(physicsmodel=..., currentframes=..., baseseed=..., qubitcap=...)` to construct noise/fidelity/reward + external contexts/rewards. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)
- Instantiate `ExperimentConfiguration` and `MultiRunEvaluator`, then let the helper wire physics into the environment via `setenvironment`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)

This is the **recommended way** to drive paper testbeds for allocator and model evaluation from notebooks.

### Pattern B: Direct MultiRunEvaluator for Paper #2

Minimal example using the existing configuration and defaults:

```python
from daqr.config.experimentconfig import ExperimentConfiguration
from daqr.evaluation.multirunevaluator import MultiRunEvaluator

# Paper #2 style testbed, stochastic focus
config = ExperimentConfiguration(
    runs=3,
    envtype="stochastic",
    attacktype="stochastic",          # stochastic natural failures
    attackintensity=0.25,
    models=None,                      # default research models (Oracle, GNeuralUCB, EXPNeuralUCB, CPursuitNeuralUCB, iCPursuitNeuralUCB)
    testbedid=2,                      # Paper 2 testbed config
    verbose=True
)

evaluator = MultiRunEvaluator(
    configs=config,
    baseframes=4000,
    framestep=2000
)

results = evaluator.run_multi_model_evaluation()
```

Here, `testbedid=2` pulls Paper 2 parameters from `PAPERCONFIGS`, and standard stochastic/adversarial scenarios are handled via `testscenarios` and attack mappings inside `ExperimentConfiguration`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)


***

## STEP 5: Allocator + Paper Physics (Advanced)

`AllocatorRunner` provides a **single-allocator harness** that is already wired to work with paper physics and testbeds. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)

Key points from `AllocatorRunner`:

- It imports `MultiRunEvaluator` and `ExperimentConfiguration`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)
- It reads allocator/testbed configuration (e.g., `numpaths`, `totalqubits`, `minqubitsperroute`, `testbed`) from `FRAMEWORKCONFIG` for physics models `"paper2"`, `"paper7"`, `"paper12"`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)
- It calls `createallocator(...)` which passes testbed-aware parameters into `QubitAllocator`, `RandomQubitAllocator`, `DynamicQubitAllocator`, or `ThompsonSamplingAllocator`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)
- For each physics model and scale, it builds an `ExperimentConfiguration`, injects the allocator, and runs `MultiRunEvaluator`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)

Example (adapted from the notebook) to run **Paper 2 allocator evaluation**:

```python
from daqr.evaluation.allocatorrunner import AllocatorRunner
from daqr.config.experimentconfig import ExperimentConfiguration
from daqr.evaluation.multirunevaluator import MultiRunEvaluator
from daqr.core.qubitallocator import QubitAllocator

# FRAMEWORKCONFIG should define paper2 under the hood (see clean testbed notebook)
PHYSICSMODELS = ["paper2"]
ALLOCATORS = ["Default"]  # maps to QubitAllocator baseline
SCALES =  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
RUNS =  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)

# Example framework ExperimentConfiguration used inside runner
framework_cfg = ExperimentConfiguration(
    envtype="stochastic",
    scenarios={"stochastic": "Stochastic Random Failures"},
    models=None,                # default research models
    attackintensity=0.25,
    basecapacity=False,
    verbose=True
)

runner = AllocatorRunner(
    allocatortype="Default",
    physicsmodels=PHYSICSMODELS,
    frameworkconfig=framework_cfg,
    scales=SCALES,
    runs=RUNS,
    models=framework_cfg.models,
    testscenarios={"stochastic": "Stochastic Random Failures"}
)

# getphysicsparams is the helper from the notebook
from H_MABs_Eval_T_XQubit_Alloc_XQRuns import getphysicsparams  # path symbolic

runner.run(getphysicsparamsfunc=getphysicsparams)
```  


This will:

- Generate Paper 2 topology and paths. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b763d538-0411-4ab5-b724-bf4750f65ea6/topology_generator.py)
- Build Paper 2 physics (noise, fidelity, reward) and contexts. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9fdf19ed-1342-4075-a957-3e8584ca76cc/quantum_physics.py)
- Run your allocator + research models across stochastic and adversarial scenarios using `MultiRunEvaluator`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)


***

## QUICK START: Paper #2 Testbed (≈45 min)

**Goal**: Compare your neural bandits against a Paper 2-style environment.

```python
from daqr.config.experimentconfig import ExperimentConfiguration
from daqr.evaluation.multirunevaluator import MultiRunEvaluator

# Paper 2 UCB-style testbed
config = ExperimentConfiguration(
    runs=3,
    envtype="stochastic",
    attacktype="stochastic",
    attackintensity=0.25,
    models=["Oracle", "GNeuralUCB", "EXPNeuralUCB"],
    testbedid=2,          # Paper2UCB2023
    verbose=True
)

evaluator = MultiRunEvaluator(
    configs=config,
    baseframes=4000,
    framestep=2000
)

results = evaluator.run_multi_model_evaluation()
```

This approximates the Paper 2 setting (15‑node topology, 8 paths, depolarizing/fiber loss noise, ~1400–4000 frames) while using your framework’s standard research models. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b763d538-0411-4ab5-b724-bf4750f65ea6/topology_generator.py)


***

## QUICK START: Cross-Paper Comparison (Papers #2, #7, #12)

You can run the same **model set** under multiple paper testbeds by looping over `testbedid` and/or `physicsmodel`.

Conceptual pattern:

```python
from daqr.config.experimentconfig import ExperimentConfiguration
from daqr.evaluation.multirunevaluator import MultiRunEvaluator

paper_ids = [2, 7, 12]
common_models = ["GNeuralUCB", "EXPNeuralUCB", "CPursuitNeuralUCB"]

all_results = {}

for pid in paper_ids:
    cfg = ExperimentConfiguration(
        runs=3,
        envtype="stochastic",
        attacktype="stochastic",
        attackintensity=0.25,
        models=common_models,
        testbedid=pid,
        verbose=False
    )

    evaluator = MultiRunEvaluator(
        configs=cfg,
        baseframes=cfg.PAPERCONFIGS[pid]["totalframes"],
        framestep=cfg.PAPERCONFIGS[pid]["totalframes"],  # single block per paper
    )

    res = evaluator.run_multi_model_evaluation()
    all_results[f"paper{pid}"] = res
```

Here, `PAPERCONFIGS[pid]["totalframes"]` gives paper-specific frame budgets so you do not have to hard-code them in the loop. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)


***

## File Layout After Integration

With the current design, **no extra Python files** are needed; paper support is already wired into core modules. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b763d538-0411-4ab5-b724-bf4750f65ea6/topology_generator.py)

Typical structure:

```text
DynamicRoutingEvalFramework/
├── daqr/
│   ├── config/
│   │   └── experimentconfig.py          # ExperimentConfiguration + PAPERCONFIGS
│   ├── core/
│   │   ├── topologygenerator.py         # Paper2TopologyGenerator, Paper7ASTopologyGenerator, Paper12WaxmanTopologyGenerator
│   │   ├── quantumphysics.py            # FiberLossNoiseModel, FullPaper2FidelityCalculator, Paper2RewardFunction, FusionNoiseModel, Paper12RetryFidelityCalculator, ...
│   ├── evaluation/
│   │   ├── multirunevaluator.py         # MultiRunEvaluator
│   │   ├── allocatorrunner.py           # AllocatorRunner (paper-aware)
│   │   └── visualizer.py                # QuantumEvaluatorVisualizer
│   └── algorithms/
│       ├── predictivebandits.py         # EXPNeuralUCB, GNeuralUCB, CPursuitNeuralUCB, iCPursuitNeuralUCB, ...
│       └── basebandit.py, neuralbandits.py
└── notebooks/
    └── H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb   # Clean paper testbed + evaluation workflow
```



***

## Expected Comparison Table

After running paper testbeds and aggregating metrics with `QuantumEvaluatorVisualizer` + your own summarization, you should be able to populate a table like:

| Paper | Metric                     | Our Model      | Paper Baseline | Gap  | Status            |
|-------|----------------------------|----------------|----------------|------|-------------------|
| #2    | Convergence (steps)        | [X]            | [Y]            | [Z%] | ✅ Within 5%       |
| #2    | Synchronized Gain (%)      | [A]            | [B]            | [C%] | ✅ Comparable      |
| #7    | Top‑K Accuracy (%)         | [P]            | [Q]            | [R%] | ✅ Exceeds         |
| #7    | Entanglement Consumed      | [M]            | [N]            | [O%] | ✅ More efficient  |
| #5    | Feedback Efficiency        | [X]            | [Y]            | [Z%] | ✅ Better          |
| #12   | QuARC Throughput / Retry   | [U]            | [V]            | [W%] | ✅ Comparable/Best |

Metrics for Papers #7 and #12 will often be derived from the external contexts/rewards generated by the helper physics functions (`generatepaper7contexts`, `getphysicsparamspaper12`, etc.). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)


***

## Key Integration Points

1. **Config-driven paper testbeds**  
   - `PAPERCONFIGS` centralizes per-paper parameters (arms, frames, topology and physics knobs). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
   - `testbedid` on `ExperimentConfiguration` selects a paper. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)

2. **Environment and physics separation**  
   - Topology generation and noise/fidelity/reward models are modular and capacity-agnostic. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b763d538-0411-4ab5-b724-bf4750f65ea6/topology_generator.py)
   - `ExperimentConfiguration.setenvironment(...)` can accept externally-built physics objects (noise model, fidelity calculator, external contexts/rewards). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)

3. **MultiRunEvaluator compatibility**  
   - No API changes are required; paper experiments use the same `MultiRunEvaluator` entry points as baseline/stochastic/adversarial runs. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/f977fe86-d826-41c1-abb0-166453ab4b46/multi_run_evaluator.py)

4. **Allocator integration**  
   - `AllocatorRunner` passes paper-aware parameters to allocators (including `testbed`) and then delegates to `MultiRunEvaluator`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)

5. **Visualization and reporting**  
   - `QuantumEvaluatorVisualizer` can load any `framework_state/day_YYYYMMDD` directory and plot scenario comparisons, including paper runs. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)


***

## Common Errors & Solutions

**ERROR:** “Unknown testbed” or `gettestbedconfig` returns `None`  
**CAUSE:** `testbedid` not set or not in `PAPERCONFIGS`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
**FIX:** Set `testbedid` to one of `{2, 5, 7, 8, 12, 99}` or extend `PAPERCONFIGS` for your new paper.

***

**ERROR:** Paper2 physics not matching expected noise model  
**CAUSE:** Feature toggles (`usegateerror`, `usememorydecay`, `usepaper2rewards`, `swapmode`) misconfigured. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9fdf19ed-1342-4075-a957-3e8584ca76cc/quantum_physics.py)
**FIX:** Align these in your config/notebook with the paper; for strict replication, use recommended values in the clean testbed notebook (`gateerrorrate≈0.02`, `swapmode="sync"`, `memoryT2≈5000`, etc.). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

***

**ERROR:** Paper 7 / Paper 12 paths or contexts look wrong  
**CAUSE:** Custom changes to `generatepaper7paths`, `generatepaper7contexts`, or `getphysicsparamspaper12`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)
**FIX:** Start from the notebook’s reference implementation and only adjust clearly-documented knobs (e.g., `k`, `nqisps`, `rewardmode`, `splitconstant`). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b763d538-0411-4ab5-b724-bf4750f65ea6/topology_generator.py)

***

## Success Checklist

- [ ] `ExperimentConfiguration.PAPERCONFIGS` has entries for Papers #2, #5, #7, #8, #12. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
- [ ] `testbedid` is set correctly in your `ExperimentConfiguration`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
- [ ] Topologies are generated by `Paper2TopologyGenerator`, `Paper7ASTopologyGenerator`, or `Paper12WaxmanTopologyGenerator` as appropriate. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b763d538-0411-4ab5-b724-bf4750f65ea6/topology_generator.py)
- [ ] Physics models (`FiberLossNoiseModel`, `FullPaper2FidelityCalculator`, `Paper7RewardFunction`, `FusionNoiseModel`, `Paper12RetryFidelityCalculator`, etc.) are active for the corresponding papers. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9fdf19ed-1342-4075-a957-3e8584ca76cc/quantum_physics.py)
- [ ] `MultiRunEvaluator` runs complete without errors for at least one configuration per paper. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/f977fe86-d826-41c1-abb0-166453ab4b46/multi_run_evaluator.py)
- [ ] Visualizations load from `quantum_data_lake/framework_state/day_YYYYMMDD/` and show paper runs. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)
- [ ] You can populate a markdown comparison table summarizing performance gaps between your models and each paper’s baseline metrics.