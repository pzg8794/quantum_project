"""Three-block T/Tb execution over a configured layered route catalog.

Topology level, replay anchor and capacity multiplier are independent inputs.
This module reuses the established full-roster evaluator and passive evidence
plugin; it does not select or change an allocator strategy.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import argparse
import math

import networkx as nx
import numpy as np

from daqr.campaigns.medium_spec import build_catalog, seed_manifest
from daqr.campaigns.medium_tier1 import (
    BASE_SEED,
    MODEL_ROSTER,
    PROFILE_POOL,
    PROTOCOL_NAMESPACE,
    SCENARIOS,
    configure_external_persistence,
)
from daqr.config.execution_contract import ExecutionSettings
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.core.catalog_components import LayeredPrimaryCatalog, PrimaryPayoff
from daqr.core.qubit_allocator import QubitAllocator
from daqr.core.scenario_execution import ScenarioExecutionComponent
from daqr.evaluation.allocator_runner import AllocatorRunner


BASE_FRAMES = 4000
FRAME_STEP = 2000
BLOCK_IDS = (0, 1, 2)
PHYSICS_MODEL = "layered_primary_spectrum"


def route_count(scale_m: int) -> int:
    if type(scale_m) is not int or scale_m < 1:
        raise ValueError("Topology scale must be a positive integer")
    return 3 * scale_m + 1


def fixed_allocation(scale_m: int) -> tuple[int, ...]:
    return (9,) * route_count(scale_m)


def catalog_configuration(
    *,
    scale_m: int,
    block_id: int,
    frames: int,
    replay: str,
    capacity_scale: float,
    base_seed: int = BASE_SEED,
) -> ExperimentConfiguration:
    if block_id not in BLOCK_IDS:
        raise ValueError("Block must belong to the three-run notebook sequence")
    if frames != BASE_FRAMES + FRAME_STEP * block_id:
        raise ValueError("Frame horizon does not match the notebook sequence")
    if replay not in {"T", "Tb"}:
        raise ValueError("Replay anchor must be T or Tb")
    if not math.isfinite(capacity_scale) or capacity_scale <= 0:
        raise ValueError("Capacity scale must be positive and finite")
    allocation = fixed_allocation(scale_m)
    config = ExperimentConfiguration(
        models=list(MODEL_ROSTER),
        scenarios=deepcopy(SCENARIOS),
        runs=len(BLOCK_IDS),
        scale=capacity_scale,
        base_capacity=(replay == "Tb"),
        base_seed=base_seed,
        attack_intensity=0.25,
        attack_rate=0.25,
        physics_params={"entanglement_success_factor": 100},
        testbed_config={
            "topology_family": "layered-primary-form-v1",
            "profile_pool": list(PROFILE_POOL),
        },
        allocator=QubitAllocator(
            total_qubits=sum(allocation),
            num_routes=len(allocation),
            min_qubits_per_route=1,
            baseline_allocation=allocation,
        ),
        persistence=False,
        resume=False,
        use_last_backup=False,
        overwrite=False,
        catalog_component=LayeredPrimaryCatalog(),
        reward_component=PrimaryPayoff(),
    )
    config.execution = ExecutionSettings(
        protocol_namespace=PROTOCOL_NAMESPACE,
        horizon=frames,
        base_horizon=BASE_FRAMES,
        scale_points=(scale_m,),
        execution_kind="scientific",
    )
    return config


def build_block_payload(
    *,
    scale_m: int,
    replay: str,
    capacity_scale: float,
    physics_model: str,
    current_frames: int,
    base_seed: int,
    qubit_cap,
    block_id: int,
):
    if physics_model != PHYSICS_MODEL:
        raise ValueError("Unexpected physics model")
    if tuple(qubit_cap) != fixed_allocation(scale_m):
        raise ValueError("Configured allocator does not match the route catalog")
    config = catalog_configuration(
        scale_m=scale_m,
        block_id=block_id,
        frames=current_frames,
        replay=replay,
        capacity_scale=capacity_scale,
        base_seed=base_seed,
    )
    catalog = build_catalog(config, block_id, scale_m)
    graph = nx.Graph()
    graph.add_nodes_from(catalog["topology"]["nodes"])
    graph.add_edges_from(catalog["topology"]["edges"])
    contexts = [
        np.asarray(route["actions"], dtype=int)
        for route in catalog["observations"]["routes"]
    ]
    rewards = [
        np.asarray(values, dtype=float)
        for values in catalog["physics"]["base_expected_payoffs"]
    ]
    if len(contexts) != route_count(scale_m) or len(rewards) != len(contexts):
        raise ValueError("Incomplete route/action/reward catalog")
    scenario_components = {}
    for scenario in SCENARIOS:
        strategy = config.resolve_attack_strategy(scenario)
        threat_seed = seed_manifest(
            config, block_id, MODEL_ROSTER[0], scenario, scale_m
        )["threat"]["actual_seed"]
        scenario_components[scenario] = ScenarioExecutionComponent(
            strategy=strategy,
            seed=threat_seed,
        )
    return {
        "noise_model": None,
        "fidelity_calculator": None,
        "external_topology": graph,
        "external_contexts": contexts,
        "external_rewards": rewards,
        "_campaign_catalog_identity": {
            "block": block_id,
            "topology_hash": catalog["topology_hash"],
            "route_set_hash": catalog["route_set_hash"],
            "action_catalog_hash": catalog["action_catalog_hash"],
            "observation_catalog_hash": catalog["observation_catalog_hash"],
            "physics_hash": catalog["physics_hash"],
        },
        "_campaign_trace_catalog": catalog,
        "_scenario_execution_components": scenario_components,
        "_execution_evidence_configuration": config,
    }


def run_cell(
    output_root,
    *,
    scale_m: int,
    replay: str,
    capacity_scale: float,
) -> Path:
    output_root = Path(output_root).expanduser().resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise FileExistsError("Scientific output root must be empty")
    allocation = fixed_allocation(scale_m)
    config = ExperimentConfiguration(
        env_type="stochastic",
        scenarios=deepcopy(SCENARIOS),
        use_last_backup=False,
        resume=False,
        models=list(MODEL_ROSTER),
        attack_intensity=0.25,
        attack_rate=0.25,
        scale=capacity_scale,
        base_capacity=(replay == "Tb"),
        overwrite=False,
        base_seed=BASE_SEED,
        allocator=QubitAllocator(
            total_qubits=sum(allocation),
            num_routes=len(allocation),
            min_qubits_per_route=1,
            baseline_allocation=allocation,
        ),
        persistence=False,
    )
    config.cleanup_cooldown_seconds = 0
    configure_external_persistence(config, output_root, scale_m=scale_m)
    config.suffix = (
        f"layered_spectrum_m{scale_m}_{replay}_s{str(capacity_scale).replace('.', '_')}"
    )
    framework = {
        "base_frames": BASE_FRAMES,
        "frame_step": FRAME_STEP,
        "exp_num": len(BLOCK_IDS),
        "main_env": "stochastic",
        "intensity": 0.25,
        "env_attrs": {"base_seed": BASE_SEED},
        "scientific_block_ids": list(BLOCK_IDS),
        "aggregate_state": False,
        "enable_plots": False,
        PHYSICS_MODEL: {
            "testbed": PHYSICS_MODEL,
            "num_paths": len(allocation),
            "total_qubits": sum(allocation),
            "min_qubits_per_route": 1,
            "baseline_allocation": allocation,
            "state_suffix": config.suffix,
        },
    }
    runner = AllocatorRunner(
        allocator_type="Default",
        physics_models=[PHYSICS_MODEL],
        framework_config=framework,
        scales=[capacity_scale],
        runs=[len(BLOCK_IDS)],
        models=list(MODEL_ROSTER),
        test_scenarios=deepcopy(SCENARIOS),
        config=config,
    )
    def payload_builder(**kwargs):
        return build_block_payload(
            scale_m=scale_m,
            replay=replay,
            capacity_scale=capacity_scale,
            **kwargs,
        )
    runner.run(get_physics_params_func=payload_builder)
    receipt = output_root / "q04-evidence" / "campaign-receipt.json"
    if not receipt.exists():
        raise RuntimeError("Full-roster run did not produce a completion receipt")
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale-m", type=int, required=True)
    parser.add_argument("--replay", choices=("T", "Tb"), required=True)
    parser.add_argument("--capacity-scale", type=float, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    receipt = run_cell(
        args.output_root,
        scale_m=args.scale_m,
        replay=args.replay,
        capacity_scale=args.capacity_scale,
    )
    print(receipt)


if __name__ == "__main__":
    main()
