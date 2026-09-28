# Quantum Execution Reproducibility + Versioned Execution Contract

**Canonical owner:** `pzg8794/quantum_project`
**Stage:** DESIGN / post-run packaging queued after the corrected scientific pipeline is accepted
**Owner:** Sol for post-run packaging/documentation; implementation may be delegated under normal SDLC
**Planning boundary:** semester/master-plan documents may point to this contract and track status, but must not duplicate or own the execution/reproducibility contract.
**Does not block:** current Q-04 independent review, Q-05 scientific execution, Q-06 validation, or Q-07 analysis

## Owner intent

After the corrected medium campaign and result-validation path are complete:

1. Document the qualified process-isolated parallel execution approach.
2. Preserve a clearly identified version of the current/serial execution path used by the existing DSCI601/602 compatibility boundary where applicable.
3. Create a clearly identified version of the new process-isolated parallel execution path.
4. Make terminal execution reproducible from a clean environment using one environment-bootstrap entrypoint and one experiment-launch entrypoint.
5. Make Colab execution reproducible using one complete setup/bootstrap cell followed by experiment cells that invoke the same underlying configuration/runner instead of duplicating scientific logic.
6. Audit old execution code and either retain it with explicit compatibility/deprecation comments or archive it with a replacement map when no active consumer remains.
7. Preserve all raw scientific evidence and historical execution artifacts.

This is a packaging/reproducibility deliverable, not authorization to change scientific semantics or redesign the framework.

## Existing precedent that Sol must inspect first

- `scripts/1_startup.sh`: useful separation of environment setup from experiments, but currently unsafe as a canonical interface because it contains embedded credential material, destructive reclone behavior, global/system Python mutation, and broad mutable installs. Preserve as historical precedent; do not reuse verbatim.
- `scripts/2_exp_runner.sh`: useful separate-runner precedent, but its defaults and execution assumptions predate the corrected five-model contract. Do not bless it as the current launcher without validation.
- `docs/setup/SETUP_LOCAL.md` and `docs/setup/SETUP_COLAB.md`: reconcile with the final accepted workflow.
- `requirements.txt`: current dependency snapshot is broad/environment-derived; establish the smallest authoritative pinned/locked environment representation rather than assuming every package is required.
- accepted corrected serial medium path in the shared medium Tier-1 configuration/runner.
- qualified process-isolated path in `daqr/campaigns/medium_process.py`.
- current medium execution runbook and immutable evidence/receipt contract.
- `pzg8794/DSCI601/NEXT_PHASE_INTEGRATION.md`: compatibility/scope bridge only. Shared infrastructure is allowed; GA and DSCI claims, credit, results, and deliverables remain separate.

## Versioned execution products

### Version A — serial/current compatibility release

Purpose: preserve the proven serial execution behavior as the correctness/reference implementation and compatibility target.

Acceptance:
- exact accepted five-model/threat/block/topology/replay/seed/evidence semantics;
- no reuse of the superseded 45-cell diagnostic;
- discoverable version identifier tied to exact source commit;
- documented relationship to DSCI601/602 compatibility consumers;
- remains the fallback if parallel execution is unavailable.

### Version B — process-isolated parallel release

Purpose: expose the qualified accelerated execution mode.

Acceptance:
- same scientific contract as Version A;
- private worker configuration, allocator, models, RNG/state, logging/scratch state;
- complete comparison groups preserved;
- existing evaluator/runner/evidence path used internally;
- parent-owned campaign validation/receipt;
- no thread/shared-process scientific execution unless separately designed/tested/reviewed later;
- serial/process qualification evidence documented.

Use the strongest existing repository version/release convention after inspection. Do not create duplicate implementation stacks merely to create two version names; both versions should share the authoritative scientific configuration and core execution logic wherever possible.

## Terminal reproducibility contract

### Environment/bootstrap entrypoint

One file/command must establish the complete required environment from a clean checkout.

