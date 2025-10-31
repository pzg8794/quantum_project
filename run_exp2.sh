#!/bin/bash
set +e
./1_startup.sh
./dynamic_exp_runner.sh 10000 2 2000 12345 "Exp2"
./3_push_results.sh
echo "Exp2 DONE"