# M-Q Q-04 — Default Allocator Notebook Runbook

## Frozen inputs

- Scientific contract: corrected `MQ_Q03_TIER1_SCIENTIFIC_CONTRACT.md` at manager commit `7be586af`.
- Copied workflow source: `H-MABs_Eval-Testbed-Paper8-PaperRunConfig.ipynb` at commit `96b327de7e3571ad3cbf05bbeee02cfb922ca2c3`, blob `599bb49b58a41fc98ff7d6f10c4077c941507269`, SHA-256 `714eefbd1eafc3c66347fc6b0460e6aaf706ad25b1ea411bcc89ac317a4711c9`.
- Execution notebook: `notebooks/H-MABs_Eval-MediumScale-Default-FullThreat.ipynb`.
- Allocator: Default/fixed only.
- Matrix: 5 policies × 5 threats × 3 blocks = 75 cells, 6,000 frames each.
- Campaign isolation: fresh namespace/output root; no cell from the preserved 45-cell reduced diagnostic is reused or pooled.

## Before execution

1. Checkout the pushed Q-04 execution commit; never run from an uncommitted source tree.
2. Set `QUANTUM_MEDIUM_OUTPUT_ROOT` to a durable directory outside this source repository.
3. Execute the notebook from top to bottom. `QUANTUM_MEDIUM_MAX_WORKERS=1` retains the direct serial `daqr.evaluation.allocator_runner.AllocatorRunner` path; a value greater than one uses the qualified process-isolated outer scheduler while retaining `MultiRunEvaluator -> QuantumExperimentRunner` inside every worker.
4. Parallel execution is limited to independent scenario-group processes. Each process reconstructs configuration from primitive inputs, uses a unique state/log root, evaluates the complete five-model roster and all three blocks, and writes immutable attempt bundles to the shared evidence root. Do not use the existing thread executors for this campaign.
5. Do not delete, retry, or replace valid poor/zero state solely because of performance.
6. Outcome/performance-triggered reruns are disabled for this campaign. The existing
   bounded technical-exception retry remains available, and a terminal failure is
   recorded rather than replaced by a favorable rerun.

## Acceptance

- The executed notebook must cover the complete pinned five-model roster under all five configured threats for three equal 6,000-frame runs (75 policy × threat × block cells in the scientific matrix).
- `BASE_FRAMES=6000`, `FRAME_STEP=0`, `RUNS=[3]`, `SCALES=[2]`, `base_capacity=True`, and seed 12345 must remain unchanged.
- The external catalog must report 15 nodes, 10 routes, and 550 route-action pairs with a fixed 90-qubit budget.
- State, logs, and outputs must remain under `QUANTUM_MEDIUM_OUTPUT_ROOT`, outside the source repository.
- Each of the 75 cells must have an immutable PR2 `AttemptBundle` under
  `q04-evidence/<run_id>/attempt-<n>/` containing:
  - `manifest.json` with block, threat, policy, actual seed, config identity, catalog identity, and trajectory identity;
  - `availability.json` with the full route-availability trajectory;
  - `events.jsonl` with ordered, joinable `PRESELECTION`, `DECISION`, `OUTCOME`, and `UPDATE` events for every frame;
  - `result.json` with the bounded outcome summary;
  - `completion.json` with status, four-phase event counts, and hashes covering every artifact, including `result.json`.
