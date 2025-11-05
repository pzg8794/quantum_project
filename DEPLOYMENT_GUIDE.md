# 🚀 Quantum MAB Automated Deployment Guide

Your repo: `pzg8794/quantum_project`

## Step 1: Create GitHub Personal Access Token

1. Go to https://github.com/settings/tokens
2. Click **"Generate new token"** → **"Generate new token (classic)"**
3. Give it a name: `GCP Quantum MAB`
4. Select scopes: ✅ **repo** (full control of private repositories)
5. Click **"Generate token"** at bottom
6. **COPY the token** (you'll only see it once!)
   - Format: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx`

## Step 2: Prepare Your Local Repo

Add the automation scripts to your repo:

```bash
# On your local machine
cd ~/quantum_project

# Download the startup scripts
# (Copy the startup.sh and deploy-gcp.sh files from above)

# OR create them manually:
cat > startup.sh << 'EOF'
# (Paste the entire startup.sh script here)
EOF

cat > deploy-gcp.sh << 'EOF'
# (Paste the entire deploy-gcp.sh script here)
EOF

# Make scripts executable
chmod +x startup.sh deploy-gcp.sh

# Commit to GitHub
git add startup.sh deploy-gcp.sh
git commit -m "Add automated startup and GCP deployment scripts"
git push origin main
```

## Step 3: Test Startup Script Locally (Optional but Recommended)

```bash
# Create a test directory
mkdir ~/test_quantum_local
cd ~/test_quantum_local

# Clone your repo
git clone https://YOUR_TOKEN@github.com/pzg8794/quantum_project.git .

# Run startup script with dry-run or test
chmod +x startup.sh

# Test with seed offset 0
./startup.sh 0 YOUR_GITHUB_TOKEN

# Expected output:
# [2025-10-30 02:05:00] ================================
# [2025-10-30 02:05:00] PHASE 1: System Setup
# ...
# ✅ System dependencies installed
# ✅ Git configured
# ✅ Repository ready
# ...
```

## Step 4: Deploy on GCP (Automated)

### Option A: Using the deployment script (Easiest)

```bash
# Make script executable
chmod +x deploy-gcp.sh

# Run with your GitHub token
./deploy-gcp.sh ghp_xxxxxxxxxxxxxxxxxxxx

# This creates all 4 VMs automatically!
```

### Option B: Manual GCP Setup (If script doesn't work)

```bash
# Set variables
GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"
GITHUB_USERNAME="pzg8794"
GITHUB_REPO="quantum_project"

# Create VM 0 (Seed offset 0)
gcloud compute instances create quantum-run-0 \
    --machine-type=e2-standard-4 \
    --zone=us-central1-a \
    --metadata startup-script="#!/bin/bash
set -e
apt-get update -y
apt-get install -y git python3 python3-pip python3-venv
cd /root
git clone 'https://${GITHUB_TOKEN}@github.com/${GITHUB_USERNAME}/${GITHUB_REPO}.git' quantum_project
cd quantum_project
chmod +x startup.sh
./startup.sh 0 ${GITHUB_TOKEN}"

# Create VM 1 (Seed offset 1)
gcloud compute instances create quantum-run-1 \
    --machine-type=e2-standard-4 \
    --zone=us-central1-b \
    --metadata startup-script="#!/bin/bash
set -e
apt-get update -y
apt-get install -y git python3 python3-pip python3-venv
cd /root
git clone 'https://${GITHUB_TOKEN}@github.com/${GITHUB_USERNAME}/${GITHUB_REPO}.git' quantum_project
cd quantum_project
chmod +x startup.sh
./startup.sh 1 ${GITHUB_TOKEN}"

# Create VM 2 (Seed offset 2)
gcloud compute instances create quantum-run-2 \
    --machine-type=e2-standard-4 \
    --zone=us-central1-c \
    --metadata startup-script="#!/bin/bash
set -e
apt-get update -y
apt-get install -y git python3 python3-pip python3-venv
cd /root
git clone 'https://${GITHUB_TOKEN}@github.com/${GITHUB_USERNAME}/${GITHUB_REPO}.git' quantum_project
cd quantum_project
chmod +x startup.sh
./startup.sh 2 ${GITHUB_TOKEN}"

# Create VM 3 (Seed offset 3)
gcloud compute instances create quantum-run-3 \
    --machine-type=e2-standard-4 \
    --zone=us-central1-d \
    --metadata startup-script="#!/bin/bash
set -e
apt-get update -y
apt-get install -y git python3 python3-pip python3-venv
cd /root
git clone 'https://${GITHUB_TOKEN}@github.com/${GITHUB_USERNAME}/${GITHUB_REPO}.git' quantum_project
cd quantum_project
chmod +x startup.sh
./startup.sh 3 ${GITHUB_TOKEN}"
```

## Step 5: Monitor Execution

### Check VM Status

```bash
# List all quantum VMs
gcloud compute instances list --filter="name:quantum-run-*"

# Expected output:
# NAME            STATUS    INTERNAL_IP  EXTERNAL_IP
# quantum-run-0   RUNNING   10.128.0.2   34.123.45.67
# quantum-run-1   RUNNING   10.128.0.3   34.123.45.68
# quantum-run-2   RUNNING   10.128.0.4   34.123.45.69
# quantum-run-3   RUNNING   10.128.0.5   34.123.45.70
```

### View Live Logs

```bash
# VM 0
gcloud compute instances get-serial-port-output quantum-run-0 --zone=us-central1-a | tail -100

# VM 1
gcloud compute instances get-serial-port-output quantum-run-1 --zone=us-central1-b | tail -100

# VM 2
gcloud compute instances get-serial-port-output quantum-run-2 --zone=us-central1-c | tail -100

# VM 3
gcloud compute instances get-serial-port-output quantum-run-3 --zone=us-central1-d | tail -100
```

### SSH Into a VM (if needed for debugging)

```bash
# SSH into VM 0
gcloud compute ssh quantum-run-0 --zone=us-central1-a

# Inside VM, check the full log
tail -f /root/quantum_logs/run_0_*.log

# Check experiment status
ps aux | grep multi_run_evaluator

# Exit SSH
exit
```

## Step 6: Wait for Completion (~2.5 hours per VM)

Each VM will:
1. ✅ Set up system packages
2. ✅ Configure Python environment
3. ✅ Clone your repo
4. ✅ Run ALL scenarios (stochastic, markov, onlineadaptive, none) with ALL models
5. ✅ Collect results
6. ✅ **Automatically push to GitHub**

You can safely close your terminal - the VMs run independently!

## Step 7: Check Results on GitHub

```bash
# Open your repo
https://github.com/pzg8794/quantum_project

# Check results directory
results/
├── run_0/          # VM 0 results (seed offset 0)
│   ├── experiment_output.log
│   ├── SUMMARY.txt
│   └── [data files]
├── run_1/          # VM 1 results
├── run_2/          # VM 2 results
└── run_3/          # VM 3 results
```

## Step 8: Delete VMs (IMPORTANT - Save Money!)

```bash
# Delete all 4 VMs at once
gcloud compute instances delete quantum-run-{0..3} --quiet

# Or delete individually
gcloud compute instances delete quantum-run-0 --zone=us-central1-a
gcloud compute instances delete quantum-run-1 --zone=us-central1-b
gcloud compute instances delete quantum-run-2 --zone=us-central1-c
gcloud compute instances delete quantum-run-3 --zone=us-central1-d
```

**⚠️ CRITICAL: Delete VMs when done or you'll burn through your $300 credit!**

## Step 9: Aggregate Results

Once all 4 VMs finish, combine results:

```python
# aggregate_results.py
import pandas as pd
import glob

results = []
for i in range(4):
    # Find all CSV files in run_i/
    csv_files = glob.glob(f'results/run_{i}/**/*.csv', recursive=True)
    for csv in csv_files:
        df = pd.read_csv(csv)
        df['seed_offset'] = i
        results.append(df)

combined = pd.concat(results, ignore_index=True)

# Compute statistics
summary = combined.groupby(['Model', 'Scenario', 'Horizon']).agg({
    'Efficiency': ['mean', 'std', 'min', 'max', 'count']
}).round(3)

print(summary)
summary.to_csv('results/aggregate_summary.csv')
```

## 📊 Expected Results Structure

After all 4 VMs complete, your GitHub repo will have:

```
results/
├── run_0/
│   ├── SUMMARY.txt
│   ├── experiment_output.log
│   └── (model results)
├── run_1/
│   ├── SUMMARY.txt
│   ├── experiment_output.log
│   └── (model results)
├── run_2/
│   ├── SUMMARY.txt
│   ├── experiment_output.log
│   └── (model results)
└── run_3/
    ├── SUMMARY.txt
    ├── experiment_output.log
    └── (model results)

Total data points:
  4 independent runs × 4 scenarios × 3 horizons × 3 repetitions × 5 models
  = 2,880 model evaluations with full statistical rigor!
```

## 💰 Cost Summary

| Item | Cost |
|------|------|
| VM per hour (e2-standard-4) | $0.15 |
| Per 2.5-hour run | $0.375 |
| 4 VMs (parallel) | $1.50 |
| Your GCP credit | $300 |
| Remaining after runs | $298.50 |

## ❌ Troubleshooting

### Issue: VMs stuck in provisioning
**Solution**: Wait 5-10 minutes, then check status again

### Issue: Git push fails
**Solution**: 
- Verify token is correct
- Token has "repo" scope
- Check network connectivity: `ping github.com`

### Issue: Python import errors
**Solution**:
- SSH into VM: `gcloud compute ssh quantum-run-0 --zone=us-central1-a`
- Check logs: `tail -f /root/quantum_logs/run_0_*.log`
- Reinstall packages: `pip install -q torch numpy pandas tqdm`

### Issue: Experiments take too long
**Solution**:
- Use larger machines: `--machine-type=e2-standard-8` (costs 2x)
- Check experiment output: `gcloud compute instances get-serial-port-output quantum-run-0 --zone=us-central1-a`

## ✅ Quick Checklist

- [ ] GitHub token created and copied
- [ ] startup.sh and deploy-gcp.sh added to repo
- [ ] Scripts committed and pushed to GitHub
- [ ] Local test passed (optional but recommended)
- [ ] GCP VMs created with `deploy-gcp.sh` or manual commands
- [ ] Monitored logs to confirm experiments running
- [ ] Results automatically pushed to GitHub
- [ ] Verified results in `results/run_X/` directories
- [ ] Deleted all 4 VMs to save credits
- [ ] Aggregated results from all 4 runs

**You're all set! The automation handles everything else.** 🚀
