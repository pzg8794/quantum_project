"""Explicit technical fixtures ONLY; not the scientific campaign definition."""
from itertools import combinations_with_replacement
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.config.execution_contract import ExecutionSettings
from daqr.core.qubit_allocator import QubitAllocator
from daqr.campaigns import medium_spec, medium_runner


def fixture_config(frames=8, scale_m=3, budget=9, rates=(1e-4, 1.5e-4, 2e-4)):
    routes = 3*scale_m+1
    cfg = ExperimentConfiguration(
        models=["Oracle","CEpsilonGreedy","EXPNeuralUCB"],
        scenarios={"NoAttack":{"strategy":"none","parameters":{}},
                   "RandomAttack":{"strategy":"random","parameters":{"attack_rate":0.0625}}},
        runs=5, scale=2, base_capacity=True, base_seed=12345,
        physics_params={"entanglement_success_factor":100},
        testbed_config={"topology_family":"layered-primary-form-v1",
                        "profile_pool":list(combinations_with_replacement(rates,3))},
        allocator=QubitAllocator(total_qubits=budget*routes,num_routes=routes,
                                 baseline_allocation=(budget,)*routes),
        persistence=False, resume=False, use_last_backup=False)
    cfg.execution=ExecutionSettings("technical-regression-v2",frames,6000,(scale_m,),"technical_preflight")
    return cfg


def prepare_manifest(policy,threat,block=0,frames=8,scale_m=3):
    return medium_runner.prepare_manifest(fixture_config(frames,scale_m),policy,threat,block,scale_m=scale_m)


def run_policy(policy,contexts,rewards,mask,seed,recorder=None,capture_state=False):
    return medium_runner.run_policy(fixture_config(len(mask)),policy,contexts,rewards,mask,seed,recorder,capture_state)


def execute_preflight(root,policy="EXPNeuralUCB",threat="RandomAttack",block=0,frames=8):
    return medium_runner.execute_preflight(root,fixture_config(frames),policy,threat,block,3)


def build_catalog(block=0,scale_m=3):
    return medium_spec.build_catalog(fixture_config(scale_m=scale_m),block,scale_m)


def build_mask(threat,frames,block=0,scale_m=3):
    return medium_spec.build_mask(fixture_config(frames,scale_m),threat,frames,block,scale_m)


PROTOCOL=medium_spec.protocol(fixture_config())
PROTOCOL_ROOT_ID=medium_spec.digest(PROTOCOL)


def seed_for(domain,block,scale_m=3,qualifier=""):
    return medium_spec.seed_for(domain,block,scale_m,qualifier,PROTOCOL_ROOT_ID)


def seed_manifest(block,policy,threat,scale_m=3):
    return medium_spec.seed_manifest(fixture_config(scale_m=scale_m),block,policy,threat,scale_m)
