"""Pass-2 technical extension fixtures: no scientific defaults or results."""
from copy import deepcopy
from dataclasses import asdict, replace
import json
import numpy as np
import pytest

from medium_fixtures import FULL_MODEL_ROSTER, fixture_config
from test_medium_preflight import exact_equal
from daqr.config.execution_contract import resolve_configuration
from daqr.core.attack_strategy import (
    AttackStrategy, NoAttack, RandomAttack, MarkovAttack, AdaptiveAttack,
    OnlineAdaptiveAttack, STRATEGY_REGISTRY,
)
from daqr.core.catalog_components import LayeredPrimaryCatalog
from daqr.core.primary_routes import PrimaryRoute, allocations
from daqr.core.identity import digest
from daqr.campaigns.medium_spec import build_catalog, build_mask, build_scenario
from daqr.campaigns.medium_runner import prepare_manifest, execute_preflight, run_policy
from daqr.campaigns.medium_trace import AttemptBundle, validate_completion, validate_scale_completion


class ConstantReward:
    component_id = "test-constant-reward"
    def validate_config(self, params):
        if set(params) != {"level"} or not 0 <= params["level"] <= 1:
            raise ValueError("constant reward schema")
    def values(self, route, actions, params):
        return np.full(len(actions),params["level"])
    def build(self, params, routes, actions):
        self.validate_config(params)
        return {"routes":[asdict(r) for r in routes],
                "base_expected_payoffs":[self.values(r,a,params).tolist() for r,a in zip(routes,actions)]}


class TwoHopCatalog:
    component_id = "test-two-hop"
    def validate_config(self, params):
        if set(params) != {"width"} or params["width"] < 1:
            raise ValueError("two-hop schema")
    def build(self, cfg, scale, topology_seed, physics_seed, reward):
        width = cfg.testbed_config["width"]
        dest = width+1
        topology = {"family":self.component_id,"nodes":list(range(dest+1)),
                    "edges":[e for i in range(1,dest) for e in ((0,i),(i,dest))],
                    "source":0,"destination":dest,"scale_m":scale}
        th = digest(topology)
        routes = [PrimaryRoute(digest({"topology_hash":th,"ordered_nodes":(0,i,dest)}),
                               (0.1,0.2),(0,i,dest)) for i in range(1,dest)]
        budgets = cfg.allocator.allocate(timestep=0,route_stats={},verbose=False)
        assert len(budgets)==width
        actions = [allocations(b,2).tolist() for b in budgets]
        observations={"version":"two-hop-test-v1","observation_kind":"allocation_context",
                      "link_measurements_present":False,
                      "routes":[{"route_id":r.route_id,"nodes":r.nodes,"hops":2,"budget":b,"actions":a}
                                for r,b,a in zip(routes,budgets,actions)]}
        physics=reward.build(cfg.physics_params,routes,actions)
        route_data=[asdict(r) for r in routes]
        result={"topology":topology,"topology_hash":th,"routes":route_data,
                "route_set_hash":digest(sorted(route_data,key=lambda r:r["route_id"])),
                "observations":observations,"observation_catalog_hash":digest(observations),
                "physics":physics,"physics_hash":digest(physics),
                "action_catalog_hash":digest(actions),"diagnostics":{"total_actions":sum(map(len,actions))}}
        self.validate(result,reward,cfg.physics_params)
        return result
    def validate(self, catalog, reward, params):
        assert all(len(r["nodes"])==3 for r in catalog["routes"])


class ModeFreePolicy:
    """Independent registered policy; no QuantumModel inheritance or mode."""
    supports_causal_scenarios = True
    validated = 0
    @classmethod
    def validate_execution_config(cls, kwargs):
        if set(kwargs) != {"action"}:
            raise ValueError("test policy requires action, not mode")
        cls.validated += 1
    def __init__(self, configs, X_n, reward_list, frame_number, attack_list, capacity, action):
        self.action=action
        self.pairs=[]
        self.total=0.
    def take_action(self):
        return 0,self.action
    def update(self, route, action, payoff):
        self.pairs.append([int(route),int(action)])
        self.total+=float(payoff)
    def get_results(self):
        return {"path_action_list":deepcopy(self.pairs),"final_reward":self.total}


class SnapshotPolicy(ModeFreePolicy):
    def diagnostic_snapshot(self):
        return {"injected_snapshot":{"updates":len(self.pairs),"total":self.total}}


def inject_policy(cfg, cls):
    cfg.models=["test-policy"]
    cfg.algorithm_configs["test-policy"]={"model_class":cls,"kwargs":{"action":0},
                                         "runner_type":"step-wise","seed_offset":999}


