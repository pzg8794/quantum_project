"""Bounded preflight entry point using real policies; no campaign launch CLI.

Legacy caches/retry orchestrators are intentionally outside this campaign path.
Only a future separately approved launch may use the scientific manifest.
"""
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from importlib.metadata import version
import platform
from pathlib import Path
import random
import subprocess
import sys
import time
from copy import copy
from daqr.config.execution_contract import resolve_configuration

import numpy as np
import torch
from threadpoolctl import threadpool_limits

from daqr.algorithms.base_bandit import Oracle
from daqr.algorithms.neural_bandits import EXPNeuralUCB
from daqr.algorithms.predictive_bandits import CEpsilonGreedy
from daqr.core.recorded_environment import RecordedQuantumEnvironment
from daqr.core.primary_routes import PrimaryRoute
from daqr.campaigns.medium_spec import (
    build_catalog, build_mask, protocol,
    seed_manifest, digest, canonical_json, validate_catalog,
)
from daqr.campaigns.medium_trace import AttemptBundle, run_identity, validate_completion, write_json_exclusive

FRAME_LIMIT = 512  # technical safety ceiling, not a scientific horizon
PREFLIGHT_LABEL = "TECHNICAL PREFLIGHT — NOT SCIENTIFIC EVIDENCE"


def code_identity():
    framework = Path(__file__).resolve().parents[2]
    repo = framework.parent
    imported = {}
    for module in tuple(sys.modules.values()):
        filename = getattr(module,"__file__",None)
        if not filename:
            continue
        path = Path(filename).resolve()
        if path.suffix == ".py" and path.is_relative_to(framework/"daqr"):
            imported[str(path.relative_to(repo))] = sha256(path.read_bytes()).hexdigest()
    def git(*args):
        return subprocess.check_output(["git","-C",str(repo),*args]).decode().strip()
    # Imported implementation only; unrelated scratch edits are retained but not executed.
    diff = subprocess.check_output(["git","-C",str(repo),"diff","HEAD","--",*sorted(imported)])
    return {"commit":git("rev-parse","HEAD"), "imported_files":dict(sorted(imported.items())),
            "imported_diff_hash":sha256(diff).hexdigest(),
            "runtime":{"python":platform.python_version(), "platform":platform.platform(),
                       "machine":platform.machine(), "packages":{p:version(p) for p in
                           ("numpy","torch","networkx","scipy","scikit-learn","pmdarima","threadpoolctl")},
                       "device":"cpu", "torch_threads":1, "blas_threads":1, "deterministic_algorithms":True}}


def prepare_manifest(configs, policy, threat, block, *, scale_m):
    resolved = resolve_configuration(configs)
    if policy not in resolved["policies"] or threat not in resolved["scenarios"]:
        raise ValueError("Requested cell is absent from configured axes")
    frames = configs.execution.horizon
    execution_kind = configs.execution.execution_kind
    if execution_kind == "technical_preflight" and frames > FRAME_LIMIT:
        raise ValueError("Preflight frame limit exceeded")
    catalog = build_catalog(configs, block, scale_m)
    seeds = seed_manifest(configs, block, policy, threat, scale_m)
    mask = build_mask(configs, threat, frames, block, scale_m)
    policy_config = resolved["policies"][policy]
    config = {"protocol": protocol(configs), "resolved": resolved, "policy": policy,
              "policy_kwargs": policy_config["kwargs"], "threat": threat,
              "required_run_count": len(resolved["required_cells"])}
    identity = {"protocol_root_id":digest(protocol(configs)), "config_hash":digest(config),
        **{k:catalog[k] for k in ("topology_hash","route_set_hash","action_catalog_hash","physics_hash","observation_catalog_hash")},
        "block_id":block,"scale_m":scale_m,"seeds":seeds,"policy":policy,
        "policy_kwargs":policy_config["kwargs"], "policy_class":policy_config["class"],
        "trace_contract":policy_config["trace"], "threat":threat,
        "scenario":resolved["scenarios"][threat],
        "threat_trajectory_hash":digest(mask.tolist()), "allocator":resolved["allocator"],
        "replay":resolved["replay"], "horizon":frames,
        "execution_frames":frames,"execution_kind":execution_kind,"code":code_identity()}
    manifest = {"schema_version":"medium-run-v2","run_id":run_identity(identity),"identity":identity,
                "execution_frames":frames,"configuration":config,
                "label":PREFLIGHT_LABEL if execution_kind=="technical_preflight" else "SCIENCE — SEPARATE APPROVAL REQUIRED"}
    return manifest,catalog,mask


def model_config_view(configs):
    """Execution-only view of canonical config, never a second policy registry."""
    if configs.persistence or configs.overwrite:
        raise ValueError("Immutable execution requires persistence=False, overwrite=False")
    view = copy(configs)
    view.algorithm_configs = deepcopy(configs.algorithm_configs)
    # Constructors multiply capacity at BOTH parent/child levels. Supply resolved
    # capacity once, with unit conversion disabled in this execution-only view.
    view.scale = 1
    view.cleanup_cooldown_seconds = 0
    return view


@contextmanager
def policy_rng(seed):
    # Restore surrounding process state so preflight tests do not leak global seeds.
    np_state, py_state, torch_state = np.random.get_state(), random.getstate(), torch.get_rng_state()
    deterministic = torch.are_deterministic_algorithms_enabled()
    threads = torch.get_num_threads()
    if torch.cuda.is_available():
        raise RuntimeError("This preflight is qualified for CPU only; GPU needs separate qualification")
    try:
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True)
        np.random.seed(seed)
        random.seed(seed)
        torch.manual_seed(seed)
        with threadpool_limits(limits=1):
            yield
    finally:
        np.random.set_state(np_state)
        random.setstate(py_state)
        torch.set_rng_state(torch_state)
        torch.use_deterministic_algorithms(deterministic)
        torch.set_num_threads(threads)


