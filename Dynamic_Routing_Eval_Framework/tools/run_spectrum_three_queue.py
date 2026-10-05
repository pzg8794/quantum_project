"""One-attempt queue for the twelve independent three-block spectrum cells.

Concurrency is across complete notebook cells only. Each cell preserves the
framework's internal model and scenario scheduling.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save(path: Path, value: dict) -> None:
    temp = path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temp, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--framework-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--max-concurrent", type=int, default=2)
    parser.add_argument("--poll-seconds", type=int, default=30)
    args = parser.parse_args()
    if not 1 <= args.max_concurrent <= 12:
        raise ValueError("Invalid concurrency")
    source = args.framework_root.resolve()
    root = args.output_root.resolve()
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"Queue root must be new and empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    executor = source / "tools" / "execute_spectrum_three_notebook.py"
    if not executor.is_file():
        raise FileNotFoundError(executor)
    cells = []
    for m in (2, 3):
        for replay in ("T", "Tb"):
            notebook = source / "notebooks" / "spectrum-three" / f"Layered-m{m}-{replay}-3runs.ipynb"
            digest = hashlib.sha256(notebook.read_bytes()).hexdigest()
            for capacity in ("1", "1.5", "2"):
                name = f"m{m}-{replay}-s{capacity.replace('.', '_')}-3"
                cells.append({"id": name, "m": m, "replay": replay,
                              "capacity_scale": capacity, "notebook": str(notebook),
                              "notebook_sha256": digest, "status": "QUEUED",
                              "output_root": str(root / name), "attempt": 1})
    state = {"created_at": now(), "source_root": str(source),
             "execution_kind": "three-block-scientific-notebook",
             "max_concurrent": args.max_concurrent, "cells": cells}
    state_path = root / "QUEUE-STATUS.json"
    save(state_path, state)
    active: dict[str, tuple[subprocess.Popen, object]] = {}
    env = dict(os.environ)
    env["PYTHONPATH"] = str(source) + os.pathsep + env.get("PYTHONPATH", "")
    while any(cell["status"] in {"QUEUED", "RUNNING"} for cell in cells):
        for cell in cells:
            if cell["status"] != "QUEUED" or len(active) >= args.max_concurrent:
                continue
            log = root / f"{cell['id']}.log"
            handle = log.open("x")
            command = ["nice", "-n", "10", sys.executable, "-B", str(executor),
                       "--notebook", cell["notebook"],
                       "--expected-sha256", cell["notebook_sha256"],
                       "--capacity-scale", cell["capacity_scale"],
                       "--output-root", str(root / cell["id"])]
            process = subprocess.Popen(command, env=env, stdout=handle,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            cell.update(status="RUNNING", pid=process.pid, started_at=now(),
                        log=str(log), command=command)
            active[cell["id"]] = (process, handle)
            save(state_path, state)
            print(f"START {cell['id']} pid={process.pid}", flush=True)
        time.sleep(args.poll_seconds)
        for cell in cells:
            if cell["id"] not in active:
                continue
            process, handle = active[cell["id"]]
            code = process.poll()
            if code is None:
                continue
            handle.close()
            active.pop(cell["id"])
            receipt = root / cell["id"] / "q04-evidence" / "campaign-receipt.json"
            cell.update(status="EXECUTION_COMPLETE_UNVALIDATED" if code == 0 and receipt.is_file() else "FAILED",
                        returncode=code, finished_at=now(),
                        receipt=str(receipt) if receipt.is_file() else None)
            save(state_path, state)
            print(f"END {cell['id']} status={cell['status']} code={code}", flush=True)
    state["queue_finished_at"] = now()
    save(state_path, state)


if __name__ == "__main__":
    main()
