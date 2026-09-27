# M-Q Q-05 — Independent Default/Fixed Result Review

**Verdict: ACCEPT — the immutable result package and numeric manager summary are supported.**  
**Required report-only correction:** reject the current unqualified `clear hierarchy reversal` wording; use the narrower wording specified below before downstream scientific reuse. This is not a code, configuration, or rerun finding.

## Reviewed scope

- Manager RUN checkpoint: `b6d3ccd4127ba98ed900dcecbbdbf48b2fd0a001`.
- Reviewed execution commit: `fdcefee58adc8df8d802d33f8c079666d115d68d`.
- Frozen Q-03 contract: `7036f0d0044bac576c61093c6361fb6739dfc292`.
- Evidence root: `/Users/pitergarcia/DataScience/Semester4/GA-Work/quantum_experiment_evidence/medium-tier1/default-fixed`.
- Manager report reviewed at SHA-256 `e682051cc8e221f4593b8340e48c1081c215e7a84972f502a56582c622a63804`.
- No scientific cell was rerun. This review parsed the frozen notebooks and raw artifacts, ran the existing PR2 validators read-only, and independently recomputed the result summaries.

## Independent evidence validation

- The existing PR2 `validate_scale_completion` returned `complete=true`, `required_cells=45`, and `completed_cells=45`; it invoked `validate_completion` over every bundle.
- The observed matrix is exactly `3 blocks × 5 threats × 3 policies = 45` unique cells, with no duplicate or extra identity. Every manifest and result records 6,000 frames, scale `m=3`, replay scale `2`, capacity `12,000`, Default allocation `[9] × 10`, and scientific execution.
- Independent event-stream parsing found 270,000 records for each of `PRESELECTION`, `DECISION`, `OUTCOME`, and `UPDATE` (1,080,000 total), in exact frame/phase order. The summed `selected_continuous_payoff` equals the saved final reward in all 45 cells.
- All 450 completion-listed raw-file hashes match. All 45 completion-file hashes match the campaign receipt. All 38 imported-source hashes match the exact blobs at execution commit `fdcefee58adc8df8d802d33f8c079666d115d68d`; every manifest records the empty imported-diff SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- All bundles contain only `attempt-1`; every completion lineage is attempt 1 with no predecessor or restart reason. Every result records one technical attempt, zero performance reruns, completed status, and no error.
- The nine static block/threat pairs (`stochastic`, `markov`, `none`) each share one realized trajectory across policies. The six causal pairs (`adaptive`, `onlineadaptive`) each have three policy-conditioned trajectories under a common block/threat seed.
- The executed notebook has all four code cells executed, zero error outputs, and cell source text identical to the source notebook.

## Evidence hashes

| Artifact | SHA-256 |
|---|---|
| Source notebook | `2f5f922cfdd3b4bd8dc1448a41b54bb28cc1afe8bfe8b656ae8fee7325e9accb` |
| Executed notebook | `b2765cebee8bcf253926814c851808d7b6d7cd6fe20cd804dd2120432fe0f028` |
| Campaign receipt | `dee8b9fc17b2e5d670896deb85beaae8edbc7be19359a42f39cb6a90e72dbbb3` |
| Manager validation | `08325900c5c6a88529bc4ac4b35a692af8880c330055781cee973ddbbae6f202` |
| Independent 45-cell seed registry | `e8a5c5da8ccfd4cec8da227ffb9c726e6b165fa565573597e4835e9395e04812` |
| Independent 45-cell result registry | `1629d12b9d92a90a85d64ca11e35211f6a50357303026296d2d398632e9392a1` |
| Independent raw-file-hash registry | `35b8a93ba7a758bb980d9a8b5c8908d4fb358d9f56e76329e26b0b8982669752` |

The three independent registry hashes use the framework's canonical JSON encoding. Rows are ordered by block, frozen threat order, and frozen policy order; the raw-file registry maps each run ID to its completion-listed file hashes.

## Seed identities

Base seed is `12345`. Values below are the recomputed and manifest-matched `actual_seed` identities. Threat order is `stochastic / markov / adaptive / onlineadaptive / none`; policy order is `Oracle / CEpsilonGreedy / EXPNeuralUCB`. `none` correctly has no consumed threat RNG seed.