def model_state(model):
    """Read-only state snapshot for exact equivalence tests; not a resume format."""
    result = {"results":deepcopy(model.get_results())}
    if isinstance(model,EXPNeuralUCB):
        result["group_estimates"]=deepcopy(model.estimate_group_reward)
        result["neural"]=[{
            "parameters":{k:v.detach().cpu().clone() for k,v in n.net.state_dict().items()},
            "gradients":[None if p.grad is None else p.grad.detach().cpu().clone() for p in n.net.parameters()],
            "optimizer":deepcopy(n.optimizer.state_dict()), "sigma_inv":n.sigma_inv.copy(),
            "replay":deepcopy(n.replay_buffer.__dict__),"T":n.T,
        } for n in model.neuralucb_list]
    elif isinstance(model,CEpsilonGreedy):
        result["path_rewards"]=deepcopy(model.path_rewards)
        result["path_counts"]=deepcopy(model.path_counts)
        result["bandits"]=[deepcopy(b.bandit.__dict__) for b in model.path_bandits]
    else:
        result["current_frame"]=model.current_frame
    result["rng"]={"numpy":np.random.get_state(),"python":random.getstate(),"torch":torch.get_rng_state().clone()}
    return result


def run_policy(configs, policy, contexts, rewards, mask, seed, recorder=None, capture_state=False):
    """Registry-driven single attempt; no legacy retry/cache orchestration."""
    resolved = resolve_configuration(configs)
    if policy not in resolved["policies"]:
        raise ValueError("Unconfigured policy")
    entry = configs.algorithm_configs[policy]
    view = model_config_view(configs)
    with policy_rng(seed):
        model=entry["model_class"](configs=view,X_n=contexts,reward_list=rewards,
                                  frame_number=len(mask),attack_list=mask,
                                  capacity=resolved["replay"]["capacity"],**deepcopy(entry["kwargs"]))
        if model.mode != entry["kwargs"]["mode"] or model.capacity != resolved["replay"]["capacity"]:
            raise ValueError("Constructed policy contradicts resolved mode/capacity")
        if entry["runner_type"] == "batch":
            model.run(mask,verbose=False,event_sink=recorder)
        else:
            for frame in range(len(mask)):
                if recorder is not None:
                    recorder.preselection(frame,contexts)
                selected=model.take_action()
                if not isinstance(selected,tuple) or len(selected)!=2:
                    raise ValueError("HOLD: step-wise trace requires route/allocation action pair")
                route, action=selected
                if recorder is not None:
                    recorder.decision(frame,route,action)
                q=rewards[route][action]
                availability=mask[frame][route]
                continuous=q*availability
                if recorder is not None:
                    recorder.outcome(frame,q,availability,continuous)
                model.update(route,action,continuous)
                if recorder is not None:
                    recorder.update(frame,None,False,policy_target=continuous)
        return model.get_results(), model_state(model) if capture_state else None


def execute_preflight(output_root, configs, policy, threat, block, scale_m):
    """Bounded technical execution only; all choices are explicit configuration."""
    if configs.execution.execution_kind != "technical_preflight":
        raise ValueError("Scientific execution is not authorized by this entry point")
    frames=configs.execution.horizon
    manifest,catalog,mask=prepare_manifest(configs,policy,threat,block,scale_m=scale_m)
    validate_catalog(catalog)
    routes=tuple(PrimaryRoute(r["route_id"],tuple(r["link_rates"]),tuple(r["nodes"])) for r in catalog["routes"])
    env=RecordedQuantumEnvironment(attack=configs.resolve_attack_strategy(threat),availability=mask,
                           qubit_capacities=tuple(r["budget"] for r in catalog["observations"]["routes"]),
                           route_metadata=routes,num_paths=len(routes),frame_length=frames,
                           horizon_length=frames, external_topology=catalog["topology"],
                           num_total_qubits=configs.allocator.total_qubits,
                           seed=manifest["identity"]["seeds"]["environment"]["actual_seed"],
                           **configs.physics_params)
    for x,obs,q,expected in zip(env.contexts,catalog["observations"]["routes"],env.reward_list,catalog["physics"]["base_expected_payoffs"]):
        if not np.array_equal(x,obs["actions"]) or not np.array_equal(q,expected):
            raise ValueError("Environment/catalog mismatch")
    bundle=AttemptBundle(output_root,manifest,catalog,mask)
    try:
        start=time.perf_counter()
        results,_=run_policy(configs,policy,env.contexts,env.reward_list,mask,
                            manifest["identity"]["seeds"]["policy"]["actual_seed"],bundle.recorder)
        elapsed=time.perf_counter()-start
        # These legacy keys are confined to the test observation, never the raw event schema.
        summary={"label":PREFLIGHT_LABEL,"frames_exercised":frames,
                 "policy":policy,"wall_seconds":elapsed,
                 "selected_pairs":[list(map(int,p)) for p in results["path_action_list"]],
                 "cumulative_continuous_payoff":float(results["final_reward"])}
        write_json_exclusive(bundle.directory/"technical_summary.json",summary)
        completion=bundle.finish()
        validate_completion(bundle.directory,manifest)
        return bundle.directory,completion
    except BaseException as error:
        if not bundle.terminal:
            kind="interruption" if isinstance(error,KeyboardInterrupt) else "technical_fault"
            bundle.finish("INTERRUPTED" if isinstance(error,KeyboardInterrupt) else "FAILED",kind,str(error) or type(error).__name__)
        raise


def main():
    raise SystemExit("Supply explicit ExperimentConfiguration to execute_preflight; no scientific/default CLI preset.")


if __name__=="__main__":
    main()
