"""Passive, phase-ordered campaign events and immutable attempt bundles."""
from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
import time

import numpy as np

from daqr.campaigns.medium_spec import canonical_json, digest
from daqr.core.scenario_execution import ScenarioSession

PHASES = ("PRESELECTION", "DECISION", "OUTCOME", "UPDATE")
EXP3_NEURAL_FEEDBACK = "bernoulli-route-continuous-allocation-v2"
DIRECT_BERNOULLI_NEURAL_FEEDBACK = "bernoulli-route-direct-continuous-allocation-v1"
DIRECT_CONTINUOUS_NEURAL_FEEDBACK = "continuous-route-direct-continuous-allocation-v1"
NEURAL_ALLOCATION_FEEDBACK = {
    EXP3_NEURAL_FEEDBACK,
    DIRECT_BERNOULLI_NEURAL_FEEDBACK,
    DIRECT_CONTINUOUS_NEURAL_FEEDBACK,
}
BERNOULLI_FEEDBACK = {
    EXP3_NEURAL_FEEDBACK,
    DIRECT_BERNOULLI_NEURAL_FEEDBACK,
}


def file_hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write_json_exclusive(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        stream.write(canonical_json(value) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


class EventRecorder:
    """Records copies of existing values; performs no selection or RNG calls."""

    def __init__(self, manifest, catalog, attempt_no=1, directory=None):
        self.manifest = manifest
        self.catalog = catalog
        self.attempt_no = attempt_no
        self.frames = manifest["execution_frames"]
        self.sequence = 0
        self.counts = Counter()
        self.positive_route_feedback_count = 0
        self.allocation_update_count = 0
        self.events = [] if directory is None else None
        self.stream = (Path(directory)/"events.jsonl").open("x", encoding="utf-8") if directory else None
        self.selected = None

    def _emit(self, phase, frame, **fields):
        if phase != PHASES[self.sequence % 4] or frame != self.sequence // 4 or frame >= self.frames:
            raise ValueError("Event phase/frame order violation")
        identity = self.manifest["identity"]
        row = {"schema_version": "medium-events-v2", "phase": phase, "frame": int(frame),
               "event_id": f"{self.manifest['run_id']}:{self.attempt_no}:{frame}:{phase}",
               "decision_id": f"{self.manifest['run_id']}:{self.attempt_no}:{frame}",
               "protocol_root_id": identity["protocol_root_id"], "run_id": self.manifest["run_id"],
               "attempt_no": self.attempt_no, "block_id": identity["block_id"],
               "topology_hash": identity["topology_hash"], "route_set_hash": identity["route_set_hash"],
               "threat_trajectory_hash": identity["threat_trajectory_hash"],
               "policy": identity["policy"], "threat": identity["threat"],
               "seed_identity_hash": digest(identity["seeds"]),
               "environment_seed": identity["seeds"]["environment"]["actual_seed"],
               "threat_seed": identity["seeds"]["threat"]["actual_seed"],
               "policy_seed": identity["seeds"]["policy"]["actual_seed"],
               "frame_time_unit": "simulator_decision_index", **fields}
        # Round-trip detaches every mutable value from the policy.
        encoded = canonical_json(row)
        if self.stream:
            self.stream.write(encoded + "\n")
            self.stream.flush()  # partial trace survives interruption; no model checkpoint claim
        else:
            self.events.append(json.loads(encoded))
        self.counts[phase] += 1
        self.sequence += 1

    def preselection(self, frame, contexts):
        observation = self.catalog["observations"]
        if len(contexts) != len(observation["routes"]):
            raise ValueError("Unexpected dynamic context count")
        if any(not np.array_equal(x, r["actions"]) for x,r in zip(contexts,observation["routes"])):
            raise ValueError("Context changed without a versioned snapshot")
        self._emit("PRESELECTION", frame, observation_kind=observation["observation_kind"],
                   observation_catalog_hash=self.catalog["observation_catalog_hash"],
                   observation_version=observation["version"],
                   producer=self.manifest["configuration"]["resolved"]["components"]["catalog"]["component_id"],
                   link_measurements_present=observation["link_measurements_present"], history_cutoff_frame=frame-1,
                   policy_state_version=f"after-{frame}-updates",
                   information_regime="privileged_reference" if self.manifest["identity"]["trace_contract"]["privileged"] else "past-feedback-and-allocation-context")

    def decision(self, frame, route, action, probabilities=None):
        route, action = int(route), int(action)
        if route < 0 or route >= len(self.catalog["routes"]):
            raise ValueError("Invalid selected route")
        obs = self.catalog["observations"]["routes"][route]
        if action < 0 or action >= len(obs["actions"]):
            raise ValueError("Invalid selected allocation")
        probs = None if probabilities is None else np.asarray(probabilities).tolist()
        if probs is not None and (len(probs)!=len(self.catalog["routes"]) or
                                  not np.isfinite(probs).all() or min(probs)<0 or
                                  not np.isclose(sum(probs),1.0)):
            raise ValueError("Invalid route probability vector")
        self.selected = (route, action)
        self._emit("DECISION", frame, selected_route_index=route, selected_route_id=obs["route_id"],
                   selected_action_index=action, selected_allocation=obs["actions"][action],
                   route_probability_vector=probs,
                   selected_route_probability=None if probs is None else float(probs[route]),
                   route_probability_support=[r["route_id"] for r in self.catalog["routes"]] if probs is not None else None,
                   route_probability_semantics="pre-sampling marginal over routes; not joint allocation propensity" if probs is not None else None,
                   probability_unavailable_reason=None if probs is not None else "not_exposed_by_policy",
                   joint_action_propensity=None, joint_propensity_unavailable_reason="not_produced")

    def outcome(self, frame, q, availability, continuous, bernoulli=None, masked=None):
        sampled = None if bernoulli is None else int(bernoulli)
        group = None if masked is None else float(masked)
        positive = None if group is None else bool(group > 0)
        self.positive_route_feedback_count += int(positive or False)
        self._emit("OUTCOME", frame, base_expected_payoff=float(q), availability=int(availability),
                   selected_continuous_payoff=float(continuous), sampled_bernoulli_draw=sampled,
                   masked_route_feedback=group, positive_route_feedback=positive,
                   sampled_feedback_unavailable_reason="policy_does_not_sample_bernoulli_feedback" if sampled is None else None,
                   quantity_semantics="expected routing payoff and policy training feedback; no physical delivery observation")

    def update(self, frame, allocation_target, allocation_applied, group_target=None, policy_target=None):
        self.allocation_update_count += int(allocation_applied)
        feedback = self.manifest["identity"]["trace_contract"]["feedback"]
        neural_allocation = feedback in NEURAL_ALLOCATION_FEEDBACK
        importance_weighted = feedback == EXP3_NEURAL_FEEDBACK
        if importance_weighted:
            route_semantics = "masked Bernoulli / selected route probability"
        elif feedback == DIRECT_BERNOULLI_NEURAL_FEEDBACK:
            route_semantics = "direct masked Bernoulli route update"
        elif feedback == DIRECT_CONTINUOUS_NEURAL_FEEDBACK:
            route_semantics = "direct continuous selected-payoff route update"
        else:
            route_semantics = None
        self._emit("UPDATE", frame, allocation_update_target=None if allocation_target is None else float(allocation_target),
                   allocation_update_applied=bool(allocation_applied),
                   allocation_update_recipient="within-route NeuralUCB" if neural_allocation else None,
                   allocation_update_unavailable_reason=None if allocation_applied else ("selected_route_unavailable" if neural_allocation else "no_within_route_NeuralUCB"),
                   importance_weighted_route_update=float(group_target) if importance_weighted and group_target is not None else None,
                   direct_route_update=float(group_target) if not importance_weighted and group_target is not None else None,
                   route_update_semantics=route_semantics,
                   policy_update_target=None if policy_target is None else float(policy_target),
                   policy_update_semantics=None if policy_target is None else "continuous selected payoff")

    def close(self):
        if self.stream and not self.stream.closed:
            self.stream.flush()
            os.fsync(self.stream.fileno())
            self.stream.close()


def run_identity(identity):
    required = {"protocol_root_id","config_hash","topology_hash","route_set_hash","action_catalog_hash",
                "physics_hash","threat_trajectory_hash","seeds","policy","policy_kwargs","threat",
                "allocator","replay","horizon","code","block_id","execution_kind","execution_frames"}
    if not required.issubset(identity):
        raise ValueError(f"Incomplete run identity: {sorted(required-set(identity))}")
    return digest(identity)


def validate_manifest(manifest):
    identity = manifest["identity"]
    if run_identity(identity) != manifest["run_id"]:
        raise ValueError("Run identity mismatch")
    if digest(manifest["configuration"]) != identity["config_hash"]:
        raise ValueError("Configuration hash mismatch")
    if digest(manifest["configuration"]["protocol"]) != identity["protocol_root_id"]:
        raise ValueError("Protocol root mismatch")
    if manifest["execution_frames"] != identity["execution_frames"]:
        raise ValueError("Execution frame count mismatch")
    for key in ("policy","policy_kwargs","threat"):
        if manifest["configuration"][key] != identity[key]:
            raise ValueError(f"Configuration/identity {key} mismatch")


class AttemptBundle:
    """Exclusive attempt creation; no overwrite, favorable retries, or best selection."""
    def __init__(self, root, manifest, catalog, mask, restart_reason=None):
        validate_manifest(manifest)
        if Path(root).resolve().is_relative_to(Path(__file__).resolve().parents[3]):
            raise ValueError("Raw campaign bundles must remain outside the source repository")
        self.manifest = manifest
        run_dir = Path(root)/manifest["run_id"]
        run_dir.mkdir(parents=True, exist_ok=True)
        attempt_no, previous_hash = 1, None
        if (run_dir/"attempt-1").exists():
            prior_path = run_dir/"attempt-1"/"completion.json"
            if not restart_reason or not prior_path.exists():
                raise ValueError("Existing attempt requires documented terminal infrastructure failure")
            prior = json.loads(prior_path.read_text())
            if prior["state"] != "FAILED" or prior["failure_kind"] != "infrastructure" or not prior["reason"]:
                raise ValueError("Only a documented infrastructure failure permits restart")
            if prior["run_id"] != manifest["run_id"]:
                raise ValueError("Restart identity mismatch")
            attempt_no, previous_hash = 2, file_hash(prior_path)
        self.directory = run_dir/f"attempt-{attempt_no}"
        self.directory.mkdir(exist_ok=False)
        self.attempt_no = attempt_no
        self.started = time.perf_counter()
        self.terminal = False
        self.lineage = {"attempt_no":attempt_no, "previous_completion_hash":previous_hash,
                        "restart_reason":restart_reason, "restart_from_frame":0}
        write_json_exclusive(self.directory/"manifest.json", manifest)
        write_json_exclusive(self.directory/"attempt.json", self.lineage)
        self.scenario_session = mask if isinstance(mask, ScenarioSession) else None
        for filename, value in (("topology.json",catalog["topology"]),("routes.json",catalog["routes"]),
                                ("observations.json",catalog["observations"]),("physics.json",catalog["physics"]),
                                ("catalog_diagnostics.json",catalog["diagnostics"])):
            write_json_exclusive(self.directory/filename, value)
        if self.scenario_session is None:
            write_json_exclusive(self.directory/"availability.json", np.asarray(mask).tolist())
        self.recorder = EventRecorder(manifest,catalog,attempt_no,self.directory)

    def finish(self, state="COMPLETE", failure_kind=None, reason=None):
        if self.terminal:
            raise ValueError("Attempt already terminal")
        self.recorder.close()
        expected = {p:self.manifest["execution_frames"] for p in PHASES}
        actual = {p:self.recorder.counts[p] for p in PHASES}
        if state == "COMPLETE" and actual != expected:
            raise ValueError("Incomplete event counts cannot be completed")
        if state not in {"COMPLETE","FAILED","INTERRUPTED"} or (state != "COMPLETE" and not reason):
            raise ValueError("Invalid terminal state/reason")
        if self.scenario_session is not None and not (self.directory/"availability.json").exists():
            # Write once after execution; -1 in a failed/interrupted bundle means
            # unrealized, never an availability observation.
            realized = (self.scenario_session.completed_mask() if state == "COMPLETE"
                        else self.scenario_session.realized)
            write_json_exclusive(self.directory/"availability.json", realized.tolist())
        trajectory = json.loads((self.directory/"availability.json").read_text())
        completion = {"phase":"COMPLETION", "state":state, "run_id":self.manifest["run_id"],
            "realized_trajectory_hash":digest(trajectory),
            "attempt_no":self.attempt_no, "manifest_hash":digest(self.manifest),
            "expected_record_counts":expected, "actual_record_counts":actual,
            "file_hashes":{p.name:file_hash(p) for p in sorted(self.directory.iterdir()) if p.is_file()},
            "wall_seconds":time.perf_counter()-self.started,
            "positive_route_feedback_count":self.recorder.positive_route_feedback_count if self.manifest["identity"]["trace_contract"]["feedback"] in BERNOULLI_FEEDBACK else None,
            "allocation_update_count":self.recorder.allocation_update_count if self.manifest["identity"]["trace_contract"]["feedback"] in NEURAL_ALLOCATION_FEEDBACK else None,
            "hybrid_diagnostics_unavailable_reason":None if self.manifest["identity"]["trace_contract"]["feedback"] in NEURAL_ALLOCATION_FEEDBACK else "policy_has_no_hybrid_feedback_producer",
            "completion_record_count":1,
            "failure_kind":failure_kind, "reason":reason,
            "scientific_evidence":self.manifest["identity"]["execution_kind"]=="scientific",
            "attempt_lineage":self.lineage}
        if state == "COMPLETE":
            _validate_payload(self.directory,self.manifest,completion)
        # Publish only a fully flushed marker; hard-link is atomic and refuses replacement.
        pending = self.directory/"completion.pending"
        write_json_exclusive(pending,completion)
        os.link(pending,self.directory/"completion.json")
        pending.unlink()
        self.terminal = True
        return completion


def _validate_payload(directory, manifest, completion):
    validate_manifest(manifest)
    identity = manifest["identity"]
    def read(name):
        return json.loads((directory/name).read_text())
    if run_identity(identity) != manifest["run_id"] or completion["manifest_hash"] != digest(manifest):
        raise ValueError("Manifest identity mismatch")
    if digest(read("topology.json")) != identity["topology_hash"]:
        raise ValueError("Topology mismatch")
    if digest(sorted(read("routes.json"),key=lambda r:r["route_id"])) != identity["route_set_hash"]:
        raise ValueError("Route-set mismatch")
    trajectory = read("availability.json")
    trajectory_hash = digest(trajectory)
    if digest(read("physics.json")) != identity["physics_hash"] or (identity["threat_trajectory_hash"] is not None and trajectory_hash != identity["threat_trajectory_hash"]):
        raise ValueError("Physics/mask mismatch")
    if trajectory_hash != completion["realized_trajectory_hash"]:
        raise ValueError("Realized trajectory mismatch")
    if np.asarray(trajectory).shape != (manifest["execution_frames"], len(read("routes.json"))) or not np.isin(trajectory,[0,1]).all():
        raise ValueError("Incomplete or invalid realized trajectory")
    observations = read("observations.json")
    if digest(observations) != identity["observation_catalog_hash"]:
        raise ValueError("Observation mismatch")
    required_files={"manifest.json","attempt.json","topology.json","routes.json","observations.json",
                    "physics.json","availability.json","catalog_diagnostics.json","events.jsonl"}
    present={p.name for p in directory.iterdir() if p.is_file()}-{"completion.json","completion.pending"}
    if not required_files.issubset(completion["file_hashes"]) or present!=set(completion["file_hashes"]):
        raise ValueError("Incomplete completion file inventory")
    for name, expected_hash in completion["file_hashes"].items():
        if Path(name).name != name or file_hash(directory/name) != expected_hash:
            raise ValueError("Raw file checksum mismatch")
    counts, positives, updates = Counter(), 0, 0
    physics, mask = read("physics.json"), read("availability.json")
    selected = outcome = decision = None
    with (directory/"events.jsonl").open() as stream:
        for seq,line in enumerate(stream):
            row = json.loads(line)
            if row["phase"] != PHASES[seq%4] or row["frame"] != seq//4:
                raise ValueError("Event phase/frame sequence mismatch")
            if row["run_id"] != manifest["run_id"] or row["attempt_no"] != completion["attempt_no"]:
                raise ValueError("Event identity mismatch")
            if row["decision_id"] != f"{manifest['run_id']}:{completion['attempt_no']}:{seq//4}":
                raise ValueError("Decision join mismatch")
            if row["event_id"] != f"{row['decision_id']}:{row['phase']}":
                raise ValueError("Event identity mismatch")
            for key in ("protocol_root_id","block_id","topology_hash","route_set_hash","threat_trajectory_hash","policy","threat"):
                if row[key] != identity[key]:
                    raise ValueError("Event provenance mismatch")
            if "reward" in row:
                raise ValueError("Ambiguous reward channel")
            if row["phase"]=="PRESELECTION":
                if row["observation_catalog_hash"]!=identity["observation_catalog_hash"] or row["history_cutoff_frame"]!=row["frame"]-1:
                    raise ValueError("Preselection snapshot/cutoff mismatch")
                if any(k in row for k in ("availability","base_expected_payoff","sampled_bernoulli_draw","selected_continuous_payoff")):
                    raise ValueError("Privileged values in preselection record")
            elif row["phase"]=="DECISION":
                decision=row
                selected=(row["selected_route_index"],row["selected_action_index"])
                route,action=selected
                if route<0 or route>=len(observations["routes"]) or action<0 or action>=len(observations["routes"][route]["actions"]):
                    raise ValueError("Invalid decision index")
                obs=observations["routes"][route]
                probs=row["route_probability_vector"]
                if identity["trace_contract"]["feedback"]==EXP3_NEURAL_FEEDBACK:
                    if probs is None or len(probs)!=len(observations["routes"]) or not np.isfinite(probs).all() or min(probs)<0 or not np.isclose(sum(probs),1.0) or row["selected_route_probability"]!=probs[route]:
                        raise ValueError("Invalid selected-route probability")
                if row["selected_route_id"]!=obs["route_id"] or row["selected_allocation"]!=obs["actions"][action]:
                    raise ValueError("Decision/catalog mismatch")
            elif row["phase"]=="OUTCOME":
                route,action=selected
                q=physics["base_expected_payoffs"][route][action]
                available=mask[row["frame"]][route]
                if row["base_expected_payoff"]!=q or row["availability"]!=available or row["selected_continuous_payoff"]!=q*available:
                    raise ValueError("Selected outcome/physics mismatch")
                if identity["trace_contract"]["feedback"] in BERNOULLI_FEEDBACK:
                    if row["sampled_bernoulli_draw"] not in (0,1) or row["masked_route_feedback"]!=row["sampled_bernoulli_draw"]*available:
                        raise ValueError("Sampled/masked feedback mismatch")
                    if row["positive_route_feedback"]!=bool(row["masked_route_feedback"]>0):
                        raise ValueError("Positive-feedback diagnostic mismatch")
                elif row["sampled_bernoulli_draw"] is not None or row["masked_route_feedback"] is not None:
                    raise ValueError("Fabricated sampled feedback")
                outcome=row
            elif row["phase"]=="UPDATE":
                feedback = identity["trace_contract"]["feedback"]
                if feedback==EXP3_NEURAL_FEEDBACK:
                    applied=bool(outcome["availability"])
                    target=outcome["base_expected_payoff"] if applied else None
                    if row["allocation_update_applied"]!=applied or row["allocation_update_target"]!=target or row["importance_weighted_route_update"]!=outcome["masked_route_feedback"]/max(decision["selected_route_probability"],identity["trace_contract"]["probability_floor"]):
                        raise ValueError("Hybrid update-channel mismatch")
                elif feedback==DIRECT_BERNOULLI_NEURAL_FEEDBACK:
                    applied=bool(outcome["availability"])
                    target=outcome["base_expected_payoff"] if applied else None
                    if row["allocation_update_applied"]!=applied or row["allocation_update_target"]!=target or row["direct_route_update"]!=outcome["masked_route_feedback"]:
                        raise ValueError("Direct Bernoulli update-channel mismatch")
                elif feedback==DIRECT_CONTINUOUS_NEURAL_FEEDBACK:
                    applied=bool(outcome["availability"])
                    target=outcome["base_expected_payoff"] if applied else None
                    if row["allocation_update_applied"]!=applied or row["allocation_update_target"]!=target or row["direct_route_update"]!=outcome["selected_continuous_payoff"]:
                        raise ValueError("Direct continuous update-channel mismatch")
                elif row["allocation_update_applied"] or row["policy_update_target"]!=outcome["selected_continuous_payoff"]:
                    raise ValueError("Policy update-channel mismatch")
            counts[row["phase"]] += 1
            positives += int(row.get("positive_route_feedback") or False)
            updates += int(row.get("allocation_update_applied") or False)
    expected = {p:manifest["execution_frames"] for p in PHASES}
    if dict(counts) != expected or completion["actual_record_counts"] != expected or completion["expected_record_counts"] != expected:
        raise ValueError("Record-count mismatch")
    feedback=identity["trace_contract"]["feedback"]
    if ((positives if feedback in BERNOULLI_FEEDBACK else None) != completion["positive_route_feedback_count"] or
            (updates if feedback in NEURAL_ALLOCATION_FEEDBACK else None) != completion["allocation_update_count"]):
        raise ValueError("Feedback diagnostic mismatch")


def validate_completion(directory, expected_manifest):
    directory = Path(directory)
    manifest = json.loads((directory/"manifest.json").read_text())
    completion = json.loads((directory/"completion.json").read_text())
    if manifest != json.loads(canonical_json(expected_manifest)) or completion["state"] != "COMPLETE":
        raise ValueError("Only exact completed identities can be reused")
    _validate_payload(directory,manifest,completion)
    return completion


def validate_scale_completion(configs, scale_m, bundles):
    """A scale is complete only for every configured block/scenario/policy cell."""
    from daqr.config.execution_contract import resolve_configuration
    resolved=resolve_configuration(configs)
    expected={(c["block"],c["scenario"],c["policy"]) for c in resolved["required_cells"] if c["scale"]==scale_m}
    if not expected:
        raise ValueError("Unconfigured scale")
    actual=set()
    for path in bundles:
        manifest=json.loads((Path(path)/"manifest.json").read_text())
        validate_completion(path,manifest)
        if canonical_json(manifest["configuration"]["resolved"])!=canonical_json(resolved):
            raise ValueError("Completion configuration differs from requested matrix")
        identity=manifest["identity"]
        cell=(identity["block_id"],identity["threat"],identity["policy"])
        if identity["scale_m"]!=scale_m or cell in actual:
            raise ValueError("Wrong scale or duplicate completed cell")
        actual.add(cell)
    if actual!=expected:
        raise ValueError(f"Incomplete scale: missing {sorted(expected-actual)}, extra {sorted(actual-expected)}")
    return {"complete":True,"required_cells":len(expected),"completed_cells":len(actual)}


def validate_scale_completion_by_block(block_configs, scale_m, bundles):
    """Validate a configured matrix whose notebook blocks have distinct horizons."""
    from daqr.config.execution_contract import resolve_configuration
    if not block_configs:
        raise ValueError("No configured blocks")
    resolved = {int(block): resolve_configuration(config)
                for block, config in block_configs.items()}
    first = next(iter(resolved.values()))
    expected = {(cell["block"], cell["scenario"], cell["policy"])
                for cell in first["required_cells"] if cell["scale"] == scale_m}
    if not expected or set(resolved) != {cell[0] for cell in expected}:
        raise ValueError("Missing or unconfigured block")
    for block, configuration in resolved.items():
        cells = {(cell["block"], cell["scenario"], cell["policy"])
                 for cell in configuration["required_cells"] if cell["scale"] == scale_m}
        if cells != expected:
            raise ValueError(f"Block {block} changes the configured matrix")
    actual = set()
    for path in bundles:
        manifest = json.loads((Path(path) / "manifest.json").read_text())
        validate_completion(path, manifest)
        identity = manifest["identity"]
        block = identity["block_id"]
        cell = (block, identity["threat"], identity["policy"])
        if identity["scale_m"] != scale_m or cell not in expected or cell in actual:
            raise ValueError("Wrong scale, unexpected cell or duplicate completion")
        if canonical_json(manifest["configuration"]["resolved"]) != canonical_json(resolved[block]):
            raise ValueError("Completion configuration differs from its block contract")
        actual.add(cell)
    if actual != expected:
        raise ValueError(f"Incomplete scale: missing {sorted(expected-actual)}")
    return {"complete": True, "required_cells": len(expected),
            "completed_cells": len(actual)}
