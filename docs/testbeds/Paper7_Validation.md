# Paper 7 - Validation & Testing Guide

**Paper**: Liu et al. 2024 - QBGP  
**Status**: ✅ Fully Integrated with Automated Testing  
**Last Updated**: January 30, 2026

---

## Testing Framework

### Unit Tests
- **Test File**: `run_paper7_sanity_tests.py`
- **Test Count**: 5+ unit tests
- **Coverage**: Topology, context features, rewards, physics, integration
- **Status**: ✅ All passing

---

## Running Tests

### Quick Start
```bash
cd hybrid_variable_framework/Dynamic_Routing_Eval_Framework/

# Run Paper 7 unit tests
python run_paper7_sanity_tests.py

# View results
cat results/paper7_sanity_tests.json | python -m json.tool
```

### Detailed Testing Procedures

See detailed validation procedures in testbed:
`Testbeds/Paper7-lizhuohua-quantum-bgp-online-path-selection-aeb35c0/validation/PAPER7_VALIDATION.md`

---

## Test Coverage

| Test | What's Tested |
|------|---|
| **Topology** | 100 nodes, 4 paths, correct shapes |
| **Context** | Features constant per path, correct values |
| **Rewards** | 35 arms, [5,100] range, realistic variation |
| **Physics** | Fidelity model, delay parameters |
| **Format** | Dictionary keys, types match framework |

---

## Validation Status

✅ Topology generation validated  
✅ Context features validated  
✅ Reward generation validated  
✅ Physics parameters validated  
✅ Integration format validated  

---

## References

- **Full Summary**: [Paper7_Summary.md](Paper7_Summary.md)
- **Testbed Location**: `Testbeds/Paper7-...`
- **Validation Details**: See `validation/` folder in testbed

---

**See Also**: [Paper7_Quick_Reference.md](Paper7_Quick_Reference.md)
