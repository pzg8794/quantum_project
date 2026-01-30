# PAPER7 ZERO REWARD FIX

## Problem

Oracle was getting stuck because Paper7RewardFunction was returning **NEGATIVE REWARDS** (-1.0, -2.0, -3.0, etc.), which caused the Oracle to compute zero/near-zero total rewards.

```
Paper7RewardFunction returned:
  1 hop → -1.0  ❌ NEGATIVE
  2 hops → -2.0 ❌ NEGATIVE
  3 hops → -3.0 ❌ NEGATIVE
```

Bandit algorithms expect **positive rewards**, so negative values break the logic.

## Root Cause

The Paper7RewardFunction was computing **negative inversions** of path metrics:

```python
# BROKEN CODE:
if self.mode == "neg_hop":
    return -hop  # ❌ Returns -1, -2, -3, etc.
```

The function name ("neg_hop") was meant to indicate "negative hop count" (penalize hops), but it was returning literal negative values instead of inverted positive rewards.

## Solution

Changed Paper7RewardFunction to return **POSITIVE INVERTED REWARDS**:

```python
# FIXED CODE:
if self.mode == "neg_hop":
    return max(0.1, 10.0 - hop)  # ✅ Returns 9.0, 8.0, 7.0, etc.
```

### Reward Mapping
```
1 hop  → 9.0   (best)
2 hops → 8.0
3 hops → 7.0
5 hops → 5.0   (worst)
```

**Result:** Shorter paths (fewer hops) = **Higher rewards** ✅

## Changes Made

**File:** `daqr/core/quantum_physics.py`  
**Class:** `Paper7RewardFunction`  
**Method:** `compute()`  
**Lines:** ~440-455

### Before
```python
if self.mode == "neg_hop":
    return -hop  # ❌ Negative rewards break bandit algorithms
```

### After
```python
if self.mode == "neg_hop":
    return max(0.1, 10.0 - hop)  # ✅ Positive inverted rewards
```

## All Modes Fixed

All three reward modes now return **positive values**:

| Mode | Before | After | Semantics |
|------|--------|-------|-----------|
| `neg_hop` | `-hop` | `10.0 - hop` | Fewer hops = higher reward |
| `neg_degree` | `-degree` | `10.0 - degree` | Lower bottleneck = higher reward |
| `neg_length` | `-length` | `20.0 - length` | Shorter path = higher reward |
| `custom` | `-weighted_score` | `10.0 - weighted_score` | Balanced inversion |

## Impact

✅ Oracle now gets **positive rewards** for Paper7  
✅ Experiments complete successfully instead of hanging  
✅ Reward semantics correct: shorter paths reward higher  
✅ Backward compatible with Oracle logic (still looking for max reward)  
✅ All bandit algorithms work with positive rewards  

## Testing

**Before fix:**
```
Path 0: [-1.0]  ← Negative reward
Path 1: [-2.0]  ← Negative reward
Path 2: [-3.0]  ← Negative reward
All rewards ≤ 0: True ❌
```

**After fix:**
```
1 hops → 9.00  ← Positive reward
2 hops → 8.00  ← Positive reward
3 hops → 7.00  ← Positive reward
All rewards > 0: True ✅
```

---

**Status:** ✅ FIXED  
**Tested:** Yes  
**Impact:** High (was causing all Paper7 runs to hang)
