"""Versioned primary-form medium catalog. No routing execution at import."""
from dataclasses import asdict
from hashlib import sha256
from itertools import combinations_with_replacement
import json

import networkx as nx
import numpy as np

from daqr.core.primary_routes import PrimaryRoute, allocations, primary_rewards
from daqr.core.attack_strategy import NoAttack, RandomAttack


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


# Queue/phase/block count/optional future treatments are intentionally absent.
# Freeze the serialized root at launch approval; any semantic change is a new protocol.
PROTOCOL = {
    "schema_version": "medium-v1",
    "topology_family": "layered-primary-form-v1",
    "topology_rng": "numpy.Generator(PCG64)",
    "route_rule": "all-simple-three-hop-lexicographic-v1",
    "profile_rule": "physics-profile-v1",
    "rate_values": [1e-4, 1.5e-4, 2e-4],
    "action_rule": "all-weak-compositions-lexicographic-v1",
    "qubits_per_route": 9,
    "success_factor": 100,
    "reward_rule": "primary-two-stage-power-left-product-v1",
    "feedback_rule": "existing-policy-specific-channels-v1",
    "seed_rule": "sha256-first-four-bytes-big-endian-v1",
    "allocator": "fixed-equal",
    "base_horizon": 6000,
    "replay_anchor": "T_b",
    "replay_scale": 2,
    "replay_capacity": 12000,
    "random_interruption": 0.0625,
}
PROTOCOL_ROOT_ID = digest(PROTOCOL)
POLICIES = ("Oracle", "CEpsilonGreedy", "EXPNeuralUCB")
THREATS = ("NoAttack", "RandomAttack")
# Inherited from the selected registry entry/default constructor, recorded explicitly.
POLICY_KWARGS = {
    "Oracle": {"mode": "base"},
    "CEpsilonGreedy": {"mode": "hybrid"},
    "EXPNeuralUCB": {"mode": "hybrid", "beta": 1.0, "gamma_factor": 0.01, "eta_factor": 0.05},
}
DOMAINS = {"topology", "physics", "environment", "threat", "policy", "allocator", "route_generation", "observation"}


def seed_for(domain, block, scale_m=3, qualifier="", protocol_root_id=PROTOCOL_ROOT_ID):
    if domain not in DOMAINS or type(block) is not int or block < 0 or type(scale_m) is not int or scale_m < 1:
        raise ValueError("Invalid seed domain/block/scale")
    if "|" in qualifier:
        raise ValueError("Seed qualifier cannot contain delimiter")
    value = f"medium-v1|{protocol_root_id}|{scale_m}|{block}|{domain}|{qualifier}"
    return int.from_bytes(sha256(value.encode("utf-8")).digest()[:4], "big")


def seed_manifest(block, policy, threat, scale_m=3):
    if policy not in POLICIES or threat not in THREATS:
        raise ValueError("Unsupported campaign policy/threat")
    result = {}
    for domain in sorted(DOMAINS):
        qualifier = policy if domain == "policy" else threat if domain == "threat" else ""
        derived = seed_for(domain, block, scale_m, qualifier)
        consumed = domain in {"topology", "physics", "policy"} or (domain == "threat" and threat == "RandomAttack")
        result[domain] = {
            "derived_seed": derived, "actual_seed": derived if consumed else None,
            "qualifier": qualifier, "consumed": consumed,
            "reason": None if consumed else "deterministic_or_absent_producer",
        }
    result["physics"]["rng"] = "SHA256 route-rank assignment; no random draw"
    result["topology"]["rng"] = "numpy.Generator(PCG64)"
    result["threat"]["rng"] = "numpy.Generator(PCG64)" if threat == "RandomAttack" else None
    result["policy"]["rng"] = "numpy.RandomState(MT19937), Python random, torch CPU"
    return result


