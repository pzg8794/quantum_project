# Quantum Routing Paper Testbeds – Parallel Runners

## Problem addressed

The original monolithic pipeline (e.g., a single script with nested loops over allocators, physics models, and scales) tended to accumulate graph state, file handles, and GPU memory, which eventually led to stalls or out-of-memory conditions. The current design separates concerns into a **dedicated allocator runner** and optional thin wrapper scripts so that each paper-style testbed can run independently or in parallel processes. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)


## Core runner and suggested scripts

### Core implementation (already in the framework)

- **`daqr/evaluation/allocator_runner.py`**  
  - Provides **`AllocatorRunner`**, an isolated OOP runner for a single allocator type across one or more physics models (e.g., `"paper2"`, `"paper7"`, `"paper12"`, `"default"`). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)
  - Handles configuration wiring from a shared framework config (paths, qubit capacities, seeds) and calls `getphysicsparams(...)` to build paper-specific physics (topology, noise, fidelity, rewards). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)
  - Includes aggressive cleanup of environments, backup managers, model registries, CUDA memory, and file descriptors between runs. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9fdf19ed-1342-4075-a957-3e8584ca76cc/quantum_physics.py)

### Suggested thin runner scripts (you create these)

You can define small front-end scripts that each focus on a subset of physics models or testbeds:

```text
run_allocator_default.py      # Default/stochastic framework environment
run_allocator_paper2.py       # Paper 2 (Huang et al. 2023) physics model
run_allocator_paper7.py       # Paper 7 (Liu et al. 2024 – QBGP) physics model
run_allocator_paper12.py      # Paper 12 (Wang et al. 2024 – QuARC) physics model
launch_all_allocators.py      # Master launcher to run several in parallel
```

Each of these scripts just configures `AllocatorRunner` and passes in the appropriate `physicsmodels` list and `getphysicsparams` function from the clean testbed notebook. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)


## Usage

### Option 1 – Run individual paper-style physics models (separate terminals)

Example shell usage:

```bash
# Window 1 – Default / baseline physics model
python run_allocator_default.py

# Window 2 – Paper 2 physics model
python run_allocator_paper2.py

# Window 3 – Paper 7 physics model
python run_allocator_paper7.py

# Window 4 – Paper 12 physics model
python run_allocator_paper12.py
```

A minimal pattern for `run_allocator_paper2.py`:

```python
#!/usr/bin/env python
from daqr.evaluation.allocator_runner import AllocatorRunner
from daqr.config.experimentconfig import ExperimentConfiguration
from H_MABs_Eval_T_XQubit_Alloc_XQRuns import FRAMEWORKCONFIG, getphysicsparams  # adjust import path

if __name__ == "__main__":
    # Shared framework config (Paper 2 physics block is in FRAMEWORKCONFIG["paper2"])
    framework_config = FRAMEWORKCONFIG

    runner = AllocatorRunner(
        allocatortype="Default",          # "Default", "Random", "Dynamic", "ThompsonSampling", etc.
        physicsmodels=["paper2"],         # focus on Paper 2 physics model
        frameworkconfig=framework_config,
        scales=[1.0],                     # e.g., single scale for quick tests
        runs= [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py),                         # number of independent runs per scale
        models=None,                      # use framework default research models
        testscenarios=None,               # use default stochastic + baseline mapping
        config=None                       # optional custom ExperimentConfiguration
    )

    runner.run(getphysicsparamsfunc=getphysicsparams)
```

`AllocatorRunner.run(...)` then iterates over physics models, scales, and runs, calling `getphysicsparams(physicsmodel=..., currentframes=..., baseseed=..., qubitcap=...)` under the hood and feeding those into `MultiRunEvaluator`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)


### Option 2 – Launch multiple physics models in parallel (single command)

You can use a master script (e.g., `launch_all_allocators.py`) that starts one Python process per physics model:

```python
#!/usr/bin/env python
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

SCRIPTS = [
    "run_allocator_default.py",
    "run_allocator_paper2.py",
    "run_allocator_paper7.py",
    "run_allocator_paper12.py",
]

if __name__ == "__main__":
    procs = []
    for script in SCRIPTS:
        p = subprocess.Popen([sys.executable, str(ROOT / script)])
        procs.append(p)

    for p in procs:
        p.wait()
```

This pattern gives you **process-level isolation** between different physics models and allocators while reusing the same `AllocatorRunner` core. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)


## Configuration

Each runner script configures **which allocators, scales, and runs** to use; `AllocatorRunner` takes care of the testbed and physics details via `frameworkconfig` and `getphysicsparams`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

Example – inside `run_allocator_paper2.py`:

```python
from daqr.evaluation.allocator_runner import AllocatorRunner
from H_MABs_Eval_T_XQubit_Alloc_XQRuns import FRAMEWORKCONFIG, getphysicsparams

def main(test_mode: bool = True):
    scales = [1.0] if test_mode else [1.0, 1.5, 2.0]
    runs =  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py) if test_mode else [1, 2, 3]

    runner = AllocatorRunner(
        allocatortype="Default",                 # or "Random", "Dynamic", "ThompsonSampling"
        physicsmodels=["paper2"],
        frameworkconfig=FRAMEWORKCONFIG,
        scales=scales,
        runs=runs,
        models=None,                             # use default research models from ExperimentConfiguration
        testscenarios=None,
        config=None
    )

    runner.run(getphysicsparamsfunc=getphysicsparams)

if __name__ == "__main__":
    main(test_mode=True)                         # ← flip to False for full production runs
```

