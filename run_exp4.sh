#!/bin/bash
set +e
./1_startup.sh
./dynamic_exp_runner.sh 20000 3 2000 12345 "Exp4" 0.25 "$ALLOCATOR"
./3_push_results.sh
gcloud compute instances add-metadata $(hostname) --zone=us-central1-a --metadata=status=complete
echo "Exp4 DONE"