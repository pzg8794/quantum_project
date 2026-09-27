# Q-02 second independent scientific review

## Review identity and verdict

- **Role:** second independent ULTRA scientific reviewer for M-Q Q-02.
- **Manager checkpoint:** `29b449bd2a1ea4cd972b4572f55017324f04d776`.
- **Frozen PR #2 source baseline:** `d97dbde30241cd04b561cdd187a3b622a35b7592`.
- **Integrated artifacts reviewed:** `Q02_REVISED_DESIGN_AFTER_PROVENANCE.md`, `Q02_CANONICAL_SCENARIO_PROVENANCE.md`, `Q02_INDEPENDENT_REVIEW.md`, and `MQ_Q02_MANAGER_CHECKPOINT.md`.
- **Additional evidence:** only the bounded immutable Git source/history needed to check the provenance claims and the cited authoritative Quantum records at `0bcc913bc5a28b1e1116245cf692989a9ec98aae`.
- **Verdict:** **PASS**.

This PASS accepts the revised design's three `NOT RECOVERED — HOLD` dispositions and owner-decision boundary. It does **not** accept any candidate as canonical, authorize development, open Q-03/Q-04, validate historical results, or authorize F-09/Q-05.

## Required decisions

| Review question | Decision | Scientific basis |
|---|---|---|
| Is the bounded provenance search sufficient and credible? | **YES, for its declared repository-history boundary.** | The search distinguishes executable candidates, data-adjacent source/logs, and authoritative prose; it does not claim that missing external evidence cannot exist. All currently fetched local/remote refs cover 579 reachable commits, no tags exist, the relevant source blobs reduce to the two conflicting implementation families reported, and neither historical family has a run-linked source/configuration manifest. |
| Are all three `NOT RECOVERED — HOLD` dispositions required? | **YES.** | No scenario has a complete process definition selected by data-producing provenance. The complete-approved-scenario rule forbids filling any slot with a convenient but unselected implementation. |
| Should `Adaptive` remain minimal-config-correctable? | **NO.** | The missing information is mechanism-level, not merely `w=100` versus `w=50`: the deleted candidate is a gated, single-target deterministic `argmax` process, while the later family makes independent route-wise draws from base-plus-usage probabilities. Base `.25` and `w=50` do not select between them or settle cold start, 25% meaning, or trace mode. |
| Is the owner boundary genuine and exhaustive? | **YES, at the decision-class level.** | For each held slot, the only legitimate paths are evidence-backed recovery, explicit authorization of a new non-equivalent canonical contract, or continued hold. These choices may be mixed by scenario, but the present campaign cannot resume until every approved slot has a complete authorized definition. |
| Is any development, Q-03, or Q-04 allowed now? | **NO.** | Q-02 has correctly resolved to holds rather than executable definitions. A PASS on the hold design is not a PASS on scenario readiness. The complete Tier-1 axis cannot be frozen, implemented, or executed while any required slot remains held. |

## Provenance assessment

The bounded search is credible because its conclusions are proportional to its evidence:

1. Commit `2594f7a50a29129c52cd8345e32bb877c30d9348` contains the deleted four-state / `w=50` / decay-softmax candidate family and its runner. The runner uses `attack_intensity=1.0`, process-dependent Python `hash()`, and pre-generated synthetic traces rather than a manifest-linked closed-loop data-producing path.
2. Commit `f17b5eb1d25f500064695625ed24f814b925c4be` contains data-adjacent logs and the later binary-Markov / probabilistic-Adaptive / delay-burst-OnlineAdaptive family. The logs name scenarios and rate `.25` but do not identify a commit, source hash, complete effective parameters, chronology, or RNG contract.
3. Reachable historical blobs show those as materially different implementation families, with copies and incremental variants rather than a third manifest-linked canonical generator.
4. The authoritative decision record at `QuantumFaultTolerant@0bcc913bc5a28b1e1116245cf692989a9ec98aae` approves the conceptual five-regime taxonomy while explicitly leaving exact Markov, Adaptive, and OnlineAdaptive process cells provenance-pending and forbidding their freeze until the data-producing implementation/configuration is traced.
5. The validated staging labels identify `25% four-state`, `25% high-usage, w=50`, and `25%, gamma=0.97, softmax`, but those labels do not resolve the competing executable semantics.

