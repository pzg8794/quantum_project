#!/usr/bin/env python3
"""Build the frozen Default-allocator notebook from the proven Paper8 notebook."""
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


def markdown(text):
    return {"cell_type": "markdown", "metadata": {}, "source": lines(text)}


def code(text):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": lines(text),
    }


def main():
    source_bytes = SOURCE.read_bytes()
    if sha256(source_bytes).hexdigest() != SOURCE_SHA256:
        raise SystemExit("Proven source notebook hash changed; refusing to generate")
    source = json.loads(source_bytes)
    notebook = {
        "cells": [
            markdown("""# F-08 Tier-1 Medium-Scale Full-Threat Run — Default Allocator

This notebook is the copied/adapted successor to the proven Paper8 allocator notebook. It retains the one-allocator `ExperimentConfiguration` + `AllocatorRunner` workflow and executes the complete five-threat spectrum. Each completed notebook references 45 immutable scientific bundles written outside the source repository.
"""),
            markdown("## Environment Setup & Library Installation\n"),
            code("""import os
import sys
from pathlib import Path

try:
    import google.colab
    from google.colab import drive
    drive.mount('/content/drive')
    project_dir = Path('/content/drive/MyDrive/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework')
    os.chdir(project_dir)
except ImportError:
    project_dir = Path.cwd()

sys.path.insert(0, str(Path.cwd()))

from daqr.config.experiment_config import ExperimentConfiguration
from daqr.campaigns.medium_scientific import (
    AllocatorRunner,
    TIER1_MODELS,
    TIER1_SCENARIOS,
    build_tier1_default_config,
)

print(f'Framework root: {Path.cwd()}')
"""),
            markdown("## Frozen Tier-1 Run Configuration\n"),
            code("""SOURCE_NOTEBOOK_COMMIT = '96b327de7e3571ad3cbf05bbeee02cfb922ca2c3'
SOURCE_NOTEBOOK_BLOB = '599bb49b58a41fc98ff7d6f10c4077c941507269'
SOURCE_NOTEBOOK_SHA256 = '714eefbd1eafc3c66347fc6b0460e6aaf706ad25b1ea411bcc89ac317a4711c9'

allocator_type = 'Default'
models = list(TIER1_MODELS)
test_scenarios = dict(TIER1_SCENARIOS)
config = build_tier1_default_config()
assert isinstance(config, ExperimentConfiguration)
assert list(test_scenarios) == ['stochastic', 'markov', 'adaptive', 'onlineadaptive', 'none']
assert config.runs * len(models) * len(test_scenarios) == 45

OUTPUT_ROOT = Path(os.environ.get(
    'QUANTUM_MEDIUM_OUTPUT_ROOT',
    '/content/drive/MyDrive/GA-Work/quantum_experiment_evidence/medium-tier1/default-fixed',
)).expanduser().resolve()
MAX_WORKERS = int(os.environ.get('QUANTUM_MEDIUM_MAX_WORKERS', '1'))

print('Allocator:', allocator_type)
print('Policies:', models)
print('Threat order:', list(test_scenarios))
print('Blocks:', config.runs)
print('Frames per cell:', config.execution.horizon)
print('Required cells:', config.runs * len(models) * len(test_scenarios))
print('External evidence root:', OUTPUT_ROOT)
print('Process workers:', MAX_WORKERS)
"""),
            markdown("## Run One Allocator Across the Complete Threat Spectrum\n"),
            code("""alloc_runner = AllocatorRunner(
    allocator_type=allocator_type,
    output_root=OUTPUT_ROOT,
    max_workers=MAX_WORKERS,
    config=config,
)
receipt = alloc_runner.run()

assert receipt['required_cells'] == 45
assert receipt['completed_cells'] == 45
assert receipt['scenario_order'] == ['stochastic', 'markov', 'adaptive', 'onlineadaptive', 'none']

print('COMPLETE:', receipt['completed_cells'], '/', receipt['required_cells'])
print('Notebook receipt:', receipt['receipt_path'])
"""),
            markdown("""## Evidence Boundary

- The notebook is complete evidence only when all 45 immutable bundles validate.
- Valid poor or zero results are retained; no performance-triggered reruns are permitted.
- The fixed-allocator notebook alone does not establish allocator sensitivity.
- DynamicUCB and ThompsonSampling remain on hold; Random remains conditional.
"""),
        ],
        "metadata": deepcopy(source.get("metadata", {})),
        "nbformat": source["nbformat"],
        "nbformat_minor": source["nbformat_minor"],
    }
    notebook["metadata"]["quantum_medium_provenance"] = {
        "source_path": str(SOURCE.relative_to(ROOT)),
        "source_commit": SOURCE_COMMIT,
        "source_blob": SOURCE_BLOB,
        "source_sha256": SOURCE_SHA256,
        "allocator": "Default",
        "required_threats": list(("stochastic", "markov", "adaptive", "onlineadaptive", "none")),
        "required_cells": 45,
    }
    OUTPUT.write_text(json.dumps(notebook, indent=1) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
