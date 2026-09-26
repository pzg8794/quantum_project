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
from types import SimpleNamespace

import numpy as np
import torch
from threadpoolctl import threadpool_limits

from daqr.algorithms.base_bandit import Oracle
from daqr.algorithms.neural_bandits import EXPNeuralUCB
from daqr.algorithms.predictive_bandits import CEpsilonGreedy
from daqr.core.attack_strategy import NoAttack
from daqr.core.network_environment import QuantumEnvironment
from daqr.core.primary_routes import PrimaryRoute
from daqr.campaigns.medium_spec import (
    PROTOCOL, PROTOCOL_ROOT_ID, POLICY_KWARGS, build_catalog, build_mask,
    seed_manifest, digest, canonical_json, validate_catalog,
)
from daqr.campaigns.medium_trace import AttemptBundle, run_identity, validate_completion, write_json_exclusive

FRAME_LIMIT = 64
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


def prepare_manifest(policy, threat, block=0, *, execution_kind="technical_preflight", frames=8, scale_m=3):
    if execution_kind not in ("technical_preflight","scientific"):
        raise ValueError("Unknown execution kind")
    if execution_kind == "technical_preflight" and not 1 <= frames <= FRAME_LIMIT:
        raise ValueError("Preflight frame limit exceeded")
    if execution_kind == "scientific" and frames != 6000:
        raise ValueError("Scientific horizon is frozen at 6000")
    catalog = build_catalog(block,scale_m)
    seeds = seed_manifest(block,policy,threat,scale_m)
    mask = build_mask(threat,frames,block,scale_m)
    config = {"protocol":deepcopy(PROTOCOL), "policy":policy, "policy_kwargs":deepcopy(POLICY_KWARGS[policy]),
              "threat":threat, "effective_interruption":0.0625 if threat=="RandomAttack" else 0.0,
              "scale_m":scale_m, "capacity_applies":policy=="EXPNeuralUCB",
              "cepsilon_effective_defaults":{"epsilon":0.1,"learning_rate":0.1,"n_experts":1},
              "neural_defaults":{"hidden_size":128,"learning_rate":1e-4,"regularization":0.000625,"lambda":1,
                                 "train_after_within_route_pulls":55,"epochs_per_update":2,"batch_size":64},
              "interpretation":"sparse-feedback stress condition" if policy=="EXPNeuralUCB" else "configured policy/reference"}
    identity = {"protocol_root_id":PROTOCOL_ROOT_ID, "config_hash":digest(config),
        **{k:catalog[k] for k in ("topology_hash","route_set_hash","action_catalog_hash","physics_hash","observation_catalog_hash")},
        "block_id":block,"scale_m":scale_m,"seeds":seeds,"policy":policy,
        "policy_kwargs":deepcopy(POLICY_KWARGS[policy]), "threat":threat,
        "threat_trajectory_hash":digest(mask.tolist()), "allocator":{"name":"fixed-equal","per_route":9,"total":9*(3*scale_m+1)},
        "replay":{"anchor":"T_b","scale":2,"capacity":12000,"applies":policy=="EXPNeuralUCB"},
        "horizon":6000,"execution_frames":frames,"execution_kind":execution_kind,"code":code_identity()}
    manifest = {"schema_version":"medium-run-v1","run_id":run_identity(identity),"identity":identity,
                "execution_frames":frames,"configuration":config,
                "label":PREFLIGHT_LABEL if execution_kind=="technical_preflight" else "SCIENCE — SEPARATE APPROVAL REQUIRED"}
    return manifest,catalog,mask


