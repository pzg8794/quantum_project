#!/bin/bash
set +e
./1_startup.sh
./dynamic_exp_runner.sh 100 1 100 12345 "Test" 0.25 None
./3_push_results.sh
gcloud compute instances add-metadata $(hostname) --zone=us-central1-a --metadata=status=complete
echo "Test DONE"