from __future__ import annotations

from dataclasses import dataclass

from daqr.config.state_naming import model_state_filename, runner_state_filename


@dataclass(frozen=True)
class ParsedEvaluatorFilename:
    cap_id: int
    allocator_id: str
    env_id: str
    attack_id: str
    base_frames: int
    frame_step: int
    runs_id: int
    st: str  # testbed/runtime suffix inferred from filename (e.g., "paper2", "paper8_m1_rate_only")


def parse_multirun_evaluator_filename(name: str) -> ParsedEvaluatorFilename | None:
    """
    Parse `MultiRunEvaluator_...pkl` into a dependency-light spec used for targeted restore.

    Expected pattern (example):
      MultiRunEvaluator_4000-Default_All_All-4000_2000_2_S1T_paper12.pkl
    """
    core = name.replace(".pkl", "")
    try:
        _prefix, rest = core.split("_", 1)
    except ValueError:
        return None

    parts = rest.split("-")
    if len(parts) < 3:
        return None

    try:
        cap_id = int(round(float(parts[0])))
    except Exception:
        return None

    alloc_env_attack = parts[1].split("_")
    if len(alloc_env_attack) != 3:
        return None

    allocator_id, env_id, attack_id = alloc_env_attack
    last_params = parts[-1]

    try:
        base_frames, frame_step, runs_id = map(int, last_params.split("_")[:3])
    except Exception:
        return None

    # The suffix can contain underscores (e.g., "paper8_m1_rate_only").
    # Recover it by:
    # - splitting on "_"
    # - skipping the first 3 numeric params (base_frames, frame_step, runs_id)
    # - then taking everything from the first token that starts with "paper" onward
    #   (falling back to joining remaining tokens if "paper" isn't present).
    st = ""
    tokens = last_params.split("_")
    if len(tokens) > 3:
        remainder = tokens[3:]
        paper_idx = next((i for i, tok in enumerate(remainder) if tok.lower().startswith("paper")), None)
        if paper_idx is not None:
            st = "_".join(remainder[paper_idx:])
        else:
            st = "_".join(remainder)
    return ParsedEvaluatorFilename(
        cap_id=cap_id,
        allocator_id=allocator_id,
        env_id=env_id,
        attack_id=attack_id,
        base_frames=base_frames,
        frame_step=frame_step,
        runs_id=runs_id,
        st=st,
    )


def generate_expected_state_keys(
    *,
    evaluator_filename: str,
    parsed: ParsedEvaluatorFilename,
    runs: int,
    models: list[str],
    algorithm_configs: dict,
    scale: int,
    base_capacity: bool,
    include_evaluator_key: bool = True,
) -> dict[str, dict[str, str]]:
    """
    Generate expected runner + model state filenames implied by the evaluator artifact.

    This is dependency-light by design (no numpy/torch imports). It produces the
    same naming contract as runtime objects by delegating to state_naming helpers.
    """
    # Expected keys are allocation-agnostic, but they must preserve the
    # testbed/runtime suffix used in the artifact naming contract.
    runtime_suffix = f"_{parsed.st}" if parsed.st else ""

    # Legacy naming semantics (as observed in the curated evaluation corpus):
    # - Baseline (no-attack) uses env_id="Baseline (None)" and attack_id="No"
    # - Stochastic uses env_id="Stochastic" and attack_id="Random"
    # - Adversarial uses env_id="Adversarial" and one of:
    #   Markov / Adaptive / OnlineAdaptive
    combos: list[tuple[str, str]] = [
        ("Baseline (None)", "No"),
        ("Stochastic", "Random"),
        ("Adversarial", "Markov"),
        ("Adversarial", "Adaptive"),
        ("Adversarial", "OnlineAdaptive"),
    ]

    # If evaluator filename is already specific (not "All"), filter combos.
    if parsed.env_id and parsed.env_id.lower() != "all":
        combos = [c for c in combos if c[0].lower().startswith(parsed.env_id.lower())]
    if parsed.attack_id and parsed.attack_id.lower() != "all":
        combos = [c for c in combos if c[1].lower() == parsed.attack_id.lower()]

    framework_state: dict[str, str] = {}
    model_state: dict[str, str] = {}

    if include_evaluator_key:
        framework_state[evaluator_filename] = evaluator_filename

    for run_idx in range(runs):
        runner_id = run_idx + 1
        frame_no = parsed.base_frames + (parsed.frame_step * run_idx)
        cap_id = (
            frame_no * scale
            if not base_capacity
            else parsed.base_frames * scale
        )

        for env_name, attack_name in combos:
            runner_key = runner_state_filename(
                runner_id=runner_id,
                cap_id=int(cap_id),
                allocator_id=parsed.allocator_id,
                env_id=env_name,
                attack_id=attack_name,
                frames_count=int(frame_no),
                runtime_suffix=runtime_suffix,
            )
            framework_state[runner_key] = runner_key

            for model_name in models:
                model_class = algorithm_configs[model_name]["model_class"].__name__
                mode = algorithm_configs[model_name]["kwargs"]["mode"]
                model_key = model_state_filename(
                    model_id=model_class,
                    mode=mode,
                    cap_id=int(cap_id),
                    allocator_id=parsed.allocator_id,
                    env_id=env_name,
                    attack_id=attack_name,
                    frame_no=int(frame_no),
                    runtime_suffix=runtime_suffix,
                )
                model_state[model_key] = model_key

    return {"framework_state": framework_state, "model_state": model_state}
