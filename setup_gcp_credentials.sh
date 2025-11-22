# In your repo, create: setup_gcp_credentials.sh

#!/bin/bash
# Dynamic GCP credentials loader

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check multiple locations (in order of preference)
CREDENTIAL_LOCATIONS=(
    "$SCRIPT_DIR/../quantum-gcp-credentials.json"           # Parent directory
    "$SCRIPT_DIR/quantum-gcp-credentials.json"              # Repo root
    "$HOME/quantum-gcp-credentials.json"                     # Home directory
    "/app/credentials/quantum-gcp-credentials.json"         # Docker mount
)

# Find first existing credential file
for location in "${CREDENTIAL_LOCATIONS[@]}"; do
    if [ -f "$location" ]; then
        export GOOGLE_APPLICATION_CREDENTIALS="$location"
        echo "✅ Found GCP credentials at: $location"
        return 0
    fi
done

echo "⚠️ No GCP credentials found. Checked:"
printf '%s\n' "${CREDENTIAL_LOCATIONS[@]}"
return 1