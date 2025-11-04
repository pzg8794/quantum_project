#!/usr/bin/env python3
"""GCP Experiment Runner - Final version with quick-test mode and dynamic command generation."""
from concurrent.futures import ThreadPoolExecutor
import re
import sys
import time
import subprocess
import threading
from dataclasses import dataclass
from typing import List


@dataclass
class ExperimentConfig:
    name: str
    script_with_args: str


class GCPExperimentRunner:
    """Manages creation, execution, and cleanup of GCP experiments."""
    ALLOCATORS = ["none", "thompson", "dynamic", "random"]

    ZONE_MAP = {
        "none": "us-central1-a",
        "thompson": "us-central1-f", 
        "dynamic": "us-west1-b",
        "random": "us-east1-b"
    }

    def __init__(self, allocator: str, zone: str = "us-central1-a",
                machine_type: str = "n2-standard-8", disk_size: str = "50GB",
                mode: str = "production"):

        self.allocator = allocator.lower()
        self.zone = self.ZONE_MAP.get(self.allocator, zone)
        self.mode = mode.lower()
        self.disk_size = disk_size
        self.machine_type = machine_type
        self.test_mode = self.mode != "production"
        self.vms_to_cleanup = []
        self.to_delete = []
        self.branch_name = "gcp-main"

        allocator_arg = "None" if self.allocator == "none" else self.allocator.lower()

        if self.test_mode:
            self.experiments = [
                ExperimentConfig(f"test1-{self.allocator}", f"run_exp_test.sh {self.mode} {allocator_arg}")
            ]
        else:
            self.experiments = [
                ExperimentConfig(f"exp1-{self.allocator}", f"run_exp1.sh {allocator_arg}"),
                ExperimentConfig(f"exp2-{self.allocator}", f"run_exp2.sh {allocator_arg}"),
                ExperimentConfig(f"exp3-{self.allocator}", f"run_exp3.sh {allocator_arg}"),
                ExperimentConfig(f"exp4-{self.allocator}", f"run_exp4.sh {allocator_arg}")
            ]

        print(f"⚡ PERFORMANCE MODE: {self.machine_type}")

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

    def _run_gcloud_cmd(self, cmd: List[str], suppress_errors=False) -> bool:
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return True
        except subprocess.CalledProcessError as e:
            if not suppress_errors:
                error_msg = e.stderr.lower()
                if "quota" in error_msg:
                    print(f"💡 Quota exceeded - trying next tier...")
                else:
                    print(f"ERROR: Command failed: {' '.join(cmd)}\n{e.stderr}")
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

    def _generate_test_branch_name(self, mode: str, allocator: str) -> str:
        """Generate a unique test branch name with timestamp."""
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"test/{mode}-{allocator}-{timestamp}"

    def _create_and_switch_test_branch(self, vm_name: str, test_branch: str) -> str:
        """Create test branch and return the command to switch to it."""
        return f"""
            echo "🔧 Creating test branch: {test_branch} for {vm_name}"
            git checkout {self.branch_name}
            git checkout -b {test_branch} 2>/dev/null || git checkout {test_branch}
            git push -u origin {test_branch} 2>/dev/null || echo "Branch already exists on remote"
        """

    def run_and_stream_experiment(self, vm_name: str, script_with_args: str, gcp: bool = True):
        """Runs the experiment on a remote VM and streams logs live."""
        shown_progress = set()
        print(f"--- Starting Experiment on {vm_name} ---")
        
        try:
            subprocess.run([
                "gcloud", "compute", "instances", "add-metadata", vm_name,
                f"--zone={self.zone}", "--metadata=status=starting", "--quiet"
            ], check=False, text=True)
        except Exception as e:
            print(f"[{vm_name}] WARN: failed to set metadata to 'starting': {e}")
            
        log_dir = f'$HOME/quantum_project/Dynamic_Routing_Eval_Framework/logs'
        log_file = f'{log_dir}/{vm_name}_$(date +"%Y%m%d_%H%M%S").log'

        # 🎯 INTELLIGENT BRANCH LOGIC
        if self.test_mode:
            test_branch = self._generate_test_branch_name(self.mode, self.allocator)
            branch_setup = self._create_and_switch_test_branch(vm_name, test_branch)
            self.branch_name = test_branch
            print(f"🧪 Test mode: Creating branch '{test_branch}' for {vm_name}")
            script_with_args = f"{script_with_args} {self.branch_name}"
            print(f"🔧 Test script command: {script_with_args}")
        else:
            branch_setup = ""
            self.branch_name = "gcp-main" if gcp else "main"

        command_str = f"""
            set -e
            echo "--- Remote script started. Preparing log directory: {log_dir}"
            mkdir -p "{log_dir}"
            
            (
                cd "$HOME/quantum_project"
                echo '--- Remote log started at $(date) ---'
                echo "🔄 Switching to branch: {self.branch_name}"
                
                {branch_setup}
                git checkout --quiet {self.branch_name}
                git pull --quiet origin {self.branch_name} 2>/dev/null || echo "First push to new branch"
                
                chmod +x ./*.sh
                echo "🚀 Executing: {script_with_args}"
                ./{script_with_args}
                
            ) | tee -a "{log_file}"
        """
        
        ssh_cmd = [
            "gcloud", "compute", "ssh", vm_name,
            f"--zone={self.zone}",
            "--command", command_str
        ]

        try:
            proc = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                line_stripped = line.strip()

                if "Progress" in line_stripped:
                    match = re.search(r"(\d+)%\|", line_stripped)
                    if match:
                        percent = int(match.group(1))
                        if percent in shown_progress:
                            continue
                        shown_progress.add(percent)
                        if percent not in (50, 75, 100):
                            continue
                            
                if "Test DONE" in line_stripped:
                    self.to_delete.append(vm_name)

                print(f"[{vm_name}] {line_stripped}")
            proc.wait()

            if proc.returncode == 0:
                print(f"--- SUCCESS: Experiment on {vm_name} finished. ---")
            else:
                print(f"--- ERROR: Experiment on {vm_name} failed. ---")

        except Exception as e:
            print(f"--- FATAL ERROR running experiment on {vm_name}: {e} ---")
        finally:
            self.cleanup_vm()

    def cleanup_vm(self):
        if not self.to_delete:
            return

        to_delete = list(self.to_delete)
        for vm in self.to_delete:
            print(f"DELETING: {vm} (metadata status=DONE)")
        
        if to_delete:
            print("\nCleaning up VMs (status=done):", ", ".join(to_delete))
            cmd = ["gcloud", "compute", "instances", "delete"] + to_delete + [f"--zone={self.zone}", "--quiet"]
            self._run_gcloud_cmd(cmd)

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

    @classmethod
    def run_all_allocators_pipelined(cls, mode, exclude: list[str] = None, max_workers: int = 8):
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import json
        import os
        from datetime import datetime
        
        exclude = [e.lower() for e in (exclude or [])]
        all_allocators = [a for a in cls.ALLOCATORS if a not in exclude]

        print(f"\n🚀 ===== PIPELINED EXECUTION [{mode.upper()}] =====")
        print(f"📋 Included: {', '.join(all_allocators)}")
        print(f"⚡ Max Workers: {max_workers}")

        if "test" in mode:
            rounds = [("exp-test", f"run_exp_test.sh {mode}")]
        else:
            rounds = [("exp2", "run_exp2.sh"), ("exp3", "run_exp3.sh"), ("exp4", "run_exp4.sh")]

        experiment_queue = []
        for round_name, script in rounds:
            for allocator in all_allocators:
                experiment_queue.append((round_name, script, allocator))

        print(f"\n📊 Pipeline Stats:")
        print(f"• Total experiments: {len(experiment_queue)}")
        print(f"• Estimated duration: ~{len(experiment_queue) / max_workers:.1f}x experiment slots")
        print(f"• Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        def run_single_experiment(round_name, script, allocator):
            allocator_arg = "None" if allocator == "none" else allocator.capitalize()
            runner = cls(allocator, mode=mode)
            exp_name = f"{round_name}-{allocator}"
            script_with_args = f"{script} {allocator_arg}"
            
            start_time = datetime.now()

            try:
                print(f"🔄 [{datetime.now().strftime('%H:%M:%S')}] Starting {exp_name}")
                
                if not runner.create_vm(exp_name):
                    return {"name": exp_name, "success": False, "error": "VM creation failed", "start_time": start_time, "end_time": datetime.now()}
                
                if not runner.wait_for_ssh(exp_name):
                    return {"name": exp_name, "success": False, "error": "SSH connection failed", "start_time": start_time, "end_time": datetime.now()}
                
                runner.run_and_stream_experiment(exp_name, script_with_args)
                
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                return {
                    "name": exp_name, "success": True, "error": None,
                    "start_time": start_time, "end_time": end_time,
                    "duration_seconds": duration
                }
                
            except Exception as e:
                return {"name": exp_name, "success": False, "error": str(e), "start_time": start_time, "end_time": datetime.now()}

        results = []
        successful = 0
        failed = 0
        
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(run_single_experiment, round_name, script, allocator)
                    for round_name, script, allocator in experiment_queue
                ]
                
                print("📈 Live Pipeline Progress:")
                print("⏱️ Status | Experiment | Duration")
                print("─────────────────────────────────────────────")
                
                for i, future in enumerate(as_completed(futures), 1):
                    result = future.result()
                    results.append(result)
                    
                    if result["success"]:
                        successful += 1
                        status_icon = "✅"
                        duration = f"{result.get('duration_seconds', 0):.1f}s"
                    else:
                        failed += 1
                        status_icon = "❌"
                        duration = "failed"
                    
                    print(f"{status_icon} [{i:2d}/{len(experiment_queue):2d}] {result['name']:<15} | {duration:<8} | Success: {successful}, Failed: {failed}")
                    
        except KeyboardInterrupt:
            print(f"\n🛑 Pipeline interrupted by user")

        print(f"\n🎯 ===== PIPELINE COMPLETE =====")
        print(f"📊 Final Stats:")
        print(f"• Total experiments: {len(results)}")
        print(f"• ✅ Successful: {successful}")
        print(f"• ❌ Failed: {failed}")
        print(f"• 📈 Success rate: {successful/max(len(results), 1)*100:.1f}%")
        print(f"• 🚀 Max efficiency achieved: {max_workers} concurrent VMs")
        
        os.makedirs("results", exist_ok=True)
        json_path = f"results/pipeline_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        summary = {"timestamp": datetime.now().isoformat(), "mode": mode, "successful": successful, "failed": failed, "results": results}
        
        try:
            with open(json_path, "w") as f:
                json.dump(summary, f, indent=2, default=str)
            print(f"💾 Execution summary saved to {json_path}")
        except Exception as e:
            print(f"⚠️ Could not save summary: {e}")

    def cleanup_all_instances(self, require_done: bool = True):
        print("\n🧹 Scanning for active experiment instances...")
        protected = ("base", "template", "image", "main")
        
        try:
            list_cmd = ["gcloud", "compute", "instances", "list", "--project=bright-zodiac-476705-d6", "--filter=status=RUNNING", "--format=value(name,zone)"]
            r = subprocess.run(list_cmd, check=True, capture_output=True, text=True)
            lines = [l.strip() for l in r.stdout.splitlines() if l.strip()]

            if not lines:
                print("✅ No running instances found.")
                return

            to_delete = []
            for line in lines:
                name, zone = line.split()
                if not any(p in name.lower() for p in protected) and name != "quantum-exp":
                    to_delete.append((name, zone))

            if to_delete:
                print(f"\n🚀 Deleting {len(to_delete)} instances...")
                for name, zone in to_delete:
                    del_cmd = ["gcloud", "compute", "instances", "delete", name, f"--zone={zone}", "--quiet"]
                    try:
                        subprocess.run(del_cmd, check=True, capture_output=True, text=True)
                        print(f"Deleted {name}")
                    except subprocess.CalledProcessError as e:
                        print(f"⚠️ Failed to delete {name}: {e.stderr.strip()}")

            print("\n✨ Cleanup complete.")
        except Exception as e:
            print(f"[ERROR] Cleanup failed: {e}")


