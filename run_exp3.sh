#!/bin/bash
set +e

ALLOCATOR=$1

./1_startup.sh
./dynamic_exp_runner.sh 14000 3 2000 12345 "Exp3" 0.25 "$ALLOCATOR"
./3_push_results.sh
gcloud compute instances add-metadata $(hostname) --zone=us-central1-a --metadata=status=complete
echo "Exp3 DONE"