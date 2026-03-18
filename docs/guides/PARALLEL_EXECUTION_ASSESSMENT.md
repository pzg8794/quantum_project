# Parallel Execution Assessment (Framework)

This note captures a practical assessment of where parallelism is safe and useful in the evaluation framework, and where it is likely to break correctness (state naming, registry, resume) or degrade performance (memory/Drive throttling).

---

## Current state (what exists today)

- `MultiRunEvaluator(..., maxworkers=...)` is the primary parallelism knob used by the framework today (see `docs/setup/TROUBLESHOOTING.md` for the OOM guidance).
- State persistence is local-first with optional best-effort Drive upload:
  - local path: `Dynamic_Routing_Eval_Framework/daqr/config/quantum_data_lake/{framework_state,model_state}/day_YYYYMMDD/*.pkl`
  - Drive can be unavailable; when it is unavailable we must not assume Drive paths exist.

---

## Safe parallelism boundaries (recommended)

### 1) I/O-bound tasks: threads (good)

Good candidates:

- Drive downloads/uploads (API + filesystem mirror) where latency dominates.
- Targeted restore of expected keys (many small independent files).

Constraints:

- Throttle concurrency to avoid Google Drive API rate limits / local mirror contention.
- Keep registry updates serialized (or lock-protected) so parallel fetches do not race on `backup_registry`.

### 2) CPU-bound simulation/evaluation: processes (good)

Good candidates:

- Running independent experiments (e.g., different threat scenarios) where CPU dominates and objects can be cleanly isolated per worker.

Constraints:

- Python GIL limits multi-threaded CPU speedups; prefer process pools.
- Memory pressure is the real limiter: parallel runs multiply model memory + pickle state + intermediate results.
- If using GPU / torch, parallel workers can easily OOM; keep `maxworkers` low or force CPU.

### 3) Parallel within a single experiment loop: caution

Parallelizing *inside* an experiment (e.g., per-model updates each frame) is risky because:

- it often requires shared environment state,
- it increases synchronization overhead,
- it complicates deterministic replay/debugging.

Recommendation:

- Prefer parallelizing across **independent configurations** (threat scenarios / runs / evaluators), not within a single step loop.

---

## Correctness hazards (must address before scaling parallelism)

### A) State naming collisions

Parallel workers must never write the same `{component}/{day}/{filename}` concurrently. Safe parallelism requires:

- unique filenames per worker/run, and
- unique `day_YYYYMMDD` namespace per logical run group (or a higher-granularity subdirectory if needed later).

### B) Registry races

The registry is a shared mutable map (`backup_registry`) and is used to resolve resume paths.

If parallel workers update the registry concurrently without a lock, we risk:

- lost updates,
- incorrect “latest path” selection,
- resume choosing the wrong file.

Recommendation:

- treat registry writes as a serialized critical section (single writer), or
- enforce a lock around registry mutations + persistence.

### C) Drive rate limits + eventual consistency

Even when uploads succeed, “find/download immediately after upload” can be flaky due to:

- API throttling,
- filesystem mirror lag,
- verification windows.

Recommendation:

- use bounded concurrency for Drive I/O,
- treat verification failures as “keep local staged copy”, and retry later.

---

## Practical guidance (what to do now)

- Keep `maxworkers` conservative by default; increase only after confirming memory headroom and stable Drive behavior.
- Use parallelism primarily for:
  - “many independent configs” (scenario/threat × allocator × evaluator),
  - Drive I/O (download/upload) with throttling.
- Avoid parallelism that mixes multiple writers into the same local state directory unless filename uniqueness and registry locking are guaranteed.

