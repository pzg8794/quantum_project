from copy import deepcopy
import json
import os
import subprocess
import sys

import numpy as np
import pytest

from daqr.campaigns.medium_spec import (
    PROTOCOL,PROTOCOL_ROOT_ID,build_catalog,build_mask,seed_for,seed_manifest,digest,validate_catalog,
)


def test_three_blocks_catalog_invariants_and_determinism():
    hashes=[]
    for block in range(3):
        catalog=build_catalog(block)
        assert catalog==build_catalog(block)
        validate_catalog(catalog)
        assert len(catalog["topology"]["nodes"])==15
        assert len(catalog["routes"])==10
        assert len(set(tuple(r["nodes"]) for r in catalog["routes"]))==10
        assert {n for r in catalog["routes"] for n in r["nodes"]}==set(range(15))
        assert all(len(r["nodes"])==4 and len(r["link_rates"])==3 for r in catalog["routes"])
        assert len(set(tuple(r["link_rates"]) for r in catalog["routes"]))==10
        actions=[r["actions"] for r in catalog["observations"]["routes"]]
        assert sum(map(len,actions))==550
        for a in actions:
            assert len(a)==len(set(map(tuple,a)))==55
            assert all(len(x)==3 and sum(x)==9 and min(x)>=0 for x in a)
        maxima=sorted(max(q) for q in catalog["physics"]["base_expected_payoffs"])
        assert len(set(maxima))==10 and maxima[0]>0
        assert maxima[-1]/maxima[-2]<=1.5
        assert maxima[-1]/np.median(maxima)<=3
        hashes.append(catalog["topology_hash"])
    assert len(set(hashes))==3


@pytest.mark.parametrize("scale,nodes,routes",[(1,7,4),(2,11,7),(3,15,10)])
def test_prespecified_family(scale,nodes,routes):
    cat=build_catalog(0,scale)
    assert len(cat["topology"]["nodes"])==nodes
    assert len(cat["routes"])==routes


@pytest.mark.parametrize("mutation",["duplicate","bad_edge","bad_action","bad_hash","missing_route"])
def test_fail_closed_catalog(mutation):
    cat=deepcopy(build_catalog())
    if mutation=="duplicate": cat["routes"][1]=cat["routes"][0]
    if mutation=="bad_edge": cat["topology"]["edges"].pop()
    if mutation=="bad_action": cat["observations"]["routes"][0]["actions"].pop()
    if mutation=="bad_hash": cat["route_set_hash"]="wrong"
    if mutation=="missing_route": cat["routes"].pop()
    with pytest.raises(ValueError): validate_catalog(cat)


def test_domain_seeds_queue_invariance_and_pairing():
    root=PROTOCOL_ROOT_ID
    base=seed_manifest(0,"EXPNeuralUCB","NoAttack")
    alternate=seed_manifest(0,"EXPNeuralUCB","RandomAttack")
    assert base["policy"]==alternate["policy"]
    assert seed_manifest(0,"Oracle","RandomAttack")["threat"]==alternate["threat"]
    assert len({seed_for(d,0) for d in ("topology","physics","environment","threat","policy","allocator")})==6
    assert base["route_generation"]["actual_seed"] is None
    assert base["observation"]["actual_seed"] is None
    assert base["allocator"]["actual_seed"] is None
    # Additional queue elements cannot mutate or enter the protocol root.
    for block in (3,4):
        build_catalog(block,1)
    assert digest(PROTOCOL)==root
    assert seed_manifest(0,"EXPNeuralUCB","NoAttack")==base


def test_seeds_are_process_independent():
    command=[sys.executable,"-B","-c","from daqr.campaigns.medium_spec import seed_for; print(seed_for('policy',0,3,'EXPNeuralUCB'))"]
    results=[subprocess.check_output(command,env={**os.environ,"PYTHONHASHSEED":s}) for s in ("1","876")]
    assert results[0]==results[1]


def test_mask_semantics_exact_threshold_and_noattack():
    assert np.array_equal(build_mask("NoAttack",20),np.ones((20,10)))
    seed=seed_for("threat",0,3,"RandomAttack")
    # Mask-only validation: no routing policy or learning execution.
    expected=(np.random.Generator(np.random.PCG64(seed)).random((1000,10))>=0.0625).astype(np.int8)
    actual=build_mask("RandomAttack",1000)
    np.testing.assert_array_equal(actual,expected)
    np.testing.assert_array_equal(actual,build_mask("RandomAttack",1000))
    assert set(np.unique(actual))=={0,1}
    assert 0.045 < 1-float(actual.mean()) < 0.08
    assert not np.array_equal(actual,build_mask("RandomAttack",1000,block=1))


def test_observation_catalog_has_no_privileged_values():
    obs=json.dumps(build_catalog()["observations"])
    for forbidden in ("link_rates","payoff","availability","feedback","threat","bernoulli"):
        assert forbidden not in obs
