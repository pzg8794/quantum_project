"""Architecture/extensibility tests; all choices below are technical fixtures."""
from copy import deepcopy
from dataclasses import replace
import json
import resource
import time
import numpy as np
import pytest

from medium_fixtures import fixture_config
from daqr.config.execution_contract import resolve_configuration
from daqr.core.attack_strategy import NoAttack
from daqr.algorithms.base_bandit import Oracle
from daqr.campaigns.medium_spec import build_catalog, build_mask, digest, protocol, seed_manifest
from daqr.campaigns.medium_runner import prepare_manifest, execute_preflight, run_policy, code_identity
from daqr.campaigns.medium_trace import AttemptBundle, validate_completion


class InjectedScenario(NoAttack):
    """New valid scenario ID and class, without campaign edits."""


class InjectedPolicy(Oracle):
    def __str__(self):
        return "InjectedPolicy"


def test_strict_constructor_cannot_replace_empty_axes_with_legacy_defaults():
    from daqr.config.experiment_config import ExperimentConfiguration
    with pytest.raises(ValueError,match="explicit nonempty"):
        ExperimentConfiguration(models=[],scenarios={},persistence=False)


def test_scenario_extensibility_and_complete_cell_counts(tmp_path):
    cfg=fixture_config(frames=2)
    from daqr.core.attack_strategy import STRATEGY_REGISTRY
    cfg.strategy_registry={**STRATEGY_REGISTRY,"injected":InjectedScenario}
    cfg.test_scenarios["Third"]={"strategy":"injected","parameters":{}}
    cfg.test_scenarios["Markov"]={"strategy":"markov","parameters":{"attack_rate":0.1,"p_stay":0.7}}
    resolved=resolve_configuration(cfg)
    assert len(resolved["required_cells"])==cfg.runs*len(cfg.models)*len(cfg.test_scenarios)
    for scenario in ("Third","Markov"):
        path,done=execute_preflight(tmp_path,cfg,"Oracle",scenario,0,3)
        assert done["state"]=="COMPLETE"
        manifest=json.loads((path/"manifest.json").read_text())
        assert len(manifest["configuration"]["resolved"]["scenarios"])==4
        assert manifest["identity"]["threat"]==scenario


def test_policy_extension_uses_registry_not_campaign_dispatch(tmp_path):
    cfg=fixture_config(frames=2)
    cfg.models.append("InjectedPolicy")
    cfg.algorithm_configs["InjectedPolicy"]={
        "model_class":InjectedPolicy,"kwargs":{"mode":"base"},"runner_type":"step-wise","seed_offset":123}
    path,done=execute_preflight(tmp_path,cfg,"InjectedPolicy","NoAttack",0,3)
    assert done["state"]=="COMPLETE"
    m=json.loads((path/"manifest.json").read_text())
    assert m["identity"]["policy_class"].endswith(".InjectedPolicy")
    assert m["identity"]["trace_contract"]["privileged"]


def test_existing_description_scenarios_use_canonical_scalar_settings():
    cfg=fixture_config(frames=2)
    cfg.test_scenarios={"none":"Baseline","stochastic":"Failures","markov":"Structured"}
    cfg.attack_rate=0.4
    cfg.attack_intensity=0.5
    resolved=resolve_configuration(cfg)
    assert resolved["scenarios"]["stochastic"]["parameters"]["attack_rate"]==0.2
    assert resolved["scenarios"]["markov"]["parameters"]["attack_rate"]==0.5
    assert set(resolved["scenarios"])==set(cfg.test_scenarios)


def test_scale_extension_no_whitelist():
    cfg=fixture_config(scale_m=4,rates=(1e-4,1.5e-4,2e-4,2.5e-4))
    cat=build_catalog(cfg,0,4)
    assert len(cat["routes"])==13 and len(cat["topology"]["nodes"])==19
    assert cat["diagnostics"]["total_actions"]==13*55


