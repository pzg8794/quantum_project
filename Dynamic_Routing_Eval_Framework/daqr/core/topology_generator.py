"""
Network topology generators for quantum networks.

DESIGN PHILOSOPHY:
-----------------
Topology generators create the network graph structure (nodes, edges, distances).
They are DELIBERATELY capacity-agnostic and do NOT determine:
  - Number of paths (K): Determined by path enumeration algorithm
  - Qubit allocation: Determined by QubitAllocator classes
  - Routing strategy: Determined by bandits/algorithms

This separation allows:
  - Same topology with different path counts (4-path vs 8-path)
  - Same topology with different allocation strategies
  - Modular testing of topology vs. allocation vs. routing
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, Iterable

import networkx as nx
import numpy as np


class TopologyGenerator:
    """
    ✅ Base interface for topology generation.
    
    Topology generators ONLY create graph structure.
    Path enumeration and allocation are separate concerns.
    """
    def generate(self) -> nx.Graph:
        """Returns NetworkX graph with 'distance' edge attributes."""
        raise NotImplementedError
    
    def suggest_path_config(self, src, dst, max_paths=None) -> dict:
        """
        Optional: Suggest path enumeration configuration for this topology.
        
        Args:
            src: Source node
            dst: Destination node
            max_paths: Maximum paths to enumerate (None = auto)
        
        Returns:
            Dict with suggested 'num_paths', 'max_hops', etc.
        """
        # Default: no specific suggestion
        return {
            'num_paths': max_paths or 4,
            'max_hops': None,
            'method': 'k_shortest_paths'
        }


class Paper2TopologyGenerator(TopologyGenerator):
    """
    ✅ Paper #2 QNetworkGraph_LearningAlgo.m topology.
    Random 2D placement, distance-based connectivity.
    
    CAPACITY-AGNOSTIC: Works with any num_paths (4, 8, 12, etc.)
    Path enumeration is done separately by the environment.
    """
    def __init__(self, num_nodes=15, area_km=20, link_threshold_km=10, 
                 seed=42, testbed="paper2"):
        self.num_nodes = int(num_nodes)
        self.area_km = float(area_km)
        self.link_threshold_km = float(link_threshold_km)
        self.testbed = testbed
        self.rng = np.random.default_rng(seed)

    def generate(self) -> nx.Graph:
        G = nx.Graph()
        positions = {}

        for i in range(self.num_nodes):
            x = self.rng.uniform(-self.area_km / 2, self.area_km / 2)
            y = self.rng.uniform(-self.area_km / 2, self.area_km / 2)
            positions[i] = (x, y)
            G.add_node(i, pos=(x, y))

        for i in range(self.num_nodes):
            for j in range(i + 1, self.num_nodes):
                dist = float(np.linalg.norm(np.array(positions[i]) - np.array(positions[j])))
                if dist <= self.link_threshold_km:
                    G.add_edge(i, j, distance=dist)

        G.graph['testbed'] = self.testbed
        G.graph['num_nodes'] = self.num_nodes
        G.graph['area_km'] = self.area_km
        
        print(f"Generated {self.testbed} topology: {G.number_of_nodes()} nodes, "
              f"{G.number_of_edges()} edges")

        return G
    
    def suggest_path_config(self, src, dst, max_paths=None) -> dict:
        """Paper2: Suggests 4 or 8 paths based on testbed."""
        if self.testbed == "paper2":
            default_paths = max_paths or 8
        else:
            default_paths = max_paths or 4
        
        return {
            'num_paths': default_paths,
            'max_hops': 3,
            'method': 'k_shortest_paths'
        }




# class Paper2TopologyGenerator(TopologyGenerator):
#     """
#     ✅ Paper #2 QNetworkGraph_LearningAlgo.m topology.
#     Random 2D placement, distance-based connectivity.
    
#     CAPACITY-AGNOSTIC: Works with any num_paths (4, 8, 12, etc.)
#     Path enumeration is done separately by the environment.
#     """
#     def __init__(self, num_nodes=15, area_km=20, link_threshold_km=10, 
#                  seed=42, testbed="paper2"):
#         self.num_nodes = int(num_nodes)
#         self.area_km = float(area_km)
#         self.link_threshold_km = float(link_threshold_km)
#         self.testbed = testbed
#         self.rng = np.random.default_rng(seed)

#     def generate(self) -> nx.Graph:
#         G = nx.Graph()
#         positions = {}

#         for i in range(self.num_nodes):
#             x = self.rng.uniform(-self.area_km / 2, self.area_km / 2)
#             y = self.rng.uniform(-self.area_km / 2, self.area_km / 2)
#             positions[i] = (x, y)
#             G.add_node(i, pos=(x, y))

#         for i in range(self.num_nodes):
#             for j in range(i + 1, self.num_nodes):
#                 dist = float(np.linalg.norm(np.array(positions[i]) - np.array(positions[j])))
#                 if dist <= self.link_threshold_km:
#                     G.add_edge(i, j, distance=dist)

