# Medium-scale execution preparation

Date: 2026-09-26

Phase: **source recovery and engineering design; execution not authorized**

Execution owner: Quantum framework (`pzg8794/quantum_project`)

Analysis and claim owner: the quantum manuscript project, through its F-08/F-09 evidence gates

This is a public-safe engineering preparation record. It does not approve a
scientific configuration, close F-08/F-09, report new results, or authorize a
campaign launch. No substantive experiment was run during this inspection.

## September 26 scientific proposal — approval and preflight required

**PROPOSED SCIENTIFIC CONTRACT — PITER APPROVAL REQUIRED BEFORE SUBSTANTIAL EXECUTION.** A current scientific adjudication proposes `layered-primary-form-v1`: 15 nodes (source, seven first-layer relays, six second-layer relays, destination), ten distinct three-hop source–destination routes from a seeded, degree-bounded, covering bipartite middle-edge catalog, and all 15 nodes represented on routes. This is a controlled synthetic route-breadth anchor, **not** a geometric-network claim or a causal comparison with the historical four-route diamond. The matched continuation would use the same family at `(nodes,routes)=(7,4),(11,7),(15,10),(19,13)`; node and route count co-vary, with a separately prespecified fixed-topology route-subset check if needed.

The proposed fixed allocator gives nine qubits per route (90 total for ten routes); each three-hop route has 55 nonnegative integer within-route allocations summing to nine (550 route–action pairs). Preserve the implemented primary product-form payoff with its `entanglement_success_factor=100`, route-local effective per-hop rates, route availability gate, and an exact four-route regression fixture. The new medium quality catalog assigns five routes `p_e=2e-4` and five `p_e=1.5e-4` per hop by stable metadata/seed. Shared physical edges are not presently modeled as shared rate/failure/resource coupling. Do not substitute Paper2/Paper8's different action/reward semantics.

The proposed Tier-1 comparison is privileged frame-wise `Oracle`, `CEpsilonGreedy`, and explicit `EXPNeuralUCB(mode='hybrid')`, crossed with `NoAttack` and verified independent `RandomAttack` at **0.0625 effective interruption per route/frame**, one fixed `T_b` replay setting (`s=2`, capacity 12,000), and 6,000 frames. Three predeclared paired topology/environment seed blocks yield **18 policy-run units**; the first six-unit block is only a descriptive pilot. Current pursuit-named model configurations do not activate their pursuit/informed branches under `mode='neural'`, so pursuit comparison requires a separate mode/provenance audit. Current adaptive labels may fall back to random without selection traces.

Hard preflight: deterministic domain-separated SHA-256 seeds (not Python `hash`); valid distinct routes/all-node coverage; 550 aligned contexts/actions/rewards; policy mode and mask nonanticipation; expected-payoff versus sampled learner-feedback distinction; exact attempt retention and completion hashes. The current manuscript describes a different per-link exponent and Bernoulli observed reward than the primary code's `100*x` exponent and continuous accumulated payoff. Resolve data-producing provenance before a GA result claim; do not silently edit either scientific interpretation. Valid zero/poor outcomes must be retained, and performance-triggered/best-attempt reruns bypassed. No exact mid-frame resume is claimed. F-09 remains held for Piter/F-08 approval and passing technical checks; F-10 remains a separate 100-node diagnosis.

## Authority and inspected source state

