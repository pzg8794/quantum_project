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

from daqr.config.execution_contract import ExecutionSettings
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.config.local_backup_manager import LocalBackupManager
from daqr.core.catalog_components import LayeredPrimaryCatalog, PrimaryPayoff
from daqr.core.qubit_allocator import QubitAllocator
from daqr.campaigns.medium_spec import build_catalog
from daqr.evaluation.allocator_runner import AllocatorRunner

print('✓ medium-scale catalog components and real AllocatorRunner loaded')
""")
    replace_source(cells[3], "## F-08 Tier-1 Run Configuration (Frozen Default Allocator)\n")
    replace_source(cells[4], """# --- Frozen F-08 Tier-1 medium-scale run configuration ---
SOURCE_NOTEBOOK_COMMIT = '96b327de7e3571ad3cbf05bbeee02cfb922ca2c3'
SOURCE_NOTEBOOK_BLOB = '599bb49b58a41fc98ff7d6f10c4077c941507269'
SOURCE_NOTEBOOK_SHA256 = '714eefbd1eafc3c66347fc6b0460e6aaf706ad25b1ea411bcc89ac317a4711c9'

models = ['Oracle', 'CEpsilonGreedy', 'EXPNeuralUCB']
BASE_FRAMES = 6000
FRAME_STEP = 0
RUNS = [3]
SCALES = [2]
ALLOCATORS = ['Default']
ATTACK_INTENSITY = 0.25
BASE_SEED = 12345
PHYSICS_MODELS = ['medium_tier1']

# Preserve the established full-spectrum notebook order.
test_scenarios = {
    'stochastic': 'Stochastic Random Failures',
    'markov': 'Markov Adversarial Attack',
    'adaptive': 'Adaptive Adversarial Attack',
    'onlineadaptive': 'Online Adaptive Attack',
    'none': 'Baseline (Optimal Conditions)',
}

PROFILE_POOL = list(itertools.combinations_with_replacement((1e-4, 1.5e-4, 2e-4), 3))
MEDIUM_CONFIG = {
    'testbed': 'medium_tier1',
    'topology_family': 'layered-primary-form-v1',
    'profile_pool': PROFILE_POOL,
    'num_paths': 10,
    'total_qubits': 90,
    'min_qubits_per_route': 1,
    'baseline_allocation': (9,) * 10,
    'entanglement_success_factor': 100,
    'physics_model_name': 'medium_tier1',
    'state_suffix': 'medium_tier1_default',
}

FRAMEWORK_CONFIG = {
    'exp_num': 3,
    'test_mode': False,
    'base_frames': BASE_FRAMES,
    'frame_step': FRAME_STEP,
    'models': models,
    'intensity': ATTACK_INTENSITY,
    'routing_strategy': 'fixed',
    'capacity': 12000,
    'main_env': 'stochastic',
    'aggregate_state': False,
    'enable_plots': False,
    'env_attrs': {
        'intensity': ATTACK_INTENSITY,
        'base_seed': BASE_SEED,
        'reproducible': True,
    },
    'medium_tier1': MEDIUM_CONFIG,
}

assert list(test_scenarios) == ['stochastic', 'markov', 'adaptive', 'onlineadaptive', 'none']
assert len(models) * len(test_scenarios) * RUNS[0] == 45
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
    allocation = tuple(int(value) for value in qubit_cap)
    if allocation != (9,) * 10:
        raise ValueError(f'F-08 fixed allocator must supply ten nine-qubit budgets, got {allocation}')
    config = ExperimentConfiguration(
        models=models,
        scenarios=test_scenarios,
        runs=3,
        scale=2,
        base_capacity=True,
        base_seed=int(base_seed),
        attack_intensity=ATTACK_INTENSITY,
        attack_rate=ATTACK_INTENSITY,
        physics_params={'entanglement_success_factor': 100},
        testbed_config={
            'topology_family': 'layered-primary-form-v1',
            'profile_pool': PROFILE_POOL,
        },
        allocator=QubitAllocator(
            total_qubits=90,
            num_routes=10,
            min_qubits_per_route=1,
            baseline_allocation=allocation,
        ),
        persistence=False,
        resume=False,
        use_last_backup=False,
        overwrite=False,
        catalog_component=LayeredPrimaryCatalog(),
        reward_component=PrimaryPayoff(),
    )
    config.execution = ExecutionSettings(
        protocol_namespace='f08-tier1-default-fixed-v1',
        horizon=BASE_FRAMES,
        base_horizon=BASE_FRAMES,
        scale_points=(3,),
        execution_kind='scientific',
    )
    return config


