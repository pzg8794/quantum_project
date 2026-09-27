# Q-02 scenario scientific decision

## Checkpoint state

- **Slice:** Q-02 — F-08 scientific semantic closure for configured scenarios.
- **Stage:** **DESIGN checkpoint only**.
- **Design disposition:** **COHERENT FOR TIER-1, CONDITIONAL ON CONFORMANCE**.
- **Q-02 acceptance:** **NOT YET MET**. Current-implementation conformance, contract-specific tests, and independent review remain pending.
- **Scope:** exactly `Markov`, `Adaptive`, and `OnlineAdaptive`.
- **Baseline:** Quantum PR #2 head `d97dbde30241cd04b561cdd187a3b622a35b7592` on branch `codex/mq-q02-scientific-design`.
- **Not authorized here:** code/config changes, test changes, architecture work, manuscript edits, F-09 execution, historical-corpus revalidation, or a new threat model.

This record freezes the proposed scientific meaning against which the separate code-inspection worker must evaluate PR #2. It does not declare that the implementation conforms, that Q-02 is accepted, or that F-08/F-09 execution is approved.

## Source identities and precedence

The adjudication follows the requested precedence order. Paths identify the exact files at the listed commits.

| Precedence | Source | Commit identity | Use in this decision |
|---:|---|---|---|
| 1 | `Fall-2026-Semester-Master-Plan/CAMPAIGNS/2026-09-26-MEDIUM-SCALE/SDLC-EXECUTION-BOARD-2026-09-27.md` | live `origin/main` `dd1c32d0a8e4f05ea1054e296917fa06c5dd83ff` | Q-02 stage, owner, causal-blocker rule, and pending Test/Review/Accept gates |
| 1 | `Fall-2026-Semester-Master-Plan/CAMPAIGNS/2026-09-26-MEDIUM-SCALE/PARALLEL-WORKER-BRIEFS-2026-09-27.md` | live `origin/main` `dd1c32d0a8e4f05ea1054e296917fa06c5dd83ff` | Exact Q-02 deliverable and acceptance criteria |
| 2 | `Fall-2026-Semester-Master-Plan/CAMPAIGNS/2026-09-26-MEDIUM-SCALE/PROPOSED-SCIENTIFIC-CONTRACT.md` | live `origin/main` `dd1c32d0a8e4f05ea1054e296917fa06c5dd83ff` | Configuration-driven scenario axis, nonanticipation, seed/mask pairing, manifest, and claim boundaries |
| 3 | `QuantumFaultTolerant/updates/REVIEWER_C_SCALE_CLAIM_DECISION_RECORD.md` | `0bcc913bc5a28b1e1116245cf692989a9ec98aae`; scenario-axis correction last changed by `14fd0d680c6fe63d547bc521fb3cb208bb53c899` | F-08 question, mandatory anchor, controlled scale-spectrum boundary, and complete approved scenario set |
| 4 | `QuantumFaultTolerant/updates/F06_THREAT_TAXONOMY_PHYSICAL_GROUNDING_DECISION_RECORD.md` | snapshot `0bcc913bc5a28b1e1116245cf692989a9ec98aae`; record introduced by `4c22041bed2aa7a0f3bb4b66252b0ecf5e663ad9` | Piter-approved conceptual meanings and evidence boundaries |
| 4 | `QuantumFaultTolerant/updates/MEDIUM_SCALE_PREPARATION_2026-09-26.md` | `0bcc913bc5a28b1e1116245cf692989a9ec98aae` | Complete-config rule, no silent scenario omission, and F-08/F-09 hold |
| 4 | `QuantumFaultTolerant/updates/FEEDBACK_TASKS.md` | snapshot `0bcc913bc5a28b1e1116245cf692989a9ec98aae`; scenario-axis update `854ab5a9d98923b5b762003bc142f5c871d9c264` | Approved five-setting interpretation and historical provenance hold |
| 5 | `pzg8794/quantum_project` PR #2 | `d97dbde30241cd04b561cdd187a3b622a35b7592` | Non-authoritative evidence of current behavior only; conformance verdict delegated to the code-inspection worker |