if __name__ == "__main__":
    mode = "production"
    max_workers = 8
    
    if "--quick-test" in sys.argv:
        mode = "quick-test"
        max_workers = 4
    elif "--test" in sys.argv:
        mode = "test"
        max_workers = 4

    exclude = []
    if "--exclude" in sys.argv:
        idx = sys.argv.index("--exclude")
        if idx + 1 < len(sys.argv):
            exclude = [x.strip().lower() for x in sys.argv[idx + 1].split(",")]

    args = [arg for arg in sys.argv[1:] if arg not in ["--test", "--quick-test", "--exclude", "--pipeline", "--cleanup", "--cleanup-all"] and not arg.startswith(",")]

    if "--cleanup" in sys.argv or "--cleanup-all" in sys.argv:
        runner = GCPExperimentRunner("none", mode="quick-test")
        runner.cleanup_all_instances()
        sys.exit(0)

    if not args and "--pipeline" not in sys.argv:
        print("""
Usage:
python gcp_experiment_runner.py <allocator> [--test|--quick-test]
python gcp_experiment_runner.py --pipeline [--test|--quick-test] [--exclude none,random]
python gcp_experiment_runner.py --cleanup
        """)
        sys.exit(1)

    if "--pipeline" in sys.argv:
        GCPExperimentRunner.run_all_allocators_pipelined(mode=mode, exclude=exclude, max_workers=max_workers)
    else:
        runner = GCPExperimentRunner(args[0], mode=mode)
        runner.run()