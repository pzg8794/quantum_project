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
            "--image=quantum-exp-base-img",
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
            
        # Use $HOME for reliability instead of ~.
        # The shell on the remote VM will expand $HOME to the correct user's home directory.
        log_dir = f'$HOME/quantum_project/Dynamic_Routing_Eval_Framework/logs'
        log_file = f'{log_dir}/{vm_name}_$(date +"%Y%m%d_%H%M%S").log'

        # Build the command string with robust error handling
        command_str = f"""
            set -e
            
            # 1. Announce what we are doing for easier debugging.
            echo "--- Remote script started. Preparing log directory: {log_dir}"
            
            # 2. Create the log directory. Exit if this fails.
            mkdir -p "{log_dir}"
            
            # 3. Start tee to capture all subsequent output to the log file.
            # The ( ... ) creates a subshell.
            (
                cd "$HOME/quantum_project"
                
                echo '--- Remote log started at $(date) ---'
                
                git checkout --quiet {"gcp-main" if gcp else "main"}
                
                git pull --quiet
                
                chmod +x ./*.sh
                
                ./{script_with_args}
            ) | tee -a "{log_file}"
        """
        
        # Pass the command to SSH
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
                        if percent not in (50, 75, 100):
                            continue

                print(f"[{vm_name}] {line_stripped}")
            proc.wait()

            if proc.returncode == 0:
                print(f"--- SUCCESS: Experiment on {vm_name} finished. ---")
            else:
                print(f"--- ERROR: Experiment on {vm_name} failed. ---")

        except Exception as e:
            print(f"--- FATAL ERROR running experiment on {vm_name}: {e} ---")


    def _get_instance_status(self, vm_name: str, max_retries: int = 3) -> str:
        """
        Return VM metadata 'status' value. Retries on empty or failed attempts.
        Returns the status string (e.g., 'RUNNING') or 'ERROR' if it fails after retries.
        """
        
        for attempt in range(max_retries):
            try:
                r = subprocess.run(
                    [
                        "gcloud", "compute", "instances", "describe", vm_name,
                        f"--zone={self.zone}",
                        "--format=get(status)"
                    ],
                    check=False,
                    capture_output=True,
                    text=True
                )

                # Case 1: The command failed
                if r.returncode != 0:
                    print(f"Attempt {attempt + 1}/{max_retries}: Error fetching status for {vm_name}. Stderr: {r.stderr.strip()}")
                    time.sleep(3) # Wait longer after an error
                    continue # Go to the next attempt

                # Case 2: The command succeeded, but returned an empty string
                retrieved_status = r.stdout.strip()
                if not retrieved_status:
                    print(f"Attempt {attempt + 1}/{max_retries}: Status for {vm_name} is empty. Retrying...")
                    time.sleep(3)
                    continue # Go to the next attempt
                
                # Case 3: Success! We got a status.
                print(f"Successfully retrieved status for {vm_name}: '{retrieved_status}'")
                return retrieved_status

            except Exception as e:
                print(f"[CRITICAL ERROR] Exception in _get_instance_status for '{vm_name}': {e}")
                return "ERROR" # Return immediately on a critical code failure
                
        print(f"Failed to get status for {vm_name} after {max_retries} attempts.")
        return "ERROR"

    def wait_for_vms_and_cleanup(manager, max_wait_minutes=15):
        """
        Waits for all VMs to report 'done' and then cleans them up.
        """
        print("\n--- Waiting for all VMs to finish experiments ---")
        
        start_time = time.time()
        vms_to_wait_for = list(manager.vms_to_cleanup) # Get the initial list of VMs

        while vms_to_wait_for:
            # Check for timeout
            elapsed_seconds = time.time() - start_time
            if elapsed_seconds > max_wait_minutes * 60:
                print(f"--- ERROR: Timeout reached after {max_wait_minutes} minutes. ---")
                # Force cleanup of any remaining VMs regardless of status
                manager.cleanup_vms(require_done=False) 
                return

            # Check the status of each remaining VM
            finished_vms = []
            for vm_name in vms_to_wait_for:
                # This is your existing function to get status
                status = manager._get_instance_status(vm_name) 
                
                if status.lower() == 'done':
                    print(f"✔️ VM '{vm_name}' has finished.")
                    finished_vms.append(vm_name)
                else:
                    print(f"⏳ VM '{vm_name}' is still working (status: {status})...")
            
            # Remove finished VMs from the waiting list
            if finished_vms:
                vms_to_wait_for = [vm for vm in vms_to_wait_for if vm not in finished_vms]

            # If there are still VMs running, wait before polling again
            if vms_to_wait_for:
                print(f"--- {len(vms_to_wait_for)} VMs remaining. Waiting 30 seconds before next check. ---")
                time.sleep(30)

        print("\n--- All VMs have finished. Proceeding with cleanup. ---")
        # Now that we've confirmed all VMs are done, this will work every time.
        manager.cleanup_vms(require_done=True)
        
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
            # runner.cleanup_vms(require_done=True)
            self.wait_for_vms_and_cleanup(runner)

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
            # runner.cleanup_vms(require_done=True)
            cls.wait_for_vms_and_cleanup(runner)

        print("\n===== ✓ ALL ALLOCATORS COMPLETE =====")


    def cleanup_all_instances(self, require_done: bool = True):
        """
        Deletes all *running* experiment/test VMs across zones.
        Skips base/template/image instances automatically.
        """
        print("\n🧹 Scanning for active experiment instances (status=RUNNING)...")

        protected = ("base", "template", "image", "main")
        try:
            # list only running instances across all zones
            list_cmd = [
                "gcloud", "compute", "instances", "list",
                "--project=bright-zodiac-476705-d6",
                "--filter=status=RUNNING",
                "--format=value(name,zone)"
            ]
            r = subprocess.run(list_cmd, check=True, capture_output=True, text=True)
            lines = [l.strip() for l in r.stdout.splitlines() if l.strip()]

            if not lines:
                print("✅ No running instances found.")
                return

            to_delete = []
            for line in lines:
                name, zone = line.split()
                lname = name.lower()

                if any(p in lname for p in protected):
                    print(f"🛑 Skipping protected instance: {name}")
                    continue

                if self.vms_to_cleanup and name not in self.vms_to_cleanup: continue
                status = self._get_instance_status(name)
                if name != "quantum-exp" and (not require_done or status.lower() == "done"):
                    print(f"DELETING: {name} (metadata status={status})")
                    to_delete.append((name, zone))
                else:
                    print(f"⏳ KEEPING: {name} (metadata status={status})")

            if not to_delete:
                print("No experiment VMs marked for deletion.")
                return

            print("\n🚀 Deleting selected instances...")
            for name, zone in to_delete:
                del_cmd = ["gcloud", "compute", "instances", "delete", name, f"--zone={zone}", "--quiet"]
                try:
                    subprocess.run(del_cmd, check=True, capture_output=True, text=True)
                    print(f"Deleted {name}")
                except subprocess.CalledProcessError as e:
                    print(f"⚠️  Failed to delete {name}: {e.stderr.strip()}")

            print("\n✨ Cleanup complete.")
        except Exception as e:
            print(f"[ERROR] Cleanup failed: {e}")



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
        if "test" in mode:
            rounds = [("exp-test", f"run_exp_test.sh  {mode}")]
        else:
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
                # runner.cleanup_vms(require_done=True)
                cls.wait_for_vms_and_cleanup(runner)
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

    # Display help
    if not args and not ("--cleanup" in sys.argv or "--cleanup-all" in sys.argv):
        print("""
            Usage:
            python gcp_experiment_runner.py <allocator|--all> [--test|--quick-test] [--exclude none,random]
            python gcp_experiment_runner.py --cleanup        # deletes VMs with status=done
            python gcp_experiment_runner.py --cleanup-all    # deletes all experiment VMs
            """)
        sys.exit(1)

    # Handle cleanup directly
    if "--cleanup" in sys.argv or "--cleanup-all" in sys.argv:
        require_done = "--cleanup" in sys.argv
        runner = GCPExperimentRunner("none", mode="quick-test")
        runner.cleanup_all_instances(require_done=require_done)
        sys.exit(0)

    # Normal experiment runs
    command = args[0]
    if "--sequential" in sys.argv:
        GCPExperimentRunner.run_all_allocators_sequential(mode=mode, exclude=exclude)
    elif command == "--all":
        GCPExperimentRunner.run_all_allocators(mode=mode, exclude=exclude)
    else:
        runner = GCPExperimentRunner(command, mode=mode)
        runner.run()