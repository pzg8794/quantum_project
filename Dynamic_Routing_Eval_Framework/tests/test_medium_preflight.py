from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import torch

from medium_fixtures import FULL_MODEL_ROSTER,prepare_manifest,run_policy,execute_preflight
from daqr.campaigns.medium_runner import FRAME_LIMIT
from daqr.campaigns.medium_trace import (
    EventRecorder,AttemptBundle,validate_completion,run_identity,
)
from daqr.campaigns.medium_spec import digest


def exact_equal(a,b):
    if isinstance(a,torch.Tensor):
        assert torch.equal(a,b)
    elif isinstance(a,np.ndarray):
        np.testing.assert_array_equal(a,b)
    elif isinstance(a,dict):
        assert a.keys()==b.keys()
        for k in a: exact_equal(a[k],b[k])
    elif isinstance(a,(list,tuple)):
        assert len(a)==len(b)
        for x,y in zip(a,b): exact_equal(x,y)
    else:
        assert a==b


@pytest.mark.parametrize("policy",FULL_MODEL_ROSTER)
@pytest.mark.parametrize("threat",["NoAttack","RandomAttack"])
def test_real_policy_logging_exact_equivalence(policy,threat,tmp_path):
    manifest,cat,mask=prepare_manifest(policy,threat,frames=8)
    contexts=[np.array(r["actions"]) for r in cat["observations"]["routes"]]
    rewards=cat["physics"]["base_expected_payoffs"]
    seed=manifest["identity"]["seeds"]["policy"]["actual_seed"]
    off,off_state=run_policy(policy,contexts,rewards,mask,seed,capture_state=True)
    bundle=AttemptBundle(tmp_path,manifest,cat,mask)
    on,on_state=run_policy(policy,contexts,rewards,mask,seed,bundle.recorder,capture_state=True)
    completion=bundle.finish()
    exact_equal(off,on)
    exact_equal(off_state,on_state)  # optimizer, replay, covariance, tensors, gradients, RNGs
    assert completion["state"]=="COMPLETE"
    assert completion["scientific_evidence"] is False
    validate_completion(bundle.directory,manifest)
    rows=[json.loads(line) for line in (bundle.directory/"events.jsonl").read_text().splitlines()]
    assert len(rows)==32
    for frame in range(8):
        pre,decision,outcome,update=rows[frame*4:(frame+1)*4]
        assert [r["phase"] for r in (pre,decision,outcome,update)]==["PRESELECTION","DECISION","OUTCOME","UPDATE"]
        assert "availability" not in pre and "base_expected_payoff" not in pre
        route,action=on["path_action_list"][frame]
        assert decision["selected_allocation"]==contexts[route][action].tolist()
        assert outcome["selected_continuous_payoff"]==rewards[route][action]*mask[frame,route]
        if policy=="EXPNeuralUCB":
            assert decision["route_probability_vector"]==on["prob_list"][frame].tolist()
            assert decision["joint_action_propensity"] is None
            assert update["allocation_update_applied"]==bool(mask[frame,route])
            assert update["allocation_update_target"]==(rewards[route][action] if mask[frame,route] else None)
            assert outcome["sampled_bernoulli_draw"] in (0,1)
            assert update["importance_weighted_route_update"] is not None
        elif policy in {"GNeuralUCB","CPursuitNeuralUCB"}:
            assert decision["route_probability_vector"] is None
            assert outcome["sampled_bernoulli_draw"] in (0,1)
            assert update["direct_route_update"]==outcome["masked_route_feedback"]
        elif policy=="iCPursuitNeuralUCB":
            assert decision["route_probability_vector"] is None
            assert outcome["sampled_bernoulli_draw"] is None
            assert outcome["masked_route_feedback"] is None
            assert update["direct_route_update"]==outcome["selected_continuous_payoff"]
        else:
            assert outcome["sampled_bernoulli_draw"] is None
            assert decision["route_probability_vector"] is None
            assert update["policy_update_target"]==outcome["selected_continuous_payoff"]


class CapturingSink:
    """Test-only passive sink for a two-action optimizer-activation fixture."""
    def __init__(self): self.events=[]
    def preselection(self,*args): self.events.append(("pre",deepcopy(args)))
    def decision(self,*args): self.events.append(("decision",deepcopy(args)))
    def outcome(self,*args): self.events.append(("outcome",deepcopy(args)))
    def update(self,*args,**kwargs): self.events.append(("update",deepcopy((args,kwargs))))


