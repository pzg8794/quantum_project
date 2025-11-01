#!/bin/bash
set +e

MODE=$1
ALLOCATOR=$2

./dynamic_exp_runner.sh 100 1 100 12345 "$MODE" 0.25 "$ALLOCATOR"
./3_push_results.sh
gcloud compute instances add-metadata $(hostname) --zone=us-central1-a --metadata=status=complete
echo "Test DONE"