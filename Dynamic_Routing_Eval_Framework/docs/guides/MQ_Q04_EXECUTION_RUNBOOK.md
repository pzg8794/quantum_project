# M-Q Q-04 — Default Allocator Notebook Runbook

## Frozen inputs

- Scientific contract: `MQ_Q03_TIER1_SCIENTIFIC_CONTRACT.md` at manager commit `7036f0d0044bac576c61093c6361fb6739dfc292`.
- Copied workflow source: `H-MABs_Eval-Testbed-Paper8-PaperRunConfig.ipynb` at commit `96b327de7e3571ad3cbf05bbeee02cfb922ca2c3`, blob `599bb49b58a41fc98ff7d6f10c4077c941507269`, SHA-256 `714eefbd1eafc3c66347fc6b0460e6aaf706ad25b1ea411bcc89ac317a4711c9`.
- Execution notebook: `notebooks/H-MABs_Eval-MediumScale-Default-FullThreat.ipynb`.
- Allocator: Default/fixed only.
- Matrix: 3 policies × 5 threats × 3 blocks = 45 cells, 6,000 frames each.

## Before execution

1. Checkout the pushed Q-04 execution commit; never run from an uncommitted source tree.
2. Set `QUANTUM_MEDIUM_OUTPUT_ROOT` to a durable directory outside this source repository.
3. Set `QUANTUM_MEDIUM_MAX_WORKERS=1` for the conservative serial path. Increase only after the bounded serial/process equivalence test passes on the exact execution commit.
4. Execute the notebook from top to bottom. Do not delete, retry, or replace valid poor/zero bundles.

## Acceptance

- The notebook must report `45 / 45` completed cells.
- Every bundle must pass `validate_completion` and the set must pass `validate_scale_completion`.
- `default-fixed-notebook-receipt.json` must reference all 45 run IDs and bundle directories.
- The executed notebook, receipt, source commit, test receipt, and output-root location form the handoff package.

## Receipt template

```text
Execution commit:
Notebook SHA-256 before execution:
Notebook SHA-256 after execution:
External output root:
Start/end time:
Worker count:
Completed cells: 45/45
Notebook receipt path:
Targeted test result:
PR #2 regression result:
BLOCKER:
DEBT:
OPTIONAL:
Independent reviewer:
Independent review decision:
```

## Holds

- Random remains conditional on a separately proven deterministic one-time catalog contract.
- DynamicUCB and ThompsonSampling remain held; do not label initialization-only allocation as adaptive execution.
- No manuscript, historical corpus, Tier-2, or F-10 change is authorized by this runbook.