Required:
- no committed credentials/tokens/secrets;
- no hidden dependency on Piter-specific local paths;
- isolated Python environment by default, not system-Python mutation;
- authoritative pinned/locked dependencies;
- exact Python/version checks and core import self-test;
- exact repo commit/execution version recorded;
- required output/scratch locations prepared safely outside source where appropriate;
- machine-readable environment manifest with execution version, git commit, Python version, dependency/lock identity, relevant platform/runtime information, and setup timestamp;
- rerunnable/idempotent or fail clearly without silently changing semantics.

### Full experiment-launch entrypoint

A second file/command must launch the accepted experiment without reconstructing configuration manually.

Required:
- explicit Version A serial or Version B process-isolated mode;
- accepted configuration only; never a historical quick-test model default;
- shared authoritative Tier-1 config rather than shell-duplicated matrix logic;
- fresh/scoped scientific output root;
- exact launch args, source version, config identity/hash, seed namespace, and execution mode recorded;
- existing immutable bundles and parent campaign receipt produced;
- fail closed on incomplete/mismatched matrix;
- complete corrected experiment runs without hand-editing model/threat/block lists.

A shell wrapper may call Python, but scientific logic stays in the existing Python framework.

## Colab reproducibility contract

### Setup/bootstrap cell

The first functional cell must be sufficient to:
- obtain/checkout the exact approved source version;
- install the pinned environment;
- mount/authorize external storage only through runtime/user-provided authorization;
- configure paths/output root;
- verify imports and expected execution version;
- emit/display the environment/version manifest;
- fail clearly on mismatch.

No committed credential may appear in the notebook.

### Experiment cells

- invoke the same shared config/launcher as terminal execution;
- expose serial vs qualified process mode clearly;
- avoid copied scientific configuration that can drift from terminal behavior;
- preserve the evidence/receipt contract;
- use fresh campaign roots;
- run the complete matrix without hand-editing roster/scenario/block lists.

## Old execution-code disposition

Before moving or deleting execution code, Sol performs a usage/reference audit. Every historical path receives exactly one status:

- **ACTIVE CURRENT** — Version A/shared infrastructure;
- **ACTIVE PARALLEL** — Version B;
- **COMPATIBILITY ONLY** — retained for DSCI601/602 or another supported consumer;
- **DEPRECATED** — retained temporarily with replacement/version pointer;
- **ARCHIVED** — no active dependency; preserved under the established archive/history convention with old-path -> replacement mapping;
- **REMOVE LATER** — only after evidence shows no active dependency and normal change control permits removal.

Rules:
- never delete raw experiment evidence as cleanup;
- never archive code merely because it looks old;
- do not build another runner architecture;
- comments explain why a path is compatibility/deprecated and where the replacement lives;
- README/setup docs stop advertising obsolete launch paths once replacements are accepted.

## Reproducibility proof before ACCEPT

1. Clean-environment terminal bootstrap from a clean checkout/container/VM or equivalent; environment manifest produced and core checks pass.
2. Bounded Version A terminal run and equivalent Version B run; verify scientific equivalence using the already accepted evidence standard.
3. Fresh Colab runtime or strongest available equivalent executes bootstrap and bounded run against the same shared launcher/config and produces valid evidence/receipt.
4. Documentation lets a new researcher identify both execution versions, setup command/cell, all-experiment launch, output locations, DSCI compatibility mapping, and old-code disposition.
5. Independent review checks secrets/security, hidden local assumptions, dependency pinning, version identity, no quick-test defaults, terminal/Colab semantic equivalence, and no GA/DSCI claim mixing.

## Expected handoff artifacts

Exact filenames are implementation choices unless existing conventions dictate them, but equivalents are required:
- terminal environment/bootstrap entrypoint;
- terminal full-experiment launcher;
- Colab notebook with complete bootstrap cell + accepted run cells;
- authoritative dependency/lock specification;
- environment/version manifest format;
- execution-version map: serial/current vs process-isolated parallel;
- parallel design/qualification document;
- legacy/deprecated/archive map;
- updated README/setup/runbook pointers;
- reproducibility test evidence;
- independent review record.