The conclusion is therefore bounded: **canonical definitions were not recovered from reachable repository evidence**. It is not the broader claim that no missing notebook, external run package, Drive artifact, or owner record can exist. Any such item must be supplied or identified and then verified before it changes a hold.

## Scenario findings

### Markov — hold required

The deleted executable and the prose candidate disagree about whether the latent state directly denotes the attacked route or instead parameterizes a separate emission draw. The current PR #2 class is a per-route binary process and cannot substitute for either four-state interpretation. State meanings, initialization, transition/emission semantics, target count, and the meaning of 25% remain unresolved. `Markov` is **NOT RECOVERED — HOLD**.

### Adaptive — hold required

The first independent review's minimal-config disposition was reasonable before the bounded history search exposed a conflicting `w=50` executable candidate. That new evidence defeats the premise that the current class already represents the selected family and needs only a window override. Deterministic single-target `argmax` and independent route-wise probabilistic attacks produce different masks, severities, tie behavior, innovation requirements, and policy contrasts. Q-03 would be choosing a treatment, not freezing a recovered parameter set. `Adaptive` is **NOT RECOVERED — HOLD**.

### OnlineAdaptive — hold required

The deleted gamma/softmax implementation is useful design evidence, but its runner uses a synthetic pre-generated trace and does not link its configuration to the validated output. The later delay/burst class is a different family and cannot occupy the gamma/softmax slot. Trace source, initialization, target count, temperature, 25% meaning, chronology, and addressable RNG semantics remain incomplete. `OnlineAdaptive` is **NOT RECOVERED — HOLD**.

## Owner decisions for Viber to escalate

Viber must escalate one explicit disposition for **each** held scenario; different scenarios may use different dispositions, but the campaign remains blocked until all three are resolved:

1. **Identify data-producing provenance.** Provide the exact run-linked source/configuration evidence selecting the canonical process. M-Q must verify the tie and revise Q-02; a filename, co-committed log, prose label, or remembered default is insufficient.
2. **Authorize a new canonical contract.** Explicitly approve a new versioned, non-equivalent treatment and the strict no-pooling/no-reproduction boundary. The approval must select complete semantics rather than merely name a recovered class:
   - `Markov`: state meanings, initialization, transition and emission rules, target count/coupling, and exact 25% interpretation.
   - `Adaptive`: targeting family, `w=50` chronology, gate/occupancy meaning of 25%, cold-start/tie behavior, trace source, and any strength/cap or single-target rule.
   - `OnlineAdaptive`: completed-history statistic, `gamma=0.97` update, softmax temperature/sampling, initialization/warm-up, target count, trace source, and exact 25% interpretation.
   - Cross-cutting: stable versioned IDs, source/config hashes, addressable innovation mapping, seed derivation, per-policy realized-mask identity, and explicit historical non-equivalence.
3. **Accept the hold.** Leave unresolved slots held and stop the current F-08 Tier-1 campaign as incomplete until evidence or a new authorization is available.

Viber must not translate option 2 into a semantic choice on the owner's behalf. It may prepare bounded alternatives and consequences, but the owner must authorize the selected contract. Supplying provenance for only some slots or approving only part of a new contract does not unlock development or the complete campaign.

## Integration findings

These record-level inconsistencies do not overturn the scientific PASS, but they must be reconciled by the manager before Q-02 is marked accepted:

1. `MQ_Q02_MANAGER_CHECKPOINT.md` still labels `Adaptive` as **MINIMAL CONFIG CORRECTION REQUIRED** and its blocker list names only the Markov and OnlineAdaptive definition gaps, while its status, provenance entry, and next action acknowledge three holds. The manager record must be synchronized to the revised disposition; the stale row is not authorization.
2. `Q02_REVISED_DESIGN_AFTER_PROVENANCE.md` says exogenous `Markov` “may” share an identical realized mask. The accepted pairing rule in the manager checkpoint and first independent review is stronger: paired policies **must** share the same realized exogenous Markov mask within a block. The permissive wording must not weaken that requirement.
3. `MQ_Q02_MANAGER_CHECKPOINT.md` says to advance to Dev/Q-03 only after Q-02 passes. This review passes the **hold design**, not scenario readiness; the preceding owner/provenance gate still controls. No downstream work is authorized by this PASS alone.

## Scope and verification boundary

No production code, tests, manuscript, validated corpus, authority file, scenario semantics, or campaign output was changed. No F-09/Q-05 execution or scientific/runtime test was performed. The review used read-only source/history inspection and created only this review record.
