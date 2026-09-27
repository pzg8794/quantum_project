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
3. Execute the notebook from top to bottom through the real `daqr.evaluation.allocator_runner.AllocatorRunner` path.
4. Keep the Default run serial. Process acceleration is optional and deferred because no acceleration layer has yet demonstrated identity with the proven notebook workflow.
5. Do not delete, retry, or replace valid poor/zero state solely because of performance.

## Acceptance

- The executed notebook must cover all three policies under all five configured threats for three equal 6,000-frame runs (45 policy × threat × block cells in the scientific matrix).
- `BASE_FRAMES=6000`, `FRAME_STEP=0`, `RUNS=[3]`, `SCALES=[2]`, `base_capacity=True`, and seed 12345 must remain unchanged.
- The external catalog must report 15 nodes, 10 routes, and 550 route-action pairs with a fixed 90-qubit budget.
- State, logs, and outputs must remain under `QUANTUM_MEDIUM_OUTPUT_ROOT`, outside the source repository.
- The executed notebook, output-root inventory, source commit, and test receipt form the handoff package.

## Receipt template

```text
Execution commit:
Notebook SHA-256 before execution:
Notebook SHA-256 after execution:
External output root:
Start/end time:
Execution mode: serial proven AllocatorRunner
Policies/threats/blocks: 3/5/3
External catalog: 15 nodes / 10 routes / 550 actions
External state/log inventory:
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
- Process acceleration is OPTIONAL and remains deferred; it must not replace or shadow the proven runner.
- No manuscript, historical corpus, Tier-2, or F-10 change is authorized by this runbook.
