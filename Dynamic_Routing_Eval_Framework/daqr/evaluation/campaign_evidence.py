"""Q-04 deterministic seeds and immutable per-cell execution evidence."""
from hashlib import sha256
import json
import os
from pathlib import Path

import numpy as np

from daqr.core.identity import canonical_json, digest


def stable_environment_seed(configs, frames, threat=None, block=None):
    """Return a process-stable environment seed for an opted-in campaign."""
    namespace = getattr(configs, "scientific_seed_namespace", None)
    if not namespace:
        return None
    threat = str(threat if threat is not None else configs.attack_type)
    block = int(block if block is not None else getattr(configs, "scientific_block_id", 0))
    campaign_seed = int(getattr(configs, "scientific_campaign_base_seed", configs.base_seed))
    payload = {
        "namespace": str(namespace),
        "base_seed": campaign_seed,
        "block": block,
        "threat": threat,
        "frames": int(frames),
        "domain": "environment",
    }
    offset = int(sha256(canonical_json(payload).encode("utf-8")).hexdigest()[:8], 16) % 10000
    return campaign_seed + offset


def _write_immutable(path, encoded):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != encoded:
            raise ValueError(f"Existing campaign evidence differs: {path}")
        return path
    with path.open("x", encoding="utf-8") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    return path


def _write_immutable_json(path, payload):
    return _write_immutable(path, canonical_json(payload) + "\n")


def _write_immutable_jsonl(path, rows):
    return _write_immutable(path, "".join(canonical_json(row) + "\n" for row in rows))


def file_hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def _outcome_summary(result):
    result = result if isinstance(result, dict) else {}
    return {
        "status": "failed" if result.get("error") else "completed",
        "final_reward": float(result.get("final_reward", 0.0) or 0.0),
        "avg_reward": float(result.get("avg_reward", 0.0) or 0.0),
        "efficiency": float(result.get("efficiency", 0.0) or 0.0),
        "gap": float(result.get("gap", 0.0) or 0.0),
        "error": str(result.get("error")) if result.get("error") else None,
        "technical_attempts": int(result.get("retries", 0) or 0) + 1,
        "performance_reruns": 0,
    }


def _catalog_payload(configs, block):
    payload = getattr(configs, "scientific_trace_catalogs", {}).get(int(block))
    if not payload:
        raise ValueError(f"Missing trace catalog for scientific block {block}")
    return payload


def _availability_and_rewards(environment, frames, routes):
    if environment is None:
        return [], []
    try:
        env_info = environment.get_environment_info()
    except Exception:
        return [], []
    availability = np.asarray(env_info["attack_pattern"], dtype=int)
    rewards = [np.asarray(values, dtype=float) for values in env_info["reward_functions"]]
    if availability.shape != (int(frames), int(routes)):
        raise ValueError(
            f"Availability shape {availability.shape} != {(int(frames), int(routes))}"
        )
    if not np.isin(availability, [0, 1]).all():
        raise ValueError("Availability trajectory must be binary")
    return availability.tolist(), [values.tolist() for values in rewards]


def _event_rows(result_identity, identity, result, catalog, availability, rewards, frames):
    model_results = result.get("model_results", {}) if isinstance(result, dict) else {}
    trajectory = model_results.get("path_action_list", []) if isinstance(model_results, dict) else []
    if len(trajectory) != int(frames):
        raise ValueError(
            f"Policy trajectory has {len(trajectory)} decisions; expected {int(frames)}"
        )
    observations = catalog["observations"]["routes"]
    catalog_payoffs = catalog["physics"]["base_expected_payoffs"]
    if len(observations) != len(rewards) or len(observations) != len(availability[0]):
        raise ValueError("Catalog/environment route counts differ")
    for route_index, values in enumerate(rewards):
        if not np.allclose(values, catalog_payoffs[route_index], rtol=0.0, atol=0.0):
            raise ValueError(f"Environment/catalog rewards differ for route {route_index}")

    rows = []
    for frame, selected in enumerate(trajectory):
        if not isinstance(selected, (list, tuple)) or len(selected) != 2:
            raise ValueError(f"Invalid path/action record at frame {frame}: {selected}")
        route_index, action_index = (int(selected[0]), int(selected[1]))
        if route_index < 0 or route_index >= len(observations):
            raise ValueError(f"Invalid route index at frame {frame}: {route_index}")
        actions = observations[route_index]["actions"]
        if action_index < 0 or action_index >= len(actions):
            raise ValueError(f"Invalid action index at frame {frame}: {action_index}")
        decision_id = f"{result_identity}:{frame}"
        common = {
            "schema_version": "q04-cell-events-v1",
            "result_identity": result_identity,
            "decision_id": decision_id,
            "frame": frame,
            "block": identity["block"],
            "threat": identity["threat"],
            "policy": identity["policy"],
            "catalog_identity": identity["catalog_identity"],
            "trajectory_identity": identity["threat_trajectory_identity"],
        }
        route_id = observations[route_index]["route_id"]
        allocation = actions[action_index]
        rows.append({
            **common,
            "phase": "DECISION",
            "event_id": f"{decision_id}:DECISION",
            "selected_route_index": route_index,
            "selected_route_id": route_id,
            "selected_action_index": action_index,
            "selected_allocation": allocation,
        })
        base_payoff = float(rewards[route_index][action_index])
        available = int(availability[frame][route_index])
        rows.append({
            **common,
            "phase": "OUTCOME",
            "event_id": f"{decision_id}:OUTCOME",
            "selected_route_index": route_index,
            "selected_route_id": route_id,
            "selected_action_index": action_index,
            "base_expected_payoff": base_payoff,
            "availability": available,
            "selected_continuous_payoff": base_payoff * available,
            "quantity_semantics": "expected routing payoff used by the proven AllocatorRunner workflow",
        })
    return rows


