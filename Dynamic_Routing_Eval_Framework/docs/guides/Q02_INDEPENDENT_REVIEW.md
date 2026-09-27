# Q-02 independent scientific review

## Review identity and verdict

- **Role:** independent final scientific reviewer for M-Q Q-02.
- **Integrated checkpoint reviewed:** `fc8f1892fc394bb2cb9ce2f4acd8aa01166f44ff`.
- **Frozen PR #2 source baseline:** `d97dbde30241cd04b561cdd187a3b622a35b7592` (`pzg8794/quantum_project#2`).
- **Files reviewed:** `Q02_SCENARIO_SCIENTIFIC_DECISION.md`, `Q02_SCENARIO_CODE_INSPECTION.md`, `MQ_Q02_MANAGER_CHECKPOINT.md`, and only the PR #2 source/config/tests needed to verify their claims.
- **Read-only authorities:** the canonical board/contract under `/tmp/Fall-2026-Semester-Master-Plan-MQ` and the Quantum decision records under `/tmp/QuantumFaultTolerant-Q02-MQ`.
- **Verdict:** **REVISE BEFORE DEV**.

The integrated design has a coherent conceptual taxonomy and reaches the correct cross-policy pairing principle, but it is not ready for development because it treats a new-version/no-pooling boundary as permission to substitute currently available implementations for the canonical approved scenario semantics. That is not permitted by the governing complete-scenario rule. Binary `Markov` cannot silently replace the required four-state setting, and delay/burst/last-route `OnlineAdaptive` cannot silently replace the required gamma/softmax setting. These are treatment-definition mismatches, not documentation clarifications.

This is a revision verdict, not rejection of the entire Q-02 approach. The `Adaptive` implementation family is structurally compatible after an explicit configuration correction, and the common-innovation pairing decision should be retained.

## Governing rule

The controlling sources establish the following boundary:

1. Q-02 resolves the minimum scientific definitions and whether current PR #2 implements them; Q-03 then freezes the exact run manifest (`SDLC-EXECUTION-BOARD-2026-09-27.md:143`-`:147`; `PARALLEL-WORKER-BRIEFS-2026-09-27.md:93`-`:135`).
2. The campaign must consume the complete approved scenario set from the canonical configuration/study-design source. A configured scenario that cannot execute faithfully is a hold/incomplete condition; it may not be dropped, renamed, or replaced (`PROPOSED-SCIENTIFIC-CONTRACT.md:24`, `:33`; `MEDIUM_SCALE_PREPARATION_2026-09-26.md:9`-`:11`).
3. The approved conceptual progression remains temporal persistence, route-history-dependent targeting, and continuously reactive targeting, while exact historical process provenance is unresolved (`F06_THREAT_TAXONOMY_PHYSICAL_GROUNDING_DECISION_RECORD.md:57`-`:73`, `:115`-`:144`).
4. The current approved study-design source identifies `Markov` as 25% four-state structured disruption, `Adaptive` as 25% high-usage targeting over `w=50`, and `OnlineAdaptive` as 25% adaptive targeting with `gamma=0.97` and softmax selection (`STUDY_DESIGN_VALIDATED_STAGING.tex:149`-`:151`).

Consequently, versioning and a strict no-pooling boundary are necessary provenance controls, but they do not authorize a different scenario family under the canonical scenario name.

## Scenario dispositions

| Scenario | Exact PR #2 evidence | Independent disposition | Smallest scientifically valid next step |
|---|---|---|---|
| `Markov` | `MarkovAttack` is a per-route binary state initialized by `attack_rate`, then held or toggled symmetrically by `p_stay` (`daqr/core/attack_strategy.py:140`-`:170`). At `.25/.7`, the first emitted disruption probability is `.40`, and the nondegenerate long-run disruption probability is `.50`. It has no four-state process or 25%-prevalence parameterization. | **HOLD/DEFER.** The manager's “minimal config/code clarification” is not acceptable. Rewording the new run around the existing binary class would replace, rather than faithfully execute, the canonical four-state scenario. | Recover the canonical four-state state meanings, transition/emission rule, initialization, and meaning of 25% from the data-producing source, then implement/resolve that exact family or keep the configured scenario held. A separately versioned binary scenario could be proposed later, but it cannot substitute for `Markov` in the approved set. |
| `Adaptive` | `AdaptiveAttack` uses completed history through `t-1`, trailing-window counts, and route-wise disruption probability `min(base + strength * usage_share, 0.9)` (`daqr/core/attack_strategy.py:177`-`:218`; `daqr/core/scenario_execution.py:41`-`:55`). The mechanism is order-invariant at fixed counts. Defaults are base `.25`, window `100`, strength `.5`; no scientific preset freezes the canonical `w=50` treatment. | **REQUIRE MINIMAL CONFIG CORRECTION.** The implementation family matches the required aggregate-usage dependence, but execution by defaults or legacy string resolution does not establish the approved treatment. | Use an explicit structured scenario spec with base `.25` and `w=50`, and freeze strength, cap, cold start, normalization, cadence, scenario ID/version, and innovation mapping in Q-03. Add distinguishing, nonanticipation, and cross-policy common-innovation tests. Do not infer scientific values from constructor defaults. |
| `OnlineAdaptive` | `OnlineAdaptiveAttack` implements response delay, a global burst draw, hard-coded ten-frame burst carry-over, last-selected-route targeting, and background attacks (`daqr/core/attack_strategy.py:225`-`:275`). It has no `gamma` or softmax field. Its conditional draws make equal seeds an unstable innovation coupling across policies, and its targeted assignment can re-enable the selected route during a pending global burst (`daqr/core/attack_strategy.py:245`-`:260`). | **HOLD/DEFER.** Selecting the existing delay/burst family as the new `OnlineAdaptive` treatment is a semantic substitution, not a minimal correction. A fixed innovation schedule alone would not repair the missing gamma/softmax mechanism. | Recover the canonical gamma/softmax state statistic, update rule, temperature/normalization, initialization, 25% interpretation, and chronology, then implement/resolve that family with addressable common innovations. Until then, hold the configured scenario and therefore hold completion of the full Tier-1 axis. |

