#!/usr/bin/env python3
"""Copy and minimally adapt the pinned Paper8 allocator notebook for Q-04."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "notebooks" / "H-MABs_Eval-Testbed-Paper8-PaperRunConfig.ipynb"
OUTPUT = ROOT / "notebooks" / "H-MABs_Eval-MediumScale-Default-FullThreat.ipynb"
SOURCE_COMMIT = "96b327de7e3571ad3cbf05bbeee02cfb922ca2c3"
SOURCE_BLOB = "599bb49b58a41fc98ff7d6f10c4077c941507269"
SOURCE_SHA256 = "714eefbd1eafc3c66347fc6b0460e6aaf706ad25b1ea411bcc89ac317a4711c9"


def lines(text):
    return text.splitlines(keepends=True)


def replace_source(cell, text):
    cell["source"] = lines(text)
    if cell["cell_type"] == "code":
        cell["execution_count"] = None
        cell["outputs"] = []


def main():
    source_bytes = SOURCE.read_bytes()
    if sha256(source_bytes).hexdigest() != SOURCE_SHA256:
        raise SystemExit("Proven source notebook hash changed; refusing to generate")
    source = json.loads(source_bytes)

    # Preserve the proven notebook's actual setup/config/helper/Default-run flow.
    # Cells 10-15 are the unsupported Dynamic/Thompson/Random sections.
    cells = deepcopy(source["cells"][:10])
    for cell in cells:
        if cell["cell_type"] == "code":
            cell["execution_count"] = None
            cell["outputs"] = []

    replace_source(cells[0], """# Neural Bandit Algorithm Evaluation Framework

## F-08 Tier-1 Medium-Scale External Testbed — Default Allocator

This notebook is copied from the pinned proven Paper8 full-spectrum workflow. It preserves the environment setup, `ExperimentConfiguration`, helper, and real `daqr.evaluation.allocator_runner.AllocatorRunner` flow while changing only the frozen medium-scale configuration and external catalog adapter.
""")
    replace_source(cells[2], """# ============================================================
# Setup: Quantum MAB Framework (F-08 Tier-1 medium-scale anchor)
# ============================================================

# --- (Optional) Install Dependencies ---
# !pip install -q torch torchvision numpy matplotlib seaborn pandas tqdm scipy scikit-learn pmdarima networkx

# --- Core Imports ---
import os, sys, gc, warnings, importlib, subprocess
import itertools
import numpy as np
import matplotlib.pyplot as plt
import torch
import networkx as nx
from pathlib import Path

warnings.filterwarnings('ignore')

# --- Path Setup ---
print(f"Current working directory: {os.getcwd().split('/')[-1]}")
try:
    import google.colab
    from google.colab import drive
    drive.mount('/content/drive')
    project_dir = '/content/drive/MyDrive/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework'
    os.chdir(project_dir)
    print("Running in Google Colab")
except ImportError:
    print("Running locally (not in Colab)")

sys.path.append(os.path.join(os.getcwd(), 'src'))
sys.path.append(os.getcwd())

print("Framework dependencies installed successfully")
print(f"Python version: {sys.version.split()[0]}")
print(f"PyTorch version: {torch.__version__}")
print(f"NumPy version: {np.__version__}")
print(f"NetworkX version: {nx.__version__}")

import daqr
print('✓ daqr import OK')

from daqr.config.experiment_config import ExperimentConfiguration
from daqr.core.qubit_allocator import QubitAllocator
from daqr.campaigns.medium_process import run_process_isolated_campaign
from daqr.campaigns.medium_tier1 import (
    MODEL_ROSTER,
    PROFILE_POOL as MEDIUM_PROFILE_POOL,
    build_block_payload,
    catalog_configuration as medium_catalog_configuration,
    configure_external_persistence as configure_medium_persistence,
    framework_configuration,
)
from daqr.evaluation.allocator_runner import AllocatorRunner

print('✓ medium-scale catalog components and real AllocatorRunner loaded')
""")
    replace_source(cells[3], "## F-08 Tier-1 Run Configuration (Frozen Default Allocator)\n")
    replace_source(cells[4], """# --- Frozen F-08 Tier-1 medium-scale run configuration ---
