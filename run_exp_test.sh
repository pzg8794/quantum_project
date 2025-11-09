#!/bin/bash
set +e

MODE=$1
TARGET_BRANCH=$2
ALLOCATOR=$3

./dynamic_exp_runner.sh 100 1 100 12345 "$MODE" 0.25 "$ALLOCATOR"
./3_push_results.sh "$TARGET_BRANCH"
echo "Test DONE"
#!/bin/bash
set +e

MODE=$1
TARGET_BRANCH=$2
ALLOCATOR=$3

./dynamic_exp_runner.sh 100 1 100 12345 "$MODE" 0.25 "$ALLOCATOR" 
./3_push_results.sh "$TARGET_BRANCH"
echo "Test DONE"