class CampaignModelConfig:
    """Minimal real-policy config with legacy persistence unavailable by design."""
    def __init__(self):
        self.overwrite=False
        self.verbose=False
        self.cleanup_cooldown_seconds=0
        self.scale=1  # capacity is already the final 12000; do not double it twice
        self.base_capacity=True
        self.base_model=None
        self.dir="."
        self.day_str="campaign-managed"
        self.allocator="fixed-equal"
        self.environment="primary-route-metadata"
        self.attack_strategy="external-immutable-mask"
        self.algorithm_configs={p:{"kwargs":deepcopy(k)} for p,k in POLICY_KWARGS.items()}
        self.algorithm_configs["NeuralUCB"]={"kwargs":{"mode":"neural"}}
        self.backup_mgr=SimpleNamespace(mode="campaign",quantum_data_paths={"obj":{"model_state":{"campaign":Path("campaign-managed-no-legacy-io")}}})

    def can_resume(self, model):
        return True  # suppress submodel fallback; no legacy resume path is consulted

    def resume_obj(self, model):
        return False

    def save_obj(self, model):
        raise RuntimeError("Campaign persistence belongs exclusively to AttemptBundle")


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


def run_policy(policy, contexts, rewards, mask, seed, recorder=None, capture_state=False):
    """Single execution, no retry or cache. Called only by the bounded entry point/tests."""
    frames=len(mask)
    configs=CampaignModelConfig()
    kwargs=deepcopy(POLICY_KWARGS[policy])
    classes={"Oracle":Oracle,"CEpsilonGreedy":CEpsilonGreedy,"EXPNeuralUCB":EXPNeuralUCB}
    with policy_rng(seed):
        # No learner receives a selector argument containing the mask or q table.
        # Existing models retain these internally for outcome/reference bookkeeping.
        model=classes[policy](configs=configs,X_n=contexts,reward_list=rewards,
                              frame_number=frames,attack_list=mask,capacity=12000,**kwargs)
        if policy=="CEpsilonGreedy" and (model.epsilon,model.learning_rate,model.n_experts)!=(0.1,0.1,1):
            raise ValueError("Inherited CEpsilonGreedy defaults changed")
        if policy=="EXPNeuralUCB":
            if model.mode != "hybrid" or any(n.replay_buffer.capacity!=12000 for n in model.neuralucb_list):
                raise ValueError("Hybrid mode/replay invariant failed")
            model.run(mask,verbose=False,event_sink=recorder)
        else:
            for frame in range(frames):
                if recorder is not None:
                    recorder.preselection(frame,contexts)
                route, action=model.take_action()
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


def execute_preflight(output_root, policy="EXPNeuralUCB", threat="RandomAttack", block=0, frames=8):
    """At most 64 frames. Never launches a 6000-frame scientific unit."""
    manifest,catalog,mask=prepare_manifest(policy,threat,block,frames=frames)
    validate_catalog(catalog)
    routes=tuple(PrimaryRoute(r["route_id"],tuple(r["link_rates"]),tuple(r["nodes"])) for r in catalog["routes"])
    env=QuantumEnvironment(NoAttack(),qubit_capacities=(9,)*10,route_metadata=routes,num_paths=10,num_total_qubits=90)
    for x,obs,q,expected in zip(env.contexts,catalog["observations"]["routes"],env.reward_list,catalog["physics"]["base_expected_payoffs"]):
        if not np.array_equal(x,obs["actions"]) or not np.array_equal(q,expected):
            raise ValueError("Environment/catalog mismatch")
    bundle=AttemptBundle(output_root,manifest,catalog,mask)
    try:
        start=time.perf_counter()
        results,_=run_policy(policy,env.contexts,env.reward_list,mask,
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
    import argparse
    parser=argparse.ArgumentParser(description=PREFLIGHT_LABEL)
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--policy",choices=tuple(POLICY_KWARGS),default="EXPNeuralUCB")
    parser.add_argument("--threat",choices=("NoAttack","RandomAttack"),default="RandomAttack")
    parser.add_argument("--frames",type=int,default=8)
    args=parser.parse_args()
    directory,completion=execute_preflight(args.output,args.policy,args.threat,frames=args.frames)
    print(canonical_json({"label":PREFLIGHT_LABEL,"bundle":str(directory),"completion":completion}))


if __name__=="__main__":
    main()