No reviewed scenario earns **ACCEPT versioned semantics** at this checkpoint. `Adaptive` is the only one whose existing mechanism can reach the canonical treatment through a bounded configuration correction.

## Pairing decision

The integrated common-innovation decision is **scientifically correct and should be retained**:

- Exogenous `Markov` realizations must use one identical realized mask across policies within a paired block.
- History-dependent `Adaptive` and `OnlineAdaptive` treatments must share policy-independent exogenous innovations while allowing each policy's completed route history to produce its own realized mask and mask hash.
- Requiring identical adaptive masks would remove the treatment's defining history dependence; using unrelated randomness would add avoidable Monte Carlo noise to policy contrasts.

The implementation contract must define addressable innovation channels, not merely equal seeds. At minimum, innovations must be stable by block, scenario version, frame, route, and stochastic component (for example background, target, transition, and burst channels as applicable). PR #2's current `Adaptive` loop has policy-independent draw cardinality, but this property is not contract-tested. Current `OnlineAdaptive` conditionally skips draws, so its equal threat seed is not a common innovation tape (`daqr/campaigns/medium_spec.py:33`-`:49`; `daqr/core/attack_strategy.py:248`-`:260`).

## New-version and no-pooling boundary

The proposed strict no-pooling boundary is **accepted but insufficient**:

- New F-08 results must not be pooled with, described as reproducing, or used to retrofit the historical scenario rows without recovered data-producing provenance.
- Every retained treatment needs a distinct versioned identity containing its semantic family, effective parameters, chronology, source hash, innovation rule, and scenario ID.
- A distinct version may change parameters within an approved semantic family. It may not silently change the family while keeping the canonical scenario slot.
- A future binary-Markov or delay/burst treatment could be separately proposed and named, but adding it would not discharge the requirement to execute or explicitly hold the canonical configured scenario.

Thus the manager's no-pooling decision correctly protects historical claims, but it does not cure the current `Markov` and `OnlineAdaptive` conformance failures.

## Minimality review

The following corrections are genuinely minimal:

1. Require structured scientific scenario specifications and reject legacy string/default resolution on the scientific path.
2. Freeze the compatible `Adaptive` configuration explicitly rather than changing its algorithm family.
3. Use frame/component/route-addressed innovations for history-dependent scenarios while preserving policy-conditioned masks.
4. Add only contract-specific determinism, causality, distinguishing-invariant, complete-axis, and pairing tests.

The following proposed actions are not minimal scientific corrections:

1. Reframing binary `MarkovAttack` as the required `Markov` treatment changes the treatment instead of repairing conformance.
2. Choosing delay/burst/last-route `OnlineAdaptiveAttack` under the canonical `OnlineAdaptive` slot changes the treatment instead of implementing gamma/softmax semantics.
3. Editing hard-coded burst details before deciding whether that noncanonical family is retained would optimize the wrong treatment.

No general architecture refactor is justified. If canonical Markov or OnlineAdaptive semantics cannot be recovered and implemented within the frozen architecture, the valid disposition is hold/defer, not an architecture expansion or silent replacement.

## Classification audit

