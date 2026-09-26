"""Explicit route-local primary physics and ordered allocation catalogs.

The two-stage power and left-to-right product deliberately preserve the legacy
floating-point calculation. Rates describe route-local hops, not shared edges.
"""
from dataclasses import dataclass
from math import comb, isfinite
from numbers import Integral

import numpy as np


@dataclass(frozen=True)
class PrimaryRoute:
    route_id: str
    link_rates: tuple[float, ...]
    nodes: tuple[int, ...] = ()

    def __post_init__(self):
        if not self.route_id or not self.link_rates:
            raise ValueError("Primary route requires identity and ordered link rates")
        if any(not isfinite(p) or not 0 <= p <= 1 for p in self.link_rates):
            raise ValueError("Link rates must be finite probabilities")
        if self.nodes and (len(self.nodes) != self.hops + 1 or len(set(self.nodes)) != len(self.nodes)):
            raise ValueError("Route nodes must be simple and aligned with the hop profile")

    @property
    def hops(self):
        return len(self.link_rates)


# Stable compatibility identities; no physical node sequence is inferred.
LEGACY_PRIMARY_ROUTES = (
    PrimaryRoute("legacy-primary-0", (1.5e-4, 1.5e-4)),
    PrimaryRoute("legacy-primary-1", (1e-4, 1e-4)),
    PrimaryRoute("legacy-primary-2", (2e-4, 2e-4, 2e-4)),
    PrimaryRoute("legacy-primary-3", (1.5e-4, 1.5e-4, 1.5e-4)),
)


def validate_routes(routes, capacities):
    routes = tuple(routes)
    if len(routes) != len(capacities) or not routes:
        raise ValueError("Route metadata and capacities must have the same nonzero length")
    if len({r.route_id for r in routes}) != len(routes):
        raise ValueError("Duplicate route identity")
    for budget in capacities:
        if not isinstance(budget, Integral) or isinstance(budget, bool) or budget < 0:
            raise ValueError("Route budgets must be nonnegative integers")
    return routes


def allocations(budget, hops, max_actions=1_000_000):
    """All weak compositions in legacy lexicographic order; never truncate."""
    if (not isinstance(budget, Integral) or isinstance(budget, bool) or budget < 0
            or not isinstance(hops, Integral) or isinstance(hops, bool) or hops < 1):
        raise ValueError("Invalid allocation dimension or budget")
    count = comb(budget + hops - 1, hops - 1)
    if count > max_actions:
        raise ValueError(f"Action catalog of {count} exceeds explicit safety bound {max_actions}")

    def parts(total, dim):
        if dim == 1:
            yield (total,)
        else:
            for first in range(total + 1):
                for rest in parts(total - first, dim - 1):
                    yield (first,) + rest

    result = np.asarray(list(parts(int(budget), int(hops))), dtype=int)
    if result.shape != (count, hops):
        raise ValueError("Allocation cardinality mismatch")
    return result


def primary_rewards(route, contexts, success_factor=100):
    contexts = np.asarray(contexts)
    if contexts.ndim != 2 or contexts.shape[1] != route.hops:
        raise ValueError("Action/context dimension does not match route hops")
    if not isfinite(success_factor) or success_factor <= 0:
        raise ValueError("Invalid entanglement success factor")
    link_probabilities = [1 - (1 - p) ** success_factor for p in route.link_rates]
    rewards = []
    for context in contexts:
        terms = [1 - (1 - p) ** x for p, x in zip(link_probabilities, context)]
        value = terms[0]
        for term in terms[1:]:
            value = value * term
        rewards.append(value)
    return rewards