The approved F-06 record controls the conceptual taxonomy but explicitly leaves exact historical simulator parameters and process rows provenance-pending. Historical manuscript values and current class defaults therefore cannot silently become the new F-08 contract. Q-03 must materialize a versioned canonical configuration after Q-02 acceptance.

## Reconciled common contract

Let `R_t` be the route selected at completed frame `t`, `H_{t-1}=(R_0,...,R_{t-1})` the completed routing history available before frame `t`, `A_t(r) in {0,1}` the availability gate for route `r`, and `U_t(r)=1-A_t(r)` the corresponding unavailability indicator. Let `Xi` denote the scenario's declared exogenous random-innovation stream.

All three scenarios must obey this causal chronology:

1. Initialize scenario state from the manifest and scenario seed before frame `0`.
2. Before the frame-`t` route decision, compute scenario state, target propensities, and the full `A_t` vector using only declared parameters, prior scenario state, `Xi`, and the history allowed below.
3. Emit and record `A_t`; it must not depend on `R_t`, the frame-`t` action, reward, or any future observation.
4. The policy selects `R_t` and its within-route action, and the environment records the configured payoff/feedback channels.
5. Append the completed selection to history and update scenario state for frame `t+1`.

This one-frame causal boundary is mandatory even when a setting is called “online.” Online reactivity means reaction to the latest **completed** routing behavior, not same-frame action leakage.

Common minimum invariants:

- The exact scenario ID, implementation/class version, all effective parameters, initialization, RNG algorithm/domain/seed, chronology version, and history cutoff are present in the per-run identity.
- A fixed configuration, innovation stream, and allowed routing history produce byte-identical availability and diagnostic traces.
- Unknown, incomplete, or semantically unsupported configured scenarios fail closed; no fallback, relabeling, silent omission, or random substitute is allowed.
- The full route-selection trace, full availability trace or content-addressed equivalent, and enough scenario diagnostics to reconstruct the declared targeting probabilities are retained.
- Scenario parameters cannot take a degenerate value that removes the defining dependence/reactivity property while retaining the scenario name.
- These scenarios alter `A_t`; they do not redefine the route-local quantum-success term `q_r(x)`.

## Markov

### Intended scientific meaning

`Markov` is an **exogenous temporally persistent route-unavailability process**. It models bursty or persistent route-level interruption while remaining independent of the evaluated policy's routing history.

### Required dependence property

For each configured route, the latent binary unavailability state follows a declared time-homogeneous first-order transition kernel. Positive persistence must hold:

`P(U_t=1 | U_{t-1}=1) > P(U_t=1 | U_{t-1}=0)`.

Both recovery and entry transitions must be possible in the Tier-1 configuration; an always-on, always-off, absorbing, or i.i.d.-equivalent parameterization does not satisfy the `Markov` label. Conditional on the previous scenario state and `Xi`, `U_t` must not depend on `H_{t-1}` or policy identity.

### Minimum deterministic and observable invariants

- Initialization order is explicit: initialize `U_-1`, transition once, then emit `U_0`; repeat one transition before each subsequent emitted frame.
- The transition matrix is finite, valid, nondegenerate, and positively persistent.
- Replaying the same seed and manifest yields the same full mask, regardless of which policy consumes it.
- Changing route-selection history while holding the transition innovations fixed cannot change the mask.
- The artifact records the initial-state rule, transition matrix, per-route transition counts, realized unavailability rate, seed, and mask hash.
- A parameter named `attack_rate` is not interpreted as the long-run unavailability rate unless the declared transition kernel mathematically makes it so.

### Permitted configurable parameters

- Initial attacked/unavailable-state distribution.
- A shared or explicitly route-indexed two-state transition matrix, preferably represented as attack-entry and recovery probabilities or as stationary prevalence plus persistence.
- Scenario seed/domain and the declared route-wise innovation mapping.

