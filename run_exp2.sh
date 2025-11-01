#!/bin/bash
set +e

ALLOCATOR=$1

./dynamic_exp_runner.sh 10000 2 2000 12345 "Exp2" 0.25 "$ALLOCATOR"
./3_push_results.sh
gcloud compute instances add-metadata $(hostname) --zone=us-central1-a --metadata=status=complete
echo "Exp2 DONE"