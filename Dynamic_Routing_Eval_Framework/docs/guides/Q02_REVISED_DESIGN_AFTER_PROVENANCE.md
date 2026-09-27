# Q-02 revised design after bounded provenance reconciliation

## Decision state

- **Slice:** Q-02 — F-08 scientific-semantic closure.
- **Stage:** revised DESIGN, before the required second independent review.
- **Source baseline:** frozen Quantum PR #2 head `d97dbde30241cd04b561cdd187a3b622a35b7592`.
- **Integrated review:** `Q02_INDEPENDENT_REVIEW.md` — `REVISE BEFORE DEV`.
- **Bounded provenance search:** `Q02_CANONICAL_SCENARIO_PROVENANCE.md`.
- **Development authorization:** none.
- **Q-03/Q-04 authorization:** none.

The bounded repository-history search did not recover a unique canonical implementation tied to the validated outputs for any of the three disputed scenarios. Q-02 therefore must preserve the complete-scenario rule by holding unresolved scenario slots rather than relabeling a convenient implementation.

## Revised dispositions

| Scenario | Evidence recovered | Revised disposition | Reason |
|---|---|---|---|
| `Markov` | A deleted executable four-state candidate and a conflicting prose candidate were found. State meanings, emission rule, initialization, and the meaning of 25% are not uniquely selected by data-producing provenance. The later data-adjacent implementation is binary and incompatible with the four-state label. | **NOT RECOVERED — HOLD** | Choosing either reachable candidate would guess which family generated or defines the approved treatment. The current binary class cannot substitute. |
| `Adaptive` | A deleted candidate uses `w=50`, one targeted route, deterministic `argmax`, and a synthetic sticky fallback; the later data-adjacent implementation uses `w=100`, strength `0.5`, cap `0.9`, and independent route-wise draws. No manifest ties either to the canonical result. | **NOT RECOVERED — HOLD** | The previous minimal-config disposition is withdrawn: base `.25` and `w=50` do not resolve targeting, cold-start, 25% meaning, or trace mode. |
| `OnlineAdaptive` | A deleted candidate contains `gamma=0.97`, temperature `0.5`, decayed counts, and softmax targeting, but its runner pre-generates a synthetic trace and no manifest ties it to data-producing output. The later class is a different delay/burst family. | **NOT RECOVERED — HOLD** | Gamma/softmax mechanism evidence is useful design input but not enough to declare the canonical treatment or its 25%/trace/RNG semantics. The delay/burst class cannot substitute. |

## Retained scientific decisions

The following remain accepted because they do not depend on choosing among the unresolved candidates:

1. `Markov` must be exogenous to routing history and may share one identical realized mask across paired policies.
2. `Adaptive` and `OnlineAdaptive` must remain causal: frame `t` can use completed routing history only through `t-1`.
3. History-dependent scenarios must use common addressable exogenous innovations with policy-conditioned realized masks and per-policy mask hashes; identical adaptive masks are invalid.
4. New results cannot be pooled with or described as reproducing historical scenario rows without a data-producing provenance tie.
5. Legacy string/default scenario resolution is forbidden for scientific execution.

## Consequence for the campaign

The canonical contract requires the complete approved scenario set. Three held scenario slots mean the Tier-1 scenario axis cannot yet be frozen or executed completely. Q-03 and Q-04 therefore remain blocked; silently dropping the held scenarios would violate the board and produce an incomplete campaign.

## Genuine owner decision

The repository evidence is exhausted. Progress now requires one of these explicit owner actions:

1. **Provide or identify missing data-producing provenance** that selects the canonical definitions; M-Q then verifies and revises Q-02 without changing the approved scenario set.
2. **Authorize a new canonical scenario contract** using explicitly chosen, versioned semantics from the recovered candidates, with a strict non-equivalence/no-pooling statement. This changes the approved canonical configuration and must not be presented as historical recovery.
3. **Accept the hold** and stop the current F-08 Tier-1 campaign as incomplete until the missing definitions are available.

M-Q does not recommend silently using current defaults or adding new scenario names. If the owner chooses a new canonical contract, the strongest available design input is the deleted four-state / `w=50` / gamma-softmax family, corrected to use actual completed policy history, deterministic addressable innovations, explicit 25% semantics, and stable seed derivation. Those corrections would be a newly approved treatment, not a recovered historical one.

## Findings

### BLOCKER

- No unique canonical, data-producing definition for the three disputed scenario slots.
- Complete approved scenario axis cannot be frozen while those slots are held.
- No Dev, Q-03, Q-04, or Q-05 work is scientifically authorized from this state.

### DEBT

- Future scientific runs require source/config hashes, complete effective parameters, stable RNG/seed identity, chronology, and output linkage.
- The deleted candidate's Python `hash()` seed derivation is process-dependent and cannot be reused as a scientific identity rule.

### OPTIONAL

- Spatial failures, hardware-calibrated adversaries, and severity sensitivity remain outside this campaign.

## Second-review question

The second independent reviewer must decide whether the three HOLD dispositions and the owner-decision boundary follow from the governing complete-scenario rule and the bounded provenance evidence. The reviewer must not select candidate semantics on the owner's behalf or authorize development.