The governing public decision is the manuscript project's
[Reviewer-C scale decision record at `07b1d47`](https://github.com/pzg8794/QuantumFaultTolerant/blob/07b1d47ce773f2be405cdee1d9f89ca264b05007/updates/REVIEWER_C_SCALE_CLAIM_DECISION_RECORD.md#b-f-08--design-medium-scale--controlled-scale-spectrum-validation).
Its F-08 design requires a compatible topology/testbed family and a mandatory
**15–20-node, at least 10-candidate-route anchor**. Existing heterogeneous
external testbeds do not by themselves establish a controlled scale curve.
The wider spectrum should not delay the required medium anchor. F-09 executes
only an approved F-08 design; F-10 remains a separate targeted diagnosis of the
existing 100-node result. See the
[pinned F-08/F-09/F-10 checklist](https://github.com/pzg8794/QuantumFaultTolerant/blob/07b1d47ce773f2be405cdee1d9f89ca264b05007/updates/FEEDBACK_TASKS.md#f-08--design-medium-scale-validation-as-a-controlled-scale-spectrum).

Code observations below refer to `gcp-main` at
`284746944e4ed4e3e95ae545925ff159d51dcc93`. That checkout matched its remote at
the recovery checkpoint. Existing edits in five scratch algorithm files and
`Dynamic_Routing_Eval_Framework/run_tests.sh`, plus untracked `run_scripts/`,
were outside this documentation pass and were preserved. The findings describe
current source behavior; they are not claims about the historical
data-producing implementation or a newly executed medium experiment.

## Architecture and readiness conclusion

Use one manifest-controlled routing execution, preserve its raw output, and
derive analysis products from its immutable records and hashes. Instrument the
execution before launching it. Keep analysis code out of the decision loop.

```text
approved scientific configuration + pinned code/runtime
                         |
                 campaign manifest
                         |
          topology + route + action catalogs
                         |
          routing execution with passive tracing
                         |
      per-run immutable raw records + completion hashes
                         |
             validated scale-analysis artifacts
                         |
             bounded manuscript evidence/claims
```

The framework supplies useful variable-size graph, policy, allocator, and state
machinery. It does **not yet demonstrate a ready primary-style medium campaign**.
The immediate engineering question is whether a route-driven generalization of
the primary context/reward contract can use the existing topology machinery
while preserving the approved matched semantics.

### Topology and action-space path

| Present implementation | Implication for preparation |
|---|---|
| `Paper2TopologyGenerator` accepts `num_nodes` and generates distance-bearing edges [S1]. | Reuse is plausible; a particular 15–20-node graph with at least 10 valid candidate routes still needs a deterministic sanity check. |
| Paper2's standardized notebook has configurable node/path counts, uses distance-weighted `shortest_simple_paths`, and currently returns `external_contexts=None` [S2]. | This is existing external-testbed scaffolding, not automatic preservation of the primary allocator-dependent within-route action space. |
| The Paper2 helper substitutes repeated endpoint paths when no path exists [S2]. | The campaign builder must fail when the selected graph cannot supply the required distinct valid routes. It must not pad the reviewer anchor with duplicates or nonexistent edges. |
| The default environment builds two-hop contexts for route indices 0/1 and three-hop contexts for all other indices, then computes exactly four reward lists [S3]. | Changing only `num_paths` cannot produce a valid primary-style medium experiment. Introduce route-metadata-driven context/reward construction after the scientific semantics are selected. |
| Paper8 uses one eight-feature vector and one action per route [S4]. | Do not silently substitute that representation for the primary within-route allocation experiment. |
| Allocators accept variable route counts; minimum-allocation enforcement can exceed the budget for an infeasible input [S5]. | Reject infeasible budgets and validate conservation, per-route action counts, action dimensions, and reward/context alignment. |

The proposed configuration owner is a small importable campaign builder and
versioned manifest within this execution repository, called by a thin notebook.
It should reuse the selected topology generator and existing evaluator/model
interfaces. Scientific values belong in the approved manifest, not duplicated
notebook globals. No new topology family or numerical settings are selected
by this record.

For primary-style actions, the proposed invariant is a route-specific
nonnegative integer allocation vector of the route's actual hop dimension,
with its sum equal to the allocator-assigned route budget. The reward equation,
link parameters, admissible zero allocations, and any action enumeration limit
remain subject to the selected scientific contract. Before generalization,
preserve a complete small-primary fixture and verify its contexts/rewards are
unchanged. Compute the action-space cardinality before allocating it in memory;
do not silently subsample or truncate actions to meet a runtime target.

## Passive logging contract

The campaign needs explicit records beyond current cumulative model results.
The following is a proposed schema, not a statement that the logger exists.

| Artifact | Required content and boundary |
|---|---|
| `campaign_manifest` | Schema version; configuration hash; code commit and relevant file hashes; interpreter/library/hardware versions; exact policy, threat, allocator, replay, horizon, and metric configuration; deterministic seed derivation version; approved run list. |
| `topology_catalog` | Stable graph ID/hash; generation family/parameters/seed; nodes, edges, physical/model attributes and units; connectivity and density diagnostics. |
| `route_action_catalog` | Stable route ID; topology ID; ordered nodes/edges; source/destination; hops/distance; overlap diagnostics; action-space version; budgets and action vectors. Route index alone is not a persistent identity. |
| `decision_events` | Campaign/run/attempt/policy ID; frame and decision ID; topology/route-catalog hash; decision-time context/observation or immutable snapshot reference; observation time/version; current route budgets; chosen route and within-route action. Capture before the outcome/update. |
| `outcome_events` | Joinable decision ID; actual simulator reward; availability factor; sampled learner feedback if applicable; error/status; explicit outcome semantics and units. Do not conflate an expected reward, a sampled learning signal, and a physical delivery event. |
| `run_completion` | Complete/failed/interrupted state; expected/actual event counts; raw file hashes; manifest/catalog hashes; wall time, memory/storage diagnostics; exception details; trace cursor; checkpoint pointers. |

Decision-time features and later outcomes must remain separate schema fields
and storage views. Preserve grouping keys for topology realization, route
catalog, run seed, policy, attempt, and frame. Multiple frames, policies, or
noise replicas from one underlying topology are not automatically independent
held-out examples. Do not choose a future prediction target in the logger.
Static catalogs should be stored once and referenced by hash; dynamic
observations must preserve the snapshot actually available at the decision.
Logging all candidate contexts does not establish counterfactual realized
outcomes for routes the policy did not select.

Existing insertion points:

- Step-wise policies: `QuantumExperimentRunner.run_step_wise_oracle`, between
  action selection and feedback/update [S6]. Despite its method name, the
  runner dispatches other step-wise policies here.
- Neural batch policies: after route/action selection and before update in
  `neural_bandits.py:403–415` [S7].
- Predictive batch policies: the corresponding loop in
  `predictive_bandits.py:280–310` [S8].
- Runner completion: existing results contain algorithm seed, frame count,
  attack label, and model results; the neural payload includes cumulative
  reward/regret and route/action pairs [S6, S7]. Extend with a versioned trace
  reference and completion validation.

Current batch loops compute observed reward as base reward multiplied by route
availability and separately sample a Bernoulli signal used by learning. The
trace must record those with distinct names where present. Its schema must
also represent policies for which a field is unavailable without inventing a
value. Passive tracing must consume no model/environment randomness and must
pass an instrumentation-on/off trajectory-equivalence test.

`ExperimentConfiguration.set_environment()` accepts `metadata` but does not
put it into the environment parameter dictionary [S9]. A tested propagation
path is needed; merely passing a manifest as metadata is insufficient.

## Reproducibility, attempts, checkpointing, and progress

These are source-established readiness issues, not retrospective findings
about the validated corpus:

1. Environment seeding uses Python `hash()` [S6, S10]. Use an explicit,
   versioned deterministic seed map for the new campaign and verify it across
   fresh processes. Record topology, route-generation, threat, allocator, and
   policy RNG identities separately.
2. Legacy configuration/resume comparisons omit seeds and some external
   objects [S9]. New campaign records need manifest/topology/route/run hashes
   checked before any skip/resume. Do not rename or rewrite historical state
   files; keep existing state handling and add a campaign-specific validation
   boundary.
3. `run_single_model()` contains performance-threshold retries and retains
   a best result [S6]. Record every attempt before selecting any summary.
   Execution errors must be distinguishable from valid zero/low scientific
   outcomes. Sol must approve the fresh campaign's retry/selection protocol;
   this inspection does not infer how that affected historical data.
4. `MultiRunEvaluator.run_experiment()` increments horizon with experiment
   index while also changing the seed [S10]. Represent seed repeats and
   horizon sweeps as separate manifest axes; do not report such runs as
   equal-horizon independent repeats without checking the configuration.
5. The live-progress wrapper passes `progress_callback` to a parallel method
   that does not accept it [S11]. Wire and test a monotonic event callback, or
   use a simpler queue-level progress table and existing per-model bars.
6. Parallel models use shared global NumPy/Torch seeding in the current
   runner [S6, S11]. Establish reproducibility with serial preflight or
   isolated per-run processes before approving concurrency.

The initial resumability contract should be **run-boundary checkpointing**:
save every complete run atomically, verify hashes/counts on restart, skip only
verified complete runs, and deterministically restart an interrupted run.
Interrupted traces remain labeled partial attempts and are excluded from
scientific summaries until resolved. Existing completed-model/run resume tests
are useful regression protection; they do not prove exact frame-level resume.

If uninterrupted run length makes frame-level checkpoints necessary, persist
and test the frame cursor, model/optimizer/replay state, every RNG state,
allocator/threat state, and raw-trace cursor together. Compare an interrupted
and resumed trajectory with an uninterrupted reference. Do not claim that
capability before the equality test passes.

Use the existing data-lake/state configuration. Preserve the established
`quantum_data_lake/framework_state/` and `quantum_data_lake/model_state/` roots
and full saved filenames. Raw artifacts belong to an explicit campaign
namespace under the existing output configuration; record resolved local and
Drive locations before launch. This record does not create new remote roots.

## Notebook and monitoring plan

Proposed notebooks are interfaces to importable code, not duplicated engines:

1. **Canonical medium execution:** runtime/module-path checks; immutable
   manifest display; topology/route/action diagnostics; planned run count and
   resource estimate; explicit approved run invocation; per-run progress
   table; errors/checkpoints; completion manifest and hashes.
2. **GA scale analysis:** load pinned completed-run manifests; validate
   completeness and approved comparison groups; produce the approved metrics,
   uncertainty summaries, and bounded cross-scale artifacts. It must not
   launch experiments as an analysis side effect.

The execution table should show run ID, seed, topology, policy/threat labels,
status, frame/total progress where available, elapsed time, last checkpoint,
error, and raw artifact pointer. Estimate remaining time from measured pilot
costs, not existing notebook prose. Existing standardized notebooks contain
installation and duplicate-cleanup setup cells; do not copy those side effects
into the canonical execution notebook.

## Atomic engineering tasks

All tasks below are proposed; none is marked implemented by this record.
Scientific approval means the task cannot finalize the relevant experimental
choice until the scientific decision is recorded. Public-safe code/contracts
may be reviewed separately from unpublished raw results.

| ID / task | Project owner / code owner | Dependency | Expected evidence | Privacy | Scientific approval? | Next action |
|---|---|---|---|---|---|---|
| M01: pin execution source/runtime | Quantum / `quantum_project` | current recovery | manifest schema, import-path/version check, selected commit | public-safe schema; raw manifest reviewed before release | No | Define the manifest and module provenance check. |
| M02: select scientific contract | Quantum manuscript / F-08 record | M01 evidence | approved topology/reward/action and run matrix specification | public-safe decision summary | Yes | Resolve the decision list below. |
| M03: route catalog builder | Quantum / topology + campaign builder | M02 topology choice | deterministic graph/route hashes; >=10 distinct valid paths | public-safe implementation | Yes for scientific strategy | Reuse the selected generator and fail on invalid catalog. |
| M04: primary action/reward generalization | Quantum / environment + physics | M02, M03 | small-primary equivalence; variable-hop route/action/reward invariants | public-safe implementation | Yes for semantics | Design the route-driven builder without changing legacy defaults. |
| M05: allocator and policy shape validation | Quantum / allocator + selected policies | M03, M04 | budget/shape checks; all selected policies accept medium action catalog | public-safe tests | Yes for chosen settings | Test infeasible budgets and heterogeneous route dimensions. |
| M06: deterministic seed/attempt protocol | Quantum / runner + evaluator | M01, M02 | fresh-process repeatability; complete attempts and error records | public-safe implementation | Yes for scientific retry rules | Separate repeat/horizon axes and remove implicit seed identity. |
| M07: passive raw trace | Quantum / step-wise + batch loops | M01, M04 | schema validation; on/off trajectory equivalence; no feature/outcome leakage | public-safe schema; raw results held for review | No | Add the common callback contract to the actual loop seams. |
| M08: completion checkpoint/progress | Quantum / runner + state layer | M06, M07 | crash/restart test; complete-run hash checks; visible progress/errors | public-safe implementation | No | Implement the minimal run-boundary contract. |
| M09: canonical execution notebook | Quantum / thin notebook | M03–M08 | clean setup, preview, explicit launch cell, audit output | public-safe source; outputs reviewed | No | Call importable code and suppress automatic cleanup/launch. |
| M10: technical preflight/runtime estimate | Quantum / test and pilot harness | M02–M09 | regression report, tiny labeled fixture, trace counts, cost estimate | public-safe report; raw fixture labeled | Yes before scientific configuration execution | Follow the ordered validation sequence. |
| M11: F-08 approval then F-09 execution | Quantum manuscript / execution owner | M10 + scientific approval | approved manifest, immutable raw evidence, validated analysis | release reviewed | Yes | Keep on hold until the recorded launch gate is satisfied. |

## Validation and preflight sequence

1. **Recent drift only:** identify changes since the already closed
   compatibility checkpoint that affect the selected execution. Do not
   restart a broad compatibility program without new evidence.
2. **Regression:** run the applicable existing environment, allocator/runner,
   registry, and resume tests in the identified runtime. Record skipped tests
   and missing dependencies as such, not passes.
3. **Topology/routes:** validate node count, connectivity, actual valid route
   count, uniqueness, endpoints/edges, IDs/hashes, hop/overlap/distance
   diagnostics, and deterministic regeneration.
4. **Action space:** verify dimensions, allocation sums/budget feasibility,
   nonempty aligned contexts/rewards, finite values, selected-policy shape
   compatibility, and preserved small-primary behavior. Measure enumeration
   cost before large materialization.
5. **Logging/identity:** test pre-decision capture, distinct outcome fields,
   no RNG consumption, stable seed map across processes, complete attempt
   retention, schema joins/counts, atomic completion, and immutable raw hashes.
6. **Tiny run:** after those gates and the relevant scientific settings are
   resolved, execute a tightly bounded technical fixture. Label it as
   preflight, not F-09 evidence; test complete-run resume and interruption.
7. **Downstream conversion smoke:** export/read back the frozen raw schema
   through a generic consumer; confirm no missing IDs, repeated decisions,
   partial-run contamination, or unsupported fields synthesized as facts.
8. **Runtime estimate:** measure wall time, peak memory, action-space size,
   trace volume, and storage latency; project the approved run list with
   explicit uncertainty. Return that evidence for GO/RESIZE/STOP adjudication.
9. **Launch gate:** scientific configuration, technical checks, output
   locations, and F-08 approval must all be recorded before F-09 runs.

Existing tests to retain are `tests/test_environment_contexts.py`,
`tests/test_resume_behavior.py`, `tests/test_runner_resume_compare.py`,
`tests/test_allocator_runner_cleanup.py`, `tests/test_registry_update_on_save.py`,
`tests/test_drive_state_offload.py`, and
`tools/tests/test_state_naming_and_resume.py` under
`Dynamic_Routing_Eval_Framework/`. Paper8 build/reward tests protect that
specific external testbed, not the primary medium contract. New tests are
required for M03–M08 and the selected scientific representation.

## SCIENTIFIC DECISIONS RESERVED FOR SOL

The reviewer-required anchor is already established. All other final values
must come from the approved scientific record, not defaults encountered in
code:

- Exact topology family/realization, node/path spectrum, endpoints, and
  candidate-route generation strategy; treatment of path overlap/density.
- Primary-style reward/physics semantics, context dimensions, allocation
  action enumeration, and any admissibility or truncation rule.
- Policy and threat subsets; exact threat processes/parameters and whether
  adaptive labels are demonstrated to depend on routing history.
- Allocator, physical budget, update cadence, replay anchoring/capacity, and
  which factors are held fixed versus varied.
- Seed count and topology/threat/policy pairing; horizons, convergence checks,
  stopping criteria, retry/attempt-summary policy, and uncertainty treatment.
- Metrics and cross-scale interpretation rules, including valid negative or
  inconclusive findings.
- Tier-1 breadth, conditional Tier-2 expansion, compute budget, and
  GO/RESIZE/STOP scientific thresholds.

Current adaptive environment construction calls threat generation without a
selection trace; the adaptive strategies have a random fallback in that case
[S12]. Runtime preflight must identify the actual effective process for the
selected path before an adaptive-threat claim is made. This is a specific
current-source validation requirement, not a conclusion about prior evidence.

## Current blocker and exact next action

The campaign has a reviewer anchor and an engineering preparation record, but
it lacks an approved compatible topology/reward/action contract and a validated
instrumented medium execution path. F-09 and F-10 remain unexecuted in this
pass. The next action is **M01/M02: freeze the inspected source/runtime
provenance and have Sol record the scientific contract**, using the specific
primary-versus-external semantics findings above. Then implement M03–M08 in
scoped changes and complete technical preflight before requesting a launch.

**Updated September 26 next action:** the proposal above now supplies candidate M01/M02 scientific values, pending Piter approval. Engineering may prepare the metadata-driven catalog/context/reward path and four-route plus medium invariant tests, then seed/logging/attempt checks. It must not treat this proposal as F-08 signoff or launch F-09. The earlier unresolved-values queue is retained for historical traceability, not as the current decision state.

## Pinned source register

All code links below are at `284746944e4ed4e3e95ae545925ff159d51dcc93`.

- **S1 — topology generation:** [topology_generator.py:58](https://github.com/pzg8794/quantum_project/blob/284746944e4ed4e3e95ae545925ff159d51dcc93/Dynamic_Routing_Eval_Framework/daqr/core/topology_generator.py#L58), especially 66–109.
- **S2 — current Paper2 configuration/helper:** [H-MABs_Eval-Testbed-Paper2-StandardizedRunConfig.ipynb](https://github.com/pzg8794/quantum_project/blob/284746944e4ed4e3e95ae545925ff159d51dcc93/Dynamic_Routing_Eval_Framework/notebooks/H-MABs_Eval-Testbed-Paper2-StandardizedRunConfig.ipynb), code cells 3 and 5 (zero-based notebook indices); path helper source at JSON lines 993 onward. Notebook contents were inspected, not executed.
- **S3 — primary context/reward behavior:** [network_environment.py:256](https://github.com/pzg8794/quantum_project/blob/284746944e4ed4e3e95ae545925ff159d51dcc93/Dynamic_Routing_Eval_Framework/daqr/core/network_environment.py#L256), 256–283 and 341–374.
- **S4 — Paper8 representation:** [network_environment.py:285](https://github.com/pzg8794/quantum_project/blob/284746944e4ed4e3e95ae545925ff159d51dcc93/Dynamic_Routing_Eval_Framework/daqr/core/network_environment.py#L285), 285–339 and 378–419.
- **S5 — allocator budget behavior:** [qubit_allocator.py:30](https://github.com/pzg8794/quantum_project/blob/284746944e4ed4e3e95ae545925ff159d51dcc93/Dynamic_Routing_Eval_Framework/daqr/core/qubit_allocator.py#L30), 30–59 and 91–102.
- **S6 — runner seeds, step-wise loop, results, retries:** [experiment_runner.py:403](https://github.com/pzg8794/quantum_project/blob/284746944e4ed4e3e95ae545925ff159d51dcc93/Dynamic_Routing_Eval_Framework/daqr/evaluation/experiment_runner.py#L403), 403–458, 467–587, and 773–870.
- **S7 — neural loop/results:** [neural_bandits.py:377](https://github.com/pzg8794/quantum_project/blob/284746944e4ed4e3e95ae545925ff159d51dcc93/Dynamic_Routing_Eval_Framework/daqr/algorithms/neural_bandits.py#L377), 377–459.
- **S8 — predictive loop:** [predictive_bandits.py:256](https://github.com/pzg8794/quantum_project/blob/284746944e4ed4e3e95ae545925ff159d51dcc93/Dynamic_Routing_Eval_Framework/daqr/algorithms/predictive_bandits.py#L256), 256–333.
- **S9 — configuration metadata/identity:** [experiment_config.py:887](https://github.com/pzg8794/quantum_project/blob/284746944e4ed4e3e95ae545925ff159d51dcc93/Dynamic_Routing_Eval_Framework/daqr/config/experiment_config.py#L887), 887–895 and 1008–1038; runner comparison at `experiment_runner.py:150–163`.
- **S10 — run/horizon/checkpoint orchestration:** [multi_run_evaluator.py:1437](https://github.com/pzg8794/quantum_project/blob/284746944e4ed4e3e95ae545925ff159d51dcc93/Dynamic_Routing_Eval_Framework/daqr/evaluation/multi_run_evaluator.py#L1437), 1437–1514; additional environment seed construction at 144–168.
- **S11 — parallel/progress methods:** [experiment_runner.py:946](https://github.com/pzg8794/quantum_project/blob/284746944e4ed4e3e95ae545925ff159d51dcc93/Dynamic_Routing_Eval_Framework/daqr/evaluation/experiment_runner.py#L946), 946–974 and 1119–1156.
- **S12 — threat construction and fallback:** [network_environment.py:748](https://github.com/pzg8794/quantum_project/blob/284746944e4ed4e3e95ae545925ff159d51dcc93/Dynamic_Routing_Eval_Framework/daqr/core/network_environment.py#L748) and [attack_strategy.py:172](https://github.com/pzg8794/quantum_project/blob/284746944e4ed4e3e95ae545925ff159d51dcc93/Dynamic_Routing_Eval_Framework/daqr/core/attack_strategy.py#L172), 172–176 and 235–239.
