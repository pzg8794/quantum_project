"""Frozen F-08 Tier-1 fixed-allocator configuration and process execution."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import combinations_with_replacement
import multiprocessing
import os
from pathlib import Path

from daqr.campaigns.medium_runner import execute_scientific
from daqr.campaigns.medium_trace import validate_scale_completion
from daqr.config.execution_contract import ExecutionSettings, resolve_configuration
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.core.catalog_components import LayeredPrimaryCatalog, PrimaryPayoff
from daqr.core.identity import canonical_json
from daqr.core.qubit_allocator import QubitAllocator


TIER1_MODELS = ("Oracle", "CEpsilonGreedy", "EXPNeuralUCB")
TIER1_SCENARIOS = {
    "stochastic": "Stochastic Random Failures",
    "markov": "Markov Adversarial Attack",
    "adaptive": "Adaptive Adversarial Attack",
    "onlineadaptive": "Online Adaptive Attack",
    "none": "Baseline (Optimal Conditions)",
}
TIER1_SCALE_M = 3
TIER1_BLOCKS = 3
TIER1_HORIZON = 6000
TIER1_REPLAY_SCALE = 2
TIER1_BASE_SEED = 12345
TIER1_BUDGET_PER_ROUTE = 9
TIER1_ROUTE_COUNT = 10
TIER1_TOTAL_QUBITS = 90
TIER1_PROTOCOL = "f08-tier1-default-fixed-v1"


def build_tier1_default_config(*, horizon=TIER1_HORIZON, blocks=TIER1_BLOCKS,
                               execution_kind="scientific"):
    """Build the exact fixed-allocator Tier-1 configuration."""
    allocator = QubitAllocator(
        total_qubits=TIER1_TOTAL_QUBITS,
        num_routes=TIER1_ROUTE_COUNT,
        min_qubits_per_route=1,
        baseline_allocation=(TIER1_BUDGET_PER_ROUTE,) * TIER1_ROUTE_COUNT,
    )
    config = ExperimentConfiguration(
        models=list(TIER1_MODELS),
        scenarios=dict(TIER1_SCENARIOS),
        runs=blocks,
        scale=TIER1_REPLAY_SCALE,
        base_capacity=True,
        base_seed=TIER1_BASE_SEED,
        attack_intensity=0.25,
        attack_rate=0.25,
        physics_params={"entanglement_success_factor": 100},
        testbed_config={
            "topology_family": "layered-primary-form-v1",
            "profile_pool": list(
                combinations_with_replacement((1e-4, 1.5e-4, 2e-4), 3)
            ),
        },
        allocator=allocator,
        persistence=False,
        resume=False,
        use_last_backup=False,
        overwrite=False,
        catalog_component=LayeredPrimaryCatalog(),
        reward_component=PrimaryPayoff(),
    )
    config.execution = ExecutionSettings(
        protocol_namespace=TIER1_PROTOCOL,
        horizon=horizon,
        base_horizon=TIER1_HORIZON,
        scale_points=(TIER1_SCALE_M,),
        execution_kind=execution_kind,
    )
    resolved = resolve_configuration(config)
    if tuple(resolved["scenarios"]) != tuple(TIER1_SCENARIOS):
        raise ValueError("Tier-1 threat order changed")
    if len(resolved["required_cells"]) != blocks * len(TIER1_MODELS) * len(TIER1_SCENARIOS):
        raise ValueError("Tier-1 matrix size mismatch")
    return config


def _execute_cell(payload):
    output_root, config, policy, threat, block, scale_m = payload
    directory, completion, reused = execute_scientific(
        output_root,
        config,
        policy,
        threat,
        block,
        scale_m,
        reuse_completed=True,
    )
    return {
        "block": block,
        "threat": threat,
        "policy": policy,
        "directory": str(directory),
        "run_id": completion["run_id"],
        "reused": reused,
    }


def run_scientific_matrix(output_root, config, *, scale_m=TIER1_SCALE_M, max_workers=1):
    """Run every configured cell in isolated processes and validate completion."""
    if type(max_workers) is not int or max_workers < 1:
        raise ValueError("max_workers must be a positive integer")
    root = Path(output_root).expanduser().resolve()
    source_root = Path(__file__).resolve().parents[2]
    if root == source_root or root.is_relative_to(source_root):
        raise ValueError("Scientific output root must be outside the source repository")
    resolved = resolve_configuration(config)
    cells = [
        (root, config, cell["policy"], cell["scenario"], cell["block"], scale_m)
        for cell in resolved["required_cells"]
        if cell["scale"] == scale_m
    ]
    if not cells:
        raise ValueError("No configured cells for requested scale")

    context = multiprocessing.get_context("spawn")
    completed = []
    with ProcessPoolExecutor(max_workers=max_workers, mp_context=context) as executor:
        futures = {executor.submit(_execute_cell, cell): cell for cell in cells}
        for future in as_completed(futures):
            completed.append(future.result())

    order = {
        (cell["block"], cell["scenario"], cell["policy"]): index
        for index, cell in enumerate(resolved["required_cells"])
        if cell["scale"] == scale_m
    }
    completed.sort(key=lambda item: order[(item["block"], item["threat"], item["policy"])])
    bundle_paths = [item["directory"] for item in completed]
    validation = validate_scale_completion(config, scale_m, bundle_paths)
    return {
        "schema_version": "medium-notebook-receipt-v1",
        "allocator": "Default",
        "scale_m": scale_m,
        "max_workers": max_workers,
        "required_cells": validation["required_cells"],
        "completed_cells": validation["completed_cells"],
        "reused_cells": sum(item["reused"] for item in completed),
        "scenario_order": list(TIER1_SCENARIOS),
        "policy_order": list(TIER1_MODELS),
        "blocks": config.runs,
        "horizon": config.execution.horizon,
        "bundle_directories": bundle_paths,
        "run_ids": [item["run_id"] for item in completed],
    }


def write_notebook_receipt(output_root, receipt, filename="default-fixed-notebook-receipt.json"):
    """Write one deterministic notebook-level completion receipt without replacement."""
    root = Path(output_root).expanduser().resolve()
    path = root / filename
    stable = {key: value for key, value in receipt.items() if key not in {"max_workers", "reused_cells"}}
    encoded = canonical_json(stable) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != encoded:
            raise ValueError("Existing notebook receipt differs from validated matrix")
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    return path


class AllocatorRunner:
    """Notebook adapter preserving the proven one-allocator/full-spectrum workflow."""

    def __init__(self, allocator_type, output_root, *, max_workers=1, config=None):
        if allocator_type != "Default":
            raise ValueError("Tier-1 execution currently authorizes only the Default allocator")
        self.allocator_type = allocator_type
        self.output_root = Path(output_root).expanduser().resolve()
        self.max_workers = max_workers
        self.config = config or build_tier1_default_config()

    def run(self):
        receipt = run_scientific_matrix(
            self.output_root,
            self.config,
            scale_m=TIER1_SCALE_M,
            max_workers=self.max_workers,
        )
        receipt["receipt_path"] = str(write_notebook_receipt(self.output_root, receipt))
        return receipt
