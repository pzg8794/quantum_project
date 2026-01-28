#!/bin/bash
set +e

ALLOCATOR=$1

./dynamic_exp_runner.sh 20000 3 2000 12345 "Exp4" 0.25 "$ALLOCATOR"
./3_push_results.sh
echo "Exp4 DONE"