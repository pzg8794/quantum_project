# Medium-scale engineering preflight — September 26, 2026

**TECHNICAL PREFLIGHT — NOT SCIENTIFIC EVIDENCE**

Status: implementation prepared for independent pre-run audit. No substantive
Tier-1 run or F-09 experiment was launched. The proposed scientific matrix and
the existing manuscript remain unchanged. Final audit and launch approval remain
required.

Implementation: [265b9a758f6584aefb867c67ef5ed57bb8ec3385](https://github.com/pzg8794/quantum_project/commit/265b9a758f6584aefb867c67ef5ed57bb8ec3385),
on `codex/medium-scale-preflight`, based on `gcp-main` at `47757380`.
The only prior working-tree changes were five scratch-file modes, the test-script
mode, and untracked `run_scripts/`; they were not staged or altered.

## Implemented path

- `daqr/core/primary_routes.py`: explicit stable route identities and ordered
  per-hop rates; all integer allocation compositions; exact legacy arithmetic.
- `daqr/core/network_environment.py`: primary context/reward dimensions follow
  route metadata. Four-route callers receive the explicit compatibility metadata;
  other primary route counts without metadata fail closed. External testbed
  reward dispatch remains separate.
- `daqr/campaigns/medium_spec.py`: deterministic layered graph, path catalog,
  seeded ten-profile assignment, actions, domain seeds, and masks.
- `daqr/campaigns/medium_runner.py`: real Oracle, CEpsilonGreedy, and hybrid
  execution using a campaign config that cannot load/save legacy cache state.
  The command-line entry point allows only 1–64 technical frames; 6,000 is
  rejected. It exposes no scientific campaign launch command.
- `daqr/campaigns/medium_trace.py`: PRESELECTION, DECISION, OUTCOME, UPDATE
  events, exclusive attempt directories, and atomic COMPLETION markers with
  hashes, joins, counts, and numeric channel validation.
- `daqr/algorithms/neural_bandits.py`: optional passive hooks around the existing
  selection, feedback, and update path; `event_sink=None` remains the default.
- `daqr/algorithms/base_bandit.py`: campaign-only configurable teardown delay;
  legacy cleanup retains its default. This changes no policy update.

The policy constructor values are inherited from the existing registry/defaults:
hybrid beta=1, gamma=.01, eta=.05; CEpsilonGreedy epsilon=.1, learning rate=.1,
effective expert count=1. Explicit CEpsilonGreedy default keywords were rejected
by its existing base constructor during development; the runner now uses its
registry-compatible `mode` argument and verifies the resulting defaults.

## Exact invariants

The frozen four-route reference uses capacities `(8,10,8,9)`, context dimensions
`(2,2,3,3)`, and action counts `(9,11,45,55)`. Both implicit compatibility
metadata and explicitly supplied metadata produce **exactly identical arrays**
for contexts and every reward value, using `assert_array_equal`, without a
tolerance. A route-order permutation preserves route-associated outputs.

Each proposed block builds 15 nodes, source 0/destination 14, ten unique simple
three-hop routes, all 15 nodes represented, and ten deterministic distinct
ordered profiles. Every route has all 55 nonnegative allocations summing to 9:
550 route–allocation pairs total. There is no padding, truncation, or subsampling.
The graph, profile, action and observation hashes are separately identified.

Protocol root:
`c888aafde667a9a9078697b38b0f6bcf600d99731045e6401e020408aac02265`.
Queue expansion is excluded from this root. Additional prespecified scales or
blocks do not alter existing seed identities.

| Block | Topology SHA-256 | Route-set SHA-256 |
|---|---|---|
| 0 | `64bc08ebdfb0283604cb9c47bce6639ff6c12c8b9084c532e9e3df7f6cf72070` | `94c067f843c9d58954a4598730bfb316aa1c6e05de916eb1cbf6f79917cc2d65` |
| 1 | `c942b16c5fea256d202d05a72a97c8e1ab17c3200b3daf918535b3ffe6a9a63c` | `e99ebedafe6454058bf6f08a757c7fac0ccb73783116de9313e4a1a89a5c6ec7` |
| 2 | `1355244c7f6ead77108871ee20d31a191434e1034bbb4d0ab7e29a6bc6fa3c9d` | `0390afd3bb59542bb635de45b5fb039ec1613eb87f91147e16842c48500bec75` |

## Feedback and logging verification

EXPNeuralUCB remains the proposed **sparse-feedback stress condition**. Logging
retains its actually computed marginal route probability vector with support
and semantics; joint route–allocation propensity remains null. It records q,
the Bernoulli draw, selected availability, masked route feedback, continuous
selected payoff, NeuralUCB target, and whether that update occurred. Valid
zero-feedback and zero-payoff attempts are retained. Policies without sampled
feedback have null fields and explicit reasons, including completion diagnostics.

All six policy/threat combinations passed exact logging-off/on equality for
selected routes/allocations, cumulative outputs, and relevant state. The hybrid
check includes parameters, gradients, covariance, replay, optimizer state and
NumPy/Python/Torch RNG states. A separate six-frame/two-action synthetic unit
fixture exercised actual optimizer steps and blocked/unblocked Bernoulli feedback;
it is not a change to the proposed scientific catalog. Selector/gradient call
counts are identical with logging off/on. No extra selector, gradient, or random
draw is made by the recorder.

Candidate allocation contexts are stored once in `observations.json`; route
physics and full availability masks are separate privileged artifacts. A
preselection event precedes selection and references the static catalog and
history cutoff. Oracle is explicitly privileged. Tests vary the current mask
before the first learner decision and verify unchanged learner selections.

NoAttack is all ones. RandomAttack uses the existing generator with rate .0625;
the exact seeded mask matches a `PCG64` threshold at .0625, has ten columns,
is binary, regenerates identically, and changes with the block seed.

## Identity and completion

Run identity includes protocol/config, topology/routes/actions/physics, all seed
domains, exact mask hash, policy class/mode/defaults, allocator, replay, horizon,
actual execution length/kind, imported source hashes, commit, relevant dirty-diff
hash, CPU/runtime and package versions. Deterministic or absent producers have
null actual seeds with reasons. Attempt identity is separate from run identity.

Raw files live outside the source repository. Completion validates file inventory
and checksums, ordered phase counts, event joins/provenance, chosen catalog
entries and feedback/update arithmetic. Only an exact, validated completed
identity is reusable. A valid poor run cannot be retried. One documented
infrastructure failure can have attempt 2, restarting from frame zero with the
prior completion hash; attempt 3 is rejected. Code/invariant faults stop, and
an abandoned attempt without a terminal classification is not automatically
resumable. There is no exact mid-frame resume implementation.

## Tests and reproducibility

Runtime: Python 3.12.11, NumPy 1.26.4, Torch 2.8.0, NetworkX 3.5, pytest 8.4.2,
pmdarima 2.0.4; CPU, one Torch/BLAS thread, deterministic Torch algorithms.
Package versions and imported-file hashes are included in every run manifest.

From `Dynamic_Routing_Eval_Framework`, using the qualified environment:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 OMP_NUM_THREADS=1 python -B -m pytest -p no:cacheprovider tests/test_primary_routes.py tests/test_medium_catalog.py tests/test_medium_preflight.py tests/test_environment_contexts.py tests/test_resume_behavior.py tests/test_runner_resume_compare.py tests/test_allocator_runner_cleanup.py tests/test_registry_update_on_save.py tests/test_drive_state_offload.py -q
```

**Final required suite: 72 passed, 0 failed, 0 skipped, 56.60 seconds.**
Of these, 53 are new tests (6 primary regression/metadata, 13 catalog/seed/mask,
34 policy/logging/identity/preflight), plus 19 existing regression checks.

A broader discovery pass (`tests tools/tests/test_state_naming_and_resume.py`)
reported **89 passed, 4 failed, 0 skipped in 59.32 seconds** before the final
null-diagnostic/thread-control refinements. All new tests passed. Four failures
are in untouched existing tests/functions (verified zero diff against the base):

1. `test_standalone_migrate_files_by_pattern_deletes_verified_files_across_dates`
2. `test_standalone_migrate_files_by_pattern_reports_summary_status`
3. `test_standalone_migrate_files_by_pattern_runs_in_parallel_and_deletes_verified_local`
4. `test_expected_keys_no_qubit_suffix_for_random_runtime`

The first three use fake upload managers whose signatures omit the existing
`workers` keyword. The fourth creates an incomplete `ExperimentConfiguration`
fixture without `backup_registry`. They do not exercise the new campaign path;
they remain visible suite-health issues, not suppressed passes. No legacy cache
or migration code was changed to address them.

## Tiny fixture observations

Three separate eight-frame technical executions at implementation commit
`265b9a75` completed with eight records per phase plus one completion marker.
Every bundle was read back and its completion validated. These are instrumentation
fixtures, not the six-unit scientific block or any learning-performance estimate.

| Technical fixture | Bundle wall seconds | Raw bundle bytes | Process high-water RSS |
|---|---:|---:|---:|
| Oracle / NoAttack | 0.156863 | 68,018 | 385,941,504 bytes |
| CEpsilonGreedy / NoAttack | 0.148211 | 68,057 | 385,941,504 bytes |
| EXPNeuralUCB hybrid / RandomAttack | 2.457709 | 74,094 | 466,534,400 bytes |

The hybrid fixture retained **zero positive route-feedback events and seven
within-route updates**. The absent hybrid channels for the other policies are
null, not fabricated zeros. Timing excludes Python/import startup; RSS is the
process high-water mark including libraries and prior fixtures. Eight frames
do not exercise steady-state 55-action replay training, so these timings do
not establish a 6,000-frame completion estimate. The smaller optimizer unit
fixture verifies mechanics, not long-run cost or learning.

Technical fixture bundles and test-generated caches are disposable reproducible
support artifacts; only this report and the source tests are retained in Git.
No model state, scientific raw execution, or result dataset is committed.

## Audit handoff

Ready for independent pre-run code/contract audit, with the four unrelated
suite failures disclosed. Review source changes, exact invariants, seed/root
stability, channel timing, identity/retry rules and runtime limits. F-09 launch
still requires final audit and Piter approval; the bounded preflight CLI cannot
launch it. Production queue/notebook launch wiring and long-horizon runtime
qualification remain launch-stage work. No manuscript revalidation is required
by this engineering pass.
