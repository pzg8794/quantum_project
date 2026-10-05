"""Frozen medium Tier-1 configuration shared by serial and process execution."""

from copy import deepcopy
from functools import partial
import itertools
from pathlib import Path

import networkx as nx
import numpy as np

from daqr.campaigns.medium_execution_evidence import MediumExecutionEvidencePlugin
from daqr.campaigns.medium_spec import build_catalog, seed_manifest
from daqr.config.execution_contract import ExecutionSettings
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.config.local_backup_manager import LocalBackupManager
from daqr.core.catalog_components import LayeredPrimaryCatalog, PrimaryPayoff
from daqr.core.qubit_allocator import QubitAllocator
from daqr.core.scenario_execution import ScenarioExecutionComponent
from daqr.evaluation.allocator_runner import AllocatorRunner


MODEL_ROSTER = (
    "Oracle",
    "GNeuralUCB",
    "EXPNeuralUCB",
    "CPursuitNeuralUCB",
    "iCPursuitNeuralUCB",
)
SCENARIOS = {
    "stochastic": "Stochastic Random Failures",
    "markov": "Markov Adversarial Attack",
    "adaptive": "Adaptive Adversarial Attack",
    "onlineadaptive": "Online Adaptive Attack",
    "none": "Baseline (Optimal Conditions)",
}
PROFILE_POOL = tuple(
    itertools.combinations_with_replacement((1e-4, 1.5e-4, 2e-4), 3)
)
BASE_SEED = 12345
ATTACK_INTENSITY = 0.25
PROTOCOL_NAMESPACE = "f08-tier1-default-fixed-full-roster-v2"


def framework_configuration(base_frames=6000, execution_kind="scientific"):
    medium_config = {
        "testbed": "medium_tier1",
        "topology_family": "layered-primary-form-v1",
        "profile_pool": list(PROFILE_POOL),
        "num_paths": 10,
        "total_qubits": 90,
        "min_qubits_per_route": 1,
        "baseline_allocation": (9,) * 10,
        "entanglement_success_factor": 100,
        "physics_model_name": "medium_tier1",
        "state_suffix": "medium_tier1_default_full_roster_v2",
    }
    return {
        "exp_num": 3,
        "test_mode": execution_kind != "scientific",
        "base_frames": int(base_frames),
        "frame_step": 0,
        "models": list(MODEL_ROSTER),
        "intensity": ATTACK_INTENSITY,
        "routing_strategy": "fixed",
        "capacity": int(base_frames) * 2,
        "main_env": "stochastic",
        "aggregate_state": False,
        "enable_plots": False,
        "scientific_block_ids": [0, 1, 2],
        "execution_kind": execution_kind,
        "env_attrs": {
            "intensity": ATTACK_INTENSITY,
            "base_seed": BASE_SEED,
            "reproducible": True,
        },
        "medium_tier1": medium_config,
    }


def fixed_allocator():
    return QubitAllocator(
        total_qubits=90,
        num_routes=10,
        min_qubits_per_route=1,
        baseline_allocation=(9,) * 10,
    )


def catalog_configuration(base_frames, execution_kind, base_seed, qubit_cap):
    allocation = tuple(int(value) for value in qubit_cap)
    if allocation != (9,) * 10:
        raise ValueError(
            f"F-08 fixed allocator must supply ten nine-qubit budgets, got {allocation}"
        )
    config = ExperimentConfiguration(
        models=list(MODEL_ROSTER),
        scenarios=deepcopy(SCENARIOS),
        runs=3,
        scale=2,
        base_capacity=True,
        base_seed=int(base_seed),
        attack_intensity=ATTACK_INTENSITY,
        attack_rate=ATTACK_INTENSITY,
        physics_params={"entanglement_success_factor": 100},
        testbed_config={
            "topology_family": "layered-primary-form-v1",
            "profile_pool": list(PROFILE_POOL),
        },
        allocator=fixed_allocator(),
        persistence=False,
        resume=False,
        use_last_backup=False,
        overwrite=False,
        catalog_component=LayeredPrimaryCatalog(),
        reward_component=PrimaryPayoff(),
    )
    config.execution = ExecutionSettings(
        protocol_namespace=PROTOCOL_NAMESPACE,
        horizon=int(base_frames),
        base_horizon=int(base_frames),
        scale_points=(3,),
        execution_kind=execution_kind,
    )
    return config