#         # ✅ Add metadata
#         G.graph['testbed'] = self.testbed
#         G.graph['num_nodes'] = self.num_nodes
#         G.graph['area_km'] = self.area_km
        
#         print(f"Generated {self.testbed} topology: {G.number_of_nodes()} nodes, "
#               f"{G.number_of_edges()} edges")

#         return G
    
#     def suggest_path_config(self, src, dst, max_paths=None) -> dict:
#         """
#         ✅ Paper2: Suggests 4 or 8 paths based on testbed.
#         Actual path enumeration is done by environment.
#         """
#         if self.testbed == "paper2":
#             default_paths = max_paths or 8  # Paper2 commonly uses 8 paths
#         else:
#             default_paths = max_paths or 4
        
#         return {
#             'num_paths': default_paths,
#             'max_hops': 3,  # Paper2 uses 2-hop and 3-hop paths
#             'method': 'k_shortest_paths'
#         }


# ============================================================================
# Paper 7: AS Topology Loader + Synthetic Backup
# ============================================================================

@dataclass(frozen=True)
class Paper7TopologyLoadReport:
    path: str
    raw_nodes: int
    raw_edges: int
    dedup_edges: int
    kept_nodes: int
    kept_edges: int
    relabeled: bool
    largest_cc_only: bool


class Paper7ASTopologyGenerator(TopologyGenerator):
    """
    ✅ Paper #7 topology loader for topology_data/as20000101.txt
    
    CAPACITY-AGNOSTIC: Topology is independent of path count.
    Paper7 algorithms can use any number of candidate paths from this topology.
    """

    def __init__(
        self,
        edge_list_path: Union[str, Path],
        *,
        relabel_to_integers: bool = True,
        largest_cc_only: bool = True,
        max_nodes: Optional[int] = None,
        seed: int = 42,
        synthetic_fallback: bool = True,
        synthetic_kind: str = "barabasi_albert",
        synthetic_params: Optional[Dict] = None,
        testbed: str = "paper7",  # ✅ NEW
    ):
        self.edge_list_path = Path(edge_list_path)
        self.relabel_to_integers = bool(relabel_to_integers)
        self.largest_cc_only = bool(largest_cc_only)
        self.max_nodes = None if max_nodes is None else int(max_nodes)
        self.seed = int(seed)
        self.testbed = testbed  # ✅ Store testbed

        self.synthetic_fallback = bool(synthetic_fallback)
        self.synthetic_kind = str(synthetic_kind)
        self.synthetic_params = synthetic_params or {}

        self._last_report: Optional[Paper7TopologyLoadReport] = None

    @property
    def last_report(self) -> Optional[Paper7TopologyLoadReport]:
        return self._last_report

    def generate(self) -> nx.Graph:
        if self.edge_list_path.exists():
            G = self._load_as_edge_list(self.edge_list_path)
            if self.max_nodes is not None:
                G = self._sample_connected_subgraph(G, self.max_nodes)
            
            # ✅ Add metadata
            G.graph['testbed'] = self.testbed
            return G

        if not self.synthetic_fallback:
            raise FileNotFoundError(f"Paper7 AS topology file not found: {self.edge_list_path}")

        # Backup option: synthetic graph
        return self._generate_synthetic()

    def _load_as_edge_list(self, path: Path) -> nx.Graph:
        """Load AS topology from edge list file."""
        raw_nodes_seen = set()
        edges = set()

        raw_edge_lines = 0
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split("\t")
                if len(parts) < 2:
                    continue

                try:
                    u = int(parts[0])
                    v = int(parts[1])
                except ValueError:
                    continue

                raw_edge_lines += 1
                raw_nodes_seen.add(u)
                raw_nodes_seen.add(v)

                if u == v:
                    continue

                # de-dup undirected edge
                a, b = (u, v) if u < v else (v, u)
                edges.add((a, b))

        G = nx.Graph()
        G.add_nodes_from(raw_nodes_seen)
        for (u, v) in edges:
            G.add_edge(u, v, distance=1.0)

        raw_nodes = len(raw_nodes_seen)
        raw_edges = raw_edge_lines
        dedup_edges = G.number_of_edges()

        # Keep largest CC
        if self.largest_cc_only and G.number_of_nodes() > 0:
            components = list(nx.connected_components(G))
            if components:
                largest = max(components, key=len)
                G = G.subgraph(largest).copy()

        # Cap to max_nodes
        if self.max_nodes is not None and G.number_of_nodes() > self.max_nodes:
            rng = np.random.default_rng(self.seed)
            keep = rng.choice(list(G.nodes()), size=self.max_nodes, replace=False)
            G = G.subgraph(keep).copy()
            if self.largest_cc_only:
                comps = list(nx.connected_components(G))
                if comps:
                    G = G.subgraph(max(comps, key=len)).copy()

        # Relabel to integers
        relabeled = False
        if self.relabel_to_integers:
            mapping = {node: i for i, node in enumerate(G.nodes())}
            G = nx.relabel_nodes(G, mapping, copy=True)
            relabeled = True

        self._last_report = Paper7TopologyLoadReport(
            path=str(path),
            raw_nodes=raw_nodes,
            raw_edges=raw_edges,
            dedup_edges=dedup_edges,
            kept_nodes=G.number_of_nodes(),
            kept_edges=G.number_of_edges(),
            relabeled=relabeled,
            largest_cc_only=self.largest_cc_only,
        )

        return G

    def _generate_synthetic(self) -> nx.Graph:
        """Backup: synthetic AS-like topology."""
        rng = np.random.default_rng(self.seed)
        kind = self.synthetic_kind.lower()

        n = int(self.synthetic_params.get("n", self.max_nodes or 1000))

        if kind == "barabasi_albert":
            m = int(self.synthetic_params.get("m", 3))
            G = nx.barabasi_albert_graph(n=n, m=m, seed=self.seed)
        elif kind == "erdos_renyi":
            p = float(self.synthetic_params.get("p", 0.01))
            G = nx.erdos_renyi_graph(n=n, p=p, seed=self.seed)
        elif kind == "watts_strogatz":
            k = int(self.synthetic_params.get("k", 6))
            p = float(self.synthetic_params.get("p", 0.1))
            G = nx.watts_strogatz_graph(n=n, k=k, p=p, seed=self.seed)
        else:
            raise ValueError(f"Unknown synthetic_kind='{self.synthetic_kind}'")

        # Add distances
        for u, v in G.edges():
            G[u][v]["distance"] = 1.0

        # Keep largest CC
        if self.largest_cc_only:
            comps = list(nx.connected_components(G))
            if comps:
                G = G.subgraph(max(comps, key=len)).copy()

        # ✅ Add metadata
        G.graph['testbed'] = self.testbed

        self._last_report = Paper7TopologyLoadReport(
            path=f"<synthetic:{self.synthetic_kind}>",
            raw_nodes=n,
            raw_edges=G.number_of_edges(),
            dedup_edges=G.number_of_edges(),
            kept_nodes=G.number_of_nodes(),
            kept_edges=G.number_of_edges(),
            relabeled=True,
            largest_cc_only=self.largest_cc_only,
        )
        return G

    def _sample_connected_subgraph(self, G: nx.Graph, node_num: int, *, max_tries: int = 20000) -> nx.Graph:
        """Sample connected subgraph of fixed size."""
        if node_num <= 0 or node_num > G.number_of_nodes():
            raise ValueError(f"node_num={node_num} invalid for |V|={G.number_of_nodes()}")

        rng = np.random.default_rng(self.seed)
        nodes = np.array(list(G.nodes()))

        for _ in range(max_tries):
            subset = rng.choice(nodes, size=node_num, replace=False)
            H = G.subgraph(subset).copy()
            if H.number_of_nodes() == node_num and nx.is_connected(H):
                return H

        raise RuntimeError(f"Failed to sample connected subgraph after {max_tries} tries")