def get_physics_params(physics_model: str, current_frames: int, base_seed: int, qubit_cap):
    if physics_model != 'medium_tier1':
        raise ValueError(f'Unsupported medium physics model: {physics_model}')
    if int(current_frames) != BASE_FRAMES:
        raise ValueError(f'Frozen horizon is {BASE_FRAMES}, got {current_frames}')

    catalog = build_catalog(_catalog_configuration(base_seed, qubit_cap), block=0, scale_m=3)
    graph = nx.Graph()
    graph.add_nodes_from(catalog['topology']['nodes'])
    graph.add_edges_from(catalog['topology']['edges'])
    contexts = [np.asarray(route['actions'], dtype=int) for route in catalog['observations']['routes']]
    rewards = [np.asarray(values, dtype=float) for values in catalog['physics']['base_expected_payoffs']]

    assert graph.number_of_nodes() == 15
    assert len(contexts) == len(rewards) == 10
    assert sum(len(actions) for actions in contexts) == 550

    print(f'📊 Medium topology: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges')
    print(f'📊 Medium routes/actions: {len(contexts)} routes, {sum(len(x) for x in contexts)} actions')

    return {
        'noise_model': None,
        'fidelity_calculator': None,
        'external_topology': graph,
        'external_contexts': contexts,
        'external_rewards': rewards,
    }


def configure_external_persistence(custom_config, output_root):
    root = Path(output_root).expanduser().resolve()
    source_root = Path.cwd().resolve()
    if root == source_root or root.is_relative_to(source_root):
        raise ValueError('QUANTUM_MEDIUM_OUTPUT_ROOT must be outside the source repository')
    root.mkdir(parents=True, exist_ok=True)
    custom_config.dir = root
    custom_config.persistence = True
    custom_config.backup_mgr = LocalBackupManager(
        date_str=custom_config.day_str,
        config_dir=root,
        verbose=False,
    )
    custom_config.backup_mgr.in_share_drive = False
    custom_config.backup_mgr.mode = 'local'
    return custom_config
""")
    replace_source(cells[7], """## Run (Real AllocatorRunner)

The Default allocator runs serially through the same `ExperimentConfiguration` + `daqr.evaluation.allocator_runner.AllocatorRunner` workflow as the pinned source notebook. Process acceleration is intentionally deferred rather than changing workflow identity.
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
    '/content/drive/MyDrive/GA-Work/quantum_experiment_evidence/medium-tier1/default-fixed',
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

- This notebook covers only the authorized Default/fixed allocator and all five established threats.
- Three equal 6,000-frame blocks are represented by `RUNS=[3]`, `BASE_FRAMES=6000`, and `FRAME_STEP=0` in the proven runner.
- Raw state/evidence must remain under the configured external output root.
- Random is under separate native-semantics reassessment; DynamicUCB and ThompsonSampling remain on hold.
- Process acceleration is optional and is not introduced here because preserving the proven runner workflow is the critical path.
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
        "required_threats": ["stochastic", "markov", "adaptive", "onlineadaptive", "none"],
        "required_cells": 45,
        "execution_mode": "serial-proven-runner",
    }
    OUTPUT.write_text(json.dumps(notebook, indent=1) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
