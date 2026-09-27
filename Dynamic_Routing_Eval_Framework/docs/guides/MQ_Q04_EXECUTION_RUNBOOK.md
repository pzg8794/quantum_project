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
6. Outcome/performance-triggered reruns are disabled for this campaign. The existing
   bounded technical-exception retry remains available, and a terminal failure is
   recorded rather than replaced by a favorable rerun.

## Acceptance

- The executed notebook must cover all three policies under all five configured threats for three equal 6,000-frame runs (45 policy × threat × block cells in the scientific matrix).
- `BASE_FRAMES=6000`, `FRAME_STEP=0`, `RUNS=[3]`, `SCALES=[2]`, `base_capacity=True`, and seed 12345 must remain unchanged.
- The external catalog must report 15 nodes, 10 routes, and 550 route-action pairs with a fixed 90-qubit budget.
- State, logs, and outputs must remain under `QUANTUM_MEDIUM_OUTPUT_ROOT`, outside the source repository.
- Each of the 45 cells must have an immutable bundle under
  `q04-evidence/cells/<result_identity>/` containing:
  - `manifest.json` with block, threat, policy, actual seed, config identity, catalog identity, and trajectory identity;
  - `availability.json` with the full route-availability trajectory;
  - `events.jsonl` with joinable route/action `DECISION` and selected-payoff `OUTCOME` events;
  - `result.json` with the bounded outcome summary;
  - `completion.json` with status, event counts, and file hashes.
- `q04-evidence/campaign-receipt.json` must account for exactly 45 unique
  block/threat/policy cells. A cell or campaign with recorded failures is not
  scientific completion.
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
Campaign receipt SHA-256:
Completed/failed cells:
Availability frame count per cell:
Decision/outcome event count per cell:
Catalog identities for blocks 0/1/2:
Stable environment/policy seed identities:
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

## Current technical blocker

The real `AllocatorRunner` path completes the bounded Stochastic and Markov
cells and can write their availability/event/completion bundles. It does not yet
complete the full five-threat preflight: `AdaptiveAttack` and
`OnlineAdaptiveAttack` now require causal selection history, while the legacy
environment construction still attempts to generate their full availability
matrices before policy execution. The failure occurs before a valid environment
is available (`Adaptive strategy requires selection history; no random fallback`).

Resolving this requires threading the already-frozen PR #2 `ScenarioSession`
lifecycle through the existing `AllocatorRunner` evaluator path. No substitute
runner, fabricated static adaptive mask, or 6,000-frame scientific run is
authorized while this blocker remains.