@pytest.mark.parametrize("alternative",["topology","physics","both"])
def test_component_schemas_are_owned_by_selected_components(alternative,tmp_path):
    cfg=fixture_config(frames=2,scale_m=1)
    inject_policy(cfg,ModeFreePolicy)
    if alternative in {"topology","both"}:
        cfg.catalog_component=TwoHopCatalog()
        cfg.testbed_config={"width":4}
    if alternative in {"physics","both"}:
        cfg.reward_component=ConstantReward()
        cfg.physics_params={"level":0.25}
    resolved=resolve_configuration(cfg)
    assert resolved["components"]["catalog"]["component_id"]==cfg.catalog_component.component_id
    cat=build_catalog(cfg,0,1)
    if alternative in {"topology","both"}:
        assert all(len(r["nodes"])==3 for r in cat["routes"])
    if alternative in {"physics","both"}:
        assert all(set(q)=={0.25} for q in cat["physics"]["base_expected_payoffs"])
    path,done=execute_preflight(tmp_path,cfg,"test-policy","NoAttack",0,1)
    assert done["state"]=="COMPLETE"
    assert ModeFreePolicy.validated>0
    # The selected component, not the generic resolver, rejects its schema.
    if alternative=="physics": cfg.physics_params={"wrong":1}
    else: cfg.testbed_config={"wrong":1}
    with pytest.raises(ValueError): resolve_configuration(cfg)


@pytest.mark.parametrize("cls",[ModeFreePolicy,SnapshotPolicy])
def test_mode_free_optional_snapshot_policy_executes(cls,tmp_path):
    cfg=fixture_config(frames=3)
    inject_policy(cfg,cls)
    m,cat,mask=prepare_manifest(cfg,"test-policy","NoAttack",0,scale_m=3)
    assert "mode" not in m["identity"]["policy_kwargs"]
    result,state=run_policy(cfg,"test-policy",[np.array(r["actions"]) for r in cat["observations"]["routes"]],
                            cat["physics"]["base_expected_payoffs"],mask,11,capture_state=True)
    assert len(result["path_action_list"])==3
    assert ("injected_snapshot" in state)==(cls is SnapshotPolicy)
    path,done=execute_preflight(tmp_path,cfg,"test-policy","NoAttack",0,3)
    assert done["state"]=="COMPLETE"


class CausalProbe(AttackStrategy):
    mask_capability="selection_history"
    calls=[]
    def availability_at(self,t,history,state,rng,routes,frames):
        assert isinstance(history,tuple) and len(history)==t
        type(self).calls.append((t,history))
        row=np.ones(routes,dtype=np.int8)
        if history: row[history[-1]]=0
        return row


class OnlineProbe(CausalProbe):
    mask_capability="online_selection_history"


@pytest.mark.parametrize("cls",[CausalProbe,OnlineProbe])
def test_injected_causal_scenario_chronology(cls,tmp_path):
    cls.calls=[]
    cfg=fixture_config(frames=4)
    inject_policy(cfg,ModeFreePolicy)
    cfg.strategy_registry={**STRATEGY_REGISTRY,"probe":cls}
    cfg.test_scenarios={"probe":{"strategy":"probe","parameters":{}}}
    path,done=execute_preflight(tmp_path,cfg,"test-policy","probe",0,3)
    assert cls.calls==[(0,()),(1,(0,)),(2,(0,0)),(3,(0,0,0))]
    assert done["state"]=="COMPLETE"
    m=json.loads((path/"manifest.json").read_text())
    assert m["identity"]["threat_trajectory_hash"] is None
    mask=json.loads((path/"availability.json").read_text())
    assert [r[0] for r in mask]==[1,0,0,0]
    assert done["realized_trajectory_hash"]==digest(mask)
    assert all("availability" not in r for r in map(json.loads,(path/"events.jsonl").read_text().splitlines())
               if r["phase"]=="PRESELECTION")


@pytest.mark.parametrize("strategy",[NoAttack(),RandomAttack(.2),MarkovAttack(.2,.7)])
def test_static_session_matches_original_realization(strategy):
    expected=strategy.generate(np.random.default_rng(123),8,10)
    session=strategy.open_session(np.random.default_rng(123),8,10)
    assert not session.precomputed.flags.writeable
    for t in range(8):
        np.testing.assert_array_equal(session.begin(t),expected[t])
        session.observe(t,t%10)
    np.testing.assert_array_equal(session.completed_mask(),expected)


@pytest.mark.parametrize("strategy",[
    AdaptiveAttack(.2,adaptation_window=3,adaptation_strength=.5),
    OnlineAdaptiveAttack(.2,response_delay=2,burst_probability=.3)])
