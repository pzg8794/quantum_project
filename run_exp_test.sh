#!/bin/bash
set +e
./1_startup.sh
./dynamic_exp_runner.sh 1000 1 1000 12345 "Test"
./3_push_results.sh
echo "Test DONE"