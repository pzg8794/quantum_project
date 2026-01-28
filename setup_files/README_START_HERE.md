# MASTER SUMMARY – Everything You Need to Know

## Complete overview of the paper-style testbed integration

This version reflects the current **in-framework** design: paper testbeds are implemented through configuration, physics modules, and topology generators, not separate bandit classes. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9fdf19ed-1342-4075-a957-3e8584ca76cc/quantum_physics.py)


## What Has Been Created For You

### Core implementation components (already wired into the framework)

1. **Paper-style testbed registry in `experiment_config.py`**  
   - `ExperimentConfiguration.PAPERCONFIGS` now defines standardized testbeds for Papers #2, #5, #7, #8, #12, each with `narms`, `totalframes`, and `modelparams` (e.g., nodes, k, nqisps, learning rate, clusters). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
   - `gettestbedconfig()` reads `self.testbedid` and returns the corresponding paper testbed dictionary when you set `testbedid` in `ExperimentConfiguration`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
   - Paper 2: `narms=8`, `totalframes=1400`, `modelparams` include `nnodes=15`, `fidelitythreshold=0.582`, `synchronizedswapping=True`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
   - Paper 5: `narms=10`, `totalframes=2000`, `modelparams={'feedbacktype': 'combined'}`; Paper 7: `narms=15`, `totalframes=2000`, `modelparams` include `k=5`, `nqisps=3`, `networkscale='large'`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
   - Paper 8: `narms=8`, `totalframes=1500`, `modelparams={'learningrate': 0.01}`; Paper 12: `narms=10`, `totalframes=2000`, `modelparams={'nclusters': 3}`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)

2. **Paper-specific physics and topology adapters**  
   - `daqr/core/topology_generator.py` implements **Paper2TopologyGenerator**, **Paper7ASTopologyGenerator**, and **Paper12WaxmanTopologyGenerator** to reproduce each paper’s topology style while staying capacity-agnostic. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b763d538-0411-4ab5-b724-bf4750f65ea6/topology_generator.py)
   - `daqr/core/quantum_physics.py` defines reusable quantum noise and fidelity components plus paper-specific pieces: **FiberLossNoiseModel** and **Paper2RewardFunction** (Paper 2), **FusionNoiseModel** and **QuARCRewardFunction** (Paper 12), plus generic capacity-agnostic fidelity calculators. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9fdf19ed-1342-4075-a957-3e8584ca76cc/quantum_physics.py)
   - The clean testbed notebook `H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb` provides a unified `getphysicsparams(...)` helper that maps high-level `physicsmodel` labels like `"paper2"`, `"paper7"`, `"paper12"` into consistent tuples: `(noisemodel, fidelitycalculator, externaltopology, externalcontexts, externalrewards)`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)
   - Paper 2 physics uses Fiber-loss–based noise with optional gate errors and memory decay, plus a piecewise reward function if `usepaper2rewards` is enabled in the Paper 2 config block. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)
   - Paper 7 physics uses AS-level topologies from `as20000101.txt` (or synthetic Barabási–Albert fallback) and can generate **context-aware rewards** via `Paper7RewardFunction` when `usecontextrewards=True`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b763d538-0411-4ab5-b724-bf4750f65ea6/topology_generator.py)
   - Paper 12 physics uses a Waxman topology, multi-hop fusion noise via `FusionNoiseModel`, and can be wrapped by `Paper12RetryFidelityCalculator` to model QuARC-style retries and time-decay. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9fdf19ed-1342-4075-a957-3e8584ca76cc/quantum_physics.py)

3. **Allocator runner and multi-run evaluator integration**  
   - `AllocatorRunner` in `daqr/evaluation/allocator_runner.py` now reads all paper-specific parameters (including `testbed`) from the framework config, passes them into each allocator, and validates that qubit allocations match the expected `numpaths` and total qubits. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)
   - For a given `physicsmodel` (e.g., `"paper2"`), `AllocatorRunner` calls `getphysicsparams(...)`, then uses `MultiRunEvaluator` with a correctly-initialized `ExperimentConfiguration` to run the full stochastic/adversarial scenario suite. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)
   - MultiRunEvaluator is reused as-is to compute per-scenario reward, efficiency, threshold comparisons, and winner selection across baseline, stochastic, and multiple adversarial attack types. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