SOURCE_NOTEBOOK_COMMIT = '96b327de7e3571ad3cbf05bbeee02cfb922ca2c3'
SOURCE_NOTEBOOK_BLOB = '599bb49b58a41fc98ff7d6f10c4077c941507269'
SOURCE_NOTEBOOK_SHA256 = '714eefbd1eafc3c66347fc6b0460e6aaf706ad25b1ea411bcc89ac317a4711c9'

models = list(MODEL_ROSTER)
BASE_FRAMES = 6000
FRAME_STEP = 0
RUNS = [3]
SCALES = [2]
ALLOCATORS = ['Default']
ATTACK_INTENSITY = 0.25
BASE_SEED = 12345
PHYSICS_MODELS = ['medium_tier1']
EXECUTION_KIND = 'scientific'

# Preserve the established full-spectrum notebook order.
test_scenarios = {
    'stochastic': 'Stochastic Random Failures',
    'markov': 'Markov Adversarial Attack',
    'adaptive': 'Adaptive Adversarial Attack',
    'onlineadaptive': 'Online Adaptive Attack',
    'none': 'Baseline (Optimal Conditions)',
}

PROFILE_POOL = list(MEDIUM_PROFILE_POOL)
FRAMEWORK_CONFIG = framework_configuration(BASE_FRAMES, EXECUTION_KIND)
MEDIUM_CONFIG = FRAMEWORK_CONFIG['medium_tier1']

assert list(test_scenarios) == ['stochastic', 'markov', 'adaptive', 'onlineadaptive', 'none']
assert len(models) * len(test_scenarios) * RUNS[0] == 75
assert BASE_FRAMES * SCALES[0] == 12000

print('BASE_FRAMES:', BASE_FRAMES)
print('FRAME_STEP:', FRAME_STEP)
print('RUNS:', RUNS)
print('SCALES:', SCALES)
print('ALLOCATORS:', ALLOCATORS)
print('MODELS:', models)
print('THREATS:', list(test_scenarios))
print('PHYSICS_MODELS:', PHYSICS_MODELS)
""")
    replace_source(cells[5], "## Medium-Scale Helper Functions (catalog, contexts, rewards, external evidence)\n")
    replace_source(cells[6], """# --- Frozen medium-scale external catalog + physics adapter ---
def _catalog_configuration(base_seed: int, qubit_cap):
    return medium_catalog_configuration(
        BASE_FRAMES,
        EXECUTION_KIND,
        base_seed,
        qubit_cap,
    )


def get_physics_params(
    physics_model: str,
    current_frames: int,
    base_seed: int,
    qubit_cap,
    block_id: int = 0,
):
    if int(current_frames) != BASE_FRAMES:
        raise ValueError(f'Frozen horizon is {BASE_FRAMES}, got {current_frames}')
    return build_block_payload(
        physics_model,
        current_frames,
        base_seed,
        qubit_cap,
        block_id=block_id,
        execution_kind=EXECUTION_KIND,
    )


def configure_external_persistence(custom_config, output_root):
    return configure_medium_persistence(custom_config, output_root)
""")
    replace_source(cells[7], """## Run (Real AllocatorRunner)

The Default allocator uses the same configured model roster, catalog, evaluator, runner, and evidence plug-ins as the pinned source notebook. Set `QUANTUM_MEDIUM_MAX_WORKERS` above one only for the qualified process-isolated scenario-group scheduler; shared-process thread execution is not used.
""")
    replace_source(cells[8], "### Allocator: Default / fixed\n")
    replace_source(cells[9], """allocator_type = 'Default'
ALLOCATORS = ['Default']

attack_intensity = FRAMEWORK_CONFIG['intensity']
current_frames = FRAMEWORK_CONFIG['base_frames']
frame_step = FRAMEWORK_CONFIG['frame_step']
current_experiments = FRAMEWORK_CONFIG['exp_num']
last_backup = False
base_cap = True
overwrite = False

OUTPUT_ROOT = Path(os.environ.get(
    'QUANTUM_MEDIUM_OUTPUT_ROOT',
    '/content/drive/MyDrive/GA-Work/quantum_experiment_evidence/medium-tier1/default-fixed-full-roster-v2',
)).expanduser().resolve()

