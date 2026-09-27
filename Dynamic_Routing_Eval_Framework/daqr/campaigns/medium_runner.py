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

from daqr.core.scenario_execution import ScenarioSession
from daqr.campaigns.medium_spec import (
    build_catalog, build_scenario, protocol,
    seed_manifest, digest, canonical_json, validate_catalog,
)
from daqr.campaigns.medium_trace import AttemptBundle, run_identity, validate_completion, write_json_exclusive

FRAME_LIMIT = 512  # technical safety ceiling, not a scientific horizon
PREFLIGHT_LABEL = "TECHNICAL PREFLIGHT — NOT SCIENTIFIC EVIDENCE"
SCIENTIFIC_LABEL = "SCIENTIFIC EVIDENCE — F-08 TIER-1"


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
    session = build_scenario(configs, threat, frames, block, scale_m, len(catalog["routes"]))
    mask = session.precomputed if session.precomputed is not None else session
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
        "threat_trajectory_hash":digest(session.precomputed.tolist()) if session.precomputed is not None else None,
        "scenario_chronology":"availability-before-selection; history-through-t-minus-1; observe-after-update",
        "trajectory_kind":"exogenous-precomputed" if session.precomputed is not None else "policy-reactive-causal", "allocator":resolved["allocator"],
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
    snapshot = getattr(model, "diagnostic_snapshot", None)
    if snapshot is not None:
        result.update(deepcopy(snapshot()))
    result["rng"]={"numpy":np.random.get_state(),"python":random.getstate(),"torch":torch.get_rng_state().clone()}
    return result


def run_policy(configs, policy, contexts, rewards, mask, seed, recorder=None, capture_state=False):
    """Registry-driven single attempt; no legacy retry/cache orchestration."""
    resolved = resolve_configuration(configs)
    if policy not in resolved["policies"]:
        raise ValueError("Unconfigured policy")
    entry = configs.algorithm_configs[policy]
    view = model_config_view(configs)
    session = mask if isinstance(mask, ScenarioSession) else None
    availability = session.policy_mask if session is not None else mask
    causal = session is not None and session.precomputed is None
    view.causal_scenario_execution = causal
    if causal and not getattr(entry["model_class"], "supports_causal_scenarios", False):
        raise ValueError("HOLD: policy does not declare causal scenario support")
    with policy_rng(seed):
        model=entry["model_class"](configs=view,X_n=contexts,reward_list=rewards,
                                  frame_number=len(mask),attack_list=availability,
                                  capacity=resolved["replay"]["capacity"],**deepcopy(entry["kwargs"]))
        validator = getattr(model, "validate_execution_instance", None)
        if validator is not None:
            validator(entry["kwargs"], resolved["replay"]["capacity"])
        if entry["runner_type"] == "batch":
            extra = {"scenario_session": session} if session is not None else {}
            model.run(availability,verbose=False,event_sink=recorder,**extra)
        else:
            for frame in range(len(mask)):
                if session is not None:
                    row = session.begin(frame)
                    frame_hook = getattr(model, "prepare_scenario_frame", None)
                    if causal and frame_hook is not None:
                        frame_hook(frame,row)
                if recorder is not None:
                    recorder.preselection(frame,contexts)
                selected=model.take_action()
                if not isinstance(selected,tuple) or len(selected)!=2:
                    raise ValueError("HOLD: step-wise trace requires route/allocation action pair")
                route, action=selected
                if recorder is not None:
                    recorder.decision(frame,route,action)
                q=rewards[route][action]
                selected_availability=availability[frame][route]
                continuous=q*selected_availability
                if recorder is not None:
                    recorder.outcome(frame,q,selected_availability,continuous)
                model.update(route,action,continuous)
                if recorder is not None:
                    recorder.update(frame,None,False,policy_target=continuous)
                if session is not None:
                    session.observe(frame,route)
        return model.get_results(), model_state(model) if capture_state else None


def execute_preflight(output_root, configs, policy, threat, block, scale_m):
    """Bounded technical execution only; all choices are explicit configuration."""
    if configs.execution.execution_kind != "technical_preflight":
        raise ValueError("Scientific execution is not authorized by this entry point")
    frames=configs.execution.horizon
    manifest,catalog,mask=prepare_manifest(configs,policy,threat,block,scale_m=scale_m)
    validate_catalog(catalog)
    contexts = [np.asarray(r["actions"]) for r in catalog["observations"]["routes"]]
    rewards = catalog["physics"]["base_expected_payoffs"]
    bundle=AttemptBundle(output_root,manifest,catalog,mask)
    try:
        start=time.perf_counter()
        results,_=run_policy(configs,policy,contexts,rewards,mask,
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


def execute_scientific(output_root, configs, policy, threat, block, scale_m, *, reuse_completed=True):
    """Execute one explicitly configured scientific cell into an immutable bundle."""
    if configs.execution.execution_kind != "scientific":
        raise ValueError("Scientific execution requires execution_kind='scientific'")
    frames = configs.execution.horizon
    manifest, catalog, mask = prepare_manifest(
        configs, policy, threat, block, scale_m=scale_m
    )
    validate_catalog(catalog)
    existing = Path(output_root) / manifest["run_id"] / "attempt-1"
    if existing.exists():
        if not reuse_completed:
            raise FileExistsError(f"Scientific bundle already exists: {existing}")
        completion = validate_completion(existing, manifest)
        return existing, completion, True

    contexts = [np.asarray(route["actions"]) for route in catalog["observations"]["routes"]]
    rewards = catalog["physics"]["base_expected_payoffs"]
    bundle = AttemptBundle(output_root, manifest, catalog, mask)
    try:
        results, _ = run_policy(
            configs,
            policy,
            contexts,
            rewards,
            mask,
            manifest["identity"]["seeds"]["policy"]["actual_seed"],
            bundle.recorder,
        )
        cumulative = float(results["final_reward"])
        summary = {
            "schema_version": "medium-scientific-summary-v1",
            "label": SCIENTIFIC_LABEL,
            "policy": policy,
            "threat": threat,
            "block": int(block),
            "scale_m": int(scale_m),
            "frames": int(frames),
            "selected_pair_count": len(results["path_action_list"]),
            "cumulative_continuous_payoff": cumulative,
            "mean_continuous_payoff_per_frame": cumulative / frames,
        }
        write_json_exclusive(bundle.directory / "scientific_summary.json", summary)
        completion = bundle.finish()
        validate_completion(bundle.directory, manifest)
        return bundle.directory, completion, False
    except BaseException as error:
        if not bundle.terminal:
            kind = "interruption" if isinstance(error, KeyboardInterrupt) else "technical_fault"
            state = "INTERRUPTED" if isinstance(error, KeyboardInterrupt) else "FAILED"
            bundle.finish(state, kind, str(error) or type(error).__name__)
        raise


def main():
    raise SystemExit("Supply explicit ExperimentConfiguration to execute_preflight; no scientific/default CLI preset.")


if __name__=="__main__":
    main()
