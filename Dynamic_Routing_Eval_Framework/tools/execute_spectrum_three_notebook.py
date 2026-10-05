"""Execute one immutable, capacity-selected spectrum notebook in a fresh process.

This intentionally uses the notebook's own code cells and the existing Python
environment, avoiding a dependency change to a running research VM.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--notebook", required=True, type=Path)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--capacity-scale", required=True, choices=("1", "1.5", "2"))
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()

    notebook = args.notebook.resolve()
    digest = hashlib.sha256(notebook.read_bytes()).hexdigest()
    if digest != args.expected_sha256:
        raise ValueError(f"Notebook hash mismatch: {digest}")
    root = args.output_root.resolve()
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"Output root is not empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    os.environ["SPECTRUM_OUTPUT_ROOT"] = str(root)
    os.environ["SPECTRUM_CAPACITY_SCALE"] = args.capacity_scale
    cells = json.loads(notebook.read_text())["cells"]
    namespace: dict[str, object] = {"__name__": "__main__"}
    for index, cell in enumerate(cells):
        if cell["cell_type"] != "code":
            continue
        print(f"NOTEBOOK CELL {index} START", flush=True)
        source = "".join(cell["source"])
        exec(compile(source, f"{notebook}:cell:{index}", "exec"), namespace)
        print(f"NOTEBOOK CELL {index} COMPLETE", flush=True)
    print(f"NOTEBOOK COMPLETE {notebook} {args.capacity_scale} {root}", flush=True)


if __name__ == "__main__":
    main()
