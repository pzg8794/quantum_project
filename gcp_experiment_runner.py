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

    def __init__(self, allocator: str, zone: str = "us-central1-a",
                 machine_type: str = "n1-standard-4", disk_size: str = "50GB",
                 mode: str = "production"):
        self.allocator = allocator.lower()
        self.zone = zone
        self.mode = mode.lower()
        self.disk_size = disk_size
        self.machine_type = machine_type
        self.test_mode = self.mode != "production"
        self.vms_to_cleanup = []


        allocator_arg = "None" if self.allocator == "none" else self.allocator.capitalize()
        
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
            f"--zone={self.zone}", f"--machine-type={self.machine_type}",
            f"--boot-disk-size={self.disk_size}",
            "--scopes=cloud-platform",
            "--image-family=ubuntu-2204-lts",
            "--image-project=ubuntu-os-cloud", "--quiet"
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

    def run_and_stream_experiment(self, vm_name: str, script_with_args: str):
        print(f"--- Starting Experiment on {vm_name} ---")
        command_str = (
            "cd /tmp && "
            "rm -rf quantum_repo && "
            f"git clone --quiet {GIT_CLONE_URL} quantum_repo && "
            "cd quantum_repo && "
            "chmod +x ./*.sh && "
            f"./{script_with_args}"
        )
        ssh_cmd = ["gcloud", "compute", "ssh", vm_name, f"--zone={self.zone}", "--command", command_str]
        try:
            proc = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                print(f"[{vm_name}] {line.strip()}")
            proc.wait()
            if proc.returncode == 0:
                print(f"--- SUCCESS: Experiment on {vm_name} finished. ---")
            else:
                print(f"--- ERROR: Experiment on {vm_name} failed. ---")
        except Exception as e:
            print(f"--- FATAL ERROR running experiment on {vm_name}: {e} ---")

    def cleanup_vms(self):
        if not self.vms_to_cleanup: return
        print("\nCleaning up VMs...")
        cmd = ["gcloud", "compute", "instances", "delete"] + self.vms_to_cleanup + [f"--zone={self.zone}", "--quiet"]
        self._run_gcloud_cmd(cmd)
        print("Cleanup complete.")

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
    def run_all_allocators(cls, mode):
        print(f"\n===== RUNNING ALL ALLOCATORS [{mode.upper().replace('-', ' ')}] =====")
        
        # For any test mode (--test or --quick-test), only run 'none' allocator to save time
        allocators_to_run = cls.ALLOCATORS if mode.lower() == 'production' else ['none']
        for allocator in allocators_to_run:
            runner = cls(allocator, mode=mode)
            runner.run()
        print("\n===== ✓ ALL ALLOCATORS COMPLETE =====")

if __name__ == "__main__":
    mode = "production"
    if "--quick-test" in sys.argv: mode = "quick-test" 
    elif "--test" in sys.argv: mode = "test" 
    
    args = [arg for arg in sys.argv[1:] if arg not in ["--test", "--quick-test"]]

    if not args:
        print("\nUsage:\n  python gcp_experiment_runner.py <allocator|--all> [--test] [--quick-test]\n")
        sys.exit(1)
    
    command = args[0]
    if command == "--all":
        GCPExperimentRunner.run_all_allocators(mode=mode)
    else:
        runner = GCPExperimentRunner(command, mode=mode)
        runner.run()