# 3runs_S1T Verification Table

| Test | Result | Status | Notes |
|------|--------|--------|-------|
| Complete Data Coverage | ✓ PASS | Ready for merge | All 4 allocators have all 5 scenarios × 3 experiments |
| Model Count | ✓ PASS | Ready for merge | 4 models in every run |
| Reward Positivity | ✓ PASS | Ready for merge | All rewards > 0 |
| Data Duplication | ✓ PASS | Ready for merge | No identical rewards |
| Outliers | ✓ PASS | Ready for merge | All within normal variance |
| Scenario Completion | ✓ PASS | Ready for merge | All 5 scenarios present |
| Seed Consistency | ✓ PASS | Ready for merge | Seed 1 consistent throughout |
| Capacity Scaling | ✓ PASS | Ready for merge | 4000, 6000, 8000 frames correct |
| No Crashes | ✓ PASS | Ready for merge | Failed=0, no runtime errors |
| Cross-Allocator Consistency | ✓ PASS | Ready for merge | Model rankings consistent across allocators |
