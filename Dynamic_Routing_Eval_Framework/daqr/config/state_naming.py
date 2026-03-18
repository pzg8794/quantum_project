from __future__ import annotations

from threading import RLock


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


class StateNaming:
    """
    Thread-safe naming service intended to live on `ExperimentConfiguration`.

    Objects call into this service (rather than formatting ad-hoc f-strings)
    so naming policy stays centralized and consistent across the framework.
    """

    def __init__(self):
        self._lock = RLock()

    def runner_filename(
        self,
        *,
        runner_id: int,
        cap_id: int,
        allocator_id: str,
        env_id: str,
        attack_id: str,
        frames_count: int,
        runtime_suffix: str = "",
    ) -> str:
        with self._lock:
            return runner_state_filename(
                runner_id=runner_id,
                cap_id=cap_id,
                allocator_id=allocator_id,
                env_id=env_id,
                attack_id=attack_id,
                frames_count=frames_count,
                runtime_suffix=runtime_suffix,
            )

    def model_filename(
        self,
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
        with self._lock:
            return model_state_filename(
                model_id=model_id,
                mode=mode,
                cap_id=cap_id,
                allocator_id=allocator_id,
                env_id=env_id,
                attack_id=attack_id,
                frame_no=frame_no,
                runtime_suffix=runtime_suffix,
            )
