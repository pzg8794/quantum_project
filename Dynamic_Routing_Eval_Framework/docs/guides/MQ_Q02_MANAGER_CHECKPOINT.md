# M-Q Q-02 manager checkpoint

## Status

- **Slice:** Q-02 — F-08 scientific-semantic closure for `Markov`, `Adaptive`, and `OnlineAdaptive`.
- **SDLC stage:** INDEPENDENT REVIEW complete with verdict **REVISE BEFORE DEV**; **not accepted**.
- **PR:** [pzg8794/quantum_project#2](https://github.com/pzg8794/quantum_project/pull/2), frozen baseline `d97dbde30241cd04b561cdd187a3b622a35b7592`.
- **Manager branch:** `codex/mq-q02-integration`.
- **Scientific-definition worker:** ULTRA / Extra High, source checkpoint `88849da91c5aed99215be94a5486c1425f6c7ac1`, integrated as `28d727e7`.
- **Code/config inspection worker:** HIGH, source checkpoint `a7e2fc69eac684abcccbe5cf04080a205244e6f7`, integrated as `48a09a33`.
- **Runtime verification:** `20 passed in 60.80s` for the bounded scenario/config/causality selection listed in `Q02_SCENARIO_CODE_INSPECTION.md`. This is technical evidence, not scientific validation.
- **Independent reviewer:** ULTRA / Extra High, checkpoint `9f9b0c774aec24484bbbd31fab7f10168003b50b`, integrated as `2d1ce7c6`; independent rerun **20/20 passed in 55.44s**.

No production code, test code, manuscript, validated corpus, or F-09/Q-05 run changed in this checkpoint.

## Integrated intended-versus-implemented verdict

| Scenario | Intended Tier-1 scientific property | PR #2 behavior | Disposition before Q-02 acceptance |
|---|---|---|---|
| `Markov` | Canonical 25% four-state structured disruption, while preserving the approved exogenous temporal-persistence interpretation. | Independent per-route binary state with `attack_rate` initialization and symmetric `p_stay` transitions; static mask. With defaults, the first emitted disrupted probability is 0.40 and the long-run disrupted fraction tends to 0.50, not 0.25. | **HOLD/DEFER.** Binary `MarkovAttack` cannot silently replace the canonical four-state slot. Recover the canonical four-state state meanings, transition/emission rule, initialization, and meaning of 25%; then implement that exact family minimally or retain the hold. |
| `Adaptive` | Causal targeting based on aggregate route usage in a finite retrospective window; invariant to ordering at fixed counts. | Mechanism matches: target probabilities are `min(base + strength * usage_share, 0.9)` from selections through `t-1`. Defaults are window 100/base 0.25/strength 0.5; no scientific preset freezes the Tier-1 values. | **MINIMAL CONFIG CORRECTION REQUIRED.** Freeze an explicit structured configuration and test the count-based causal invariants. Do not rely on string resolution or constructor defaults as scientific provenance. |
| `OnlineAdaptive` | Canonical 25% continuously reactive targeting with `gamma=0.97` and softmax selection, under the approved completed-history chronology. | Current family uses response delay, global burst draws, last-selected-route targeting, and background attacks. It has no gamma/softmax implementation. Conditional RNG consumption and burst carry-over make cross-policy innovation alignment ambiguous. | **HOLD/DEFER.** The delay/burst family cannot substitute for the canonical gamma/softmax slot. Recover the decayed statistic, softmax rule/temperature, initialization, probability semantics, and chronology; then implement that family minimally with addressable innovations or retain the hold. |

## Manager adjudication

1. The no-pooling boundary is retained: any future F-08 Tier-1 campaign is a versioned treatment and may not be described as reproducing or pooled with historical rows without data-producing provenance. Versioning does **not** authorize substitution of a different scenario family under a canonical scenario name.
2. The accepted semantic distinction is:
   - `Markov`: prior availability state only, never routing history;
   - `Adaptive`: finite-window aggregate usage counts, order-invariant at fixed counts;
   - `OnlineAdaptive`: completed-history recency/order reactivity, distinguishable at fixed counts.
3. Pairing must distinguish exogenous and endogenous threats:
   - `Markov` shares an identical realized mask across policies within a block;
   - `Adaptive` and `OnlineAdaptive` share the same policy-independent frame/route innovation tape, but each policy produces its own history-conditioned realized mask and mask hash.
4. The proposed contract language requiring one shared realized threat mask across every policy is therefore **rejected for the two adaptive scenarios**. Identical adaptive masks would erase the scientific treatment; unrelated randomness would destroy pairing. Common innovations with policy-conditioned masks is the minimum coherent contract.
5. Q-03 may freeze explicit scenario IDs, versioned parameter dictionaries, chronology, initialization, innovation mapping, and the no-pooling boundary only after Q-02 either recovers faithful canonical semantics or records a hold. It must not infer values from legacy string resolution.

## Findings

### BLOCKER

1. No complete structured scientific scenario configuration exists at PR #2 head.
2. Legacy string resolution can map `attack_intensity=1.0` into a scenario base rate and therefore cannot be used for the scientific launch.
3. Canonical four-state `Markov` semantics and canonical gamma/softmax `OnlineAdaptive` semantics have not yet been recovered or implemented; both scenarios are held.
4. `OnlineAdaptive` does not yet guarantee a fixed policy-independent innovation schedule suitable for the approved adaptive pairing contract.
5. Contract-specific deterministic, causality, distinguishing-invariant, and cross-policy pairing tests remain to be added and run.

### DEBT

1. Historical data-producing provenance remains debt for pooling/equivalence, but the missing canonical process definitions are blockers for accepting the current binary/delay-burst implementations in the approved scenario slots.
2. Causal event rows carry the realized trajectory hash through completion/artifact joins rather than on each event row.
3. Scenario aliases alter threat seeds; Q-03 must freeze canonical IDs.
4. Per-run identity currently includes queue-level configuration; this directly violates the proposed completed-run identity rule and is a bounded Q-04 readiness blocker, not permission for architecture redesign.

### OPTIONAL

1. Redundant internal state snapshots are optional; the minimum state/propensity diagnostics required to reconstruct and test the declared transition or targeting rule are required.
2. Spatial failure, hardware-calibrated attacks, and matched-severity sensitivity analyses remain outside Q-02/Q-03/Q-04.

## Next action

1. Perform a bounded source/provenance reconciliation for the canonical four-state `Markov` and gamma/softmax `OnlineAdaptive` definitions; do not revalidate the historical paper or broaden into new threats.
2. Revise the Q-02 scientific decision to either freeze evidence-backed canonical definitions or keep each unresolved scenario held.
3. Obtain a second independent ULTRA review of the revised design before any production-code change.
4. If accepted, implement only the smallest approved scenario/config/innovation changes on top of frozen PR #2, then run contract-specific tests and independent review.
5. Advance to Q-03 only after Q-02 passes.

## Explicitly unchanged

- PR #2 general architecture.
- Manuscript and reviewer prose.
- Historical validated results.
- Topology, route, reward, allocator, replay, and policy architecture.
- F-08/F-09/Q-05 scientific execution state.