### Documentation files (your guides)

These are your human-facing guides; they describe how to drive the above components rather than adding new APIs.

3. **INTEGRATION_GUIDE.md**  
   - Step-by-step procedure to run paper testbeds through `ExperimentConfiguration`, `gettestbedconfig()`, `getphysicsparams(...)`, and `MultiRunEvaluator`.  
   - Copy-paste code for setting `testbedid`, using the physics helpers, and running minimal Paper 2/Paper 7 experiments.  

4. **IMPLEMENTATION_CHECKLIST.md**  
   - Two-day, hour-by-hour plan to go from “nothing running” to cross-testbed results saved and summarized.  
   - Emphasizes early validation of testbeds 2 and 7, then layering in 5, 8, 12 and reporting.  

5. **SEAMLESS_INTEGRATION_SUMMARY.md**  
   - High-level architecture diagram showing how `ExperimentConfiguration.PAPERCONFIGS`, topology generators, quantum physics, MultiRunEvaluator, and AllocatorRunner compose into a full evaluation stack. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b763d538-0411-4ab5-b724-bf4750f65ea6/topology_generator.py)
   - Quick-reference tables for which configs and physics blocks correspond to each paper-style testbed.  

6. **QUICK_START_CODE_SNIPPETS.md**  
   - Ready-to-run examples for:  
     - Single-paper quick test via `testbedid` and `MultiRunEvaluator`.  
     - Multi-paper loop over testbeds `[2,5,7,8,12]`.  
     - Colab-based runs that mount the shared drive and write logs to the quantum data lake. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

7. **This file – MASTER_SUMMARY.md**  
   - Big-picture orientation: what exists, how it fits together, and what you should prioritize this week.  


***

## Quick Facts

These quick facts are about **project scope and workflow**, not individual code lines.

| Metric | Value |
|--------|-------|
| **New core integration points** | 3 modules (config, physics, topology) + 1 notebook + allocator runner wiring  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py) |
| **New documentation** | 5 guides (integration, checklist, architecture, quick start, master summary) |
| **Integration effort** | ~6–8 hours hands-on (following the checklist) |
| **Testing effort** | ~3–4 hours (Paper #2 & #7 full plus spot checks on #5, #8, #12) |
| **Paper-style testbeds** | 5 (IDs 2, 5, 7, 8, 12 in `PAPERCONFIGS`)  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py) |
| **Physics-specialized papers** | 3 (Paper 2, 7, 12 via dedicated topology + physics helpers)  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b763d538-0411-4ab5-b724-bf4750f65ea6/topology_generator.py) |
| **Breaking changes** | 0 – existing model APIs and evaluation entry points remain intact  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py) |
| **External dependencies added** | 0 – uses only existing framework stack (NetworkX, NumPy, PyTorch, etc. already present)  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb) |


***

## What Each Paper-Style Testbed Does

These are **testbed definitions and physics mappings**, not standalone bandit classes. You plug in your bandit algorithms via `ExperimentConfiguration.models` or AllocatorRunner, and the testbed guarantees the paper-like environment. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9fdf19ed-1342-4075-a957-3e8584ca76cc/quantum_physics.py)

### Paper #2 – Chaudhary et al. (2023), UCB-Style Route Selection

- **Testbed ID:** `2` in `ExperimentConfiguration.PAPERCONFIGS` (`name="Paper2UCB2023"`, `narms=8`, `totalframes=1400`). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
- **Topology & physics:** Uses `Paper2TopologyGenerator` for a 15-node geometric network and `FiberLossNoiseModel` to compute per-link loss from distances, with optional gate errors and memory decay. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b763d538-0411-4ab5-b724-bf4750f65ea6/topology_generator.py)
- **Reward model:** `Paper2RewardFunction` implements a fidelity-based piecewise reward that strongly penalizes low-fidelity routes and rewards high-fidelity ones, matching Paper 2’s qualitative behavior. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9fdf19ed-1342-4075-a957-3e8584ca76cc/quantum_physics.py)
- **Key configuration knobs:** `sourcenode`, `destnode`, `numpaths` (commonly 8), `pinit`, `fattenuation`, `gateerrorrate`, `memoryT2`, `swapmode`, and feature toggles like `usepaper2rewards`, `usegateerror`, `usememorydecay`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)
- **Metrics you get out:** Standard framework stats per algorithm and scenario (reward, efficiency vs thresholds, retries, failures, and winner) under stochastic and multiple adversarial attack models. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

