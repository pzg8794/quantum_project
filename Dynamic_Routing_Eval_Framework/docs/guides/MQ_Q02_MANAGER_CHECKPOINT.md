# M-Q Q-02 manager checkpoint

## Status

- **Slice:** Q-02 — F-08 scientific-semantic closure for `Markov`, `Adaptive`, and `OnlineAdaptive`.
- **SDLC stage:** DESIGN and source-inspection evidence integrated; **not accepted**.
- **PR:** [pzg8794/quantum_project#2](https://github.com/pzg8794/quantum_project/pull/2), frozen baseline `d97dbde30241cd04b561cdd187a3b622a35b7592`.
- **Manager branch:** `codex/mq-q02-integration`.
- **Scientific-definition worker:** ULTRA / Extra High, source checkpoint `88849da91c5aed99215be94a5486c1425f6c7ac1`, integrated as `28d727e7`.
- **Code/config inspection worker:** HIGH, source checkpoint `a7e2fc69eac684abcccbe5cf04080a205244e6f7`, integrated as `48a09a33`.
- **Runtime verification:** `20 passed in 60.80s` for the bounded scenario/config/causality selection listed in `Q02_SCENARIO_CODE_INSPECTION.md`. This is technical evidence, not scientific validation.

No production code, test code, manuscript, validated corpus, or F-09/Q-05 run changed in this checkpoint.

## Integrated intended-versus-implemented verdict

| Scenario | Intended Tier-1 scientific property | PR #2 behavior | Disposition before Q-02 acceptance |
|---|---|---|---|
| `Markov` | Exogenous, first-order, positively persistent route unavailability; independent of route-selection history. | Independent per-route binary state with `attack_rate` initialization and symmetric `p_stay` transitions; static mask. With defaults, the first emitted disrupted probability is 0.40 and the long-run disrupted fraction tends to 0.50, not 0.25. | **MINIMAL CONFIG/CODE CLARIFICATION REQUIRED.** A versioned Tier-1 configuration must state initialization and transition semantics explicitly and must not label `attack_rate=0.25` as a 25% stationary rate. Historical four-state wording is not reproduced by this implementation and must not be imported into the new contract. |
| `Adaptive` | Causal targeting based on aggregate route usage in a finite retrospective window; invariant to ordering at fixed counts. | Mechanism matches: target probabilities are `min(base + strength * usage_share, 0.9)` from selections through `t-1`. Defaults are window 100/base 0.25/strength 0.5; no scientific preset freezes the Tier-1 values. | **MINIMAL CONFIG CORRECTION REQUIRED.** Freeze an explicit structured configuration and test the count-based causal invariants. Do not rely on string resolution or constructor defaults as scientific provenance. |
| `OnlineAdaptive` | Causal online recency/order-sensitive targeting based on completed routing history. | Current family uses response delay, global burst draws, last-selected-route targeting, and background attacks. It has no gamma/softmax implementation. Conditional RNG consumption and burst carry-over can make cross-policy innovation alignment ambiguous. | **MINIMAL CODE/CONFIG CORRECTION REQUIRED.** Select this existing delay/burst/recency family for the new versioned run or defer it; do not combine it with historical gamma/softmax prose. If retained, make all effective parameters explicit and consume a fixed frame/route-addressed innovation schedule without same-frame lookahead. |

## Manager adjudication

1. The new F-08 Tier-1 campaign is a **newly versioned treatment**, not an asserted reproduction of historical manuscript attack rows. Historical process provenance remains debt and prevents pooling or equivalence claims; it does not make the new controlled run impossible.
2. The accepted semantic distinction is:
   - `Markov`: prior availability state only, never routing history;
   - `Adaptive`: finite-window aggregate usage counts, order-invariant at fixed counts;
   - `OnlineAdaptive`: completed-history recency/order reactivity, distinguishable at fixed counts.
3. Pairing must distinguish exogenous and endogenous threats:
   - `Markov` shares an identical realized mask across policies within a block;
   - `Adaptive` and `OnlineAdaptive` share the same policy-independent frame/route innovation tape, but each policy produces its own history-conditioned realized mask and mask hash.
4. The proposed contract language requiring one shared realized threat mask across every policy is therefore **rejected for the two adaptive scenarios**. Identical adaptive masks would erase the scientific treatment; unrelated randomness would destroy pairing. Common innovations with policy-conditioned masks is the minimum coherent contract.
5. Q-03 must freeze explicit scenario IDs, versioned parameter dictionaries, chronology, initialization, innovation mapping, and no-pooling boundary. It must not infer values from legacy string resolution.

## Findings

### BLOCKER

1. No complete structured scientific scenario configuration exists at PR #2 head.
2. Legacy string resolution can map `attack_intensity=1.0` into a scenario base rate and therefore cannot be used for the scientific launch.
3. `OnlineAdaptive` does not yet guarantee a fixed policy-independent innovation schedule suitable for the approved adaptive pairing contract.
4. The exact effective OnlineAdaptive burst duration and target multiplier are hard-coded rather than exposed in the resolved parameter manifest.
5. Contract-specific deterministic, causality, distinguishing-invariant, and cross-policy pairing tests remain to be added and run.
6. Independent Q-02 scientific review has not yet occurred.

### DEBT

1. Historical data-producing scenario provenance remains unresolved; the new run must not be described as exact historical reproduction or pooled with historical rows.
2. Causal event rows carry the realized trajectory hash through completion/artifact joins rather than on each event row.
3. Scenario aliases alter threat seeds; Q-03 must freeze canonical IDs.
4. Per-run identity currently includes queue-level configuration; this violates the proposed completed-run identity rule and is a Q-03/Q-04 readiness issue, not permission for architecture redesign.

### OPTIONAL

1. Internal scenario-state diagnostics would improve diagnosis but are not needed if the immutable mask, inputs, parameters, source hash, and common innovation identity are sufficient to reproduce the run.
2. Spatial failure, hardware-calibrated attacks, and matched-severity sensitivity analyses remain outside Q-02/Q-03/Q-04.

## Next action

1. Obtain independent ULTRA scientific review of this integrated Q-02 design and its minimal-correction classification.
2. If accepted, implement only the smallest approved scenario/config/innovation changes on top of frozen PR #2.
3. Run contract-specific Q-02 tests and obtain separate independent review.
4. Advance to Q-03 only after Q-02 passes.

## Explicitly unchanged

- PR #2 general architecture.
- Manuscript and reviewer prose.
- Historical validated results.
- Topology, route, reward, allocator, replay, and policy architecture.
- F-08/F-09/Q-05 scientific execution state.
