# M-Q Q-02 Canonical Scenario Provenance

## Scope and decision rule

This is a bounded source/provenance inspection from manager checkpoint
`3531b47dccc555df04d00ca3062d304985a18ae2`. It does not revalidate paper
results or execute F-09/Q-05. The inspection covered all fetched reachable Git
history, local and remote branches, tags, and committed source, configuration,
logs, notebooks, and documentation. No repository tags exist at this
checkpoint.

Evidence is ranked as follows:

1. an executable implementation tied by a source/configuration manifest to a
   data-producing run;
2. executable source and committed configuration without that run tie;
3. committed run logs without a complete source/configuration manifest;
4. prose-only descriptions.

The authoritative Quantum decision record explicitly keeps the exact simulator
parameters and process rows provenance-pending and requires recovery of the
generator class/version, defaults, overrides, effective rates, and exact
semantics before reuse
(`QuantumFaultTolerant@0bcc913bc5a28b1e1116245cf692989a9ec98aae:updates/F06_THREAT_TAXONOMY_PHYSICAL_GROUNDING_DECISION_RECORD.md:3-5`,
`:115-144`, `:172-180`). It defines only the conceptual classes: temporally
persistent Markov disruption, route-history-dependent Adaptive targeting, and
continuously reactive OnlineAdaptive targeting (`:57-73`). The validated
staging text supplies the labels `25% four-state`, `25% high-usage, w=50`, and
`25%, gamma=0.97, softmax`, but not complete executable semantics
(`QuantumFaultTolerant@0bcc913bc5a28b1e1116245cf692989a9ec98aae:ICNP_VENUE_PREP/STUDY_DESIGN_VALIDATED_STAGING.tex:149-151`). Those records are
authoritative decisions, but they are prose rather than data-producing source.

## Reachable implementation families

### Deleted but reachable candidate family

Commit `2594f7a50a29129c52cd8345e32bb877c30d9348` added executable candidates in
`Eval_Framework_for_Scenarios/src/quantum_environment.py` and a runner in
`Eval_Framework_for_Scenarios/src/quantum_experiments_updated.py`. Equivalent
copies occur in the EXPNeuralUCB, Hybrid MABs, Models, and updated scenario
trees. Commit `884cb470ab0d1e0d297a81e479a717fbe27901df` later deleted this framework.
No tag or committed provenance manifest designates this family as the canonical
generator for the authoritative Quantum results.

The candidate runner defaults `attack_intensity=1.0`; configures Markov and
OnlineAdaptive target count as
`max(1, min(2, round(2 * attack_intensity)))`; configures Adaptive with `w=50`
and `sticky_p=0.7`; and configures OnlineAdaptive with `w=50`, `gamma=0.97`, and
temperature `0.5`
(`2594f7a50a29129c52cd8345e32bb877c30d9348:Eval_Framework_for_Scenarios/src/quantum_experiments_updated.py:16-20`,
`:52-74`). It derives an experiment seed using Python's process-salted `hash()`
(`:83-95`). The environment pre-generates the complete attack pattern without
passing an actual algorithm selection trace
(`2594f7a50a29129c52cd8345e32bb877c30d9348:Eval_Framework_for_Scenarios/src/quantum_environment.py:398-408`). Therefore the runner uses the generators'
synthetic sticky trace fallback for Adaptive and OnlineAdaptive rather than a
closed-loop policy trace.

### Later data-adjacent family

Commit `f17b5eb1d25f500064695625ed24f814b925c4be` contains run logs naming Markov,
Adaptive, and OnlineAdaptive at `Rate:0.25`; examples are lines 359-373,
530-544, and 701-715 of
`Dynamic_Routing_Eval_Framework/daqr/config/quantum_logs/quantum_exps-Dynamic(paper7)_alloc-all_envs-5_attacks-10_10-5_runs-S1T_20260130_log.txt`, with
scenario summaries at lines 1103-1191. The same commit's configuration maps all
three named strategies to `attack_intensity`, not to the separate base
`attack_rate=0.25`
(`f17b5eb1d25f500064695625ed24f814b925c4be:Dynamic_Routing_Eval_Framework/daqr/config/experiment_config.py:26-26`,
`:441-447`, `:1104-1113`).

That commit's executable definitions are incompatible with the authoritative
labels:

