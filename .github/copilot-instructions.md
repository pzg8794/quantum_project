# AI Coding Agent Instructions for Quantum MAB Research Framework

## Project Overview
This is a research framework for evaluating neural multi-armed bandit algorithms in adversarial quantum entanglement routing scenarios. The framework supports multiple testbeds (Paper2, Paper12, Paper5, Paper7) and runs across Colab, local machines, and GCP VMs, with results unified in a shared Google Drive data lake.

## Architecture & Key Components

### Core Package Structure (`daqr/`)
- **`algorithms/`**: Bandit algorithm implementations (neural UCB, EXP3, Thompson sampling variants)
- **`core/`**: Quantum physics simulation, network environments, attack strategies, qubit allocation
- **`config/`**: Testbed-specific configurations and experiment setup
- **`evaluation/`**: Experiment runners, multi-run evaluators, visualization tools

### Data Flow
- Experiments write results to `quantum_data_lake/` on shared Google Drive
- Models saved in `model_state/`, metadata in `framework_state/`, plots in `visualizations/`
- Cross-testbed analysis in `cross_testbed/` subdirectory

## Critical Developer Workflows

### Running Experiments
```bash
# Basic test run
bash scripts/run_exp_test.sh

# Custom experiment with parameters
bash scripts/dynamic_exp_runner.sh 1000 3 100 12345 "paper2" 0.25 "DynamicAllocator"

# From Python
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator

config = ExperimentConfiguration()
config.load_testbed_config('PAPER2')
evaluator = MultiRunEvaluator(config=config, runs=3)
results = evaluator.test_stochastic_environment(
    models=['CPursuit', 'EXPNeuralUCB'],
    scenarios=['stochastic']
)
```

### Configuration Pattern
```python
# Always start with config
from daqr.config.experiment_config import ExperimentConfiguration

config = ExperimentConfiguration()
config.load_testbed_config('PAPER2')  # or 'PAPER12'
config.setenvironment(framesno=6000, attack_type='stochastic')
```

### Isolated Allocator Execution
```python
# Use AllocatorRunner for clean state management
from notebooks.run_allocator import AllocatorRunner

runner = AllocatorRunner(allocator_type, physics_models, framework_config,
                        scales, runs, models, test_scenarios)
results = runner.run_allocator(physics_model)
```

## Project-Specific Conventions

### Import Patterns
```python
# Core imports
from daqr.core.quantum_physics import DefaultNoiseModel, DefaultFidelityCalculator
from daqr.core.network_environment import AdversarialQuantumEnvironment
from daqr.algorithms.predictive_bandits import CPursuitNeuralUCB, EXPNeuralUCB

# Config first, then evaluation
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator
```

### PyTorch Usage
- Device: `device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')`
- Reproducibility: Set seeds for `torch`, `numpy`, `random` at script start
- Neural networks in bandit algorithms use standard PyTorch patterns

### Testbed-Specific Logic
- **Paper2**: 4-node stochastic network, validated production testbed
- **Paper12**: Event-driven network (in development)
- Each testbed has dedicated config constants (e.g., `PAPER2_CONFIG`)

### Error Handling
- Use `warnings.filterwarnings('ignore')` for clean output
- Wrap experiments in try/except with `traceback.print_exc()`
- Log to files in `quantum_logs/` directory

## Integration Points

### Google Drive Sync
- Results automatically saved to shared drive via backup managers
- `gcp_backup_manager.py`, `gd_backup_manager.py`, `local_backup_manager.py`
- No manual file copying - framework handles unified storage

### Cloud Infrastructure
- GCP VMs for batch runs with metadata tracking
- Google Cloud Storage for model artifacts
- Wandb integration for experiment tracking

### External Dependencies
- PyTorch ecosystem (torch, torchaudio, torchvision)
- Scientific computing (numpy, pandas, scikit-learn, networkx)
- Visualization (matplotlib, plotly, seaborn)
- Google APIs (google-cloud-storage, google-api-python-client)

## Key Files & Examples

### Configuration Examples
- `daqr/config/experiment_config.py`: Testbed configs, model collections
- `setup_files/SETUP_LOCAL.md`: Environment setup patterns

### Algorithm Patterns
- `daqr/algorithms/base_bandit.py`: Neural network bandit base class
- `daqr/algorithms/predictive_bandits.py`: Specific algorithm implementations

### Execution Patterns
- `scripts/dynamic_exp_runner.sh`: Parameterized experiment runner
- `Dynamic_Routing_Eval_Framework/notebooks/run_allocator.py`: Isolated execution wrapper

### Physics Simulation
- `daqr/core/quantum_physics.py`: Noise models, fidelity calculations
- `daqr/core/network_environment.py`: Topology and attack simulation

## Common Patterns to Follow

1. **Always use ExperimentConfiguration** as the starting point for any experiment
2. **Load testbed config** before setting environment parameters
3. **Use MultiRunEvaluator** for batched experiments with proper cleanup
4. **Save to shared drive** - framework handles the rest
5. **Isolate allocators** using AllocatorRunner to prevent state contamination
6. **Set random seeds** at the beginning of any script for reproducibility
7. **Handle PyTorch devices** appropriately (GPU if available)

## Debugging Tips

- Check `quantum_logs/` for detailed execution logs
- Use `verbose=True` in config for additional output
- Run single experiments first before batch runs
- Validate with `bash scripts/run_exp_test.sh` before custom experiments</content>
<parameter name="filePath">/workspaces/quantum_project/.github/copilot-instructions.md