# Documentation Index

**Master reference for all framework and testbed documentation**

**Latest Update**: See [REORGANIZATION_COMPLETE.md](REORGANIZATION_COMPLETE.md) for details on how all .md files were organized under `/docs/`

---

## 🚀 Quick Start

**New to the framework?** Start here:
- [README.md](../README.md) - Main framework overview
- [TESTBEDS_OVERVIEW.md](TESTBEDS_OVERVIEW.md) - All testbeds at a glance

---

## 📚 Testbed Documentation

### All Testbeds
- **[TESTBEDS_OVERVIEW.md](TESTBEDS_OVERVIEW.md)** - Central hub with comparison matrix, all papers

### Paper 2 (MAB Quantum Routing)
- [Paper2_Quick_Reference.md](testbeds/Paper2_Quick_Reference.md) - Quick overview
- [Paper2_Integration_Report.md](testbeds/Paper2_Integration_Report.md) - Full details
- [Paper2_Test_Commands.md](testbeds/Paper2_Test_Commands.md) - Testing procedures

### Paper 7 (QBGP - Online BGP)
- [Paper7_Quick_Reference.md](testbeds/Paper7_Quick_Reference.md) - Quick overview
- [Paper7_Summary.md](testbeds/Paper7_Summary.md) - Comprehensive summary
- [Paper7_Validation.md](testbeds/Paper7_Validation.md) - Testing & validation
- [Paper7_vs_Paper12_Testing.md](testbeds/Paper7_vs_Paper12_Testing.md) - Comparison with Paper 12

### Paper 12 (QuARC - Qubit Allocation)
- [Paper12_Quick_Reference.md](testbeds/Paper12_Quick_Reference.md) - Quick overview
- [Paper12_Testing_Guide.md](testbeds/Paper12_Testing_Guide.md) - Testing procedures
- [Paper12_Parameters.md](testbeds/Paper12_Parameters.md) - Parameter documentation
- [Paper12_Framework_Quick_Reference.md](testbeds/Paper12_Framework_Quick_Reference.md) - Framework overview
- [Paper12_Delivery_Summary.md](testbeds/Paper12_Delivery_Summary.md) - Delivery summary
- [Paper12_Documentation_Index.md](testbeds/Paper12_Documentation_Index.md) - Paper 12 docs index
- [Paper12_Testing_Readme.md](testbeds/Paper12_Testing_Readme.md) - Testing procedures
- [PAPER12_TESTS_README.md](testbeds/PAPER12_TESTS_README.md) - Complete testing guide
- [PAPER12_TESTING_SUMMARY.md](testbeds/PAPER12_TESTING_SUMMARY.md) - Testing summary

---

## 🔧 Setup & Installation

**Location**: `docs/setup/` (centralized setup guides)

- [setup/SETUP_COLAB.md](setup/SETUP_COLAB.md) - Google Colab setup
- [setup/SETUP_LOCAL.md](setup/SETUP_LOCAL.md) - Local machine & GCP setup
- [setup/TROUBLESHOOTING.md](setup/TROUBLESHOOTING.md) - Common issues & fixes
- [setup/README_START_HERE.md](setup/README_START_HERE.md) - Getting started guide
- [setup/TESTBEDS.md](setup/TESTBEDS.md) - Legacy testbed hub
- [setup/IMPLEMENTATION_CHECKLIST.md](setup/IMPLEMENTATION_CHECKLIST.md) - Implementation tracking
- [setup/INTEGRATION_GUIDE.md](setup/INTEGRATION_GUIDE.md) - Integration procedures
- [setup/QUICK_START_CODE_SNIPPETS.md](setup/QUICK_START_CODE_SNIPPETS.md) - Code examples
- [setup/README_TESTBED_RUNNERS.md](setup/README_TESTBED_RUNNERS.md) - Running testbeds
- [setup/SEAMLESS_INTEGRATION_SUMMARY.md](setup/SEAMLESS_INTEGRATION_SUMMARY.md) - Integration overview

---

## 📋 Integration & Completion Documentation

### Current Integration Status
- [INTEGRATION_COMPLETE.md](INTEGRATION_COMPLETE.md) - Documentation integration summary
- [TESTBEDS_INTEGRATION_SUMMARY.md](TESTBEDS_INTEGRATION_SUMMARY.md) - What was organized
- [TESTBEDS_INTEGRATION_CHECKLIST.md](TESTBEDS_INTEGRATION_CHECKLIST.md) - Full checklist of work done

### Legacy Testbed Hub
- [TESTBEDS_HUB_LEGACY.md](TESTBEDS_HUB_LEGACY.md) - Old testbeds.md from setup_files (archived)

