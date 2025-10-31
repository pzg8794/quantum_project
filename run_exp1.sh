#!/bin/bash
set +e
./1_startup.sh
./dynamic_exp_runner.sh 4000 3 2000 12345 "Exp1"
./3_push_results.sh
echo "Exp1 DONE"