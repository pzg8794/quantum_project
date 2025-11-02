#!/usr/bin/env python3
"""GCP Experiment Runner - Final version with quick-test mode and dynamic command generation."""

import sys
import time
import subprocess
import threading
from dataclasses import dataclass
from typing import List

# Your working git clone command with the Personal Access Token (PAT)
GIT_CLONE_URL = "https://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@github.com/pzg8794/quantum_project.git"

@dataclass
class ExperimentConfig:
    name: str
    script_with_args: str

class GCPExperimentRunner:
    """Manages the creation, execution, and cleanup of GCP experiments."""
    ALLOCATORS = ["none", "thompson", "dynamic", "random"]

    # Zone mapping per allocator
    ZONE_MAP = {
        "none": "us-central1-a",
        "thompson": "us-central1-b",
        "dynamic": "us-east1-b",
        "random": "us-west1-b"
    }

    def __init__(self, allocator: str, zone: str = "us-central1-a",
                 machine_type: str = "n1-standard-4", disk_size: str = "50GB",
                 mode: str = "production"):
        self.allocator = allocator.lower()
        self.zone = self.ZONE_MAP.get(self.allocator, zone)
        self.mode = mode.lower()
        self.disk_size = disk_size
        self.machine_type = machine_type
        self.test_mode = self.mode != "production"
        self.vms_to_cleanup = []


        allocator_arg = "None" if self.allocator == "none" else self.allocator.lower()
        
        if self.test_mode:
            self.experiments = [
                ExperimentConfig(f"test1-{self.allocator}", f"run_exp_test.sh {self.mode} {allocator_arg}")
            ]
        else: # Production mode
            self.experiments = [
                ExperimentConfig(f"exp1-{self.allocator}", f"run_exp1.sh {allocator_arg}"),
                ExperimentConfig(f"exp2-{self.allocator}", f"run_exp2.sh {allocator_arg}"),
                ExperimentConfig(f"exp3-{self.allocator}", f"run_exp3.sh {allocator_arg}"),
                ExperimentConfig(f"exp4-{self.allocator}", f"run_exp4.sh {allocator_arg}"),
            ]


    def _run_gcloud_cmd(self, cmd: List[str], suppress_errors=False) -> bool:
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return True
        except subprocess.CalledProcessError as e:
            if not suppress_errors:
                print(f"ERROR: Command failed: {' '.join(cmd)}\n{e.stderr}")
            return False

    def create_vm(self, vm_name: str) -> bool:
        print(f"Creating VM: {vm_name}...")
        cmd = [
            "gcloud", "compute", "instances", "create", vm_name,
            f"--zone={self.zone}",
            f"--machine-type={self.machine_type}",
            f"--boot-disk-size={self.disk_size}",
            "--scopes=cloud-platform",
            "--image=quantum-exp-base",
            "--image-project=bright-zodiac-476705-d6",
            "--quiet",
        ]
        if self._run_gcloud_cmd(cmd):
            self.vms_to_cleanup.append(vm_name)
            return True
        return False

    def wait_for_ssh(self, vm_name: str, timeout: int = 180) -> bool:
        print(f"Waiting for SSH on {vm_name}...", end="", flush=True)
        start_time = time.time()
        while time.time() - start_time < timeout:
            cmd = ["gcloud", "compute", "ssh", vm_name, f"--zone={self.zone}", "--command=echo ready"]
            if self._run_gcloud_cmd(cmd, suppress_errors=True):
                print(" Ready.")
                return True
            time.sleep(5)
            print(".", end="", flush=True)
        print(" Timeout.")
        return False


    def run_and_stream_experiment(self, vm_name: str, script_with_args: str, gcp: bool = True):
        """
        Runs the experiment on a remote VM and streams logs live.
        If gcp=True (default), assumes the 'quantum_project' repo already exists on the image.
        Falls back to cloning if not present.
        """
        shown_progress = set()  # add this near the top of the function before reading lines
        print(f"--- Starting Experiment on {vm_name} ---")
            # 1) Mark VM as starting (LOCAL call, not inside the SSH command)
        try:
            subprocess.run(
                [
                    "gcloud", "compute", "instances", "add-metadata", vm_name,
                    f"--zone={self.zone}", "--metadata=status=starting", "--quiet"
                ],
                check=False, text=True
            )
        except Exception as e:
            print(f"[{vm_name}] WARN: failed to set metadata to 'starting': {e}")

        # New logic: reuse repo if already there
        command_str = (
            'mkdir -p ~/quantum_project/Dynamic_Routing_Eval_Framework/logs && '
            f'exec > >(tee -a ~/quantum_project/Dynamic_Routing_Eval_Framework/logs/{vm_name}_$(date +"%Y%m%d_%H%M%S").log) 2>&1 && '
            'cd ~/quantum_project && '
        )

        # Conditionally checkout GCP branch
        if gcp: command_str += "git checkout --quiet gcp-main && "
        else: command_str += "git checkout --quiet main && "

        # Skip branch checkout — the image already has gcp-main
        command_str += (
            "git pull --quiet | true && "
            "chmod +x ./*.sh && "
            f"./{script_with_args}"
        )

        ssh_cmd = [
            "gcloud", "compute", "ssh", vm_name,
            f"--zone={self.zone}",
            "--command", command_str
        ]

        try:
            proc = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                line_stripped = line.strip()

                # Collapse tqdm spam: show each progress percentage only once
                if "Progress" in line_stripped:
                    import re
                    match = re.search(r"(\d+)%\|", line_stripped)
                    if match:
                        percent = int(match.group(1))
                        if percent in shown_progress:
                            continue  # already shown
                        shown_progress.add(percent)

                        # optionally limit to a few key milestones
                        if percent not in (0, 50, 100):
                            continue

                print(f"[{vm_name}] {line_stripped}")
            proc.wait()

            if proc.returncode == 0:
                print(f"--- SUCCESS: Experiment on {vm_name} finished. ---")
            else:
                print(f"--- ERROR: Experiment on {vm_name} failed. ---")

        except Exception as e:
            print(f"--- FATAL ERROR running experiment on {vm_name}: {e} ---")


    def _get_instance_status(self, vm_name: str) -> str:
        """Return metadata status string or '' if missing."""
        try:
            r = subprocess.run(
                [
                    "gcloud", "compute", "instances", "describe", vm_name,
                    f"--zone={self.zone}",
                    "--format=value(metadata.items[?key=status].value)"
                ],
                check=True, capture_output=True, text=True
            )
            return r.stdout.strip()
        except subprocess.CalledProcessError:
            return ""

    def cleanup_vms(self, require_done: bool = True):
        if not self.vms_to_cleanup:
            return

        to_delete, to_keep = [], []
        if require_done:
            for vm in self.vms_to_cleanup:
                status = self._get_instance_status(vm)
                if status.lower() == "done":
                    to_delete.append(vm)
                else:
                    to_keep.append((vm, status if status else "unknown"))
        else:
            to_delete = list(self.vms_to_cleanup)

        if to_delete:
            print("\nCleaning up VMs (status=done):", ", ".join(to_delete))
            cmd = ["gcloud", "compute", "instances", "delete"] + to_delete + [f"--zone={self.zone}", "--quiet"]
            self._run_gcloud_cmd(cmd)
            # remove deleted ones from tracking
            self.vms_to_cleanup = [vm for vm in self.vms_to_cleanup if vm not in to_delete]

        if require_done and to_keep:
            for vm, st in to_keep:
                print(f"Keeping VM '{vm}' (status={st})")

        if not to_delete and not to_keep:
            print("Cleanup: no VMs to process.")

    def run(self):
        print(f"\n[{self.mode.replace('-', ' ').title()}] Starting experiments for allocator: {self.allocator}\n")
        try:
            if not all(self.create_vm(exp.name) for exp in self.experiments):
                raise RuntimeError("VM creation failed.")
            if not all(self.wait_for_ssh(exp.name) for exp in self.experiments):
                raise RuntimeError("VM SSH readiness failed.")
            threads = [threading.Thread(target=self.run_and_stream_experiment, args=(exp.name, exp.script_with_args)) for exp in self.experiments]
            for thread in threads: thread.start()
            for thread in threads: thread.join()
            print(f"\n✓ ALL EXPERIMENTS for allocator '{self.allocator}' are complete.")
        except Exception as e:
            print(f"\nAn error occurred during the run: {e}")
        finally:
            self.cleanup_vms()

    @classmethod
    def run_all_allocators(cls, mode, exclude: list[str] = None):
        """
        Runs experiments for all allocators except those in `exclude`.
        Each allocator runs 4 experiments (run_exp1.sh–run_exp4.sh).
        """
        exclude = [e.lower() for e in (exclude or [])]
        all_allocators = [a for a in cls.ALLOCATORS if a not in exclude]

        print(f"\n===== RUNNING ALLOCATORS [{mode.upper()}] =====")
        print(f"Included: {', '.join(all_allocators)}")
        if exclude:
            print(f"Excluded: {', '.join(exclude)}")

        all_runners = []

        for allocator in all_allocators:
            runner = cls(allocator, mode=mode)

            allocator_arg = "None" if allocator == "none" else allocator.capitalize()
            # restore 4-experiment structure with allocator-tagged names
            if runner.test_mode:
                runner.experiments = [
                    ExperimentConfig(f"test1-{allocator}", f"run_exp_test.sh {mode} {allocator_arg}")
                ]
            else:
                runner.experiments = [
                    ExperimentConfig(f"exp1-{allocator}", f"run_exp1.sh {allocator_arg}"),
                    ExperimentConfig(f"exp2-{allocator}", f"run_exp2.sh {allocator_arg}"),
                    ExperimentConfig(f"exp3-{allocator}", f"run_exp3.sh {allocator_arg}"),
                    ExperimentConfig(f"exp4-{allocator}", f"run_exp4.sh {allocator_arg}"),
                ]
            all_runners.append(runner)

        # create all vms for all allocators
        for runner in all_runners:
            for exp in runner.experiments:
                runner.create_vm(exp.name)

        # wait for ssh readiness
        for runner in all_runners:
            for exp in runner.experiments:
                runner.wait_for_ssh(exp.name)

        # run all experiments concurrently
        threads = []
        for runner in all_runners:
            for exp in runner.experiments:
                t = threading.Thread(
                    target=runner.run_and_stream_experiment,
                    args=(exp.name, exp.script_with_args)
                )
                threads.append(t)
                t.start()

        for t in threads:
            t.join()

        # cleanup all vms at the end
        for runner in all_runners:
            runner.cleanup_vms()

        print("\n===== ✓ ALL ALLOCATORS COMPLETE =====")

    @classmethod
    def run_all_allocators_sequential(cls, mode, exclude: list[str] = None):
        """
        Runs experiments for all allocators sequentially — one experiment per allocator at a time.
        Each allocator still runs exp1–exp4, but only one round (expN) runs concurrently across allocators.
        """
        exclude = [e.lower() for e in (exclude or [])]
        all_allocators = [a for a in cls.ALLOCATORS if a not in exclude]

        print(f"\n===== RUNNING ALLOCATORS SEQUENTIALLY [{mode.upper()}] =====")
        print(f"Included: {', '.join(all_allocators)}")
        if exclude:
            print(f"Excluded: {', '.join(exclude)}")

        # Define the four rounds (exp1 → exp4)
        rounds = [
            ("exp1", "run_exp1.sh"),
            ("exp2", "run_exp2.sh"),
            ("exp3", "run_exp3.sh"),
            ("exp4", "run_exp4.sh"),
        ]

        for round_name, script in rounds:
            print(f"\n--- Starting Round: {round_name} ---\n")
            runners = []
            threads = []

            # Create and launch one experiment per allocator for this round
            for allocator in all_allocators:
                allocator_arg = "None" if allocator == "none" else allocator.capitalize()
                runner = cls(allocator, mode=mode)
                exp_name = f"{round_name}-{allocator}"
                script_with_args = f"{script} {allocator_arg}"

                # Create VM
                runner.create_vm(exp_name)
                runner.wait_for_ssh(exp_name)

                # Launch thread for experiment
                t = threading.Thread(
                    target=runner.run_and_stream_experiment,
                    args=(exp_name, script_with_args)
                )
                threads.append(t)
                runners.append(runner)
                t.start()

            # Wait for all allocators in this round to finish
            for t in threads:
                t.join()

            # Cleanup all VMs from this round
            for runner in runners:
                runner.cleanup_vms()

            print(f"\n✓ ROUND {round_name.upper()} COMPLETE for all allocators.\n")

        print("\n===== ✓ ALL ROUNDS COMPLETE (Sequential Mode) =====")

if __name__ == "__main__":
    mode = "production"
    if "--quick-test" in sys.argv:
        mode = "quick-test"
    elif "--test" in sys.argv:
        mode = "test"

    # Parse exclude list (e.g., --exclude none,random)
    exclude = []
    if "--exclude" in sys.argv:
        idx = sys.argv.index("--exclude")
        if idx + 1 < len(sys.argv):
            exclude = [x.strip().lower() for x in sys.argv[idx + 1].split(",")]

    # Clean up args for allocator selection
    args = [arg for arg in sys.argv[1:] if arg not in ["--test", "--quick-test", "--exclude"] and not arg.startswith(",")]

    if not args:
        print("\nUsage:\n  python gcp_experiment_runner.py <allocator|--all> [--test|--quick-test] [--exclude none,random]\n")
        sys.exit(1)

    command = args[0]
    if "--sequential" in sys.argv:
        GCPExperimentRunner.run_all_allocators_sequential(mode=mode, exclude=exclude)
    elif command == "--all":
        GCPExperimentRunner.run_all_allocators(mode=mode, exclude=exclude)
    else:
        runner = GCPExperimentRunner(command, mode=mode)
        runner.run()