---

## 🛠️ Implementation Notes & Bug Fixes

**Location**: `docs/implementation-notes/`

These documents track technical debugging and implementation details:
- `ORACLE_FIX_*.md` - Oracle environment fixes
- `PAPER7_*.md` - Paper 7 specific fixes
- `*_PROBABILITY_FIX.md` - Probability model fixes
- `*_REWARD*.md` - Reward generation fixes
- `INFINITE_RETRY_LOOP_FIX.md` - Retry logic fix

**Purpose**: Reference for understanding issues that were encountered and resolved during framework development.

---

## 📁 Directory Structure

```
docs/
├── INDEX.md (← You are here)
├── Core Documentation & Integration (8 files)
│   ├── TESTBEDS_OVERVIEW.md (Central hub)
│   ├── REORGANIZATION_COMPLETE.md (Organization summary)
│   ├── FINAL_ORGANIZATION_SUMMARY.md
│   ├── INTEGRATION_COMPLETE.md
│   ├── TESTBEDS_INTEGRATION_SUMMARY.md
│   ├── TESTBEDS_INTEGRATION_CHECKLIST.md
│   ├── COMPLETION_CHECKLIST.md
│   ├── CHANGES_MADE.md
│   └── TESTBEDS_HUB_LEGACY.md (archived)
│
├── setup/ (10 Setup & Configuration files)
│   ├── SETUP_COLAB.md
│   ├── SETUP_LOCAL.md
│   ├── TROUBLESHOOTING.md
│   ├── README_START_HERE.md
│   ├── TESTBEDS.md (legacy)
│   ├── IMPLEMENTATION_CHECKLIST.md
│   ├── INTEGRATION_GUIDE.md
│   ├── QUICK_START_CODE_SNIPPETS.md
│   ├── README_TESTBED_RUNNERS.md
│   └── SEAMLESS_INTEGRATION_SUMMARY.md
│
├── testbeds/ (Paper-specific documentation - 19 files)
│   ├── Paper2_Quick_Reference.md
│   ├── Paper2_Integration_Report.md
│   ├── Paper2_Test_Commands.md
│   ├── Paper7_Quick_Reference.md
│   ├── Paper7_Summary.md
│   ├── Paper7_Validation.md
│   ├── Paper7_vs_Paper12_Testing.md
│   ├── Paper12_Quick_Reference.md
│   ├── Paper12_Testing_Guide.md
│   ├── Paper12_Parameters.md
│   ├── Paper12_Framework_Quick_Reference.md
│   ├── Paper12_Delivery_Summary.md
│   ├── Paper12_Documentation_Index.md
│   ├── Paper12_Testing_Readme.md
│   └── [more Paper 12 docs]
│
└── implementation-notes/ (Technical debugging docs - 12 files)
    ├── ORACLE_FIX_ANALYSIS.md
    ├── ORACLE_FIX_COMPLETE.md
    ├── ORACLE_FIX_FINAL_SUMMARY.md
    ├── ORACLE_FIX_QUICK_REFERENCE.md
    ├── ORACLE_NUMPY_BOOLEAN_FIX.md
    ├── PAPER7_IMPLEMENTATION_ALIGNMENT.md
    ├── PAPER7_PROBABILITY_FIX_COMPLETE.md
    ├── PAPER7_ZERO_REWARD_FIX.md
    ├── README_ORACLE_FIX.md
    ├── ICMAB_PROBABILITY_FIX.md
    ├── INFINITE_RETRY_LOOP_FIX.md
    └── NEURAL_NETWORK_PROBABILITY_FIX.md
```

---

## 🎯 How to Use This Index

### I want to...

**...get started quickly**
→ Read [README.md](../README.md), then [TESTBEDS_OVERVIEW.md](TESTBEDS_OVERVIEW.md)

**...learn about a specific paper**
→ See sections above for Paper 2, 7, or 12

**...compare papers**
→ [TESTBEDS_OVERVIEW.md](TESTBEDS_OVERVIEW.md) has comparison matrix

**...run tests**
→ See individual paper's `Testing_Guide.md` or `Test_Commands.md`

**...understand the implementation**
→ Check `implementation-notes/` folder for technical details

**...set up my environment**
→ Go to [docs/setup/](setup/) directory

---

## 📚 All Files Organized

**Documentation is organized into**:
- **docs/testbeds/** - Paper-specific docs
- **docs/setup/** - Setup & configuration guides
- **docs/implementation-notes/** - Technical debugging notes
- **docs/** - Integration summaries, indexes, and legacy references

**Root directory**: Only `README.md` and `.github/copilot-instructions.md` (config)