| Block | Topology | Physics | Threat seeds | Policy seeds |
|---:|---:|---:|---|---|
| 0 | `95141186` | `3677099253` | `2977384343 / 1886618156 / 3179020907 / 3682436520 / null` | `2101168486 / 4216174246 / 1493395090` |
| 1 | `2176499164` | `4251789290` | `4260623432 / 2817321875 / 3107848502 / 1275566575 / null` | `3063014887 / 3456116897 / 1612489928` |
| 2 | `3063462071` | `4045090693` | `174247565 / 3173820276 / 583865703 / 3542338703 / null` | `1364968051 / 296671616 / 3443119563` |

## Independent result recomputation

Percentages are `policy final payoff / paired Oracle final payoff × 100`, computed directly from the 45 raw `result.json` files. Parentheses are across-block sample SD (`n-1`).

| Threat | CEpsilonGreedy blocks 0/1/2 | Mean (sample SD) | EXPNeuralUCB blocks 0/1/2 | Mean (sample SD) |
|---|---|---:|---|---:|
| Stochastic | 59.954845, 67.727668, 44.981242 | 57.554585 (11.561614) | 3.463674, 3.558688, 4.086244 | 3.702869 (0.335394) |
| Markov | 34.988103, 30.362152, 27.524894 | 30.958383 (3.767160) | 2.097531, 1.895303, 3.041481 | 2.344772 (0.611782) |
| Adaptive | 25.042742, 26.078537, 25.906595 | 25.675958 (0.555079) | 3.325852, 2.747040, 3.982805 | 3.351899 (0.618294) |
| OnlineAdaptive | 62.077577, 47.044744, 59.136238 | 56.086186 (7.967034) | 0.000000, 0.152559, 0.188789 | 0.113783 (0.100190) |
| Baseline (`none`) | 64.551286, 67.101499, 49.428350 | 60.360378 (9.552896) | 3.704055, 3.713137, 4.177600 | 3.864931 (0.270818) |

- The manager validation and report match these block values, means, sample SDs, and rounded renderings.
- The non-Oracle ranking is `CEpsilonGreedy > EXPNeuralUCB` for every threat mean and for all 15 individual block/threat comparisons.
- Across-threat mean-efficiency floors are exactly `25.675957839095904%` for `CEpsilonGreedy` and `0.11378254622632573%` for `EXPNeuralUCB`.
- The sole zero cell is block `0`, `onlineadaptive`, `EXPNeuralUCB`, run ID `12b61bec5565feedede157e04e8050f56e788a42ad94a16c361c025bba14b87a`; its final and mean payoffs are both exactly `0.0`. It remains valid evidence and was not performance-rerun.

## Scientific interpretation

The supported result is narrow: in this one fixed-allocator, 15-node/10-route/550-action anchor, `CEpsilonGreedy` exceeds the tested `EXPNeuralUCB` representative in every threat and block. The run does not isolate node count, does not estimate allocator sensitivity, and does not directly test the pursuit/context-aware-neural family because that family is absent from the frozen matrix. It must not be treated as a controlled scaling curve or pooled with heterogeneous testbeds as one.

The manager report's phrase `clear hierarchy reversal relative to any expectation` is not defensible as a result claim. The Q-03 contract permits the label *reversal* when a paired ordering changes, but this report pins no prior paired comparator or preregistered ordering. A generic expectation is not evidence of a prior hierarchy.

Required replacement wording:

> Within this exact fixed-allocator medium anchor, `CEpsilonGreedy` ranks above `EXPNeuralUCB` in all five threat regimes and all 15 block/threat comparisons. This establishes the observed non-Oracle ordering for the frozen matrix. Describing it as a reversal requires an explicitly pinned prior comparator or preregistered ordering and is not established by this run alone.

Any following reference to node count causing “the reversal” should likewise say node count causing “the observed ordering.” With that report-only correction, the Q-05 Default/fixed result package is **ACCEPTED** for its explicitly bounded scope.