print('' + '=' * 70, '🎯 F-08 TIER-1 DEFAULT ALLOCATOR EVALUATION', '=' * 70)
print('Physics Models:            ', PHYSICS_MODELS)
print('Allocators:                ', ALLOCATORS)
print('Scales:                    ', SCALES)
print('Runs/blocks:               ', RUNS)
print('Policies:                  ', models)
print('Threat order:              ', list(test_scenarios))
print('External evidence root:    ', OUTPUT_ROOT)
print('=' * 70)

MAX_WORKERS = int(os.environ.get('QUANTUM_MEDIUM_MAX_WORKERS', '1'))
if MAX_WORKERS > 1:
    receipt = run_process_isolated_campaign(
        OUTPUT_ROOT,
        base_frames=BASE_FRAMES,
        execution_kind=EXECUTION_KIND,
        max_workers=MAX_WORKERS,
    )
    print('Process-isolated campaign receipt:', receipt)
else:
    for allocator_type in ALLOCATORS:
        for scale in SCALES:
            for physics_model in PHYSICS_MODELS:
                initial_allocator = QubitAllocator(
                    total_qubits=90,
                    num_routes=10,
                    min_qubits_per_route=1,
                    baseline_allocation=(9,) * 10,
                )
                custom_config = ExperimentConfiguration(
                    env_type=FRAMEWORK_CONFIG['main_env'],
                    scenarios=test_scenarios,
                    use_last_backup=last_backup,
                    resume=False,
                    models=models,
                    attack_intensity=attack_intensity,
                    attack_rate=attack_intensity,
                    scale=scale,
                    base_capacity=base_cap,
                    overwrite=overwrite,
                    base_seed=BASE_SEED,
                    allocator=initial_allocator,
                    persistence=False,
                )
                configure_external_persistence(custom_config, OUTPUT_ROOT)

                alloc_runner = AllocatorRunner(
                    allocator_type=allocator_type,
                    physics_models=[physics_model],
                    framework_config=FRAMEWORK_CONFIG,
                    scales=[scale],
                    runs=RUNS,
                    models=models,
                    test_scenarios=test_scenarios,
                    config=custom_config,
                )
                alloc_runner.run(get_physics_params_func=get_physics_params)

print('DEFAULT ALLOCATOR FULL-SPECTRUM RUN COMPLETE!')
""")

    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": lines("""## Evidence Boundary

- This notebook covers the authorized Default/fixed allocator, the pinned five-model `NEURAL_MODELS` roster, and all five established threats.
- It writes a fresh campaign and does not reuse or pool any cell from the preserved 45-cell reduced diagnostic.
- Three equal 6,000-frame blocks are represented by `RUNS=[3]`, `BASE_FRAMES=6000`, and `FRAME_STEP=0` in the proven runner.
- Raw state/evidence must remain under the configured external output root.
- Random is under separate native-semantics reassessment; DynamicUCB and ThompsonSampling remain on hold.
- Process acceleration is optional and may be used only after serial/process equivalence passes for this exact notebook/configuration.
"""),
    })

    notebook = deepcopy(source)
    notebook["cells"] = cells
    notebook["metadata"]["quantum_medium_provenance"] = {
        "source_path": str(SOURCE.relative_to(ROOT)),
        "source_commit": SOURCE_COMMIT,
        "source_blob": SOURCE_BLOB,
        "source_sha256": SOURCE_SHA256,
        "copied_source_cells": list(range(10)),
        "allocator": "Default",
        "runner_module": "daqr.evaluation.allocator_runner",
        "required_models": [
            "Oracle",
            "GNeuralUCB",
            "EXPNeuralUCB",
            "CPursuitNeuralUCB",
            "iCPursuitNeuralUCB",
        ],
        "required_threats": ["stochastic", "markov", "adaptive", "onlineadaptive", "none"],
        "required_cells": 75,
        "execution_mode": "serial-or-qualified-process-isolated",
    }
    OUTPUT.write_text(json.dumps(notebook, indent=1) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