def test_configuration_mutation_propagates_to_manifest_and_execution(tmp_path):
    cfg=fixture_config(frames=3,scale_m=1,budget=6)
    cfg.physics_params["entanglement_success_factor"]=73
    cfg.scale=3
    cfg.base_capacity=False
    cfg.algorithm_configs["EXPNeuralUCB"]["kwargs"]["beta"]=0.5
    manifest,cat,mask=prepare_manifest(cfg,"EXPNeuralUCB","NoAttack",0,scale_m=1)
    assert manifest["identity"]["horizon"]==3
    assert manifest["identity"]["replay"]["capacity"]==9
    assert manifest["identity"]["policy_kwargs"]["beta"]==0.5
    assert cat["physics"]["success_factor"]==73
    assert len(cat["observations"]["routes"][0]["actions"])==28
    contexts=[np.array(r["actions"]) for r in cat["observations"]["routes"]]
    _,state=run_policy(cfg,"EXPNeuralUCB",contexts,cat["physics"]["base_expected_payoffs"],mask,42,capture_state=True)
    assert all(n["replay"]["capacity"]==9 for n in state["neural"])
    path,done=execute_preflight(tmp_path,cfg,"Oracle","NoAttack",0,1)
    assert done["actual_record_counts"]["UPDATE"]==3


@pytest.mark.parametrize("fault",["unknown_scenario","history","online","empty_models","unknown_policy",
                                  "empty_scenarios","bad_physics","bad_profiles","bad_scale","bad_replay",
                                  "bad_allocator","budget","batch","mode"])
def test_fail_closed_entire_configuration(fault,tmp_path):
    cfg=fixture_config(frames=1)
    if fault=="unknown_scenario": cfg.test_scenarios["bad"]={"strategy":"missing","parameters":{}}
    if fault=="history": cfg.test_scenarios["history"]={"strategy":"adaptive","parameters":{}}
    if fault=="online": cfg.test_scenarios["online"]={"strategy":"onlineadaptive","parameters":{}}
    if fault=="empty_models": cfg.models=[]
    if fault=="unknown_policy": cfg.models.append("missing")
    if fault=="empty_scenarios": cfg.test_scenarios={}
    if fault=="bad_physics": cfg.physics_params={}
    if fault=="bad_profiles": cfg.testbed_config["profile_pool"]=[]
    if fault=="bad_scale": cfg.execution=replace(cfg.execution,scale_points=(0,))
    if fault=="bad_replay": cfg.scale=-1
    if fault=="bad_allocator": cfg.allocator.allocation_capability="dynamic"
    if fault=="budget": cfg.allocator.total_qubits=91
    if fault=="batch": cfg.algorithm_configs["Oracle"]["runner_type"]="unsupported"
    if fault=="mode": cfg.algorithm_configs["EXPNeuralUCB"]["kwargs"]["mode"]="neural"
    with pytest.raises(ValueError):
        execute_preflight(tmp_path,cfg,"Oracle","NoAttack",0,3)
    assert not list(tmp_path.iterdir())  # cannot run even a supported cell of an invalid matrix


def test_seed_root_independent_of_queue_expansion():
    cfg=fixture_config()
    before=seed_manifest(cfg,0,"Oracle","NoAttack",3)
    root=digest(protocol(cfg))
    cfg.runs+=1
    cfg.execution=replace(cfg.execution,scale_points=(1,3,4))
    cfg.test_scenarios["extra"]={"strategy":"markov","parameters":{"attack_rate":0.2}}
    assert digest(protocol(cfg))==root
    assert seed_manifest(cfg,0,"Oracle","NoAttack",3)==before


def test_recorded_environment_uses_supplied_strategy_mask():
    from daqr.core.recorded_environment import RecordedQuantumEnvironment
    from daqr.core.primary_routes import PrimaryRoute
    cfg=fixture_config(frames=2,scale_m=1)
    cat=build_catalog(cfg,0,1)
    mask=np.zeros((2,4),dtype=np.int8)
    env=RecordedQuantumEnvironment(
        availability=mask,attack=cfg.resolve_attack_strategy("RandomAttack"),
        route_metadata=tuple(PrimaryRoute(r["route_id"],tuple(r["link_rates"]),tuple(r["nodes"])) for r in cat["routes"]),
        qubit_capacities=(9,)*4,frame_length=2,num_paths=4,num_total_qubits=36,
        **cfg.physics_params)
    np.testing.assert_array_equal(env.get_environment_info()["attack_pattern"],mask)
    assert not env.generate_attack_pattern().flags.writeable