Paper-specific physics and topology settings (e.g., `numpaths=8`, `totalqubits=35`, `gateerrorrate`, `memoryT2`, `swapmode`) are already encoded in `FRAMEWORKCONFIG["paper2"]` and interpreted by `getphysicsparams("paper2", ...)`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)


## Memory and resource management

`AllocatorRunner` and the supporting cleanup utilities aggressively manage memory and resources between runs. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9fdf19ed-1342-4075-a957-3e8584ca76cc/quantum_physics.py)

- **Environment cleanup:** Clears environment graphs (`topology`, `paths`) and breaks references from `ExperimentConfiguration` to the environment to avoid leaks. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)
- **Backup manager cleanup:** Stops log redirection, clears registries, and detaches backup managers associated with each evaluator. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)
- **Model registry cleanup:** Optionally clears any lingering model registries or global bandit model caches. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9fdf19ed-1342-4075-a957-3e8584ca76cc/quantum_physics.py)
- **Torch / CUDA cleanup:** Empties CUDA cache and synchronizes if a GPU is used. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)
- **Garbage collection and file descriptors:** Runs multiple GC passes and closes open file descriptors related to `.pkl`, `.log`, `.csv` files when using the more aggressive `forcereleaseresources(...)` pattern. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9fdf19ed-1342-4075-a957-3e8584ca76cc/quantum_physics.py)

Running each physics model in its own OS process (Option 2) adds an additional isolation layer: when a process exits, its Python heap and CUDA context are fully released by the OS.  


## Output

Instead of per-paper CSVs with ad hoc filenames, results and model states are written via `LocalBackupManager` into organized **framework and model state directories**, keyed by configuration (allocator, environment, attack type, frame count, runs, etc.). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)

Typical locations:

- `daqr/config/frameworkstate/dayYYYYMMDD/` – per-run framework/evaluator logs and stats. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)
- `daqr/config/modelstate/dayYYYYMMDD/` – model parameter/state snapshots per run and environment. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

You can post-process these with the same tooling you already use for your neural bandit experiments, or with custom scripts that read the registries maintained by `LocalBackupManager`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)


## Troubleshooting

### “Module not found” errors

- Ensure you are running scripts from the **project root** where the `daqr` package is importable and the notebook-relative helpers (like `H_MABs_Eval_T_XQubit_Alloc_XQRuns`) are on `sys.path`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)
- From the shell:

```bash
cd /path/to/DynamicRoutingEvalFramework
python run_allocator_paper2.py
```

### Out-of-memory or long runtimes

- Reduce `scales` and `runs` in the runner script, or shorten the total frame count in the underlying `ExperimentConfiguration` or testbed config. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
- For quick validation, use small `scales=[1.0]` and `runs= [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)` before ramping up.  

### Process hangs

- Make sure `AllocatorRunner.cleanupevaluator(...)` or the more aggressive `forcereleaseresources(...)` utility (from the physics module) is being called at the end of runs, especially after keyboard interrupts. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9fdf19ed-1342-4075-a957-3e8584ca76cc/quantum_physics.py)
- If a process still hangs, inspect logs in the config state directories to see which physics model or allocator combination last printed output, then kill that PID manually.  


## Key benefits

1. **No resource conflicts:** Each physics model + allocator combination can run in its own process with explicit cleanup between runs. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)
2. **Parallel execution:** A simple launcher script can start multiple allocator runners (e.g., Paper 2, 7, 12) concurrently on a multi-core machine.  
3. **Easy debugging:** You can focus on a single physics model (e.g., `"paper7"`) by running only one runner script with very small `scales` and `runs`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)
4. **Scalable design:** Adding a new paper-style testbed usually means extending `FRAMEWORKCONFIG` / `PAPERCONFIGS` and `getphysicsparams(...)`, then pointing an `AllocatorRunner` at the new `physicsmodel`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
5. **Clean code paths:** The heavy lifting (physics, environment, evaluation, cleanup) is centralized; runner scripts stay short and declarative. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9fdf19ed-1342-4075-a957-3e8584ca76cc/quantum_physics.py)


## Next steps

1. **Verify sequentially:**  
   - Create and run `run_allocator_paper2.py` and `run_allocator_paper7.py` with `test_mode=True` (e.g., `scales=[1.0]`, `runs= [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)`). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)
2. **Scale up:**  
   - Increase `runs` and `scales`, and, if desired, include multiple allocators (`"Default"`, `"Random"`, `"Dynamic"`, `"ThompsonSampling"`). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)
3. **Parallelize:**  
   - Add `launch_all_allocators.py` to start multiple runner scripts at once when you are confident each one is stable on its own.  
4. **Analyze:**  
   - Use your existing evaluation and visualization tools (or the clean testbed notebook) to compare allocator and bandit behavior across `"default"`, `"paper2"`, `"paper7"`, and `"paper12"` physics models. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)