def test_logging_equivalence_exercises_real_optimizer_and_masked_feedback():
    contexts=[np.array([[1,0],[0,1]])]
    # Synthetic unit fixture, not primary physics or a scientific treatment.
    rewards=[[1.0,1.0]]
    mask=np.array([[1],[1],[0],[1],[1],[1]],dtype=np.int8)
    sink=CapturingSink()
    off,off_state=run_policy("EXPNeuralUCB",contexts,rewards,mask,123,capture_state=True)
    on,on_state=run_policy("EXPNeuralUCB",contexts,rewards,mask,123,sink,capture_state=True)
    exact_equal(off,on)
    exact_equal(off_state,on_state)
    assert off_state["neural"][0]["T"]==5
    assert off_state["neural"][0]["optimizer"]["state"]  # real optimizer stepped
    outcomes=[row[1] for row in sink.events if row[0]=="outcome"]
    assert [int(x[4]) for x in outcomes]==[1]*6
    assert [int(x[5]) for x in outcomes]==[1,1,0,1,1,1]


@pytest.mark.parametrize("policy",FULL_MODEL_ROSTER[1:])
def test_current_mask_not_read_by_learner_selectors(policy):
    contexts=[np.array([[1,0],[0,1]]) for _ in range(10)]
    rewards=[[0.1,0.2] for _ in range(10)]
    # Single decision before either mask can become historical feedback.
    one,_=run_policy(policy,contexts,rewards,np.ones((1,10)),321)
    zero,_=run_policy(policy,contexts,rewards,np.zeros((1,10)),321)
    exact_equal(one["path_action_list"],zero["path_action_list"])
    if "prob_list" in one: exact_equal(one["prob_list"],zero["prob_list"])


def test_logger_calls_no_rng_or_selector_and_copies_values():
    manifest,cat,mask=prepare_manifest("EXPNeuralUCB","NoAttack",frames=1)
    recorder=EventRecorder(manifest,cat)
    contexts=[np.array(r["actions"]) for r in cat["observations"]["routes"]]
    probs=np.ones(10)/10
    with patch("numpy.random.choice",side_effect=AssertionError("logger RNG")), patch("torch.rand",side_effect=AssertionError("logger RNG")):
        recorder.preselection(0,contexts)
        recorder.decision(0,0,0,probs)
        recorder.outcome(0,0.0,1,0.0,0,0)
        recorder.update(0,0.0,True,group_target=0)
    probs[0]=9
    assert recorder.events[1]["route_probability_vector"][0]==0.1
    assert recorder.events[2]["positive_route_feedback"] is False


def complete_zero_fixture(tmp_path):
    manifest,cat,mask=prepare_manifest("EXPNeuralUCB","NoAttack",frames=1)
    bundle=AttemptBundle(tmp_path,manifest,cat,mask)
    recorder=bundle.recorder
    recorder.preselection(0,[r["actions"] for r in cat["observations"]["routes"]])
    recorder.decision(0,0,0,np.ones(10)/10)
    recorder.outcome(0,0.0,1,0.0,0,0)
    recorder.update(0,0.0,True,group_target=0)
    return manifest,cat,mask,bundle,bundle.finish()


def test_valid_zero_feedback_and_payoff_retained_no_retry(tmp_path):
    manifest,cat,mask,bundle,completion=complete_zero_fixture(tmp_path)
    assert completion["positive_route_feedback_count"]==0
    assert validate_completion(bundle.directory,manifest)["state"]=="COMPLETE"
    with pytest.raises(ValueError): AttemptBundle(tmp_path,manifest,cat,mask)
    with pytest.raises(ValueError): AttemptBundle(tmp_path,manifest,cat,mask,restart_reason="poor performance")


def test_one_documented_infrastructure_restart_only(tmp_path):
    manifest,cat,mask=prepare_manifest("Oracle","NoAttack",frames=1)
    first=AttemptBundle(tmp_path,manifest,cat,mask)
    first.finish("FAILED","infrastructure","test fixture: storage interruption")
    second=AttemptBundle(tmp_path,manifest,cat,mask,restart_reason="test fixture: storage restored")
    assert second.attempt_no==2 and second.lineage["previous_completion_hash"]
    second.finish("FAILED","infrastructure","test fixture: repeated interruption")
    with pytest.raises(FileExistsError): AttemptBundle(tmp_path,manifest,cat,mask,restart_reason="third prohibited")
    assert (first.directory/"completion.json").exists()


