## Framework Design Log (Decisions + Protocol)

Purpose: capture **design decisions, working protocol, and framing** that guide future changes.

This log is intentionally lightweight:
- record decisions/agreements (not raw chat)
- use dated entries
- link to the doc(s) that define the current contract

---

### 2026-03-05 — Ownership narrative + “framework of frameworks” protocol

**Narrative model (shared vocabulary)**
- `configs` = **the sun** (shared context; visible everywhere; not uniquely “owned”).
- Allocator = **world** (defines routing/qubit-allocation conditions; worlds differ).
- Threat scenarios = **shared aerospace** (same scenario suite across worlds for fair comparison).
- Evaluator = **continent** (evaluates/aggregates performance across experiments under one scope).
- Runner = **country** (one experiment instance; must be consistent across models).
- Models = **workers** (operate inside the same country; fairness requires shared environment instance).

Source: `docs/guides/STATE_LAYERS_AND_RESUME.md`

**Working protocol (non-negotiable)**
- No code changes until design intent is confirmed with the system designer (Piter).
- For any fix that changes behavior, first identify the **owner object** and its **contract**.
- Prefer the smallest localized change; avoid refactors unless explicitly requested.
- Keep code short + reusable; do not duplicate state-discovery logic across layers.

**Environment vs ownership**
- The environment “resides” wherever we instantiate/call it.
- “Ownership” can be defined at two levels:
  - **Implementation owner (current):** where the behavior lives today (e.g., `QuantumEnvironment` + physics helpers).
  - **Conceptual ownership:** intentionally left open; validated by results as the framework evolves.

**Entanglement phase (language to use)**
- We can implement entanglement-related behavior inside current modules, but we do not claim final conceptual ownership yet.
- Stability first; entanglement architecture decisions are deferred until evidence constrains the right boundary.

