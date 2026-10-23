"""Concrete layered topology and primary-payoff components, selected by configuration."""
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import math
import networkx as nx
import numpy as np
from daqr.core.identity import digest
from daqr.core.primary_routes import PrimaryRoute, allocations, primary_rewards


class PrimaryPayoff:
    component_id = "primary-payoff-v1"

    def validate_config(self, params):
        if set(params) != {"entanglement_success_factor"}:
            raise ValueError("Explicit primary physics parameters required")
        factor = params["entanglement_success_factor"]
        if not math.isfinite(factor) or factor <= 0:
            raise ValueError("Invalid success factor")

    def values(self, route, actions, params):
        return primary_rewards(route, actions, params["entanglement_success_factor"])

    def build(self, params, routes, actions):
        self.validate_config(params)
        return {"success_factor": params["entanglement_success_factor"],
                "routes": [asdict(r) for r in routes],
                "base_expected_payoffs": [list(map(float, self.values(r,a,params)))
                                         for r,a in zip(routes,actions)]}


class LayeredPrimaryCatalog:
    component_id = "layered-primary-form-v1"

    def validate_config(self, params):
        if set(params) != {"topology_family","profile_pool"} or params["topology_family"] != self.component_id:
            raise ValueError("Unsupported or incomplete layered testbed configuration")
        profiles = params["profile_pool"]
        if not profiles or len(set(map(tuple, profiles))) != len(profiles):
            raise ValueError("Nonempty distinct explicit profile pool required")
        if any(len(p) != 3 or any(not math.isfinite(x) or not 0 <= x <= 1 for x in p) for p in profiles):
            raise ValueError("Layered three-hop profiles require three finite probabilities")

    def build(self, configs, scale_m, topology_seed, physics_seed, reward_component):
        m = scale_m
        source, destination = 0, 4*m+2
        left, right = list(range(1, 2*m+2)), list(range(2*m+2, 4*m+2))
        rng = np.random.Generator(np.random.PCG64(topology_seed))
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
        topology = {"family": configs.testbed_config["topology_family"], "nodes": list(range(destination+1)),
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
        profiles = sorted(tuple(p) for p in configs.testbed_config["profile_pool"])
        k = len(paths)
        if k > len(profiles):
            raise ValueError("Configured profile pool cannot supply distinct route profiles")
        profiles = [profiles[j*(len(profiles)-1)//(k-1)] for j in range(k)]
        ranking = sorted(ids, key=lambda rid: sha256(f"physics-profile-v1|{hex(physics_seed)}|{rid}".encode()).hexdigest())
        by_id = dict(zip(ranking, profiles))
        route_objects = [PrimaryRoute(rid, tuple(by_id[rid]), path) for rid,path in zip(ids,paths)]
        routes = [asdict(route) for route in route_objects]
        allocator = deepcopy(configs.allocator)
        if allocator.num_routes != k:
            raise ValueError("Allocator route cardinality contradicts configured scale")
        budgets = tuple(allocator.allocate(timestep=0, route_stats={}, verbose=False))
        if len(budgets) != k or sum(budgets) != allocator.total_qubits or any(b < allocator.min_qubits_per_route for b in budgets):
            raise ValueError("Allocator budget/conservation violation")
        actions = [allocations(b, route.hops).tolist() for b,route in zip(budgets,route_objects)]
        contexts = {"version": "allocation-context-v1", "observation_kind": "allocation_context",
                    "link_measurements_present": False,
                    "routes": [{"route_id": r.route_id, "nodes": r.nodes, "hops": r.hops,
                                "budget": b, "actions": a} for r,a,b in zip(route_objects, actions,budgets)]}
        physics = reward_component.build(configs.physics_params, route_objects, actions)
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
        self.validate(result, reward_component, configs.physics_params)
        return result


    def validate(self, catalog, reward_component, physics_params):
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
            if obs["route_id"] != r["route_id"] or obs["actions"] != allocations(obs["budget"],len(nodes)-1).tolist() or len(values) != len(obs["actions"]):
                raise ValueError("Route/action/context alignment mismatch")
            expected = reward_component.values(PrimaryRoute(r["route_id"],tuple(r["link_rates"]),tuple(nodes)),obs["actions"],physics_params)
            if not np.array_equal(values,expected):
                raise ValueError("Physics values do not match ordered route profile")
        if digest(sorted(routes,key=lambda r:r["route_id"])) != catalog["route_set_hash"]:
            raise ValueError("Route-set hash mismatch")
        for key, hash_key in (("observations","observation_catalog_hash"),("physics","physics_hash")):
            if digest(catalog[key]) != catalog[hash_key]:
                raise ValueError(f"{key} hash mismatch")
        if digest([r["actions"] for r in catalog["observations"]["routes"]]) != catalog["action_catalog_hash"]:
            raise ValueError("Action hash mismatch")