## SDLC sequence

**DESIGN** — this contract; inspect setup/run/versioning conventions and DSCI compatibility consumers.
**DEV** — package/version serial + accepted process path; repair bootstrap/launch surfaces; document/archive/comment historical execution paths.
**TEST** — clean terminal + Colab reproducibility; bounded serial/process equivalence; documentation/reference checks.
**INDEPENDENT REVIEW** — reproducibility, security/secrets, compatibility, and scientific-semantic audit.
**ACCEPT** — only after exact artifacts/commands/versions are recorded in the canonical handoff.

## Scope boundaries

- Do not reopen the accepted scientific matrix merely to package it.
- Do not make this a prerequisite for the current Q-04/Q-05 run sequence.
- Do not merge DSCI601/602 fairness work into GA scientific claims.
- Do not rewrite the DSCI compatibility layer unless evidence shows a bounded compatibility update is required.
- Do not delete raw scientific evidence.
- Do not introduce a third execution architecture when serial + qualified process isolation already satisfy the requirement.
## Non-regression rule — reproducibility is part of task completion

Reproducibility is not a final cleanup step. For every task in this execution/research stack that changes code, config, notebook content, dependencies, setup/bootstrap, execution paths, evidence generation, or version mapping:

- the task is not ACCEPTED if it breaks a previously accepted reproducible workflow;
- the task must run the smallest sufficient reproducibility/non-regression check before acceptance;
- if an execution surface is intentionally replaced, the replacement must be versioned and the prior surface must remain mapped as active compatibility, deprecated, or archived based on real usage;
- setup + launch + evidence generation must remain sufficient from a clean environment;
- notebook/config/script artifacts needed to reproduce or audit the task must remain preserved with exact version/hash identity.

This invariant applies throughout DEV/TEST/REVIEW, not only during Q-08 packaging.

## Notebook artifact retention contract

Piter must be able to review the notebooks at the end and make retention/versioning decisions from the actual artifacts. Therefore notebook history must not be reduced to prose summaries or hashes alone.

Required artifacts:
- **Pinned precedent notebook(s):** preserve the exact historical notebook/version used as source precedent.
- **Pre-run/source notebook snapshot:** preserve the exact notebook file that defines the accepted run before execution, with git commit/blob and SHA-256 identity.
- **Executed notebook snapshot:** when execution occurs through a notebook, preserve the post-execution `.ipynb` including outputs/metadata needed for review, stored as an immutable campaign/handoff artifact with SHA-256. Do not overwrite the only source copy.
- **Terminal-run notebook companion:** when the scientific run is launched by terminal rather than by executing the notebook, still preserve the exact approved notebook/config artifact that corresponds to the run plus the terminal launch manifest/receipt tying it to the executed version.
- **Generated notebook versions:** if builders regenerate notebooks during DEV/TEST, retain the accepted versions through Git history and include the final accepted source notebook in the explicit handoff inventory.
- **Notebook inventory:** Sol produces one final table listing notebook name/path, purpose, serial/parallel applicability, source commit/blob, pre-run hash, executed-artifact location/hash if applicable, status (ACTIVE CURRENT / ACTIVE PARALLEL / COMPATIBILITY ONLY / DEPRECATED / ARCHIVED), and replacement relationship.

Rules:
- do not delete or archive notebooks before Piter's final review/decision;
- do not rely only on Git history for the final review package; surface the exact notebook artifacts directly in the handoff;
- do not strip outputs from the only executed notebook artifact before review;
- notebook cleanup/archival happens only after the inventory is complete and Piter has had the opportunity to review it.

## Canonical artifact-location rule

This document is the owning Quantum contract. Project execution, environment, reproducibility, notebook-retention, versioning, and code-disposition requirements belong in the repository whose code they govern.

- `quantum_project` owns the Quantum execution/reproducibility contract and its evidence.
- Viber persona may own the general invariant that owning repositories hold their execution contracts.
- semester/master-plan repositories may track stage/status and link here, but must not become the canonical home of implementation or reproducibility requirements.