class Paper12WaxmanTopologyGenerator(TopologyGenerator):
    """
    ✅ Waxman topology generator for QuARC (Wang et al. 2024)
    
    CAPACITY-AGNOSTIC: Topology is independent of path selection.
    QuARC uses multi-armed bandits over paths enumerated from this topology.
    """
    
    def __init__(self, n_nodes=100, avg_degree=6, alpha=0.4, beta=0.2, 
                 seed=42, dimensions=2, testbed="paper12"):
        self.n_nodes = n_nodes
        self.avg_degree = avg_degree
        self.alpha = alpha
        self.beta = beta
        self.seed = seed
        self.dimensions = dimensions
        self.testbed = testbed  # ✅ Store testbed
        
    def generate(self):
        """Generate Waxman topology."""
        np.random.seed(self.seed)
        
        # Create Waxman graph
        G = nx.waxman_graph(
            self.n_nodes, 
            self.alpha, 
            self.beta,
            domain=(0, 0, 1, 1)
        )
        
        # Ensure connectivity
        if not nx.is_connected(G):
            components = list(nx.connected_components(G))
            for i in range(len(components) - 1):
                node1 = list(components[i])[0]
                node2 = list(components[i+1])[0]
                G.add_edge(node1, node2, distance=1.0)
        
        # Add edge distances
        for u, v in G.edges():
            if 'distance' not in G[u][v]:
                pos_u = G.nodes[u].get('pos', (np.random.rand(), np.random.rand()))
                pos_v = G.nodes[v].get('pos', (np.random.rand(), np.random.rand()))
                dist = np.linalg.norm(np.array(pos_u) - np.array(pos_v))
                G[u][v]['distance'] = dist
        
        # ✅ Add metadata
        G.graph['testbed'] = self.testbed
        
        print(f"Generated {self.testbed} Waxman topology: {G.number_of_nodes()} nodes, "
              f"{G.number_of_edges()} edges, "
              f"avg degree: {2*G.number_of_edges()/G.number_of_nodes():.2f}")
        
        return G