# INFINITE RETRY LOOP FIX - Experiment Runner

## Problem

The Oracle initialization was hanging indefinitely because `experiment_runner.py` had an infinite retry loop that only stopped when `total_reward > 0.0`.

```python
# PROBLEMATIC CODE (line 403):
while total_reward <= 0.0:  # ❌ INFINITE LOOP if reward stays 0
    # try to compute reward
```

For Paper7 with context-aware rewards, legitimate scenarios can have zero rewards, causing the loop to retry forever.

## Root Cause

The code assumed that zero rewards indicate an error condition and should retry. However:
- Paper7 context-aware mode can legitimately return 0 rewards
- The retry loop has no exit condition other than `total_reward > 0`
- This causes the program to hang indefinitely

## Solution

Added a **maximum retry limit** to escape the infinite loop:

```python
# FIXED CODE (lines 403-432):
retry_count = 0
max_retries = 3  # Prevent infinite loops

while total_reward <= 0.0 and retry_count < max_retries:
    # ... attempt to compute reward ...
    
    retry_count += 1
    if retry_count >= max_retries and total_reward <= 0.0:
        print(f"\t⚠️ Max retries ({max_retries}) reached. Proceeding with total_reward={total_reward}")
        break  # ✅ EXIT LOOP after max retries
```

## Changes Made

**File:** `daqr/evaluation/experiment_runner.py`  
**Lines:** 403-432  
**Change Type:** Add retry counter and early exit condition

### Before
```python
while total_reward <= 0.0:
    # ... retry forever ...
```

### After
```python
retry_count = 0
max_retries = 3
while total_reward <= 0.0 and retry_count < max_retries:
    # ... retry up to 3 times ...
    retry_count += 1
    if retry_count >= max_retries and total_reward <= 0.0:
        print(f"\t⚠️ Max retries reached. Proceeding with total_reward={total_reward}")
        break
```

## Impact

✅ **Fixes hanging:** Experiments will no longer hang indefinitely  
✅ **Allows zero rewards:** Paper7 context-aware mode can return 0 without error  
✅ **Graceful degradation:** Shows warning when proceeding with zero rewards  
✅ **Backward compatible:** Paper2 still works normally  

## How It Works

1. First attempt to compute oracle rewards
2. If reward is 0, retry up to 3 times
3. After 3 attempts with zero rewards, proceed anyway
4. Shows warning message: `⚠️ Max retries (3) reached. Proceeding with total_reward=0.0`

## Result

The "Getting Oracle Rewards ..." message will no longer hang. Experiments will continue and complete normally, even if the Oracle returns zero rewards.

---

**Status:** ✅ FIXED  
**Tested With:** Paper7 (QBGP) testbed  
**Backward Compatible:** Yes
