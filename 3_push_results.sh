#!/bin/bash

################################################################################
# SCRIPT 3: PUSH RESULTS - Pull, Commit, Push to GitHub
# Handles concurrent VM pushes safely
################################################################################

set +e

NOT_GCP=$1
TARGET_BRANCH=${NOT_GCP:-gcp-main}   # Default to gcp-main if none provided

REPO_DIR="/tmp/quantum_repo"
LOG_DIR="/tmp/quantum_logs"
LOG_FILE="$LOG_DIR/push_$(date +%s).log"

mkdir -p "$LOG_DIR"

log()    { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }
success(){ echo "SUCCESS: $1" | tee -a "$LOG_FILE"; }
error()  { echo "ERROR: $1" | tee -a "$LOG_FILE"; exit 1; }
warn()   { echo "WARN: $1" | tee -a "$LOG_FILE"; }

# =============================================================================
# Repo Verification
# =============================================================================

log "================================"
log "Verifying Repository"
log "================================"

if [ ! -d "$REPO_DIR" ]; then
    error "Repository not found at $REPO_DIR"
fi

cd "$REPO_DIR" || error "Failed to cd into $REPO_DIR"
success "Repository found"

# =============================================================================
# Pull Latest (Critical for Multi-VM Safety)
# =============================================================================

log "================================"
log "Pulling Latest from $TARGET_BRANCH"
log "================================"

git fetch origin "$TARGET_BRANCH" >> "$LOG_FILE" 2>&1
git checkout "$TARGET_BRANCH" >> "$LOG_FILE" 2>&1 || error "Failed to checkout $TARGET_BRANCH"

git pull origin "$TARGET_BRANCH" >> "$LOG_FILE" 2>&1
PULL_CODE=$?

if [ $PULL_CODE -ne 0 ]; then
    warn "Pull had issues (code $PULL_CODE), retrying with rebase..."
    git pull --rebase origin "$TARGET_BRANCH" >> "$LOG_FILE" 2>&1 || error "Pull/rebase failed"
fi

success "Synced with remote branch: $TARGET_BRANCH"

# =============================================================================
# Stage Results
# =============================================================================

log "================================"
log "Staging Results"
log "================================"

git add Dynamic_Routing_Eval_Framework/results/ 2>/dev/null || true
git add Dynamic_Routing_Eval_Framework/experiment_results/ 2>/dev/null || true

CHANGES=$(git diff --cached --name-only)
# if [ -z "$CHANGES" ]; then
#     warn "No changes to commit."
#     exit 0
# fi

log "Files staged:"
echo "$CHANGES" | tee -a "$LOG_FILE"

# =============================================================================
# Commit
# =============================================================================

log "================================"
log "Committing Results"
log "================================"

COMMIT_MSG="Experiment results - $(date +'%Y-%m-%d %H:%M:%S') [${TARGET_BRANCH}]"
git commit -m "$COMMIT_MSG" >> "$LOG_FILE" 2>&1 || error "Commit failed"

success "Results committed successfully"

# =============================================================================
# Push to GitHub (with retry)
# =============================================================================

log "================================"
log "Pushing to GitHub ($TARGET_BRANCH)"
log "================================"

MAX_RETRIES=3
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    git push origin "$TARGET_BRANCH" >> "$LOG_FILE" 2>&1
    PUSH_CODE=$?

    if [ $PUSH_CODE -eq 0 ]; then
        success "Results pushed to GitHub!"
        log "URL: https://github.com/pzg8794/quantum_project/tree/${TARGET_BRANCH}/Dynamic_Routing_Eval_Framework/results"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            warn "Push failed (attempt $RETRY_COUNT/$MAX_RETRIES), pulling and retrying..."
            git pull --rebase origin "$TARGET_BRANCH" >> "$LOG_FILE" 2>&1
            sleep 2
        else
            error "Push failed after $MAX_RETRIES attempts"
        fi
    fi
done

# =============================================================================
# Summary
# =============================================================================

log "================================"
log "PUSH COMPLETE"
log "================================"

cat << EOF | tee -a "$LOG_FILE"

SUMMARY
=======
Status: SUCCESS
Branch: $TARGET_BRANCH
Commit: $COMMIT_MSG
Log: $LOG_FILE

GitHub: https://github.com/pzg8794/quantum_project

EOF

success "All results pushed successfully!"