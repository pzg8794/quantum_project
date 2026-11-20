"""Explicit technical cost fixture, manually invoked; NOT scientific evidence.

The fixture selects its own config. No campaign module owns these values.
Run from framework root: python -B tests/runtime_primary_k55.py
"""
import json
import resource
import time
import numpy as np
from medium_fixtures import fixture_config
from daqr.campaigns.medium_runner import prepare_manifest, run_policy


def main():
    cfg=fixture_config(frames=256,scale_m=1)
    cfg.models=["EXPNeuralUCB"]
    cfg.test_scenarios={"NoAttack":{"strategy":"none","parameters":{}}}
    cfg.runs=1
    manifest,cat,mask=prepare_manifest(cfg,"EXPNeuralUCB","NoAttack",0,scale_m=1)
    contexts=[np.array(r["actions"]) for r in cat["observations"]["routes"]]
    assert all(len(x)==55 for x in contexts)
    start=time.perf_counter()
    _,state=run_policy(cfg,"EXPNeuralUCB",contexts,cat["physics"]["base_expected_payoffs"],
                       mask,manifest["identity"]["seeds"]["policy"]["actual_seed"],capture_state=True)
    elapsed=time.perf_counter()-start
    neural=[{"K":len(contexts[i]),"T":n["T"],"replay_size":n["replay"]["size"],
             "replay_capacity":n["replay"]["capacity"],
             "optimizer_parameter_states":len(n["optimizer"]["state"]),
             "optimizer_steps":sorted(set(float(s["step"]) for s in n["optimizer"]["state"].values()))}
            for i,n in enumerate(state["neural"])]
    assert any(n["T"]>n["K"] and n["optimizer_parameter_states"]>0 for n in neural)
    print(json.dumps({"label":"TECHNICAL COST BENCHMARK — NOT SCIENTIFIC EVIDENCE",
                      "config_hash":manifest["identity"]["config_hash"],
                      "resolved_configuration":manifest["configuration"],
                      "frames":len(mask),"route_states":neural,"wall_seconds":elapsed,
                      "peak_rss_platform_units":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                      "code_runtime":manifest["identity"]["code"]},sort_keys=True))


if __name__=="__main__":
    main()