- `q04-evidence/campaign-receipt.json` must account for exactly 75 unique
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
Execution mode: serial proven AllocatorRunner / qualified process-isolated scenario groups
Configured process workers:
Policies/threats/blocks: 5/5/3
External catalog: 15 nodes / 10 routes / 550 actions
External state/log inventory:
Campaign receipt SHA-256:
Completed/failed cells:
Availability frame count per cell:
Decision/outcome event count per cell:
Catalog identities for blocks 0/1/2:
Exact PR2 threat/policy seed identities:
Targeted test result:
PR #2 regression result:
BLOCKER:
DEBT:
OPTIONAL:
Independent reviewer:
Independent review decision:
```

## Holds

- Random remains on separate native-stochastic provenance qualification; changing allocations are expected, but every result must bind the allocation/catalog/environment that generated it.
- DynamicUCB and ThompsonSampling remain held; do not label initialization-only allocation as adaptive execution.
- Process acceleration is OPTIONAL. It may be used only through the qualified scenario-group process scheduler; the direct serial path remains the reference and fallback.
- No manuscript, historical corpus, Tier-2, or F-10 change is authorized by this runbook.

## Causal availability boundary

The real `AllocatorRunner` path reuses the frozen PR #2 `ScenarioSession`
lifecycle for Adaptive and OnlineAdaptive. Each policy receives a fresh session
with the same block, threat configuration, and threat seed. Its route-selection
history then causally determines its realized availability trajectory.

Consequently, Stochastic, Markov, and Baseline preserve a shared static
trajectory across policies within each block/threat pairing, while Adaptive and
OnlineAdaptive trajectories are policy-conditioned by definition. The evidence
manifest records this boundary; it does not force equal adaptive masks or
fabricate a static approximation.

## Q-04 process-isolated acceleration qualification — 2026-09-27

- Parallelism is outside the scientific treatment: the five threat groups may run
  in separate OS processes, but each worker executes the complete pinned roster
  (`Oracle`, `GNeuralUCB`, `EXPNeuralUCB`, `CPursuitNeuralUCB`, and
  `iCPursuitNeuralUCB`) and all three blocks through the existing evaluator and
  experiment runner.
- Workers receive only primitive job specifications and reconstruct their own
  configuration, allocator, model objects, scenario components, RNG state, and
  backup manager. Live evaluator/model/plugin objects are never shared or
  pickled across workers.
- Each worker has a unique `process-state/<scenario>` scratch root. Immutable
  attempt bundles share the campaign evidence root because their run IDs and
  exclusive-create paths are disjoint. Only the parent process validates the
  complete 75-cell matrix and writes `campaign-receipt.json`.
- `spawn` process creation and one scenario task per child prevent inherited
  process-global RNG/model state. No thread-based model execution is used.
- Exact tiny-horizon serial/process equivalence passed: one fresh 75-cell serial
  campaign and one fresh 75-cell process campaign had identical run-ID sets and
  byte-identical manifests, attempts, catalogs, availability trajectories,
  event streams, and results. Completion records were identical after removing
  the non-scientific wall-clock field (`1 passed in 306.40s`).
- This qualification changes scheduling only. It does not pool or reuse any cell
  from the superseded 45-cell diagnostic, change the five-model cohort, or alter
  topology, threat, allocator, horizon, replay, seed, reward, update, metric, or
  evidence semantics.

## Q-04 full-roster TEST checkpoint — 2026-09-27

- Required medium/primary regression: `134 passed in 171.33s`.
- Complete scientific-notebook qualification, including a fresh real serial
  75-cell matrix and fresh exact serial/process equivalence: `9 passed in
  470.62s`.
- The first expanded regression exposed a test-fixture leak because the shared
  five-model list was passed by reference and an extensibility test appended its
  injected policy. The fixture now passes a defensive list copy.
- The same regression exposed an obsolete negative fixture that treated
  `EXPNeuralUCB` mode `neural` as invalid even though corrected full-roster trace
  support legitimately uses the inherited neural mode for `GNeuralUCB`. The
  fail-closed test now uses the genuinely unsupported value `invalid-mode`.
- These two corrections affect technical tests only. They do not change runtime
  model, threat, allocator, seed, reward, update, evidence, or campaign behavior.
- `git diff --check` and Python compilation of the changed campaign modules pass.
- Scientific 6,000-frame execution remains unstarted pending independent final
  Q-04 review.

## Q-04 bounded validation receipt — 2026-09-27

- DEV commit: `477f6eb4`.
- Real tiny-horizon matrix: 45/45 block--threat--policy cells completed through
  the existing `AllocatorRunner` path with availability, joined decision/outcome
  events, completion records, and hashes (`7 passed in 111.03s`).
- Required PR #2 regression: `72 passed in 52.34s`.
- Scientific 6,000-frame execution: not launched.
- Scope: execution-layer causal-session integration only; no substitute runner,
  threat/model semantics, allocator architecture, or manuscript change.

## Q-04 plugin-dispatch corrective checkpoint — 2026-09-27

- DEV commit: `c6833b9c`.
- Focused capability/session and valid-zero regressions: `5 passed in 7.74s`.
- Real notebook-helper and tiny 45-cell matrix path: `7 passed in 44.32s`.
- Current expanded PR #2 regression command, which includes the historical
  72-test gate: `121 passed in 101.95s`.
- The runner contains no campaign import or Adaptive/OnlineAdaptive name dispatch.
  A typed `ScenarioExecutionComponent` injects the configured strategy and frozen
  seed, while the environment delegates causal lifecycle creation to
  `AttackStrategy.open_session`.
- Static strategies retain precomputed masks. Causal strategies expose no
  fabricated environment mask; each policy obtains a fresh causal session.
- **BLOCKER:** the existing `campaign_evidence.py` bundle remains a reduced
  two-phase post-run schema and is not the frozen PR #2 four-phase
  `AttemptBundle`/`EventRecorder` contract. This checkpoint is not launch-ready
  until that contract and its catalog/provenance artifacts are integrated through
  the proven workflow and independently reviewed.
- Scientific 6,000-frame Q-05 execution: not launched.

## Q-04 PR2 evidence-adapter checkpoint — 2026-09-27

- DEV commits: `f6fc73ca` (typed injected PR2 evidence adapter) and `be75b611`
  (mean continuous payoff fallback correction).
- The actual notebook injects `MediumExecutionEvidencePlugin` while retaining
  `AllocatorRunner -> MultiRunEvaluator -> QuantumExperimentRunner`.
- Each policy cell is opened through `medium_runner.prepare_manifest`; policy
  and threat seeds therefore use the frozen PR2 domain-separated seed manifest.
- Static masks are identical across policies within a block/threat. Causal
  policies receive fresh `ScenarioSession` instances with the same threat seed
  and policy-conditioned histories.
- Live model execution writes all four frozen PR2 phases. Batch policies use
  their existing `event_sink`; step-wise policies emit the same contract from
  actual selections, payoffs, and updates.
- The existing `AttemptBundle` persists the full catalogs, availability,
  events, result summary, and completion hashes. The reduced post-hoc campaign
  writer is bypassed whenever the typed plugin is present.
- Focused non-matrix tests: `12 passed in 20.24s`.
- Real notebook-helper tiny 45-cell matrix: `1 passed in 62.78s`; all 45 bundles
  validated with four phases per frame, exact PR2 seeds, retained catalogs,
  immutable result hashes, and completed zero outcomes.
- Current PR2 regression suite (a superset of the historical 72-test gate):
  `96 passed in 72.74s`.
- Scientific 6,000-frame Q-05 execution: not launched.
- Remaining gate: independent review of these pushed DEV/TEST checkpoints.