The Tier-1 manifest must freeze the exact representation and values. Spatially coupled route failures are not permitted under this label because the approved taxonomy leaves spatial correlation as a separate unmodeled axis.

### Explicit non-claims and evidence boundary

- Not a claim that operational quantum-network faults follow this exact chain.
- Not a spatially correlated failure model.
- Not policy-adaptive or adversarial targeting.
- Not necessarily severity-matched to another scenario unless Q-03 separately freezes and justifies that constraint.

## Adaptive

### Intended scientific meaning

`Adaptive` is **route-history-dependent targeting based on aggregate recent route usage**. It represents a route-observing availability-stress/adversary abstraction that preferentially disrupts routes used more often in a declared finite retrospective window.

### Required dependence property

For window length `w >= 2`, define the completed-history count

`C_t(r)=sum_{j=max(0,t-w)}^{t-1} 1[R_j=r]`.

The frame-`t` route-specific unavailability propensity must be a declared, nonconstant, monotone function of the normalized count vector. Two histories with the same route counts in the active window must produce the same propensity vector under the same scenario state; ordering within that window is not part of this scenario's targeting signal. At least one pair of valid histories with different high-usage routes must produce correspondingly different target propensities.

### Minimum deterministic and observable invariants

- Only `H_{t-1}` is visible; the current frame's route/action/reward is unavailable.
- The active window, count vector, normalized usage vector, target propensity vector, cap/normalization rule, and emitted `A_t` are reproducible from the recorded inputs.
- A same-count/permuted-order history test leaves target propensities unchanged.
- A changed-dominant-route history test changes the preferential target in the same direction.
- Cold-start behavior before sufficient history exists is explicit and policy-neutral.
- Zero adaptation strength, a one-frame window, or any setting that makes target propensities independent of route usage is invalid under the `Adaptive` ID.

### Permitted configurable parameters

- Base unavailability probability or intensity.
- Retrospective usage-window length `w`.
- Positive adaptation strength/targeting coefficient.
- Declared normalization, probability cap, deterministic tie rule, cold-start rule, and update cadence.
- Scenario seed/domain and a policy-independent innovation mapping.

Q-03 must freeze the exact keys and values from the selected canonical configuration. This record does not choose between historical `w=50`, current-default-like alternatives, or any other numeric value.

### Explicit non-claims and evidence boundary

- Not a literal or hardware-validated physical attack mechanism.
- Not an optimal attacker and not evidence about attacker capability outside this simulator.
- Not same-frame targeting and not allowed to inspect current actions or rewards.
- Not an identical-mask treatment across policies: different policy histories may legitimately produce different realized masks.

## OnlineAdaptive

### Intended scientific meaning

`OnlineAdaptive` is **order- and recency-sensitive targeting recomputed online as completed routing behavior evolves**. It represents the approved continuously reactive route-observing availability-stress/adversary abstraction.

### Required dependence/reactivity property

After a declared causal warm-up/response delay, target propensities must be evaluated at every frame from the ordered routing history through `t-1`. There must exist two histories with the same route-use counts but different order or most-recent route for which the next target propensity vector differs under the same prior scenario state and innovations. This order/recency sensitivity is the minimum scientific distinction from `Adaptive`.

Optional burst state or background interruption may coexist with the reactive rule, but it cannot replace or erase the required route-history reactivity.

### Minimum deterministic and observable invariants

- The frame-`t` target uses no information later than `R_{t-1}`.
- After warm-up, the reactive target state is recomputed on every frame, including frames with no realized disruption.
- A same-count/different-last-route test changes the next eligible target propensity or target state.
- Holding history fixed while replaying the same innovation stream yields the same target state, burst state, propensity vector, and `A_t`.
- Any response delay, burst trigger/duration, background rate, target multiplier, decay/recency rule, cap, and cold-start behavior are explicit in the manifest and trace.
- Parameter combinations that make the mask independent of ordered recent history are invalid under the `OnlineAdaptive` ID.

### Permitted configurable parameters

