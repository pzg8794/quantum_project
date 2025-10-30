#!/bin/bash

################################################################################
# GCP VM QUICK DEPLOY SCRIPT
# Creates 4 VMs and deploys automated startup on each
# Usage: ./deploy-gcp.sh <GITHUB_TOKEN>
################################################################################

GITHUB_TOKEN="${1:-}"
GITHUB_USERNAME="pzg8794"
GITHUB_REPO="quantum_project"

if [ -z "$GITHUB_TOKEN" ]; then
    echo "Usage: ./deploy-gcp.sh <GITHUB_TOKEN>"
    echo "Example: ./deploy-gcp.sh ghp_xxxxxxxxxxxxxxxxxxxx"
    exit 1
fi

echo "================================"
echo "🚀 GCP DEPLOYMENT SCRIPT"
echo "================================"
echo ""
echo "GitHub Username: $GITHUB_USERNAME"
echo "Repository: $GITHUB_REPO"
echo "Token: $(echo $GITHUB_TOKEN | cut -c1-20)..." 
echo ""
echo "Creating 4 VMs with automated startup..."
echo ""

# Create GCP startup script inline
STARTUP_SCRIPT='#!/bin/bash
set -e
apt-get update -y
apt-get install -y git python3 python3-pip python3-venv
cd /root
git clone "https://'"$GITHUB_TOKEN"'@github.com/'"$GITHUB_USERNAME"'/'"$GITHUB_REPO"'.git" quantum_project
cd quantum_project
chmod +x startup.sh
./startup.sh '"$SEED_OFFSET"' '"$GITHUB_TOKEN"''

# Create 4 VMs with different seed offsets
for i in {0..3}; do
    ZONE_LETTER=$(printf "abcd" | cut -c$((i+1)))
    ZONE="us-central1-${ZONE_LETTER}"
    VM_NAME="quantum-run-${i}"
    
    echo "Creating VM ${i+1}/4: $VM_NAME in zone $ZONE..."
    
    # Create VM with startup script
    gcloud compute instances create "$VM_NAME" \
        --machine-type=e2-standard-4 \
        --zone="$ZONE" \
        --image-family=ubuntu-2204-lts \
        --image-project=ubuntu-os-cloud \
        --boot-disk-size=50GB \
        --metadata startup-script="#!/bin/bash
set -e
apt-get update -y
apt-get install -y git python3 python3-pip python3-venv
cd /root
git clone 'https://${GITHUB_TOKEN}@github.com/${GITHUB_USERNAME}/${GITHUB_REPO}.git' quantum_project
cd quantum_project
chmod +x startup.sh
./startup.sh $i ${GITHUB_TOKEN}" \
        --scopes=cloud-platform \
        || echo "Warning: VM creation may have issues, continuing..."
    
    echo "✅ VM $VM_NAME created (seed offset: $i)"
    echo ""
done

echo "================================"
echo "✅ ALL VMs CREATED"
echo "================================"
echo ""
echo "📊 VMs Status:"
gcloud compute instances list --filter="name:quantum-run-*" --format="table(name,status,INTERNAL_IP)"
echo ""
echo "🔍 Monitor Progress:"
echo "  gcloud compute instances list --filter='name:quantum-run-*'"
echo ""
echo "📜 View Logs:"
echo "  gcloud compute instances get-serial-port-output quantum-run-0 --zone=us-central1-a"
echo "  gcloud compute instances get-serial-port-output quantum-run-1 --zone=us-central1-b"
echo "  gcloud compute instances get-serial-port-output quantum-run-2 --zone=us-central1-c"
echo "  gcloud compute instances get-serial-port-output quantum-run-3 --zone=us-central1-d"
echo ""
echo "🧹 Delete All VMs When Done:"
echo "  gcloud compute instances delete quantum-run-{0..3} --quiet"
echo ""
echo "⏱️  Expected runtime per VM: ~2.5 hours"
echo "💰 Estimated cost: $0.38 per VM, ~$1.50 total"
