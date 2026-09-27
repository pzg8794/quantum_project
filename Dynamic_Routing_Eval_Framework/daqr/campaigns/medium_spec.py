"""Versioned primary-form medium catalog. No routing execution at import."""
from hashlib import sha256

import numpy as np

from daqr.config.execution_contract import resolve_configuration


from daqr.core.identity import canonical_json, digest
from daqr.config.execution_contract import resolve_components


# Algorithm/schema versions, not experimental choices.
CATALOG_VERSION = "primary-catalog-v2"
DOMAINS = {"topology", "physics", "environment", "threat", "policy", "allocator", "route_generation", "observation"}


def seed_for(domain, block, scale_m, qualifier, protocol_root_id):
    if domain not in DOMAINS or type(block) is not int or block < 0 or type(scale_m) is not int or scale_m < 1:
        raise ValueError("Invalid seed domain/block/scale")
    if "|" in qualifier:
        raise ValueError("Seed qualifier cannot contain delimiter")
    value = f"medium-v1|{protocol_root_id}|{scale_m}|{block}|{domain}|{qualifier}"
    return int.from_bytes(sha256(value.encode("utf-8")).digest()[:4], "big")


def protocol(configs):
    # Queue membership/count excluded. Resolved run config is separately hashed.
    return {"namespace": configs.execution.protocol_namespace, "base_seed": configs.base_seed,
            "catalog_version": CATALOG_VERSION, "seed_rule": "sha256-first-four-bytes-big-endian-v1"}


def seed_manifest(configs, block, policy, threat, scale_m):
    root = digest(protocol(configs))
    strategy = configs.resolve_attack_strategy(threat)
    result = {}
    for domain in sorted(DOMAINS):
        qualifier = (f"{policy}:{configs.algorithm_configs[policy]['seed_offset']}"
                     if domain == "policy" else threat if domain == "threat" else "")
        derived = seed_for(domain, block, scale_m, qualifier, root)
        consumed = domain in {"topology", "physics", "policy"} or (domain=="threat" and strategy.uses_rng)
        result[domain] = {
            "derived_seed": derived, "actual_seed": derived if consumed else None,
            "qualifier": qualifier, "consumed": consumed,
            "reason": None if consumed else "deterministic_or_absent_producer",
        }
    result["physics"]["rng"] = "seed supplied to configured catalog component"
    result["topology"]["rng"] = "seed supplied to configured catalog component"
    result["threat"]["rng"] = "numpy.Generator(PCG64); supplied to configured strategy" if strategy.uses_rng else None
    result["environment"]["rng"] = None  # execution consumes the validated catalog directly
    result["policy"]["rng"] = "numpy.RandomState(MT19937), Python random, torch CPU"
    return result


def build_catalog(configs, block, scale_m):
    resolve_configuration(configs)
    if scale_m not in configs.execution.scale_points or block not in range(configs.runs):
        raise ValueError("Scale/block is not configured")
    catalog_component, reward_component = resolve_components(configs)
    root = digest(protocol(configs))
    catalog = catalog_component.build(configs, scale_m,
        seed_for("topology",block,scale_m,"",root),
        seed_for("physics",block,scale_m,"",root), reward_component)
    catalog_component.validate(catalog, reward_component, configs.physics_params)
    validate_catalog(catalog)
    return catalog


def validate_catalog(catalog):
    """Generic catalog integrity; scientific semantics belong to the producer."""
    routes = catalog["routes"]
    observations = catalog["observations"]["routes"]
    values = catalog["physics"]["base_expected_payoffs"]
    if not routes or len(routes) != len(observations) or len(routes) != len(values):
        raise ValueError("Route/observation/physics count mismatch")
    if len(set(r["route_id"] for r in routes)) != len(routes):
        raise ValueError("Duplicate route")
    for r, obs, q in zip(routes, observations, values):
        if r["route_id"] != obs["route_id"] or len(q) != len(obs["actions"]) or not len(q):
            raise ValueError("Route/action/context alignment mismatch")
        if not np.isfinite(q).all():
            raise ValueError("Nonfinite payoff")
    for key, hash_key in (("topology","topology_hash"),("observations","observation_catalog_hash"),("physics","physics_hash")):
        if digest(catalog[key]) != catalog[hash_key]:
            raise ValueError(f"{key} hash mismatch")
    if digest(sorted(routes,key=lambda r:r["route_id"])) != catalog["route_set_hash"]:
        raise ValueError("Route-set hash mismatch")
    if digest([r["actions"] for r in observations]) != catalog["action_catalog_hash"]:
        raise ValueError("Action hash mismatch")


def build_scenario(configs, threat, frames, block, scale_m, num_routes):
    resolve_configuration(configs)
    strategy = configs.resolve_attack_strategy(threat)
    root = digest(protocol(configs))
    rng = np.random.Generator(np.random.PCG64(seed_for("threat",block,scale_m,threat,root)))
    return strategy.open_session(rng, frames, num_routes)


def build_mask(configs, threat, frames, block, scale_m):
    """Compatibility accessor; causal scenarios cannot be pre-realized."""
    catalog = build_catalog(configs, block, scale_m)
    session = build_scenario(configs, threat, frames, block, scale_m, len(catalog["routes"]))
    if session.precomputed is None:
        raise ValueError("History-dependent scenario requires causal execution, not build_mask")
    return session.precomputed
