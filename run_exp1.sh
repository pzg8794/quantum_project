#!/bin/bash
set +e

ALLOCATOR=$1

./dynamic_exp_runner.sh 4000 3 2000 12345 "Exp1" 0.25 "$ALLOCATOR"
./3_push_results.sh
gcloud compute instances add-metadata $(hostname) --zone=us-central1-a --metadata=status=complete
echo "Exp1 DONE"