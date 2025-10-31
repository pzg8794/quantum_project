#!/bin/bash
set +e
./1_startup.sh
./dynamic_exp_runner.sh 14000 3 2000 12345 "Exp3"
./3_push_results.sh
echo "Exp3 DONE"