def build_block_payload(
    physics_model,
    current_frames,
    base_seed,
    qubit_cap,
    block_id=0,
    execution_kind="scientific",
):
    if physics_model != "medium_tier1":
        raise ValueError(f"Unsupported medium physics model: {physics_model}")
    config = catalog_configuration(
        current_frames,
        execution_kind,
        base_seed,
        qubit_cap,
    )
    catalog = build_catalog(config, block=int(block_id), scale_m=3)
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
    if graph.number_of_nodes() != 15 or len(contexts) != 10:
        raise ValueError("Unexpected medium topology shape")
    if len(rewards) != 10 or sum(len(actions) for actions in contexts) != 550:
        raise ValueError("Unexpected medium action catalog shape")

    scenario_components = {}
    for scenario in SCENARIOS:
        strategy = config.resolve_attack_strategy(scenario)
        threat_seed = seed_manifest(
            config,
            block=int(block_id),
            policy=MODEL_ROSTER[0],
            threat=scenario,
            scale_m=3,
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
            "block": int(block_id),
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


def configure_external_persistence(
    custom_config,
    output_root,
    state_root=None,
    evidence_root=None,
    scale_m=3,
):
    output_root = Path(output_root).expanduser().resolve()
    state_root = Path(state_root or output_root).expanduser().resolve()
    evidence_root = Path(
        evidence_root or output_root / "q04-evidence"
    ).expanduser().resolve()
    source_root = Path(__file__).resolve().parents[3]
    for path in (output_root, state_root, evidence_root):
        if path == source_root or path.is_relative_to(source_root):
            raise ValueError("Medium outputs must remain outside the source repository")
        path.mkdir(parents=True, exist_ok=True)
    custom_config.dir = state_root
    custom_config.persistence = True
    custom_config.backup_mgr = LocalBackupManager(
        date_str=custom_config.day_str,
        config_dir=state_root,
        verbose=False,
    )
    custom_config.backup_mgr.in_share_drive = False
    custom_config.backup_mgr.mode = "local"
    custom_config.scientific_evidence_root = evidence_root
    custom_config.execution_evidence_plugin = MediumExecutionEvidencePlugin(
        evidence_root,
        scale_m=scale_m,
    )
    custom_config.scientific_seed_namespace = PROTOCOL_NAMESPACE
    custom_config.scientific_campaign_base_seed = BASE_SEED
    custom_config.disable_outcome_retries = True
    return custom_config


def runtime_configuration(output_root, base_frames=6000, execution_kind="scientific", state_root=None):
    framework = framework_configuration(base_frames, execution_kind)
    config = ExperimentConfiguration(
        env_type=framework["main_env"],
        scenarios=deepcopy(SCENARIOS),
        use_last_backup=False,
        resume=False,
        models=list(MODEL_ROSTER),
        attack_intensity=ATTACK_INTENSITY,
        attack_rate=ATTACK_INTENSITY,
        scale=2,
        base_capacity=True,
        overwrite=False,
        base_seed=BASE_SEED,
        allocator=fixed_allocator(),
        persistence=False,
    )
    config.cleanup_cooldown_seconds = 0
    configure_external_persistence(config, output_root, state_root=state_root)
    return config, framework


def install_block_payloads(config, framework, execution_kind):
    block_physics = {}
    catalog_identities = {}
    trace_catalogs = {}
    scenario_components = {}
    evidence_configurations = {}
    allocation = tuple(config.allocator.allocate(timestep=0, route_stats={}, verbose=False))
    for block_id in framework["scientific_block_ids"]:
        payload = build_block_payload(
            "medium_tier1",
            framework["base_frames"],
            framework["env_attrs"]["base_seed"],
            allocation,
            block_id=block_id,
            execution_kind=execution_kind,
        )
        payload = dict(payload)
        catalog_identities[block_id] = payload.pop("_campaign_catalog_identity")
        trace_catalogs[block_id] = payload.pop("_campaign_trace_catalog")
        scenario_components[block_id] = payload.pop("_scenario_execution_components")
        evidence_configurations[block_id] = payload.pop(
            "_execution_evidence_configuration"
        )
        block_physics[block_id] = payload
    config.scientific_block_physics = block_physics
    config.scientific_catalog_identities = catalog_identities
    config.scientific_trace_catalogs = trace_catalogs
    config.scenario_execution_components = scenario_components
    for block_id, evidence_config in evidence_configurations.items():
        config.execution_evidence_plugin.register_block(block_id, evidence_config)
    config.scientific_block_id = framework["scientific_block_ids"][0]
    config.physics_params = deepcopy(block_physics[config.scientific_block_id])
    return config


def run_serial_campaign(output_root, base_frames=6000, execution_kind="scientific"):
    config, framework = runtime_configuration(
        output_root,
        base_frames=base_frames,
        execution_kind=execution_kind,
    )
    runner = AllocatorRunner(
        allocator_type="Default",
        physics_models=["medium_tier1"],
        framework_config=framework,
        scales=[2],
        runs=[3],
        models=list(MODEL_ROSTER),
        test_scenarios=deepcopy(SCENARIOS),
        config=config,
    )
    payload_builder = partial(
        build_block_payload,
        execution_kind=execution_kind,
    )
    runner.run(get_physics_params_func=payload_builder)
    receipt = Path(config.scientific_evidence_root) / "campaign-receipt.json"
    if not receipt.exists():
        raise RuntimeError("Serial campaign did not produce a completion receipt")
    return receipt