### Paper #7 – Liu et al. (2024), Quantum BGP / Top‑K Path Selection

- **Testbed ID:** `7` in `PAPERCONFIGS` (`name="Paper7QBGP2024"`, `narms=15`, `totalframes=2000`, `modelparams={'k': 5, 'nqisps': 3, 'networkscale': 'large'}`). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
- **Topology & contexts:** `Paper7ASTopologyGenerator` loads a real AS topology from `as20000101.txt` (or generates a synthetic AS-like graph as fallback) and you build K-shortest paths between selected ISP nodes. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b763d538-0411-4ab5-b724-bf4750f65ea6/topology_generator.py)
- **Context-aware rewards:** Helper functions in the notebook compute per-path feature vectors (hop count, average degree, path length), and `Paper7RewardFunction` can transform these into context-based rewards when `usecontextrewards=True`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)
- **Key configuration knobs:** `k` (top‑K), `nqisps`, `networkscale`, `rewardmode` (`neghop`, `negdegree`, `neglength`, or `custom`), plus `usesynthetic` to switch between real and synthetic AS topologies. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)
- **Metrics you get out:** Per-scenario reward and efficiency for each bandit across stochastic and adversarial environments, plus the usual winner and gap summaries from MultiRunEvaluator. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

### Paper #5 – Wang et al. (2025), Learning Best Paths with Feedback

- **Testbed ID:** `5` in `PAPERCONFIGS` (`name="Paper5Feedback2025"`, `narms=10`, `totalframes=2000`, `modelparams={'feedbacktype': 'combined'}`). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
- **Role in the framework:** Defines a standardized **10-arm, medium-horizon** environment where you can interpret arms as paths and design bandits that mix link-level and path-level feedback. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
- **How you use it:** Select any of your research models (e.g., `EXPNeuralUCB`, `GNeuralUCB`, contextual variants) in `ExperimentConfiguration.models` and run them under this testbed to study the impact of richer vs simpler feedback. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)

### Paper #8 – Jallow & Khan (2025), DQN-Style Routing

- **Testbed ID:** `8` in `PAPERCONFIGS` (`name="Paper8DQN2025"`, `narms=8`, `totalframes=1500`, `modelparams={'learningrate': 0.01}`). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
- **Role in the framework:** Provides an **8-action, longer-horizon** setting suitable for comparing neural and deep-learning–inspired routing methods against your existing bandits. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
- **How you use it:** Treat the environment as a bandit over 8 routing actions with a tunable effective “learning rate” parameter in `modelparams`, and evaluate your bandits in the same frame budget as the DQN-style baseline. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)

### Paper #12 – Wang et al. (2024), QuARC Clustering & Fusion

- **Testbed ID:** `12` in `PAPERCONFIGS` (`name="Paper12QuARC2024"`, `narms=10`, `totalframes=2000`, `modelparams={'nclusters': 3}`). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
- **Topology & physics:** Uses `Paper12WaxmanTopologyGenerator` to build a Waxman graph and `FusionNoiseModel` plus `FusionFidelityCalculator` (optionally wrapped in `Paper12RetryFidelityCalculator`) to approximate QuARC-style fusion and retry behavior. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9fdf19ed-1342-4075-a957-3e8584ca76cc/quantum_physics.py)
- **Reward model:** `QuARCRewardFunction` encodes throughput-style rewards that respect fusion success probabilities and memory/time decay, which can be further shaped by the retry wrapper. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9fdf19ed-1342-4075-a957-3e8584ca76cc/quantum_physics.py)
- **Key configuration knobs:** `nnodes`, `avgdegree`, `fusionprob`, `entanglementprob`, `qubitspernode`, `numsdpairs`, `epochlength`, `totaltimeslots`, `splitconstant`, `enableclustering`, `enablesecondaryfusions`, plus retry parameters (`retrythreshold`, `maxretryattempts`, `retrydecayrate`, `retrycostperattempt`). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)


