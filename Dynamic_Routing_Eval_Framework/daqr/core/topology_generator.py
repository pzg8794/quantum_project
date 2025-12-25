"""
Network topology generators for quantum networks.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, Iterable

import networkx as nx
import numpy as np


class TopologyGenerator:
    """Base interface for topology generation."""
    def generate(self) -> nx.Graph:
        """Returns NetworkX graph."""
        raise NotImplementedError


class Paper2TopologyGenerator(TopologyGenerator):
    """
    Paper #2 QNetworkGraph_LearningAlgo.m topology.
    Random 2D placement, distance-based connectivity.
    """
    def __init__(self, num_nodes=15, area_km=20, link_threshold_km=10, seed=42):
        self.num_nodes = int(num_nodes)
        self.area_km = float(area_km)
        self.link_threshold_km = float(link_threshold_km)
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

        return G


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
    Paper #7 topology loader for topology_data/as20000101.txt

    File format (from the zip):
      - comment lines start with '#'
      - edge list lines are tab-separated: FromNodeId\\tToNodeId
      - undirected graph where each edge is saved twice (u->v and v->u)
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
        synthetic_kind: str = "barabasi_albert",   # "barabasi_albert" | "erdos_renyi" | "watts_strogatz"
        synthetic_params: Optional[Dict] = None,
    ):
        self.edge_list_path = Path(edge_list_path)
        self.relabel_to_integers = bool(relabel_to_integers)
        self.largest_cc_only = bool(largest_cc_only)
        self.max_nodes = None if max_nodes is None else int(max_nodes)
        self.seed = int(seed)

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
            # Optional: sample a connected induced subgraph of fixed size (Paper7-style)
        if self.max_nodes is not None:
            G = self._sample_connected_subgraph(G, self.max_nodes)

            return G

        if not self.synthetic_fallback:
            raise FileNotFoundError(f"Paper7 AS topology file not found: {self.edge_list_path}")

        # Backup option: synthetic graph
        return self._generate_synthetic()

    def _load_as_edge_list(self, path: Path) -> nx.Graph:
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
            # Paper7 file has no distances; set unit weight for shortest path ops
            G.add_edge(u, v, distance=1.0)

        raw_nodes = len(raw_nodes_seen)
        raw_edges = raw_edge_lines
        dedup_edges = G.number_of_edges()

        # Optionally trim to largest connected component
        if self.largest_cc_only and G.number_of_nodes() > 0:
            components = list(nx.connected_components(G))
            if components:
                largest = max(components, key=len)
                G = G.subgraph(largest).copy()

        # Optional cap to max_nodes (deterministic)
        if self.max_nodes is not None and G.number_of_nodes() > self.max_nodes:
            rng = np.random.default_rng(self.seed)
            keep = rng.choice(list(G.nodes()), size=self.max_nodes, replace=False)
            G = G.subgraph(keep).copy()
            # ensure connected if possible (keep largest CC after sampling)
            if self.largest_cc_only:
                comps = list(nx.connected_components(G))
                if comps:
                    G = G.subgraph(max(comps, key=len)).copy()

        # Relabel to 0..N-1 if desired
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
        """
        Backup option: synthetic AS-like topology.

        Defaults:
          - barabasi_albert: scale-free-ish graph (good AS proxy)
        """
        rng = np.random.default_rng(self.seed)
        kind = self.synthetic_kind.lower()

        # Defaults if not specified
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

        # Add unit distance for pathfinding compatibility
        for u, v in G.edges():
            G[u][v]["distance"] = 1.0

        # Keep largest CC (important for path enumeration)
        if self.largest_cc_only:
            comps = list(nx.connected_components(G))
            if comps:
                G = G.subgraph(max(comps, key=len)).copy()

        self._last_report = Paper7TopologyLoadReport(
            path=f"<synthetic:{self.synthetic_kind}>",
            raw_nodes=n,
            raw_edges=G.number_of_edges(),
            dedup_edges=G.number_of_edges(),
            kept_nodes=G.number_of_nodes(),
            kept_edges=G.number_of_edges(),
            relabeled=True,                 # already 0..n-1
            largest_cc_only=self.largest_cc_only,
        )
        return G

    def _sample_connected_subgraph(self, G: nx.Graph, node_num: int, *, max_tries: int = 20000) -> nx.Graph:
        """
        Paper7-style connected subgraph sampling:
        - repeatedly sample a node subset of size node_num
        - keep it if the induced subgraph is connected
        This matches the *approach* (connected induced subgraph), without enumerating combinations.
        """
        if node_num <= 0 or node_num > G.number_of_nodes():
            raise ValueError(f"node_num={node_num} invalid for |V|={G.number_of_nodes()}")

        rng = np.random.default_rng(self.seed)
        nodes = np.array(list(G.nodes()))

        for _ in range(max_tries):
            subset = rng.choice(nodes, size=node_num, replace=False)
            H = G.subgraph(subset).copy()
            if H.number_of_nodes() == node_num and nx.is_connected(H):
                return H

        raise RuntimeError(f"Failed to sample a connected subgraph of size {node_num} after {max_tries} tries")


class Paper12WaxmanTopologyGenerator:
    """
    Waxman topology generator for QuARC (Wang et al. 2024)
    
    Waxman model: P(edge) = α * exp(-d/(β*L)) where d=distance, L=max distance
    Used in QuARC paper with n=100-800 nodes, Ed=6 (avg degree)
    """
    
    def __init__(self, n_nodes=100, avg_degree=6, alpha=0.4, beta=0.2, 
                 seed=42, dimensions=2):
        """
        Args:
            n_nodes: Number of quantum nodes
            avg_degree: Target average node degree (Ed parameter)
            alpha: Waxman alpha (link prob scaling)
            beta: Waxman beta (distance decay)
            seed: Random seed
            dimensions: 2D or 3D placement
        """
        self.n_nodes = n_nodes
        self.avg_degree = avg_degree
        self.alpha = alpha
        self.beta = beta
        self.seed = seed
        self.dimensions = dimensions
        
    def generate(self):
        """Generate Waxman topology with specified properties"""
        np.random.seed(self.seed)
        
        # Create Waxman random geometric graph
        G = nx.waxman_graph(
            self.n_nodes, 
            self.alpha, 
            self.beta,
            domain=(0, 0, 1, 1)  # Unit square
        )
        
        # Ensure connectivity
        if not nx.is_connected(G):
            # Connect components
            components = list(nx.connected_components(G))
            for i in range(len(components) - 1):
                node1 = list(components[i])[0]
                node2 = list(components[i+1])[0]
                G.add_edge(node1, node2, distance=1.0)
        
        # Add edge attributes
        for u, v in G.edges():
            if 'distance' not in G[u][v]:
                # Euclidean distance from node positions
                pos_u = G.nodes[u].get('pos', (np.random.rand(), np.random.rand()))
                pos_v = G.nodes[v].get('pos', (np.random.rand(), np.random.rand()))
                dist = np.linalg.norm(np.array(pos_u) - np.array(pos_v))
                G[u][v]['distance'] = dist
        
        print(f"Generated Waxman topology: {G.number_of_nodes()} nodes, "
              f"{G.number_of_edges()} edges, "
              f"avg degree: {2*G.number_of_edges()/G.number_of_nodes():.2f}")
        
        return G