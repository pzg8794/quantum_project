#!/bin/bash

################################################################################
# SCRIPT 3: PUSH RESULTS - Simple and Robust Version
# Avoids complex git reset operations that can lose data
################################################################################

gcloud compute instances add-metadata "$(hostname)" \
  --zone="$(curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/zone | awk -F/ '{print $4}')" \
  --metadata=status=pushing --quiet

set +e

REPO_DIR="${REPO_DIR:-$HOME/quantum_project}"
LOG_DIR="${LOG_DIR:-$HOME/quantum_logs}"
LOG_FILE="$LOG_DIR/push_$(date +%s).log"

mkdir -p "$LOG_DIR"

log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }
success() { echo "SUCCESS: $1" | tee -a "$LOG_FILE"; }
error() { echo "ERROR: $1" | tee -a "$LOG_FILE"; exit 1; }
warn() { echo "WARN: $1" | tee -a "$LOG_FILE"; }

# =============================================================================
# Branch Selection
# =============================================================================
TARGET_BRANCH="gcp-main"
if [ -n "$1" ]; then
    TARGET_BRANCH="$1"
fi
log "Target branch: $TARGET_BRANCH"

# =============================================================================
# Verify Repo
# =============================================================================

log "================================"
log "Verifying Repository"
log "================================"

if [ ! -d "$REPO_DIR" ]; then
    error "Repository not found at $REPO_DIR"
fi

cd "$REPO_DIR" || error "Failed to access $REPO_DIR"
success "Repository found"

# =============================================================================
# Create and Stage Results (BEFORE any pull operations)
# =============================================================================

log "================================"
log "Preparing Results"
log "================================"

# Create a unique run marker
RUN_ID=$(date +%Y%m%d_%H%M%S)
RUN_MARKER="Dynamic_Routing_Eval_Framework/results/run_marker_${RUN_ID}.txt"
echo "Run completed at ${RUN_ID}" > "$RUN_MARKER"
log "Created unique run marker: $RUN_MARKER"

# Stage experiment outputs
git add Dynamic_Routing_Eval_Framework/logs/ 2>/dev/null || true
git add Dynamic_Routing_Eval_Framework/results/ 2>/dev/null || true
git add Dynamic_Routing_Eval_Framework/experiment_results/ 2>/dev/null || true

STAGED_COUNT=$(git diff --cached --name-only | wc -l)
log "Staged $STAGED_COUNT file(s) for commit"

if [ $STAGED_COUNT -eq 0 ]; then
    warn "No changes to commit. Exiting."
    exit 0
fi

# Create the commit with staged files
COMMIT_MSG="Experiment results from $(hostname) - $(date +'%Y-%m-%d %H:%M:%S')"
git commit -m "$COMMIT_MSG" >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    error "Failed to create commit"
fi
success "Results committed locally"

# =============================================================================
# Simple Pull-and-Push with Retry
# =============================================================================

log "================================"
log "Pushing to GitHub"
log "================================"

MAX_RETRIES=5
for attempt in $(seq 1 $MAX_RETRIES); do
    log "--- Attempt $attempt/$MAX_RETRIES ---"
    
    # Try to push first (optimistic approach)
    git push origin "$TARGET_BRANCH" >> "$LOG_FILE" 2>&1
    if [ $? -eq 0 ]; then
        success "Results pushed to GitHub!"
        log "Results path: Dynamic_Routing_Eval_Framework/results on branch ${TARGET_BRANCH}"
        break
    fi
    
    warn "Push failed on attempt $attempt. Another VM likely pushed first."
    
    if [ $attempt -eq $MAX_RETRIES ]; then
        error "Push failed after $MAX_RETRIES attempts"
    fi
    
    # The key insight: pull with automatic merge commit
    log "Pulling latest changes with merge strategy..."
    git pull origin "$TARGET_BRANCH" --no-rebase >> "$LOG_FILE" 2>&1
    if [ $? -ne 0 ]; then
        warn "Pull failed. Trying with merge strategy..."
        git pull origin "$TARGET_BRANCH" --strategy=ours >> "$LOG_FILE" 2>&1
        if [ $? -ne 0 ]; then
            error "Cannot sync with remote repository"
        fi
    fi
    
    # Add exponential backoff
    SLEEP_TIME=$((2 * attempt))
    log "Waiting ${SLEEP_TIME} seconds before retry..."
    sleep $SLEEP_TIME
done

# =============================================================================
# Summary
# =============================================================================

log "================================"
log "PUSH COMPLETE"
log "================================"

success "All results pushed!"

gcloud compute instances add-metadata "$(hostname)" \
  --zone="$(curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/zone | awk -F/ '{print $4}')" \
  --metadata=status=done --quiet