- Base/background unavailability probability or intensity.
- Positive causal warm-up/response delay and the declared ordered-history/recency rule.
- Positive targeting multiplier/strength and any normalization/cap.
- Burst probability and duration only when they belong to the selected existing canonical implementation; they do not authorize a new hybrid threat model.
- Scenario seed/domain, deterministic tie rule, and policy-independent innovation mapping.

Q-03 must select one versioned existing implementation/configuration family and record every effective value. It must not silently combine the historical gamma/softmax description with the current delay/burst family.

### Explicit non-claims and evidence boundary

- Not a zero-latency same-frame adversary.
- Not a hardware-validated adversary or measured attack distribution.
- Not necessarily more severe or more physically realistic than `Adaptive`.
- A global burst component alone is not evidence of online adaptation.
- Results support only the behavior of configured policies under this declared simulator process.

## Cross-policy pairing adjudication

The proposed contract's phrase that the threat seed/mask is shared across policies is scientifically valid only after distinguishing exogenous from endogenous scenarios:

- **Markov:** share the exact realized mask across policies within a paired block because its process is exogenous to route selection.
- **Adaptive and OnlineAdaptive:** share a frame/route-addressed innovation tape or an equivalent deterministic consumption schedule, but compute a separate realized mask from each policy's own completed routing history.

Requiring an identical realized mask for `Adaptive` or `OnlineAdaptive` would sever the approved dependence on observed routing behavior. Conversely, allowing unrelated randomness across policies would confound policy-induced mask differences with avoidable Monte Carlo differences. Therefore common innovations plus policy-conditioned masks are the minimum coherent pairing contract. Each realized adaptive mask and its hash belong to that policy-run identity.

## Scientific coherence and Tier-1 sufficiency

| Scenario | Scientific axis isolated | Distinguishing invariant | DESIGN verdict |
|---|---|---|---|
| `Markov` | Exogenous temporal persistence | Mask depends on prior availability state, never routing history | Include conditionally |
| `Adaptive` | Endogenous aggregate-usage targeting | Propensity changes with finite-window counts but is invariant to order at fixed counts | Include conditionally |
| `OnlineAdaptive` | Endogenous online recency/order reactivity | Same counts with different recent order can change the next target propensity | Include conditionally |

These distinctions are scientifically coherent and sufficient for the F-08 Tier-1 **availability-stress axis**. Together they separate temporal dependence from policy-history dependence and separate aggregate-history adaptation from event-order/recency reactivity. They do not establish a universal threat taxonomy, physical severity ladder, spatial-failure model, hardware realism, or causal node-count effect.

No scenario is scientifically deferred at DESIGN. Each remains conditional on exact canonical configuration, implementation conformance, deterministic/causal tests, and independent review. A failing implementation must be minimally corrected or explicitly held; it must not be silently dropped from the complete approved scenario set.

## Intended-versus-implemented integration status

The approved F-06 record reports three unresolved implementation/manuscript discrepancies that the code-inspection worker must verify at PR #2 head `d97dbde30241cd04b561cdd187a3b622a35b7592`:

| Scenario | Source-reported reconciliation risk | Required final Q-02 disposition |
|---|---|---|
| `Markov` | Binary per-route state with a `p_stay`-style implementation was reported, while historical manuscript material described a four-state process. | `PENDING CODE INSPECTION`; then `MATCH`, `MINIMAL CONFIG/CODE CORRECTION REQUIRED`, or `DEFER FROM TIER-1` |
| `Adaptive` | Current-default-like `attack_rate`, `adaptation_window`, and `adaptation_strength` values were reported not to match the historical `w=50` statement. | `PENDING CODE INSPECTION`; then one required final disposition |
| `OnlineAdaptive` | A delay/burst/recent-route implementation was reported not to implement the historical gamma/softmax description. | `PENDING CODE INSPECTION`; then one required final disposition |