| Integrated finding | Independent classification |
|---|---|
| Historical scenario provenance is only `DEBT` | **Misclassified.** It is `BLOCKER` evidence for accepting current binary Markov or delay/burst OnlineAdaptive as faithful configured scenarios. It remains `DEBT` only for historical pooling/equivalence after a separately approved new treatment exists. |
| No complete structured scientific configuration | **Correct launch/Q-03 hold, but not a new owner gate.** Q-03 is the board-designated freeze stage. Q-02 must give correct semantic dispositions first; exact permitted values can be frozen in Q-03. |
| Legacy string resolution can yield `attack_rate=1.0` | **Correct preflight blocker.** The smallest fix is to forbid string/default resolution on the scientific path, not to refactor all legacy execution. |
| OnlineAdaptive lacks a policy-independent innovation schedule | **Correct for any retained endogenous treatment**, but secondary to the more fundamental gamma/softmax semantic hold. Do not repair coupling while retaining the wrong family under the canonical name. |
| OnlineAdaptive burst duration and target multiplier are hard-coded | **Not the controlling Q-02 blocker.** Those are properties of the noncanonical delay/burst family. They become relevant only if that family is separately approved. |
| Contract-specific tests are pending | **Test-stage gate, not an additional scientific-design finding.** Passing current regression tests cannot substitute for the missing canonical-semantic tests. |
| Independent review is pending | **Resolved by this review**, with verdict `REVISE BEFORE DEV`; it must not remain listed as an unresolved blocker after integration. |
| Causal event rows carry a null pre-run trajectory hash | **Q-03/Q-04 contract decision.** Completion-bound realized hashes can be scientifically sufficient if Q-03 explicitly revises the per-row rule and preserves unambiguous joins; otherwise the current record violates the proposed required trace contract and is a Q-04 blocker, not mere debt. |
| Per-run identity includes queue-level configuration | **Misclassified as `DEBT`.** It directly violates the proposed completed-run identity rule (`PROPOSED-SCIENTIFIC-CONTRACT.md:31`, `:39`) and is a Q-04 readiness blocker. It is not permission for broad architecture work. |
| Scenario aliases alter threat seeds | **Q-03 freeze requirement / bounded debt.** Freeze one canonical versioned ID and forbid aliases in the scientific manifest; no separate owner gate is needed. |
| Internal scenario-state diagnostics are wholly `OPTIONAL` | **Too broad.** Redundant snapshots are optional, but the minimum state/propensity diagnostics needed to reconstruct and test the declared transition or targeting rule are required. |
| Spatial failures, hardware-calibrated attacks, and matched-severity sensitivity | **Correctly `OPTIONAL`** for Q-02 and must remain out of scope. |

## Exact choices left for Q-03

This review does **not** create an additional owner gate. After the Q-02 design is revised to preserve canonical semantics, the existing Q-03 stage may freeze the following choices:

- `Markov`: recovered four-state labels, binary availability emission map, initial distribution, transition parameterization/matrix, route coupling rule, and whether 25% denotes stationary, initial, or another declared prevalence. If canonical evidence does not resolve these, keep the scenario held rather than guess.
- `Adaptive`: canonical base `.25` and `w=50`, plus exact positive strength, cap, normalization, cold-start/tie rule, update cadence, and addressable innovation scheme.
- `OnlineAdaptive`: canonical `gamma=.97`, exact decayed history statistic, softmax logits/temperature and target sampling, base/target disruption probabilities, warm-up, and innovation channels. If canonical evidence does not resolve these, keep the scenario held rather than map them to delay/burst defaults.
- All scenarios: versioned IDs, class/source identities, initialization and frame chronology, complete approved scenario membership, mask/innovation identities, and the strict no-pooling/non-equivalence flag.

These are manifest choices within the board's Q-03 responsibility. The existing Piter GO before Q-05 remains unchanged; no new pre-development owner approval is invented here.

## Verification performed

Independent source inspection confirmed the manager's chronology, strict resolution, deterministic seed, and current-class arithmetic claims in:

- `daqr/core/attack_strategy.py`
- `daqr/core/scenario_execution.py`
- `daqr/config/experiment_config.py`
- `daqr/config/execution_contract.py`
- `daqr/campaigns/medium_spec.py`
- `daqr/campaigns/medium_runner.py`
- `daqr/campaigns/medium_trace.py`
- `tests/medium_fixtures.py`
- `tests/test_medium_architecture.py`
- `tests/test_medium_architecture_pass2.py`

The exact bounded ten-selector regression command recorded in `Q02_SCENARIO_CODE_INSPECTION.md:144`-`:150` was rerun independently with Python 3.12.11 and task-scoped temporary output: **20 passed in 55.44s**. It verifies current PR #2 mechanics only. It contains no four-state Markov conformance test, no `w=50` scientific Adaptive preset/invariant suite, no gamma/softmax OnlineAdaptive test, and no cross-policy addressable-innovation test.

No F-09/Q-05 execution, code change, test change, manuscript edit, or authority-file modification was performed.

## Final decision

**REVISE BEFORE DEV.** Preserve the taxonomy and common-innovation pairing result; replace the Markov and OnlineAdaptive substitution paths with `HOLD/DEFER`, retain `Adaptive` as `REQUIRE MINIMAL CONFIG CORRECTION`, correct the blocker/debt classifications above, and leave exact evidence-supported parameter freezing to Q-03. Development may begin only after those revisions make clear that unavailable canonical scenarios are held rather than silently redefined.