***

## How Everything Fits Together

The current system uses **configs + physics + topology + evaluators**, all inside the existing package layout. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)

```text
Your Existing Framework        +    New Testbed Integration        =    Complete System
────────────────────────            ─────────────────────────           ───────────────────

daqr/config/experimentconfig.py      PAPERCONFIGS mapping               ✓ Paper-style testbeds
│                                    ├─ IDs: 2, 5, 7, 8, 12
├─ Algorithm registries              └─ gettestbedconfig()

daqr/core/topology_generator.py      Paper2TopologyGenerator            ✓ Paper-specific topologies
│                                    Paper7ASTopologyGenerator
└─ Existing topology helpers         Paper12WaxmanTopologyGenerator

daqr/core/quantum_physics.py         FiberLossNoiseModel                ✓ Physics + rewards
│                                    FusionNoiseModel
├─ DefaultNoiseModel                 Paper2RewardFunction
├─ Fidelity calculators              QuARCRewardFunction
└─ Reward functions                  Paper12RetryFidelityCalculator

H-MABs_Eval-T_XQubit_Alloc_XQRuns    getphysicsparams(...)              ✓ Clean testbeds
(notebook)                           FRAMEWORKCONFIG[paper2,7,12]

daqr/evaluation/multirunevaluator.py + ExperimentConfiguration          ✓ Scenario evaluation
daqr/evaluation/allocator_runner.py  + AllocatorRunner testbed wiring

Your bandit models (Oracle,         Run across baseline, stochastic,
GNeuralUCB, EXPNeuralUCB, etc.)     and adversarial environments with
                                    paper-inspired physics and configs
```


***

## Day-by-Day Schedule

This schedule assumes **the code is already integrated** and your focus is on **running, validating, and analyzing** paper-style testbeds.

### Wednesday (Full Day) – Focus: Paper #2 and #7

| Time       | Task                                       | Duration | Status |
|-----------|--------------------------------------------|----------|--------|
| 8:00–8:15 | Pre-work setup                             | 15 min   | ☐ New git branch, backup config files |
| 8:15–8:35 | Inspect `PAPERCONFIGS` and FRAMEWORKCONFIG | 20 min   | ☐ Understand testbed IDs 2 & 7, paper2/paper7 blocks  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py) |
| 8:35–9:00 | Run small Paper #2 quick test              | 25 min   | ☐ Use `testbedid=2` + `MultiRunEvaluator` one-run script |
| 9:00–9:30 | Paper #2 physics-accurate run              | 30 min   | ☐ Use `physicsmodel="paper2"` + `getphysicsparams(...)`  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb) |
| 9:30–10:15| Analyze Paper #2 logs                      | 45 min   | ☐ Check efficiency, thresholds, winner per scenario  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb) |
| 10:15–11:00| Paper #7 topology + paths validation      | 45 min   | ☐ Generate AS topology, K-shortest paths, contexts  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b763d538-0411-4ab5-b724-bf4750f65ea6/topology_generator.py) |
| 11:00–12:00| Run Paper #7 testbed                      | 60 min   | ☐ Use `testbedid=7` and inspect stochastic/adversarial outputs  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py) |
| 12:00–1:00 | Results checkpoint                        | 60 min   | ☐ Save logs, export summary tables, commit |
| 1:00–3:00  | Buffer / debugging                        | 120 min  | ☐ Fix any import, path, or config issues |

**Goal for Wednesday:** Paper #2 and #7 testbeds fully validated and producing interpretable metrics for your core bandit set. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b763d538-0411-4ab5-b724-bf4750f65ea6/topology_generator.py)