def _validate_cell_bundle(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    availability = json.loads((directory / "availability.json").read_text(encoding="utf-8"))
    result = json.loads((directory / "result.json").read_text(encoding="utf-8"))
    completion = json.loads((directory / "completion.json").read_text(encoding="utf-8"))
    if digest(manifest) != completion["manifest_hash"]:
        raise ValueError("Manifest hash mismatch")
    if digest(availability) != manifest["identity"]["threat_trajectory_identity"]:
        raise ValueError("Availability trajectory hash mismatch")
    for name, expected in completion["file_hashes"].items():
        if file_hash(directory / name) != expected:
            raise ValueError(f"Cell evidence hash mismatch: {name}")
    rows = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]
    expected_frames = int(manifest["identity"]["frames"])
    if completion["status"] == "completed":
        if len(availability) != expected_frames or len(rows) != expected_frames * 2:
            raise ValueError("Completed cell has incomplete trajectory/event evidence")
        for frame in range(expected_frames):
            decision, outcome = rows[2 * frame : 2 * frame + 2]
            if decision["phase"] != "DECISION" or outcome["phase"] != "OUTCOME":
                raise ValueError("Invalid event phase order")
            if decision["decision_id"] != outcome["decision_id"]:
                raise ValueError("Decision/outcome join mismatch")
            if decision["selected_route_index"] != outcome["selected_route_index"]:
                raise ValueError("Decision/outcome route mismatch")
            route = outcome["selected_route_index"]
            if outcome["availability"] != availability[frame][route]:
                raise ValueError("Outcome/availability mismatch")
            if not np.isclose(
                outcome["selected_continuous_payoff"],
                outcome["base_expected_payoff"] * outcome["availability"],
            ):
                raise ValueError("Outcome payoff mismatch")
    if result["result_identity"] != manifest["result_identity"]:
        raise ValueError("Result/manifest identity mismatch")
    return completion