def build_catalog(block=0, scale_m=3):
    if scale_m not in (1, 2, 3):
        raise ValueError("Only prespecified 7/4, 11/7, 15/10 families are defined")
    m = scale_m
    source, destination = 0, 4*m+2
    left, right = list(range(1, 2*m+2)), list(range(2*m+2, 4*m+2))
    rng = np.random.Generator(np.random.PCG64(seed_for("topology", block, m)))
    lperm, rperm = rng.permutation(left), rng.permutation(right)
    middle = {(int(u), int(rperm[i % len(right)])) for i, u in enumerate(lperm)}
    remaining = sorted(set((u,v) for u in left for v in right) - middle)
    added = 0
    for idx in rng.permutation(len(remaining)):
        u, v = remaining[int(idx)]
        if sum(a == u for a,b in middle) < 3 and sum(b == v for a,b in middle) < 3:
            middle.add((u,v))
            added += 1
            if added == m:
                break
    if added != m:
        raise ValueError("Insufficient middle edges; do not pad or reseed")
    edges = sorted([(source,u) for u in left] + list(middle) + [(v,destination) for v in right])
    topology = {"family": PROTOCOL["topology_family"], "nodes": list(range(destination+1)),
                "edges": edges, "source": source, "destination": destination, "scale_m": m}
    topology_hash = digest(topology)
    graph = nx.Graph()
    graph.add_nodes_from(topology["nodes"])
    graph.add_edges_from(edges)
    paths = sorted(tuple(p) for p in nx.all_simple_paths(graph, source, destination, cutoff=3) if len(p) == 4)
    if len(paths) != 3*m+1 or len(set(paths)) != len(paths):
        raise ValueError("Invalid distinct three-hop route count")
    if set(n for path in paths for n in path) != set(topology["nodes"]):
        raise ValueError("Not all intended nodes are represented")
    ids = [digest({"topology_hash": topology_hash, "ordered_nodes": p}) for p in paths]
    profiles = sorted(combinations_with_replacement(PROTOCOL["rate_values"], 3))
    k = len(paths)
    profiles = [profiles[j*9//(k-1)] for j in range(k)]
    physics_seed = seed_for("physics", block, m)
    ranking = sorted(ids, key=lambda rid: sha256(f"physics-profile-v1|{hex(physics_seed)}|{rid}".encode()).hexdigest())
    by_id = dict(zip(ranking, profiles))
    route_objects = [PrimaryRoute(rid, tuple(by_id[rid]), path) for rid,path in zip(ids,paths)]
    routes = [asdict(route) for route in route_objects]
    actions = [allocations(9, route.hops).tolist() for route in route_objects]
    contexts = {"version": "allocation-context-v1", "observation_kind": "allocation_context",
                "link_measurements_present": False,
                "routes": [{"route_id": r.route_id, "nodes": r.nodes, "hops": r.hops,
                            "budget": 9, "actions": a} for r,a in zip(route_objects, actions)]}
    physics = {"success_factor": 100, "routes": routes,
               "base_expected_payoffs": [list(map(float, primary_rewards(r, a))) for r,a in zip(route_objects, actions)]}
    route_set_hash = digest(sorted(routes, key=lambda r:r["route_id"]))
    edge_sets = [set(tuple(sorted(e)) for e in zip(p[:-1],p[1:])) for p in paths]
    result = {"topology": topology, "topology_hash": topology_hash,
              "routes": routes, "route_set_hash": route_set_hash,
              "observations": contexts, "observation_catalog_hash": digest(contexts),
              "physics": physics, "physics_hash": digest(physics),
              "action_catalog_hash": digest(actions),
              "diagnostics": {"node_degrees": dict(graph.degree()),
                  "route_edge_overlap": [[len(a & b) for b in edge_sets] for a in edge_sets],
                  "route_node_overlap": [[len(set(a) & set(b)) for b in paths] for a in paths],
                  "total_actions": sum(map(len, actions))}}
    validate_catalog(result)
    return result


def validate_catalog(catalog):
    t = catalog["topology"]
    if digest(t) != catalog["topology_hash"]:
        raise ValueError("Topology hash mismatch")
    graph = nx.Graph()
    graph.add_nodes_from(t["nodes"])
    graph.add_edges_from(t["edges"])
    routes = catalog["routes"]
    if len(catalog["observations"]["routes"])!=len(routes) or len(catalog["physics"]["base_expected_payoffs"])!=len(routes):
        raise ValueError("Route/observation/physics count mismatch")
    if len(routes) != 3*t["scale_m"]+1 or len(t["nodes"]) != 4*t["scale_m"]+3:
        raise ValueError("Catalog scale mismatch")
    if not nx.is_connected(graph) or len(set(r["route_id"] for r in routes)) != len(routes):
        raise ValueError("Disconnected graph or duplicate route")
    expected_paths = sorted(tuple(p) for p in nx.all_simple_paths(graph,t["source"],t["destination"],cutoff=3) if len(p)==4)
    if sorted(tuple(r["nodes"]) for r in routes) != expected_paths:
        raise ValueError("Catalog must contain exactly all three-hop routes")
    if set(n for r in routes for n in r["nodes"]) != set(t["nodes"]):
        raise ValueError("Unrepresented node")
    for r, obs, values in zip(routes, catalog["observations"]["routes"], catalog["physics"]["base_expected_payoffs"]):
        nodes = r["nodes"]
        if len(nodes) != 4 or len(set(nodes)) != 4 or any(not graph.has_edge(a,b) for a,b in zip(nodes[:-1],nodes[1:])):
            raise ValueError("Invalid simple route")
        if r["route_id"] != digest({"topology_hash":catalog["topology_hash"], "ordered_nodes":nodes}):
            raise ValueError("Route identity mismatch")
        if obs["route_id"] != r["route_id"] or obs["actions"] != allocations(9,3).tolist() or len(values) != 55:
            raise ValueError("Route/action/context alignment mismatch")
        expected = primary_rewards(PrimaryRoute(r["route_id"],tuple(r["link_rates"]),tuple(nodes)),obs["actions"])
        if not np.array_equal(values,expected):
            raise ValueError("Physics values do not match ordered route profile")
    if digest(sorted(routes,key=lambda r:r["route_id"])) != catalog["route_set_hash"]:
        raise ValueError("Route-set hash mismatch")
    for key, hash_key in (("observations","observation_catalog_hash"),("physics","physics_hash")):
        if digest(catalog[key]) != catalog[hash_key]:
            raise ValueError(f"{key} hash mismatch")
    if digest([r["actions"] for r in catalog["observations"]["routes"]]) != catalog["action_catalog_hash"]:
        raise ValueError("Action hash mismatch")


def build_mask(threat, frames, block=0, scale_m=3):
    if threat not in THREATS:
        raise ValueError("Unsupported threat")
    attack = NoAttack() if threat == "NoAttack" else RandomAttack(attack_rate=0.0625)
    rng = np.random.Generator(np.random.PCG64(seed_for("threat",block,scale_m,threat)))
    mask = attack.generate(rng, frames, 3*scale_m+1)
    if mask.shape != (frames,3*scale_m+1) or not np.isin(mask,[0,1]).all():
        raise ValueError("Availability mask must be binary and correctly shaped")
    return mask
