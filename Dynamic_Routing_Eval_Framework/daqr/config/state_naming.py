from __future__ import annotations


def runner_state_filename(
    *,
    runner_id: int,
    cap_id: int,
    allocator_id: str,
    env_id: str,
    attack_id: str,
    frames_count: int,
    runtime_suffix: str = "",
) -> str:
    """
    Canonical naming for runner state artifacts.

    Must match `QuantumExperimentRunner`'s runtime `file_name` format.
    """
    prefix = f"QuantumExperimentRunner_{runner_id}"
    return (
        f"{prefix}_{cap_id}-"
        f"{allocator_id}_{env_id}_{attack_id}-"
        f"{frames_count}_{runner_id}{runtime_suffix}.pkl"
    )


def model_state_filename(
    *,
    model_id: str,
    mode: str,
    cap_id: int,
    allocator_id: str,
    env_id: str,
    attack_id: str,
    frame_no: int,
    runtime_suffix: str = "",
) -> str:
    """
    Canonical naming for model state artifacts.

    Must match `BaseBandit`'s runtime `file_name` format.
    """
    return (
        f"{model_id}({mode})_{cap_id}-"
        f"{allocator_id}_{env_id}_{attack_id}-"
        f"{frame_no}{runtime_suffix}.pkl"
    )