def test_scientific_configuration_cannot_execute(tmp_path):
    cfg=fixture_config()
    cfg.execution=replace(cfg.execution,execution_kind="scientific")
    with pytest.raises(ValueError,match="not authorized"):
        execute_preflight(tmp_path,cfg,"Oracle","NoAttack",0,3)
    assert not list(tmp_path.iterdir())


def test_scale_completion_requires_entire_configured_axis(tmp_path):
    from daqr.campaigns.medium_trace import validate_scale_completion
    cfg=fixture_config(frames=1)
    cfg.runs=1
    cfg.models=["Oracle"]
    a,_=execute_preflight(tmp_path,cfg,"Oracle","NoAttack",0,3)
    with pytest.raises(ValueError,match="Incomplete scale"):
        validate_scale_completion(cfg,3,[a])
    b,_=execute_preflight(tmp_path,cfg,"Oracle","RandomAttack",0,3)
    assert validate_scale_completion(cfg,3,[a,b])["required_cells"]==2
    with pytest.raises(ValueError,match="duplicate"):
        validate_scale_completion(cfg,3,[a,a,b])


def test_actual_hybrid_emits_applied_importance_weighted_update():
    from test_medium_preflight import CapturingSink
    cfg=fixture_config(frames=5)
    contexts=[np.array([[1,0],[0,1]]) for _ in range(2)]
    sink=CapturingSink()
    _,state=run_policy(cfg,"EXPNeuralUCB",contexts,[[1.,1.],[1.,1.]],np.ones((5,2)),42,sink,True)
    decisions=[r[1] for r in sink.events if r[0]=="decision"]
    updates=[r[1] for r in sink.events if r[0]=="update"]
    for frame,(decision,update) in enumerate(zip(decisions,updates)):
        route=decision[1]
        probability=decision[3][route]
        assert update[1]["group_target"]==1/max(probability,1e-12)
        assert update[1]["group_target"]==state["group_estimates"][route][frame+1]
    assert any(u[1]["group_target"]!=1 for u in updates)


def test_importance_weighted_update_and_validator(tmp_path):
    # Unit accounting fixture with positive feedback; no learning performance claim.
    cfg=fixture_config(frames=1)
    m,cat,mask=prepare_manifest(cfg,"EXPNeuralUCB","NoAttack",0,scale_m=3)
    route,action=0,1
    # Pick an all-positive allocation so a positive Bernoulli draw is possible.
    action=next(i for i,a in enumerate(cat["observations"]["routes"][route]["actions"]) if min(a)>0)
    q=cat["physics"]["base_expected_payoffs"][route][action]
    b=AttemptBundle(tmp_path,m,cat,mask)
    b.recorder.preselection(0,[r["actions"] for r in cat["observations"]["routes"]])
    probs=[0.1]*len(cat["routes"])
    b.recorder.decision(0,route,action,probs)
    b.recorder.outcome(0,q,1,q,1,1)
    b.recorder.update(0,q,True,group_target=10)
    b.finish()
    assert validate_completion(b.directory,m)["positive_route_feedback_count"]==1
    # Recompute checksums too: semantic validator must reject raw-as-weighted value.
    from daqr.campaigns.medium_trace import file_hash, _validate_payload
    rows=[json.loads(x) for x in (b.directory/"events.jsonl").read_text().splitlines()]
    rows[-1]["importance_weighted_route_update"]=1
    (b.directory/"events.jsonl").write_text("".join(json.dumps(row)+"\n" for row in rows))
    completion=json.loads((b.directory/"completion.json").read_text())
    completion["file_hashes"]["events.jsonl"]=file_hash(b.directory/"events.jsonl")
    with pytest.raises(ValueError,match="update-channel"):
        _validate_payload(b.directory,m,completion)
