"""Strict resolved view of ExperimentConfiguration, independent of campaigns.

This is configuration validation, not a study preset. No scientific axes/defaults
are selected here. Legacy persistence/retry entry points remain unchanged.
"""
from copy import deepcopy
from dataclasses import dataclass, asdict
import inspect
import math
from hashlib import sha256
from pathlib import Path


def class_id(cls):
    return cls.__module__ + "." + cls.__qualname__


def source_identity(cls):
    path=Path(inspect.getfile(cls))
    return {"class":class_id(cls),"source_sha256":sha256(path.read_bytes()).hexdigest()}


@dataclass(frozen=True)
class ExecutionSettings:
    protocol_namespace: str
    horizon: int
    base_horizon: int
    scale_points: tuple[int, ...]
    execution_kind: str


def positive_int(value, name):
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def resolve_configuration(configs):
    """Validate the whole configured matrix; never filter unsupported cells."""
    settings = getattr(configs, "execution", None)
    if not isinstance(settings, ExecutionSettings) or not settings.protocol_namespace:
        raise ValueError("Explicit ExecutionSettings required")
    positive_int(settings.horizon, "horizon")
    positive_int(settings.base_horizon, "base_horizon")
    positive_int(configs.runs, "runs")
    if type(configs.base_seed) is not int or configs.base_seed < 0:
        raise ValueError("Explicit nonnegative base seed required")
    if settings.execution_kind not in {"technical_preflight", "scientific"}:
        raise ValueError("Unknown execution kind")
    if not settings.scale_points or len(set(settings.scale_points)) != len(settings.scale_points):
        raise ValueError("Nonempty unique scale points required")
    for scale in settings.scale_points:
        positive_int(scale, "scale")
    if not configs.models or len(set(configs.models)) != len(configs.models) or not configs.test_scenarios:
        raise ValueError("Nonempty unique configured policies and scenarios required")
    if not math.isfinite(configs.scale) or configs.scale <= 0 or type(configs.base_capacity) is not bool:
        raise ValueError("Invalid replay scale/anchor")
    catalog_component, reward_component = resolve_components(configs)
    tb = configs.testbed_config
    allocator = configs.allocator
    if getattr(allocator, "allocation_capability", None) != "static":
        raise ValueError("HOLD: allocator requires an unimplemented dynamic catalog interface")
    if getattr(configs, "transition_trigger", None):
        raise ValueError("HOLD: static-catalog execution cannot apply dynamic context transitions")
    scenarios = {}
    for name in configs.test_scenarios.keys():
        strategy = configs.resolve_attack_strategy(name)
        capability = getattr(strategy, "mask_capability", "undeclared")
        strategy.validate_execution()
        if not callable(getattr(strategy, "open_session", None)):
            raise ValueError(f"HOLD scenario {name}: no scenario execution interface")
        scenarios[name] = {**source_identity(type(strategy)),
                           "parameters": deepcopy(strategy.__dict__), "capability": capability,
                           "configured": deepcopy(configs.test_scenarios[name])}
    policies = {}
    for name in configs.models:
        if name not in configs.algorithm_configs:
            raise ValueError(f"Missing registry policy {name}")
        entry = configs.algorithm_configs[name]
        if not {"model_class","kwargs","runner_type","seed_offset"}.issubset(entry):
            raise ValueError(f"Incomplete registry entry {name}")
        cls, kwargs, runner = entry["model_class"], entry["kwargs"], entry["runner_type"]
        if not isinstance(kwargs, dict) or type(entry["seed_offset"]) is not int:
            raise ValueError(f"Invalid kwargs/integer seed offset for {name}")
        validator = getattr(cls, "validate_execution_config", None)
        if validator is not None:
            validator(kwargs)
        if runner == "step-wise":
            trace = {"feedback": "continuous-step-v1",
                     "privileged": bool(getattr(cls, "trace_privileged", False))}
        elif runner == "batch" and hasattr(cls, "execution_trace_contract"):
            trace = cls.execution_trace_contract(kwargs)
        else:
            raise ValueError(f"HOLD policy {name}: no supported passive trace contract")
        if any(s["capability"] != "static" for s in scenarios.values()):
            if not getattr(cls, "supports_causal_scenarios", False):
                raise ValueError(f"HOLD policy {name}: no causal scenario capability")
            if trace["privileged"] and not callable(getattr(cls, "prepare_scenario_frame", None)):
                raise ValueError(f"HOLD policy {name}: no causal privileged-frame interface")
        # Record inherited constructor defaults too, not a campaign's duplicate table.
        defaults = {}
        for base in reversed(cls.__mro__):
            for key, p in inspect.signature(base.__init__).parameters.items():
                if p.default is not inspect.Parameter.empty and isinstance(p.default, (str, int, float, bool, type(None))):
                    defaults[key] = p.default
        defaults.update(kwargs)
        policies[name] = {**source_identity(cls), "kwargs": deepcopy(kwargs),
                          "constructor_defaults": defaults, "runner_type": runner, "trace": trace,
                          "seed_offset": entry["seed_offset"]}
    replay_base = settings.base_horizon if configs.base_capacity else settings.horizon
    capacity = replay_base * configs.scale
    if not float(capacity).is_integer() or capacity < 1:
        raise ValueError("Replay capacity must resolve to a positive integer")
    return {"execution": asdict(settings), "blocks": configs.runs,
            "base_seed": configs.base_seed, "policies": policies, "scenarios": scenarios,
            "allocator": {**source_identity(type(allocator)), "parameters": deepcopy(allocator.__dict__)},
            "components": {"catalog": component_identity(catalog_component),
                           "reward": component_identity(reward_component)},
            "physics": deepcopy(configs.physics_params), "testbed": deepcopy(tb),
            "replay": {"anchor": "T_b" if configs.base_capacity else "T",
                       "scale": configs.scale, "base": replay_base, "capacity": int(capacity)},
            "required_cells": [
                {"scale": scale, "block": block, "scenario": scenario, "policy": policy}
                for scale in settings.scale_points for block in range(configs.runs)
                for scenario in configs.test_scenarios.keys() for policy in configs.models]}


def component_identity(component):
    return {**source_identity(type(component)), "component_id": component.component_id,
            "parameters": deepcopy(component.__dict__)}


def resolve_components(configs):
    """Configured objects are the extension seam; no concrete family/schema here."""
    components = []
    for field, params, methods in (
        ("catalog_component", "testbed_config", ("validate_config", "build", "validate")),
        ("reward_component", "physics_params", ("validate_config", "build", "values")),
    ):
        component = getattr(configs, field, None)
        if not isinstance(getattr(component, "component_id", None), str) or not component.component_id:
            raise ValueError(f"Explicit {field} with component_id required")
        if any(not callable(getattr(component, method, None)) for method in methods):
            raise ValueError(f"Incomplete {field} interface")
        parameters = getattr(configs, params, None)
        if not isinstance(parameters, dict):
            raise ValueError(f"{params} must be a configuration mapping")
        component.validate_config(parameters)
        components.append(component)
    return tuple(components)