def test_causal_session_matches_existing_supplied_history_algorithm(strategy):
    # Independent transcription of the pre-Pass-2 generate arithmetic. This is a
    # technical regression, not validation against a manuscript definition.
    trace=np.array([2,1,2,0,3,1,2,3,0,1,1,1,2,3,0,1,2,1,0,3])
    rng=np.random.default_rng(716)
    expected=np.ones((len(trace),4),dtype=np.int8)
    if isinstance(strategy,AdaptiveAttack):
        for t in range(len(trace)):
            recent=trace[max(0,t-strategy.adaptation_window):t]
            if len(recent):
                probs=np.bincount(recent,minlength=4)/len(recent)
                for p in range(4):
                    rate=min(strategy.attack_rate+strategy.adaptation_strength*probs[p],.9)
                    expected[t,p]=1 if rng.random()>=rate else 0
            else: expected[t,:]=(rng.random(4)>=strategy.attack_rate).astype(np.int8)
    else:
        for t in range(len(trace)):
            if rng.random()<strategy.burst_probability:
                expected[t:t+min(10,len(trace)-t),:]=0
                continue
            if t>=strategy.response_delay:
                recent=trace[max(0,t-strategy.response_delay):t]
                if len(recent): expected[t,recent[-1]]=0 if rng.random()<strategy.attack_rate*2 else 1
            for p in range(4):
                if expected[t,p]==1:
                    expected[t,p]=1 if rng.random()>=strategy.attack_rate else 0
    session=strategy.open_session(np.random.default_rng(716),len(trace),4)
    for t,route in enumerate(trace):
        np.testing.assert_array_equal(session.begin(t),expected[t])
        session.observe(t,int(route))
    np.testing.assert_array_equal(session.completed_mask(),expected)
    np.testing.assert_array_equal(strategy.generate(np.random.default_rng(716),len(trace),4,trace),expected)


@pytest.mark.parametrize("strategy",[AdaptiveAttack(),OnlineAdaptiveAttack()])
def test_missing_history_is_never_random_fallback(strategy):
    with pytest.raises(ValueError,match="history"):
        strategy.generate(np.random.default_rng(1),3,4)
    with pytest.raises(ValueError,match="history"):
        strategy.availability_at(2,(),{},np.random.default_rng(1),4,3)


def test_session_rejects_wrong_phase_and_no_premature_completion():
    session=CausalProbe().open_session(np.random.default_rng(1),3,4)
    with pytest.raises(ValueError): session.observe(0,0)
    with pytest.raises(ValueError): session.begin(1)
    session.begin(0)
    with pytest.raises(ValueError): session.begin(0)
    with pytest.raises(ValueError): session.completed_mask()
    session.observe(0,0)
    with pytest.raises(ValueError): session.observe(0,0)


@pytest.mark.parametrize("scenario",["adaptive","onlineadaptive"])
@pytest.mark.parametrize("policy",FULL_MODEL_ROSTER)
def test_real_causal_policies_logging_exact_equivalence(scenario,policy,tmp_path):
    cfg=fixture_config(frames=8)
    cfg.test_scenarios={scenario:{"strategy":scenario,"parameters":{"attack_rate":.2}}}
    m,cat,off_session=prepare_manifest(cfg,policy,scenario,0,scale_m=3)
    contexts=[np.array(r["actions"]) for r in cat["observations"]["routes"]]
    rewards=cat["physics"]["base_expected_payoffs"]
    seed=m["identity"]["seeds"]["policy"]["actual_seed"]
    off,off_state=run_policy(cfg,policy,contexts,rewards,off_session,seed,capture_state=True)
    # Freezing this already-realized trajectory must preserve the policy's
    # exact arithmetic/state. It is a technical replay, not a counterfactual.
    frozen,frozen_state=run_policy(cfg,policy,contexts,rewards,off_session.completed_mask(),
                                   seed,capture_state=True)
    exact_equal(off,frozen)
    exact_equal(off_state,frozen_state)
    _,_,on_session=prepare_manifest(cfg,policy,scenario,0,scale_m=3)
    b=AttemptBundle(tmp_path,m,cat,on_session)
    on,on_state=run_policy(cfg,policy,contexts,rewards,on_session,seed,b.recorder,True)
    b.finish()
    exact_equal(off,on)
    exact_equal(off_state,on_state)
    np.testing.assert_array_equal(off_session.completed_mask(),on_session.completed_mask())
    validate_completion(b.directory,m)
    with pytest.raises(ValueError,match="causal execution"):
        build_mask(cfg,scenario,8,0,3)


def test_complete_matrix_includes_causal_scenarios_and_blocks(tmp_path):
    cfg=fixture_config(frames=1)
    inject_policy(cfg,ModeFreePolicy)
    cfg.runs=2
    cfg.test_scenarios={k:{"strategy":k,"parameters":{}} for k in ("none","adaptive","onlineadaptive")}
    cells=resolve_configuration(cfg)["required_cells"]
    paths=[execute_preflight(tmp_path,cfg,c["policy"],c["scenario"],c["block"],c["scale"])[0] for c in cells]
    with pytest.raises(ValueError,match="Incomplete scale"): validate_scale_completion(cfg,3,paths[:-1])
    assert validate_scale_completion(cfg,3,paths)["required_cells"]==len(cells)


def test_causal_unsupported_policy_fails_entire_matrix(tmp_path):
    class Unsupported(ModeFreePolicy):
        supports_causal_scenarios=False
    cfg=fixture_config(frames=1)
    inject_policy(cfg,Unsupported)
    cfg.test_scenarios["adaptive"]={"strategy":"adaptive","parameters":{}}
    with pytest.raises(ValueError,match="causal scenario"):
        execute_preflight(tmp_path,cfg,"test-policy","NoAttack",0,3)
    assert not list(tmp_path.iterdir())
