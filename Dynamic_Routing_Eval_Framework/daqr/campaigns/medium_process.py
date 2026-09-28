"""Process-isolated acceleration for the frozen medium Tier-1 campaign."""

from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import multiprocessing
import os
from pathlib import Path

from daqr.campaigns.medium_execution_evidence import finalize_medium_campaign
from daqr.campaigns.medium_tier1 import (
    BASE_SEED,
    MODEL_ROSTER,
    SCENARIOS,
    catalog_configuration,
    install_block_payloads,
    runtime_configuration,
)


def _run_scenario_worker(job):
    scenario = job["scenario"]
    output_root = Path(job["output_root"]).expanduser().resolve()
    state_root = output_root / "process-state" / scenario
    os.environ["DAQR_AGGREGATE_STATE"] = "0"
    os.environ["DAQR_ENABLE_PLOTS"] = "0"

    config, framework = runtime_configuration(
        output_root,
        base_frames=job["base_frames"],
        execution_kind=job["execution_kind"],
        state_root=state_root,
    )
    install_block_payloads(config, framework, job["execution_kind"])
    config.suffix = framework["medium_tier1"]["state_suffix"]
    config.runs = 3
    config.scale = 2

    from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator

    evaluator = MultiRunEvaluator(
        configs=config,
        base_frames=job["base_frames"],
        frame_step=0,
        base_seed=BASE_SEED,
        runs=3,
        models=list(MODEL_ROSTER),
        scenarios=deepcopy(SCENARIOS),
        attack_intensity=framework["intensity"],
    )
    try:
        evaluator.configs.set_log_name(
            base_frames=job["base_frames"],
            frame_step=0,
        )
        evaluator.configs.backup_mgr.init_logging_redirect(evaluator)
        evaluator.run_scenario_model_evaluation(
            runs=3,
            models=list(MODEL_ROSTER),
            attack_type=scenario,
            threaded=False,
        )
        bundle_paths = [
            str(path)
            for path in config.execution_evidence_plugin._bundle_paths
        ]
        if len(bundle_paths) != 15:
            raise RuntimeError(
                f"Scenario {scenario} produced {len(bundle_paths)} bundles, expected 15"
            )
        return {"scenario": scenario, "bundle_paths": bundle_paths}
    finally:
        try:
            evaluator.configs.backup_mgr.stop_logging_redirect()
        finally:
            evaluator.cleanup(verbose=False, cooldown_seconds=0)


def run_process_isolated_campaign(
    output_root,
    base_frames=6000,
    execution_kind="scientific",
    max_workers=None,
):
    output_root = Path(output_root).expanduser().resolve()
    evidence_root = output_root / "q04-evidence"
    if (evidence_root / "campaign-receipt.json").exists():
        raise FileExistsError("Campaign receipt already exists")
    if evidence_root.exists() and any(evidence_root.glob("*/attempt-*")):
        raise FileExistsError("Process campaign requires a fresh evidence root")
    output_root.mkdir(parents=True, exist_ok=True)

    worker_count = max_workers or min(len(SCENARIOS), os.cpu_count() or 1)
    if worker_count < 1:
        raise ValueError("max_workers must be positive")
    worker_count = min(int(worker_count), len(SCENARIOS))
    jobs = [
        {
            "scenario": scenario,
            "output_root": str(output_root),
            "base_frames": int(base_frames),
            "execution_kind": execution_kind,
        }
        for scenario in SCENARIOS
    ]

    results = []
    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(
        max_workers=worker_count,
        mp_context=context,
        max_tasks_per_child=1,
    ) as executor:
        futures = {
            executor.submit(_run_scenario_worker, job): job["scenario"]
            for job in jobs
        }
        for future in as_completed(futures):
            results.append(future.result())

    if {item["scenario"] for item in results} != set(SCENARIOS):
        raise RuntimeError("Process campaign did not complete every scenario group")
    if sum(len(item["bundle_paths"]) for item in results) != 75:
        raise RuntimeError("Process campaign did not produce all 75 bundles")

    validation_config = catalog_configuration(
        base_frames,
        execution_kind,
        BASE_SEED,
        (9,) * 10,
    )
    return finalize_medium_campaign(
        evidence_root,
        validation_config,
        scale_m=3,
    )
