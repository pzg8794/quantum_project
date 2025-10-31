# Complete Guide: Testing & Deploying to Google Cloud Compute Engine

## Part 1: HOW TO GET SCRIPTS INTO THE VM

### Option A: Store in GitHub (Best for VMs)

1. **Add scripts to your repo locally:**
   ```bash
   cd ~/quantum_project
   cp 1_startup.sh .
   cp 2_exp_runner.sh .
   cp 3_push_results.sh .
   chmod +x *.sh
   
   git add *.sh
   git commit -m "Add deployment scripts"
   git push origin main
   ```

2. **VM will clone them automatically** from repo when it starts

### Option B: Pass as Startup Script (Metadata)

Pass the startup script in gcloud command (see Part 2)

### Option C: SSH and SCP (Manual)

```bash
gcloud compute scp 1_startup.sh quantum-exp-1:~/
gcloud compute scp 2_exp_runner.sh quantum-exp-1:~/
gcloud compute scp 3_push_results.sh quantum-exp-1:~/
```

---

## Part 2: TESTING ON GCP COMPUTE ENGINE

### Step 1: Create a Test VM

```bash
# Simple 4-CPU test VM
gcloud compute instances create quantum-test-1 \
  --machine-type=n1-standard-4 \
  --zone=us-central1-a \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud

# Output shows external IP - SAVE IT
```

### Step 2: SSH Into VM

```bash
# Get external IP
gcloud compute instances list

# SSH in
gcloud compute ssh quantum-test-1 --zone=us-central1-a
```

### Step 3: Run Startup Script

**Option A: If scripts are in GitHub repo (RECOMMENDED)**

```bash
# SSH into VM, then:
cd ~
git clone https://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@github.com/pzg8794/quantum_project.git
cd quantum_project

chmod +x 1_startup.sh
./1_startup.sh
```

**Option B: If scripts are uploaded to VM**

```bash
chmod +x ~/1_startup.sh
~/1_startup.sh
```

### Step 4: Check Setup Logs

```bash
# Still SSH'd into VM
cat /tmp/quantum_logs/startup_*.log
```

**Should see:**
```
[timestamp] SUCCESS: Repository cloned
[timestamp] SUCCESS: Packages installed
[timestamp] SUCCESS: Python imports tested
[timestamp] SUCCESS: Environment ready for experiments!
```

### Step 5: Run a Test Experiment

```bash
# SSH'd into VM
chmod +x ~/2_exp_runner.sh
~/2_exp_runner.sh 100 "Oracle,GNeuralUCB" 1 "stochastic" 0.25
```

**Parameters format:**
```
./2_exp_runner.sh [FRAMES] [MODELS] [RUNS] [SCENARIOS] [ATTACK_INTENSITY]

Examples:
./2_exp_runner.sh 100 "Oracle,GNeuralUCB" 1 "stochastic"  # 100 frames test
./2_exp_runner.sh 1000 "Oracle,GNeuralUCB,EXPNeuralUCB" 3 "stochastic"  # Full test
./2_exp_runner.sh 4000 "Oracle" 5 "stochastic,markov"  # Production run
```

### Step 6: Push Results to GitHub

```bash
# SSH'd into VM
chmod +x ~/3_push_results.sh
~/3_push_results.sh
```

**Check:**
```bash
# Verify push succeeded
cat /tmp/quantum_logs/push_*.log

# Should see:
[timestamp] SUCCESS: Results pushed to GitHub!
```

### Step 7: View Results Online

```
https://github.com/pzg8794/quantum_project/tree/main/Dynamic_Routing_Eval_Framework/results
```

---

## Part 3: AUTOMATED DEPLOYMENT (Full Pipeline)

### Single VM with All 3 Scripts

```bash
gcloud compute instances create quantum-exp-1 \
  --machine-type=n1-standard-4 \
  --zone=us-central1-a \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --metadata-from-file startup-script=1_startup.sh

# Wait ~5 minutes for startup

# SSH to verify
gcloud compute ssh quantum-exp-1 --zone=us-central1-a
cat /tmp/quantum_logs/startup_*.log  # Check it succeeded

# Run experiment
./2_exp_runner.sh 100 "Oracle,GNeuralUCB" 1 "stochastic"

# Push
./3_push_results.sh
```

### Multiple VMs (Parallel Runs)

```bash
TOKEN="your_token"
FRAMES=1000
MODELS="Oracle,GNeuralUCB,EXPNeuralUCB"
RUNS=3

# Create 4 VMs with different seed offsets
for i in {0..3}; do
  gcloud compute instances create quantum-exp-$i \
    --machine-type=n1-standard-4 \
    --zone=us-central1-a \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --metadata-from-file startup-script=1_startup.sh &
done

# Wait for all to start
sleep 300

# Run experiments in parallel
for i in {0..3}; do
  gcloud compute ssh quantum-exp-$i --zone=us-central1-a \
    --command="cd ~/quantum_project && ./2_exp_runner.sh $FRAMES '$MODELS' $RUNS 'stochastic'" &
done

# Wait for experiments to complete
wait

# Push all results
for i in {0..3}; do
  gcloud compute ssh quantum-exp-$i --zone=us-central1-a \
    --command="cd ~/quantum_project && ./3_push_results.sh" &
done
```

---

## Part 4: MONITORING & DEBUGGING

### Check Logs from Your Local Machine

```bash
# SSH without interactive shell, just run command
gcloud compute ssh quantum-test-1 --zone=us-central1-a \
  --command="cat /tmp/quantum_logs/*.log" | head -100
```

### Copy Logs Locally

```bash
gcloud compute scp quantum-test-1:/tmp/quantum_logs/*.log ~/local_logs/ \
  --zone=us-central1-a --recurse
```

### Debugging Issues

```bash
# SSH into VM
gcloud compute ssh quantum-test-1 --zone=us-central1-a

# Check what went wrong
tail -100 /tmp/quantum_logs/*.log

# Check repo state
cd /tmp/quantum_repo && git status

# Check Python
python3 -c "import sys; print(sys.path)"
```

---

## Part 5: CLEANUP

```bash
# Delete test VM
gcloud compute instances delete quantum-test-1 --zone=us-central1-a

# Delete multiple VMs
for i in {0..3}; do
  gcloud compute instances delete quantum-exp-$i --zone=us-central1-a --quiet &
done
```

---

## QUICK START (TL;DR)

```bash
# 1. Local: Add scripts to repo
git add 1_startup.sh 2_exp_runner.sh 3_push_results.sh
git commit -m "Add scripts"
git push origin main

# 2. Create VM
gcloud compute instances create quantum-test-1 \
  --machine-type=n1-standard-4 --zone=us-central1-a \
  --image-family=ubuntu-2204-lts --image-project=ubuntu-os-cloud

# 3. SSH in
gcloud compute ssh quantum-test-1 --zone=us-central1-a

# 4. Clone repo and run (inside VM)
git clone https://TOKEN@github.com/pzg8794/quantum_project.git
cd quantum_project
./1_startup.sh          # Setup (5 min)
./2_exp_runner.sh 100   # Run 100-frame test (2 min)
./3_push_results.sh     # Push to GitHub (1 min)

# 5. Check results online
# https://github.com/pzg8794/quantum_project/tree/main/Dynamic_Routing_Eval_Framework/results

# 6. Cleanup
gcloud compute instances delete quantum-test-1 --zone=us-central1-a
```