- Markov is one independent binary attacked/not-attacked process per route with
  default `attack_rate=0.25` and `p_stay=0.7`, not a four-state chain
  (`f17b5eb1d25f500064695625ed24f814b925c4be:Dynamic_Routing_Eval_Framework/daqr/core/attack_strategy.py:122-150`).
- Adaptive defaults to `adaptation_window=100` and
  `adaptation_strength=0.5`, then uses
  `min(base_rate + strength * recent_share, 0.9)` independently per route
  (`:157-213`).
- OnlineAdaptive defaults to response delay `5` and burst probability `0.3`;
  it has neither exponential decay nor softmax selection (`:220-271`).

The logs do not record a source commit, source hash, transition matrix,
window/strength, gamma, temperature, target count, chronology, or RNG contract.
Co-commitment of logs and source is not an execution manifest. It cannot tie
the deleted candidate family to the logged outputs, and the data-adjacent
family itself contradicts the canonical labels.

## Markov: recovered candidates and gaps

### Executable candidate

The deleted candidate has four integer latent states when there are four
routes. Its default transition matrix is

```text
[[0.35, 0.15, 0.35, 0.15],
 [0.30, 0.20, 0.30, 0.20],
 [0.35, 0.15, 0.35, 0.15],
 [0.30, 0.20, 0.30, 0.20]]
```

and its default initial distribution is uniform
(`2594f7a50a29129c52cd8345e32bb877c30d9348:Eval_Framework_for_Scenarios/src/quantum_environment.py:41-68`). On each frame it:

1. draws a Bernoulli gate using `attack_rate`;
2. if active, samples `k_attacks` unavailable route indices without replacement
   from the current latent state's transition row;
3. independently samples the next latent state from the same transition row
   after emitting the mask (`:70-77`).

Thus this executable is not a direct four-state chain whose state is simply the
attacked route. The source gives no semantic names for states `0..3`; it only
aligns the state-space dimension with the number of routes. RNG call order is
initial-state categorical draw, then per frame gate draw, conditional target
categorical draw, and next-state categorical draw. This specifies NumPy API
call order, not an implementation-independent count of underlying random bits.

### Incompatible prose-only candidate

The reachable implementation thread instead describes a direct chain: initialize
from `[0.25, 0.25, 0.25, 0.25]`, use the prior attacked path as the state, sample
the next `target_path` from that transition row, and make exactly that path
unavailable
(`2594f7a50a29129c52cd8345e32bb877c30d9348:Eval_Framework_for_EXPNeuralUCB/md/EXPNeuralUCB Paper Code Implementation-Thread.md:4892-4917`). This is prose/code-block material, not the imported executable used by a committed run. It conflicts with the executable's separate emission and state-transition draws.

### Meaning of 25%

For four routes, the executable class defaults `k_attacks=1` and
`attack_rate=1.0`, which makes exactly one route unavailable per frame: 25% of
route-frame cells. By contrast, setting `attack_rate=0.25` with `k_attacks=1`
means one route is attacked on 25% of frames, or 6.25% of route-frame cells in
expectation. The candidate runner's defaults produce `k_attacks=2` at
`attack_intensity=1.0`, or 50% of routes per active frame. No authoritative
record chooses among these meanings or ties one to validated output.

### NOT FOUND

- authoritative meanings for the four state labels;
- a unique canonical choice between direct-chain emission and separate
  transition-row emission;
- a source/configuration manifest tying either definition and one 25% meaning
  to validated output.

## OnlineAdaptive: recovered candidates and gaps

### Executable candidate

The deleted executable candidate initializes history to empty and decayed counts
to an all-zero vector (`2594f7a50a29129c52cd8345e32bb877c30d9348:Eval_Framework_for_Scenarios/src/quantum_environment.py:160-179`). After observing selected route `a`, it applies
`counts <- gamma * counts` and then increments `counts[a]` by one (`:181-192`).
The runner supplies `gamma=0.97`, softmax temperature `0.5`, and `w=50`
(`2594f7a50a29129c52cd8345e32bb877c30d9348:Eval_Framework_for_Scenarios/src/quantum_experiments_updated.py:68-74`).

For an active attack frame, positive-temperature selection computes
`logits = counts / temperature`, subtracts the maximum, exponentiates and
normalizes, then samples `k` distinct targets without replacement. At zero
counts all logits are equal, so the target distribution is uniform
(`2594f7a50a29129c52cd8345e32bb877c30d9348:Eval_Framework_for_Scenarios/src/quantum_environment.py:194-229`). There is no explicit warmup. In batch generation, the attack mask for frame `t` is sampled before `trace[t]` is observed, so the attack uses completed history through `t-1`; frame zero uses uniform scores (`:259-265`).