### Thursday (Half Day) – Focus: Papers #5, #8, #12 and Reporting

| Time       | Task                                      | Duration | Status |
|-----------|-------------------------------------------|----------|--------|
| 9:00–9:45 | Quick tests for Paper #5 and #8           | 45 min   | ☐ Use `testbedid=5` and `8`, verify basic runs complete  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py) |
| 9:45–10:45| Paper #12 QuARC physics run               | 60 min   | ☐ Use `physicsmodel="paper12"` + retry wrapper  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb) |
| 10:45–11:30| Build comparison tables                   | 45 min   | ☐ Aggregate reward/efficiency across testbeds into markdown |
| 11:30–12:30| Draft short markdown report               | 60 min   | ☐ Summarize findings + key plots or tables |
| 12:30–1:00 | Final review for supervisor meeting       | 30 min   | ☐ Ensure logs, tables, and notebooks are in a clean state |

**Total project:** ~8–10 hours of actual running/analysis across 2 days, comfortably within your Wednesday–Thursday window.


***

## Success Metrics (What You’ll Have by Thursday 1 PM)

### Minimum Success (must deliver)

- ✅ Paper #2 and #7 testbeds run end-to-end using `testbedid` and physics helpers. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b763d538-0411-4ab5-b724-bf4750f65ea6/topology_generator.py)
- ✅ At least one cross-scenario table for Paper #2 (stochastic vs adversarial) with reward/efficiency and winner per algorithm. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)
- ✅ All scripts and notebooks execute without import or configuration errors. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)
- ✅ Results persisted in a dedicated `results/` or quantum data lake location you can reference later. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

### Target Success (should deliver)

- ✅ All 5 testbeds (2, 5, 7, 8, 12) exercised at least once with your core research models. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
- ✅ Cross-testbed markdown table comparing performance of key algorithms across multiple scenarios.  
- ✅ Short markdown/LaTeX-ready report tying your model’s performance to each paper’s scenario.  

### Stretch Success (great to have)

- ✅ Multiple parameter sweeps (e.g., different attack intensities or testbed settings) for at least two papers. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)
- ✅ Simple effect-size or confidence-interval analysis on efficiency gaps between algorithms.  
- ✅ Publication-quality figures derived from your saved logs and comparison tables.  


***

## File Organization After Integration

Reflecting the **current repo structure and integration points**: [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)

```text
DynamicRoutingEvalFramework/
├── daqr/
│   ├── algorithms/
│   │   ├── predictivebandits.py          (Oracle, EXPNeuralUCB, GNeuralUCB, etc.)
│   │   └── ...                           (your existing bandits) [file:26]
│   ├── core/
│   │   ├── quantum_physics.py            (noise, fidelity, paper-specific rewards) [file:16]
│   │   ├── topology_generator.py         (Paper2, Paper7, Paper12 topology generators) [file:19]
│   │   └── qubitallocator.py             (allocators used by AllocatorRunner)
│   ├── config/
│   │   ├── experimentconfig.py           (PAPERCONFIGS, gettestbedconfig, thresholds) [file:26]
│   │   ├── localbackupmanager.py         (logging and registry support)
│   │   └── ... 
│   ├── evaluation/
│   │   ├── multirunevaluator.py          (multi-scenario evaluation engine)
│   │   ├── allocator_runner.py           (links allocators, physics, testbeds) [file:24]
│   │   └── visualizer.py                 (plots and summary views)
│   └── ...
│
├── notebooks/ or root
│   └── H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb
│       (clean testbed notebook with FRAMEWORKCONFIG + getphysicsparams) [file:27]
│
├── results/
│   ├── quantumlogs/                      (per-run logs via LocalBackupManager) [file:27]
│   └── (your saved .pkl/.md comparison outputs)
│
├── INTEGRATION_GUIDE.md
├── IMPLEMENTATION_CHECKLIST.md
├── SEAMLESS_INTEGRATION_SUMMARY.md
├── QUICK_START_CODE_SNIPPETS.md
├── MASTER_SUMMARY.md                    (this file)
└── README.md
```


***

## What Each Documentation File Does

