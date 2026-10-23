"""Frozen pre-generalization four-route calculation, plus metadata invariants."""
import numpy as np
import pytest

from daqr.core.attack_strategy import NoAttack
from daqr.core.network_environment import QuantumEnvironment
from daqr.core.primary_routes import LEGACY_PRIMARY_ROUTES, PrimaryRoute, allocations


def legacy_fixture(capacities=(8, 10, 8, 9), factor=100):
    # Reference ordering/equations from 47757380 network_environment.py.
    contexts = []
    for idx, cap in enumerate(capacities):
        if idx < 2:
            contexts.append(np.array([[i, cap-i] for i in range(cap+1)]))
        else:
            contexts.append(np.array([[i, j, cap-i-j]
                                      for i in range(cap+1) for j in range(cap+1-i)]))
    p1 = 1 - (1 - 1.5e-4)**factor
    p2 = 1 - (1 - 1e-4)**factor
    p3 = 1 - (1 - 2e-4)**factor
    rewards = [
        [(1-(1-p1)**c[0])*(1-(1-p1)**c[1]) for c in contexts[0]],
        [(1-(1-p2)**c[0])*(1-(1-p2)**c[1]) for c in contexts[1]],
        [(1-(1-p3)**c[0])*(1-(1-p3)**c[1])*(1-(1-p3)**c[2]) for c in contexts[2]],
        [(1-(1-p1)**c[0])*(1-(1-p1)**c[1])*(1-(1-p1)**c[2]) for c in contexts[3]],
    ]
    return contexts, rewards


@pytest.mark.parametrize("explicit", [False, True])
def test_four_route_exact_regression(explicit):
    env = QuantumEnvironment(NoAttack(), route_metadata=LEGACY_PRIMARY_ROUTES if explicit else None)
    contexts, rewards = legacy_fixture()
    assert [len(x) for x in contexts] == [9, 11, 45, 55]
    for new, old in zip(env.contexts, contexts):
        np.testing.assert_array_equal(new, old)
    for new, old in zip(env.reward_list, rewards):
        np.testing.assert_array_equal(new, old)  # exact; no tolerance allowed
    assert env._primary_routes() == LEGACY_PRIMARY_ROUTES


def test_route_metadata_not_position_controls_physics_and_dimensions():
    order = [2, 0, 3, 1]
    caps = (8, 10, 8, 9)
    old_contexts, old_rewards = legacy_fixture()
    env = QuantumEnvironment(NoAttack(), qubit_capacities=tuple(caps[i] for i in order),
                             route_metadata=tuple(LEGACY_PRIMARY_ROUTES[i] for i in order))
    for idx, old in enumerate(order):
        np.testing.assert_array_equal(env.contexts[idx], old_contexts[old])
        np.testing.assert_array_equal(env.reward_list[idx], old_rewards[old])


def test_ordered_heterogeneous_profile_and_allocation():
    a = PrimaryRoute("forward", (1e-4, 1.5e-4, 2e-4))
    b = PrimaryRoute("reverse", tuple(reversed(a.link_rates)))
    env = QuantumEnvironment(NoAttack(), qubit_capacities=(9, 9), route_metadata=(a, b))
    assert env.reward_list[0] != env.reward_list[1]
    for idx, vector in enumerate(env.contexts[0]):
        rev = list(map(tuple, env.contexts[1])).index(tuple(reversed(vector)))
        assert np.isclose(env.reward_list[0][idx], env.reward_list[1][rev], rtol=1e-15, atol=0)


def test_fail_closed_missing_metadata_or_bad_dimensions():
    with pytest.raises(ValueError, match="explicit route_metadata"):
        QuantumEnvironment(NoAttack(), qubit_capacities=(9,)*10)
    with pytest.raises(ValueError, match="Duplicate"):
        QuantumEnvironment(NoAttack(), qubit_capacities=(9,9),
                           route_metadata=(LEGACY_PRIMARY_ROUTES[0],)*2)
    with pytest.raises(ValueError):
        allocations(9, 3, max_actions=54)


def test_exact_55_allocation_invariants():
    actions = allocations(9, 3)
    assert actions.shape == (55, 3)
    assert len(set(map(tuple, actions))) == 55
    assert (actions >= 0).all()
    assert (actions.sum(axis=1) == 9).all()
    assert sum((actions > 0).all(axis=1)) == 28
