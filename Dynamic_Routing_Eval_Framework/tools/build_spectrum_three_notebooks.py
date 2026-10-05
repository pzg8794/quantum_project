#!/usr/bin/env python3
"""Build four small notebook entry points for the configured spectrum campaign."""

from copy import deepcopy
from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "notebooks" / "H-MABs_Eval-MediumScale-Default-FullThreat.ipynb"
OUTPUT = ROOT / "notebooks" / "spectrum-three"
SOURCE_SHA = {
    "T": "c010ade072175aea28ddef30f362104db88b78592260005471848cd754ba9330",
    "Tb": "726f985e8e591de5dc8ad53a194aca0519a99321c699852b152a97a8f586ef7a",
}


def source(text):
    return text.splitlines(keepends=True)


def make_notebook(scale_m, replay):
    title = "MEDIUM (11 nodes, 7 routes)" if scale_m == 2 else "HIGH (15 nodes, 10 routes)"
    notebook = deepcopy(json.loads(TEMPLATE.read_text()))
    notebook["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
    }
    notebook["metadata"]["spectrum_provenance"] = {
        "source_notebook": f"H-MABs_Eval-{replay}_FQubit_Alloc_3QRuns.ipynb",
        "source_sha256": SOURCE_SHA[replay],
        "topology_scale_m": scale_m,
        "route_count": 3 * scale_m + 1,
        "execution": "full configured model/scenario roster; three notebook blocks per capacity multiplier",
    }
    notebook["cells"] = [
        {"cell_type": "markdown", "metadata": {}, "source": source(
            f"# {title}: {replay} three-run spectrum notebook\n\n"
            "This entry point preserves the original T/Tb three-run clock (4,000 / 6,000 / 8,000 frames) "
            "and its full configured model and scenario roster. Topology is supplied by the "
            "layered primary catalog; allocator strategy is held fixed for this comparison.\n"
        )},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": source(
            "import json, os\n"
            "from pathlib import Path\n"
            "from daqr.campaigns.spectrum_three import (\n"
            "    BASE_FRAMES, FRAME_STEP, PHYSICS_MODEL, build_block_payload,\n"
            "    fixed_allocation, run_cell,\n"
            ")\n"
            f"TOPOLOGY_SCALE_M = {scale_m}\n"
            f"REPLAY = {replay!r}\n"
            "CAPACITY_SCALES = (1, 1.5, 2)\n"
            "RUNS = 3\n"
            "OUTPUT_ROOT = Path(os.environ['SPECTRUM_OUTPUT_ROOT']).expanduser().resolve()\n"
            "selection = os.environ.get('SPECTRUM_CAPACITY_SCALE')\n"
            "selected_scales = tuple(s for s in CAPACITY_SCALES if selection is None or str(s) == selection)\n"
            "if not selected_scales:\n"
            "    raise ValueError('Requested capacity scale is absent from the notebook contract')\n"
            "print({'topology_scale_m': TOPOLOGY_SCALE_M, 'routes': 3*TOPOLOGY_SCALE_M+1,\n"
            "       'replay': REPLAY, 'capacity_scales': selected_scales, 'blocks': RUNS})\n"
        )},
        {"cell_type": "markdown", "metadata": {}, "source": source(
            "## Catalog and capacity preflight\n\n"
            "Each block must have the configured route count and aligned contexts/rewards. "
            "T capacity follows the block horizon; Tb capacity stays anchored to the base horizon.\n"
        )},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": source(
            "for capacity_scale in selected_scales:\n"
            "    for block_id in range(RUNS):\n"
            "        frames = BASE_FRAMES + FRAME_STEP * block_id\n"
            "        payload = build_block_payload(\n"
            "            scale_m=TOPOLOGY_SCALE_M, replay=REPLAY, capacity_scale=capacity_scale,\n"
            "            physics_model=PHYSICS_MODEL, current_frames=frames, base_seed=12345,\n"
            "            qubit_cap=fixed_allocation(TOPOLOGY_SCALE_M), block_id=block_id,\n"
            "        )\n"
            "        assert len(payload['external_contexts']) == 3*TOPOLOGY_SCALE_M+1\n"
            "        assert len(payload['external_rewards']) == len(payload['external_contexts'])\n"
            "print('Catalog preflight passed')\n"
        )},
        {"cell_type": "markdown", "metadata": {}, "source": source(
            "## Execute complete experiments\n\n"
            "Every selected capacity scale gets its own immutable output root and includes the "
            "full model and scenario roster across three blocks. This notebook records routing "
            "and allocation evidence; service equity requires an eligible demand ledger.\n"
        )},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": source(
            "receipts = {}\n"
            "for capacity_scale in selected_scales:\n"
            "    scale_label = str(capacity_scale).replace('.', '_')\n"
            "    cell_root = OUTPUT_ROOT / f'm{TOPOLOGY_SCALE_M}-{REPLAY}-s{scale_label}-3'\n"
            "    receipts[str(capacity_scale)] = str(run_cell(\n"
            "        cell_root, scale_m=TOPOLOGY_SCALE_M, replay=REPLAY,\n"
            "        capacity_scale=capacity_scale,\n"
            "    ))\n"
            "print(json.dumps(receipts, indent=2))\n"
        )},
    ]
    for index, cell in enumerate(notebook["cells"]):
        cell["id"] = f"spectrum-{scale_m}-{replay.lower()}-{index}"
    return notebook


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for scale_m in (2, 3):
        for replay in ("T", "Tb"):
            path = OUTPUT / f"Layered-m{scale_m}-{replay}-3runs.ipynb"
            path.write_text(json.dumps(make_notebook(scale_m, replay), indent=1) + "\n")
            print(path)


if __name__ == "__main__":
    main()
