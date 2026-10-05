"""Catalog and replay checks for the three-run T/Tb spectrum notebooks."""

from daqr.campaigns.medium_tier1 import MODEL_ROSTER, SCENARIOS
from daqr.campaigns.spectrum_three import (
    BASE_FRAMES,
    FRAME_STEP,
    PHYSICS_MODEL,
    build_block_payload,
    fixed_allocation,
)
from daqr.config.execution_contract import resolve_configuration


def test_medium_high_catalogs_keep_topology_and_allocator_axes_separate():
    for scale_m, nodes, routes in ((2, 11, 7), (3, 15, 10)):
        for block in range(3):
            payload = build_block_payload(
                scale_m=scale_m,
                replay="Tb",
                capacity_scale=1,
                physics_model=PHYSICS_MODEL,
                current_frames=BASE_FRAMES + FRAME_STEP * block,
                base_seed=12345,
                qubit_cap=fixed_allocation(scale_m),
                block_id=block,
            )
            assert payload["external_topology"].number_of_nodes() == nodes
            assert len(payload["external_contexts"]) == routes
            assert len(payload["external_rewards"]) == routes
            assert sum(map(len, payload["external_contexts"])) == 55 * routes
            assert all(context.shape[1] == 3 for context in payload["external_contexts"])
            assert all(len(a) == len(q) for a, q in zip(
                payload["external_contexts"], payload["external_rewards"]
            ))
            config = payload["_execution_evidence_configuration"]
            assert config.allocator.num_routes == routes
            assert config.allocator.total_qubits == 9 * routes
            assert config.execution.horizon == BASE_FRAMES + FRAME_STEP * block
            assert len(config.models) == len(MODEL_ROSTER)
            assert len(config.test_scenarios) == len(SCENARIOS)


def test_t_and_tb_capacity_semantics_across_all_notebook_scales():
    for scale_m in (2, 3):
        for replay in ("T", "Tb"):
            for capacity_scale in (1, 1.5, 2):
                for block in range(3):
                    frames = BASE_FRAMES + FRAME_STEP * block
                    payload = build_block_payload(
                        scale_m=scale_m,
                        replay=replay,
                        capacity_scale=capacity_scale,
                        physics_model=PHYSICS_MODEL,
                        current_frames=frames,
                        base_seed=12345,
                        qubit_cap=fixed_allocation(scale_m),
                        block_id=block,
                    )
                    resolved = resolve_configuration(
                        payload["_execution_evidence_configuration"]
                    )
                    assert resolved["replay"]["capacity"] == int(
                        (frames if replay == "T" else BASE_FRAMES) * capacity_scale
                    )
                    assert len(resolved["required_cells"]) == (
                        3 * len(MODEL_ROSTER) * len(SCENARIOS)
                    )