| File | Purpose | Use When |
|------|---------|----------|
| **INTEGRATION_GUIDE.md** | Concrete steps to run each paper-style testbed using `ExperimentConfiguration`, `gettestbedconfig()`, and `getphysicsparams(...)`.  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py) | When you’re ready to execute experiments in order. |
| **IMPLEMENTATION_CHECKLIST.md** | Time-boxed checklist aligned with the Wednesday–Thursday plan. | When tracking daily progress and making sure nothing is skipped. |
| **SEAMLESS_INTEGRATION_SUMMARY.md** | Architecture and design rationale for embedding paper testbeds into existing modules instead of adding new bandit classes.  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py) | When you or your supervisor want to understand “how it all fits.” |
| **QUICK_START_CODE_SNIPPETS.md** | Copy-paste snippets for: quick Paper 2 run, multi-testbed loop, Colab integration, and simple comparison tables.  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py) | When you need exact code to drop into a notebook or script. |
| **MASTER_SUMMARY.md** | High-level overview of goals, assets, and schedule. | When you need the big picture and priorities at a glance. |


***

## Common Questions Answered

### Q: How long will this actually take?

You can realistically run and analyze Paper #2 and #7 in one long day (~5–6 focused hours) and finish Papers #5, #8, #12 plus reporting the next morning (~3–4 hours).  

### Q: Do I need to install anything new?

No; the integrations use your existing stack (PyTorch, NumPy, NetworkX, etc.), and the notebook confirms that dependencies are already installed. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

### Q: Will this break my existing code?

No; paper-style testbeds are added via new mappings and helper functions in existing modules, and they do not alter public APIs for models or evaluators. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b7a2cf22-7034-4755-84e8-4b2ac55f363c/allocator_runner.py)

### Q: Which papers should I prioritize?

Prioritize **Paper #2** (your own prior work, now with detailed physics and reward mapping) and **Paper #7** (realistic AS-level topology and context-aware rewards) because they most strongly showcase the robustness and adaptability of your bandits. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9fdf19ed-1342-4075-a957-3e8584ca76cc/quantum_physics.py)

### Q: What if I run out of time?

If time is tight, fully validate only Paper #2 and #7 and treat Papers #5, #8, and #12 as “bonus” testbeds for future extensions. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

### Q: How do I know if a testbed is configured correctly?

- Call `cfg = ExperimentConfiguration(..., testbedid=2)` then `cfg.gettestbedconfig()` and verify `narms`, `totalframes`, and `modelparams` match expectations. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
- For physics-accurate runs, print or log the key parameters from `FRAMEWORKCONFIG['paper2']`, `FRAMEWORKCONFIG['paper7']`, or `FRAMEWORKCONFIG['paper12']` and the topology/paths produced by the helpers. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/b763d538-0411-4ab5-b724-bf4750f65ea6/topology_generator.py)

### Q: Can I run this in a Jupyter notebook?

Yes; the clean testbed notebook is already set up to import the framework, reload modules, and run allocator and bandit experiments, and you can copy the same patterns into your own notebooks. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

### Q: What’s the expected output?

For each run, MultiRunEvaluator logs reward, efficiency, thresholds, and winners per scenario (stochastic and several adversarial types), and you can post-process these into markdown tables for cross-testbed comparisons. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)


***

## Getting Started Right Now

1. **Today (15–20 min):**  
   - Skim this MASTER_SUMMARY and SEAMLESS_INTEGRATION_SUMMARY to lock in the architecture.  
2. **Next (20–30 min):**  
   - Open `experiment_config.py` and `H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb` to see `PAPERCONFIGS` and FRAMEWORKCONFIG entries for papers 2, 7, 12. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
3. **Tomorrow 8:00–11:00:**  
   - Run Paper #2 and #7 quick tests and physics-accurate runs. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)
4. **Thursday morning:**  
   - Exercise Papers #5, #8, #12 and build at least one cross-testbed comparison table. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)

By following this plan, you will have a **reproducible, paper-grounded evaluation suite** for your quantum routing bandits by Thursday’s meeting.