Those are exact provenance risks from `updates/F06_THREAT_TAXONOMY_PHYSICAL_GROUNDING_DECISION_RECORD.md` at the source identity above, not a new conformance verdict by this DESIGN worker. The separate inspection must cite exact PR #2 config/code symbols, effective parameters, and frame chronology before Q-02 can advance.

## Findings under the causal blocker rule

### BLOCKER

1. **Implementation conformance is unverified.** Without exact config/code evidence for all three scenarios, the Q-03 run contract could name treatments whose implemented dependence or chronology differs from their scientific meaning, making the requested Tier-1 comparisons invalid.
2. **Adaptive pairing must be corrected or explicitly resolved.** If Q-03 requires one identical realized mask across policies for `Adaptive` or `OnlineAdaptive`, those treatments cannot remain routing-history-dependent; the named scientific contrasts would be invalid. Common innovations with policy-conditioned masks is the recommended minimal correction.
3. **The Q-03 manifest must freeze effective parameters and chronology.** Without versioned parameter values, initialization, history cutoff, update timing, and scenario identity, a completed run could not be reconstructed or interpreted as one of the adjudicated treatments.

### DEBT

1. **Historical data-producing provenance remains unresolved.** This blocks claims that the new Tier-1 treatment exactly reproduces historical manuscript scenario rows or permits pooling with historical results. It does not block a newly versioned F-08 run with explicit semantics and a strict no-pooling boundary.

### OPTIONAL

1. Spatially correlated failures, hardware-calibrated attack distributions, device-level fault models, and matched-severity sensitivity analyses are scientifically useful later extensions. They are not required to answer Q-02 or execute the reviewer-required Tier-1 availability-stress comparison.

## Owner decision boundary

No numeric scenario value is guessed here.

Piter's Q-03 approval is required for the exact canonical parameterization: Markov initialization/transition values; Adaptive base rate, window, strength, cap, and cadence; OnlineAdaptive base rate, response/recency rule, strength, and any burst settings. Q-03 must also identify whether the new F-08 run is a newly versioned treatment or is intended to reproduce a historically described process after provenance recovery.

If exact realized-mask sharing across policies is non-negotiable, Piter must choose between removing/renaming the adaptive treatments or abandoning their approved history-dependent meanings. The worker must not guess that choice. The scientifically recommended option is to preserve the approved meanings and pair only the exogenous innovations.

## Exact Q-02 acceptance criteria

The controlling worker brief requires all of the following:

1. The final compact intended-versus-implemented table covers `Markov`, `Adaptive`, and `OnlineAdaptive`, including exact effective parameters and chronology.
2. Each scenario receives exactly one final disposition: `MATCH — no correction`, `MINIMAL CONFIG/CODE CORRECTION REQUIRED`, or `DEFER FROM TIER-1 with reason`.
3. **Every claimed mismatch cites exact source/config/code evidence.**
4. **Each issue is blocker/debt/optional.**
5. **Any proposed change is the smallest change needed for scientific validity.**
6. **The result is sufficient for Piter to approve/reject the Q-03 frozen contract.**

This DESIGN checkpoint supplies the intended-science side and the classification rule. Criteria 1–3 remain incomplete until the separate implementation inspection is integrated. Criteria 5–6 then require contract-specific Test and Independent Review. Consequently, this commit is ready for the next Q-02 inspection/review stage, **not Q-02 acceptance**.

## Required conformance checks before acceptance

- Fixed-seed deterministic replay for every scenario.
- Frame-`t` nonanticipation test using histories identical through `t-1`.
- Markov route-history-independence and positive-persistence tests.
- Adaptive changed-dominant-route and same-count/permuted-order tests.
- OnlineAdaptive same-count/different-recent-order reactivity test.
- Markov exact-mask cross-policy pairing test.
- Adaptive/OnlineAdaptive common-innovation but policy-conditioned-mask test.
- Strict configured-scenario resolution with no fallback or silent omission.
- Independent review against this record, the canonical configuration, and PR #2 head.

No tests are claimed by this DESIGN record; the listed checks belong to the pending Q-02 Test/Review stages.