RNG consumption is path-dependent. With a supplied trace, each frame consumes
the attack-rate gate and, only when active, one `rng.choice` target operation.
With no supplied trace, the implementation first consumes one initial
`rng.integers`, then one sticky Bernoulli per trace frame plus a conditional
`rng.integers` whenever the sticky branch fails; only after constructing the
entire trace does it consume attack gate/target operations (`:242-265`). This is
the exact API-level order. It is not a stable cross-version bit-consumption
guarantee.

### Meaning of 25% and provenance gap

With four routes, `k=1` and `attack_rate=1.0` means one unavailable route per
frame, or 25% spatial occupancy. With `attack_rate=0.25`, `k=1` means 6.25% of
route-frame cells in expectation. The candidate runner instead computes `k=2`
when its default intensity is `1.0`. Moreover, its pre-generated batch path uses
synthetic sticky usage, whereas the class documentation identifies the online
hooks as the realistic closed-loop path (`quantum_environment.py:146-158`). No
manifest chooses the canonical path, 25% interpretation, or RNG stream and ties
it to data-producing output. The later committed output logs sit beside the
incompatible delay/burst implementation.

### NOT FOUND

- a data-producing provenance tie for the gamma/softmax executable;
- an authoritative choice of spatial 25% versus 25% event cadence;
- an authoritative choice between actual closed-loop observations and the
  runner's pre-generated synthetic trace;
- a stable RNG engine/version and source-hash manifest for a canonical run.

## Adaptive: remaining candidate parameters and gaps

The deleted executable candidate provides the following exact parameter set
beyond a putative base `.25` and `w=50`:

- one target route per active frame;
- event gate `attack_rate`, default `1.0`;
- `sticky_p=0.7`, used only to synthesize fallback usage when no trace is
  supplied;
- completed-history window `[max(0, t-w), t)`;
- deterministic `np.argmax` target choice, including first-index tie behavior;
- at `t=0`, target `trace[0]` because no completed history exists;
- no adaptation strength and no probability cap
  (`2594f7a50a29129c52cd8345e32bb877c30d9348:Eval_Framework_for_Scenarios/src/quantum_environment.py:82-141`).

This candidate has an important chronology split: a supplied offline trace uses
the current `trace[0]` at frame zero, while the candidate runner supplies no
trace and pre-generates a synthetic usage path before any masks. Consequently,
it is not evidence of a genuinely online attacker reacting to the evaluated
policy. As with Markov and OnlineAdaptive, `attack_rate=1.0` plus one target is
25% spatial occupancy for four routes; `attack_rate=0.25` is 25% event cadence
and 6.25% expected route-frame occupancy. The later data-adjacent family instead
uses `w=100`, strength `0.5`, cap `0.9`, and independent per-route Bernoulli
draws. No provenance record ties the deleted `w=50` candidate and its remaining
parameters to validated output.

### NOT FOUND

- a source/configuration manifest selecting this exact parameter set for a
  canonical run;
- an authoritative 25% interpretation;
- an authoritative resolution of frame-zero targeting and offline synthetic
  trace versus actual policy history.

## Classification

- **BLOCKER:** Markov state meanings, emission rule, and 25% meaning are not
  uniquely recoverable from data-producing provenance.
- **BLOCKER:** OnlineAdaptive gamma/softmax mechanics are recoverable only as an
  untied executable candidate; canonical trace mode, 25% meaning, and RNG
  provenance remain unresolved.
- **BLOCKER:** Adaptive's remaining parameters are recoverable only as an
  untied candidate and conflict with the later data-adjacent implementation.
- **DEBT:** Future data-producing runs need a manifest containing commit/source
  hash, complete effective configuration, RNG engine/version and seed derivation,
  scenario chronology, and output identifiers.
- **DEBT:** Python `hash()` seed derivation in the deleted runner is not stable
  across ordinary interpreter processes.
- **OPTIONAL:** Preserve the deleted candidate commit as design input only after
  an owner explicitly chooses semantics; do not relabel it as historical output
  provenance.

## Final dispositions

- **Markov — NOT RECOVERED—HOLD (BLOCKER).**
- **OnlineAdaptive — NOT RECOVERED—HOLD (BLOCKER).**
- **Adaptive — NOT RECOVERED—HOLD (BLOCKER).**
