# Anonymous Quantum Entanglement Routing Artifact

This repository contains an anonymized source artifact for threat-aware quantum entanglement routing evaluation. The code supports experiments that combine path selection, qubit allocation, replay-capacity settings, and stochastic/adversarial threat regimes.

The artifact includes source code, selected technical documentation, and sanitized notebooks. The main validation notebook preserves sanitized outputs so readers can inspect the validation evidence without rerunning every experiment. Private workspace files, raw logs, local registries, duplicate/dev notebooks, issue-tracking notes, and personal paths are intentionally excluded.

## Contents

```text
Dynamic_Routing_Eval_Framework/
├── daqr/                  # Core package
├── experiments/           # Example experiment entry point
├── notebooks/             # Sanitized validation and run notebooks
├── run_paper7_sanity_tests.py
├── run_paper12_sanity_tests.py
└── run_tests.sh
docs/                      # Public technical documentation
scripts/                   # Optional local or VM runners
requirements.txt
state_analysis.py
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Quick Checks

```bash
python Dynamic_Routing_Eval_Framework/run_paper7_sanity_tests.py
python Dynamic_Routing_Eval_Framework/run_paper12_sanity_tests.py
```

## Validation

The primary validation notebook is:

```text
Dynamic_Routing_Eval_Framework/notebooks/H-MABs_MasterDataset_VerificationHub.ipynb
```

It is sanitized and keeps output cells so readers can inspect the validation workflow and evidence directly.

## Optional Remote State

Remote state synchronization is opt-in. No bucket IDs, Drive folder IDs, credentials, tokens, or personal paths are included in this artifact.

Set these variables only if you want to use your own infrastructure:

```bash
export DAQR_GCS_BUCKET="<your-gcs-bucket>"
export DAQR_DRIVE_FOLDER_ID="<your-drive-folder-id>"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

Without these variables, the framework uses local state and skips remote uploads/downloads.
