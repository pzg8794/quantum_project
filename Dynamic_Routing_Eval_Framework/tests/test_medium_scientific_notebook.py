from dataclasses import replace
import json
from pathlib import Path

import pytest

from daqr.campaigns.medium_scientific import (
    TIER1_MODELS,
    TIER1_SCENARIOS,
    build_tier1_default_config,
    run_scientific_matrix,
)
from daqr.campaigns.medium_trace import validate_scale_completion
from daqr.config.execution_contract import resolve_configuration


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "H-MABs_Eval-MediumScale-Default-FullThreat.ipynb"


def bounded_config():
    config = build_tier1_default_config(horizon=2, blocks=1)
    config.models = ["Oracle"]
    config.test_scenarios = {
        "stochastic": TIER1_SCENARIOS["stochastic"],
        "none": TIER1_SCENARIOS["none"],
    }
    config.execution = replace(config.execution, protocol_namespace="q04-bounded-equivalence-v1")
    return config


def stable_bundle_files(directory):
    directory = Path(directory)
    names = {
        "manifest.json",
        "topology.json",
        "routes.json",
        "observations.json",
        "physics.json",
        "availability.json",
        "catalog_diagnostics.json",
        "events.jsonl",
        "scientific_summary.json",
    }
    return {name: (directory / name).read_bytes() for name in names}


def test_notebook_is_copied_full_spectrum_evidence_package():
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    provenance = notebook["metadata"]["quantum_medium_provenance"]
    assert provenance["source_commit"] == "96b327de7e3571ad3cbf05bbeee02cfb922ca2c3"
    assert provenance["source_blob"] == "599bb49b58a41fc98ff7d6f10c4077c941507269"
    assert provenance["source_sha256"] == "714eefbd1eafc3c66347fc6b0460e6aaf706ad25b1ea411bcc89ac317a4711c9"
    assert provenance["required_threats"] == list(TIER1_SCENARIOS)
    assert provenance["required_cells"] == 45
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])
    assert "ExperimentConfiguration" in source
    assert "AllocatorRunner" in source
    assert "QUANTUM_MEDIUM_OUTPUT_ROOT" in source
    assert "DynamicUCB and ThompsonSampling remain on hold" in source
    assert all(cell.get("execution_count") is None and not cell.get("outputs")
               for cell in notebook["cells"] if cell["cell_type"] == "code")


def test_frozen_configuration_derives_45_cells_and_15_node_anchor():
    config = build_tier1_default_config()
    resolved = resolve_configuration(config)
    assert tuple(resolved["policies"]) == TIER1_MODELS
    assert tuple(resolved["scenarios"]) == tuple(TIER1_SCENARIOS)
    assert len(resolved["required_cells"]) == 45
    assert resolved["replay"] == {"anchor": "T_b", "scale": 2, "base": 6000, "capacity": 12000}
    from daqr.campaigns.medium_spec import build_catalog
    catalog = build_catalog(config, 0, 3)
    assert len(catalog["topology"]["nodes"]) == 15
    assert len(catalog["routes"]) == 10
    assert catalog["diagnostics"]["total_actions"] == 550


def test_scientific_output_root_must_be_external():
    with pytest.raises(ValueError, match="outside"):
        run_scientific_matrix(ROOT, bounded_config(), max_workers=1)


def test_bounded_serial_process_equivalence_completion_and_reuse(tmp_path):
    config = bounded_config()
    serial = run_scientific_matrix(tmp_path / "serial", config, max_workers=1)
    parallel = run_scientific_matrix(tmp_path / "parallel", config, max_workers=2)
    assert serial["required_cells"] == parallel["required_cells"] == 2
    assert serial["run_ids"] == parallel["run_ids"]
    for left, right in zip(serial["bundle_directories"], parallel["bundle_directories"]):
        assert stable_bundle_files(left) == stable_bundle_files(right)
    assert validate_scale_completion(config, 3, serial["bundle_directories"])["complete"]
    reused = run_scientific_matrix(tmp_path / "serial", config, max_workers=1)
    assert reused["run_ids"] == serial["run_ids"]
    assert reused["reused_cells"] == 2
    assert not list((tmp_path / "serial").glob("*/attempt-2"))
