#!/bin/bash
# Quick test runner for Paper 12 sanity tests
# Usage: ./run_tests.sh

set -e

echo "🚀 Paper 12 (QuARC) Sanity Test Suite"
echo "======================================"
echo ""

# Check if we're in the right directory
if [ ! -f "run_paper12_sanity_tests.py" ]; then
    echo "❌ ERROR: run_paper12_sanity_tests.py not found"
    echo "   Please run from: Dynamic_Routing_Eval_Framework/"
    exit 1
fi

# Ensure results directory exists
mkdir -p results

# Check if Python environment is activated
if ! command -v python &> /dev/null; then
    echo "⚠️  Python not found. Activating .quantum environment..."
    source ../../.quantum/bin/activate
fi

echo "📦 Running Paper 12 Physics Tests..."
echo ""

# Run the test suite
python run_paper12_sanity_tests.py

# Check if JSON results were created
if [ -f "results/paper12_sanity_tests.json" ]; then
    echo ""
    echo "📊 Test Results Summary:"
    echo "======================="
    python3 << 'EOF'
import json

with open('results/paper12_sanity_tests.json') as f:
    results = json.load(f)

# Check each test
all_passed = True
for test_name, test_result in results.items():
    if isinstance(test_result, dict) and 'ok' in test_result:
        status = "✅ PASS" if test_result['ok'] else "❌ FAIL"
        print(f"{status} | {test_name}")
        if not test_result['ok']:
            all_passed = False

print("")
print("=" * 40)
if all_passed:
    print("✅ ALL TESTS PASSED")
else:
    print("❌ SOME TESTS FAILED")
    print("   Check results/paper12_sanity_tests.json for details")

EOF
else
    echo "⚠️  Warning: results/paper12_sanity_tests.json not created"
fi

echo ""
echo "For detailed results, see:"
echo "  - Console output above"
echo "  - results/paper12_sanity_tests.json"
echo ""
echo "Happy testing! 🎯"
