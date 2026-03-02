#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."  # Dynamic_Routing_Eval_Framework/

echo "============================================================"
echo "DAQR Small Tests (no full runs)"
echo "============================================================"

python3 tools/tests/test_task1_no_run_scripts.py
python3 tools/tests/test_task2_allocator_runner_aggregation_hook.py
python3 tools/tests/test_state_dir_aggregation.py
python3 tools/tests/test_task2b_duplicate_filename_policy_static.py
python3 tools/tests/test_task2c_aggregation_eliminates_cross_day_duplicates.py
python3 tools/tests/test_paper8_testbed_build.py
python3 tools/tests/test_paper8_environment_rewards.py

echo "============================================================"
echo "PASS: all small tests"
echo "============================================================"
