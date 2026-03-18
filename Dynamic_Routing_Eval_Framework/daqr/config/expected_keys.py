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
    st: str


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

    st = last_params.split("_")[-1] if "_" in last_params else ""
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
    runtime_suffix = ""  # policy: expected keys are allocation-agnostic
    env_names = ["Stochastic", "Adversarial"]
    attack_names = ["No", "Random", "Markov", "Adaptive", "OnlineAdaptive"]

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

        for env_name in env_names:
            for attack_name in attack_names:
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