def test_faults_and_incomplete_attempts_cannot_resume(tmp_path):
    manifest,cat,mask=prepare_manifest("Oracle","NoAttack",frames=1)
    first=AttemptBundle(tmp_path,manifest,cat,mask)
    with pytest.raises(ValueError): first.finish()
    with pytest.raises(ValueError): AttemptBundle(tmp_path,manifest,cat,mask,restart_reason="missing completion")
    first.finish("FAILED","technical_fault","test fixture: invariant violation")
    with pytest.raises(ValueError): AttemptBundle(tmp_path,manifest,cat,mask,restart_reason="not infrastructure")
    with pytest.raises(ValueError): validate_completion(first.directory,manifest)


@pytest.mark.parametrize("field",["seeds","policy","threat","allocator","replay","horizon","code","topology_hash","route_set_hash","config_hash"])
def test_any_identity_change_rejects_reuse(tmp_path,field):
    manifest,cat,mask,bundle,_=complete_zero_fixture(tmp_path)
    altered=deepcopy(manifest)
    altered["identity"][field]="different"
    altered["run_id"]=run_identity(altered["identity"])
    with pytest.raises(ValueError): validate_completion(bundle.directory,altered)


@pytest.mark.parametrize("filename",["events.jsonl","observations.json","availability.json","physics.json","routes.json"])
def test_tampering_detected(tmp_path,filename):
    manifest,cat,mask,bundle,_=complete_zero_fixture(tmp_path)
    path=bundle.directory/filename
    path.write_text(path.read_text()+" ")
    with pytest.raises(ValueError): validate_completion(bundle.directory,manifest)


def test_out_of_order_or_dynamic_context_rejected():
    manifest,cat,mask=prepare_manifest("Oracle","NoAttack",frames=1)
    recorder=EventRecorder(manifest,cat)
    with pytest.raises(ValueError): recorder.decision(0,0,0)
    contexts=deepcopy([r["actions"] for r in cat["observations"]["routes"]])
    contexts[0][0][0]=100
    with pytest.raises(ValueError): recorder.preselection(0,contexts)


def test_bounded_entry_point_refuses_scientific_horizon(tmp_path):
    with pytest.raises(ValueError,match="frame limit"):
        execute_preflight(tmp_path,frames=6000)
    assert not list(tmp_path.iterdir())
    assert FRAME_LIMIT < 6000


def test_manifest_content_must_match_identity(tmp_path):
    manifest,cat,mask=prepare_manifest("Oracle","NoAttack",frames=1)
    manifest["configuration"]["protocol"]["base_horizon"]=5
    with pytest.raises(ValueError,match="Configuration hash"):
        AttemptBundle(tmp_path,manifest,cat,mask)


def test_logging_does_not_repeat_selectors_or_gradients(monkeypatch):
    from daqr.algorithms.neural_bandits import EXPNeuralUCB
    from daqr.algorithms.base_bandit import NeuralUCB
    counts={"group":0,"action":0,"gradient":0}
    def wrap(cls,name,key):
        original=getattr(cls,name)
        def counted(self,*args,**kwargs):
            counts[key]+=1
            return original(self,*args,**kwargs)
        monkeypatch.setattr(cls,name,counted)
    wrap(EXPNeuralUCB,"select_group","group")
    wrap(EXPNeuralUCB,"select_action","action")
    wrap(NeuralUCB,"grad","gradient")
    contexts=[np.array([[1,0],[0,1]])]
    rewards=[[0.1,0.2]]
    mask=np.ones((3,1),dtype=np.int8)
    run_policy("EXPNeuralUCB",contexts,rewards,mask,7)
    off=counts.copy()
    counts.update({k:0 for k in counts})
    run_policy("EXPNeuralUCB",contexts,rewards,mask,7,CapturingSink())
    assert counts==off
    assert counts["group"]==counts["action"]==3


@pytest.mark.parametrize("policy",FULL_MODEL_ROSTER)
def test_tiny_end_to_end_real_policy_bundle(policy,tmp_path):
    directory,completion=execute_preflight(tmp_path,policy=policy,frames=4)
    assert completion["state"]=="COMPLETE"
    assert completion["scientific_evidence"] is False
    summary=json.loads((directory/"technical_summary.json").read_text())
    assert summary["frames_exercised"]==4
    assert len(summary["selected_pairs"])==4