def record_experiment_evidence(
    configs, experiment_results, block, threat, frames, environment=None
):
    """Write an immutable availability, event, outcome, and completion bundle per policy."""
    root_value = getattr(configs, "scientific_evidence_root", None)
    if not root_value:
        return []
    root = Path(root_value).expanduser().resolve()
    catalog_identity = getattr(configs, "scientific_catalog_identities", {}).get(int(block))
    if not catalog_identity:
        raise ValueError(f"Missing catalog identity for scientific block {block}")
    catalog = _catalog_payload(configs, block)
    availability, rewards = _availability_and_rewards(environment, frames, len(catalog["routes"]))
    results = experiment_results.get("results", {}) if isinstance(experiment_results, dict) else {}
    campaign_seed = int(getattr(configs, "scientific_campaign_base_seed", configs.base_seed))
    config_identity = digest({
        "namespace": getattr(configs, "scientific_seed_namespace", None),
        "models": list(configs.models),
        "scenarios": list(configs.test_scenarios),
        "runs": int(configs.runs),
        "scale": configs.scale,
        "base_capacity": bool(configs.base_capacity),
        "campaign_base_seed": campaign_seed,
        "frames": int(frames),
        "allocator": str(configs.allocator),
        "disable_outcome_retries": bool(getattr(configs, "disable_outcome_retries", False)),
    })
    env_seed = stable_environment_seed(configs, frames, threat=threat, block=block)
    threat_trajectory_identity = digest(availability)
    receipts = []
    for policy in configs.models:
        result = results.get(policy, {"error": "missing policy result", "final_reward": 0.0})
        actual_seed = int(env_seed + int(configs.algorithm_configs[policy]["seed_offset"]))
        reported_seed = result.get("seed") if isinstance(result, dict) else None
        if reported_seed is not None and int(reported_seed) != actual_seed:
            raise ValueError(f"Reported seed mismatch for {policy}: {reported_seed} != {actual_seed}")
        identity = {
            "namespace": getattr(configs, "scientific_seed_namespace", None),
            "allocator": str(configs.allocator),
            "block": int(block),
            "threat": str(threat),
            "policy": str(policy),
            "frames": int(frames),
            "environment_seed": int(env_seed),
            "actual_seed": actual_seed,
            "config_identity": config_identity,
            "catalog_identity": catalog_identity,
            "threat_trajectory_identity": threat_trajectory_identity,
        }
        result_identity = digest(identity)
        bundle = root / "cells" / result_identity
        summary = _outcome_summary(result)
        manifest = {
            "schema_version": "q04-cell-manifest-v2",
            "result_identity": result_identity,
            "identity": identity,
            "evidence_contract": {
                "availability": "full binary route-availability trajectory",
                "events": "joined route/action decisions and selected continuous outcomes",
                "source": "real daqr.evaluation.allocator_runner.AllocatorRunner workflow",
            },
        }
        rows = []
        if summary["status"] == "completed":
            try:
                rows = _event_rows(
                    result_identity, identity, result, catalog, availability, rewards, frames
                )
            except Exception as error:
                summary["status"] = "failed"
                summary["error"] = f"evidence capture failed: {error}"
        result_payload = {
            "schema_version": "q04-cell-result-v2",
            "result_identity": result_identity,
            "outcome": summary,
        }
        _write_immutable_json(bundle / "manifest.json", manifest)
        _write_immutable_json(bundle / "availability.json", availability)
        _write_immutable_jsonl(bundle / "events.jsonl", rows)
        _write_immutable_json(bundle / "result.json", result_payload)
        completion = {
            "schema_version": "q04-cell-completion-v2",
            "result_identity": result_identity,
            "status": summary["status"],
            "manifest_hash": digest(manifest),
            "expected_frames": int(frames),
            "availability_frames": len(availability),
            "decision_event_count": sum(row["phase"] == "DECISION" for row in rows),
            "outcome_event_count": sum(row["phase"] == "OUTCOME" for row in rows),
            "file_hashes": {
                name: file_hash(bundle / name)
                for name in ("manifest.json", "availability.json", "events.jsonl", "result.json")
            },
        }
        completion_path = _write_immutable_json(bundle / "completion.json", completion)
        if completion["status"] == "completed":
            _validate_cell_bundle(bundle)
        receipt = {
            "schema_version": "q04-cell-receipt-v2",
            "result_identity": result_identity,
            "identity": identity,
            "status": completion["status"],
            "bundle_path": str(bundle),
            "completion_path": str(completion_path),
            "completion_sha256": file_hash(completion_path),
        }
        receipt_path = _write_immutable_json(root / "receipts" / f"{result_identity}.json", receipt)
        receipts.append(receipt_path)
    return receipts


def record_experiment_failure(configs, block, threat, frames, error, environment=None):
    results = {policy: {"error": str(error), "final_reward": 0.0} for policy in configs.models}
    return record_experiment_evidence(
        configs,
        {"results": results},
        block=block,
        threat=threat,
        frames=frames,
        environment=environment,
    )


def finalize_campaign_evidence(configs):
    """Validate complete accounting and write a campaign-level receipt."""
    root = Path(configs.scientific_evidence_root).expanduser().resolve()
    receipts = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((root / "receipts").glob("*.json"))
    ]
    expected = {
        (block, threat, policy)
        for block in range(int(configs.runs))
        for threat in configs.test_scenarios
        for policy in configs.models
    }
    present = {
        (item["identity"]["block"], item["identity"]["threat"], item["identity"]["policy"])
        for item in receipts
    }
    if present != expected or len(receipts) != len(expected):
        raise ValueError(
            f"Incomplete campaign evidence: missing={sorted(expected - present)}, "
            f"extra={sorted(present - expected)}"
        )
    for item in receipts:
        if file_hash(item["completion_path"]) != item["completion_sha256"]:
            raise ValueError(f"Completion hash mismatch: {item['completion_path']}")
        completion = _validate_cell_bundle(item["bundle_path"])
        if completion["status"] != item["status"]:
            raise ValueError(f"Receipt/completion status mismatch: {item['result_identity']}")
    status_counts = {
        status: sum(item["status"] == status for item in receipts)
        for status in ("completed", "failed")
    }
    completion = {
        "schema_version": "q04-campaign-receipt-v2",
        "namespace": getattr(configs, "scientific_seed_namespace", None),
        "required_cells": len(expected),
        "accounted_cells": len(receipts),
        "state": "COMPLETE" if status_counts["failed"] == 0 else "FAILED",
        "status_counts": status_counts,
        "receipt_hashes": {
            item["result_identity"]: file_hash(
                root / "receipts" / f"{item['result_identity']}.json"
            )
            for item in receipts
        },
    }
    return _write_immutable_json(root / "campaign-receipt.json", completion)
