# Repository Structure

This anonymized branch is rebuilt from the current `gcp-main` source branch and reduced to source code plus public technical support material.

```text
Dynamic_Routing_Eval_Framework/
├── daqr/                  # Core package: algorithms, config, network model, evaluators
├── experiments/           # Example experiment entry point
├── notebooks/             # Sanitized validation/run notebooks
├── run_paper7_sanity_tests.py
├── run_paper12_sanity_tests.py
└── run_tests.sh
docs/                      # Anonymized technical documentation
scripts/                   # Optional local/VM runners
requirements.txt
state_analysis.py
```

Excluded material includes raw logs, local registries, issue-tracking/status documents, duplicate/dev notebooks, and private workspace references.
