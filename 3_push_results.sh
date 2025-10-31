#!/bin/bash

################################################################################
# SCRIPT 3: PUSH RESULTS - Pull, Commit, Push to GitHub
# Handles concurrent VM pushes safely
################################################################################

set +e

REPO_DIR="/tmp/quantum_repo"
LOG_DIR="/tmp/quantum_logs"
LOG_FILE="$LOG_DIR/push_$(date +%s).log"

mkdir -p "$LOG_DIR"

log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }
success() { echo "SUCCESS: $1" | tee -a "$LOG_FILE"; }
error() { echo "ERROR: $1" | tee -a "$LOG_FILE"; exit 1; }
warn() { echo "WARN: $1" | tee -a "$LOG_FILE"; }

# =============================================================================
# Branch Selection
# =============================================================================
# Default to pushing to gcp-main unless another branch name is provided.
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
# Pull Latest Changes (CRITICAL for parallel VMs)
# =============================================================================

log "================================"
log "Pulling Latest from $TARGET_BRANCH"
log "================================"

git pull origin "$TARGET_BRANCH" >> "$LOG_FILE" 2>&1
PULL_CODE=$?

if [ $PULL_CODE -ne 0 ]; then
    warn "Pull had issues (code $PULL_CODE), attempting rebase strategy..."
    git pull --rebase origin "$TARGET_BRANCH" >> "$LOG_FILE" 2>&1
    if [ $? -ne 0 ]; then
        error "Pull failed - cannot sync with remote"
    fi
fi

success "Synced with remote branch: $TARGET_BRANCH"

# =============================================================================
# Stage Results
# =============================================================================

log "================================"
log "Staging Results"
log "================================"

# Create a unique run marker so every run commits something
RUN_ID=$(date +%Y%m%d_%H%M%S)
RUN_MARKER="Dynamic_Routing_Eval_Framework/results/run_marker_${RUN_ID}.txt"
echo "Run completed at ${RUN_ID}" > "$RUN_MARKER"
log "Created unique run marker: $RUN_MARKER"

# Stage experiment outputs
git add Dynamic_Routing_Eval_Framework/results/ 2>/dev/null || true
git add Dynamic_Routing_Eval_Framework/experiment_results/ 2>/dev/null || true

log "Files staged:"
git diff --cached --name-only | tee -a "$LOG_FILE"

# =============================================================================
# Commit
# =============================================================================

log "================================"
log "Committing Results"
log "================================"

COMMIT_MSG="Experiment results - $(date +'%Y-%m-%d %H:%M:%S') [${TARGET_BRANCH}]"
git commit -m "$COMMIT_MSG" >> "$LOG_FILE" 2>&1
COMMIT_CODE=$?

if [ $COMMIT_CODE -ne 0 ]; then
    if git diff --cached --quiet; then
        warn "No changes to commit."
    else
        error "Commit failed with code $COMMIT_CODE"
    fi
else
    success "Results committed"
fi

# =============================================================================
# Push to GitHub (with retry for race conditions)
# =============================================================================

log "================================"
log "Pushing to GitHub"
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
            warn "Push failed (attempt $RETRY_COUNT/$MAX_RETRIES), rebasing and retrying..."
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
Commit: $COMMIT_MSG
Log: $LOG_FILE

GitHub: https://github.com/pzg8794/quantum_project/tree/${TARGET_BRANCH}

EOF

success "All results pushed!"