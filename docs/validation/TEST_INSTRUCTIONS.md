# Validation Test Instructions

This guide explains how to run, interpret, and verify the Phase 0 and Phase 1 validation tests.

---

## Quick Start

```bash
# Run all validation tests (29 tests, ~2.5 minutes)
PYTHONPATH=. pytest server/tests/test_validators/ -v

# Run specific test suite
PYTHONPATH=. pytest server/tests/test_validators/test_constraints.py -v
PYTHONPATH=. pytest server/tests/test_validators/test_geometry_analyzer.py -v

# Run with detailed output
PYTHONPATH=. pytest server/tests/test_validators/ -v -s
```

---

## Prerequisites

### Required Dependencies
```bash
# Core testing
pip install pytest pytest-asyncio

# ASE and validation
pip install ase pymatgen robocrystallographer

# Optional (for molecule naming)
pip install openbabel-python
```

### Environment Setup
```bash
# Ensure PYTHONPATH includes project root
export PYTHONPATH=/path/to/ASE_MCP

# Or use inline (recommended)
PYTHONPATH=. pytest server/tests/test_validators/ -v
```

---

## Test Suites

### Phase 0: GeometryAnalyzer (13 tests, ~107s)

**File**: `server/tests/test_validators/test_geometry_analyzer.py`

**What it tests**:
- Robocrystallographer integration
- Structure dimensionality detection
- Coordination number extraction
- Bond length statistics
- Geometry hint generation
- Constraint checking integration

**Run individually**:
```bash
PYTHONPATH=. pytest server/tests/test_validators/test_geometry_analyzer.py -v
```

**Expected output**:
```
13 passed, ~8-12 warnings in 90-120s
```

### Phase 1: ConstraintValidator (16 tests, ~67s)

**File**: `server/tests/test_validators/test_constraints.py`

**What it tests**:
- Three-level feedback (passed/warning/violation)
- Tolerance thresholds (5%/15%)
- Constraint types (dimensionality, coordination, bond lengths, geometry likeness)
- Deviation calculation accuracy
- Suggestion generation

**Run individually**:
```bash
PYTHONPATH=. pytest server/tests/test_validators/test_constraints.py -v
```

**Expected output**:
```
16 passed, ~8-12 warnings in 60-80s
```

---

## Understanding Test Output

### Success Example
```
server/tests/test_validators/test_constraints.py::TestConstraintValidator::test_coordination_exact_match PASSED [  3%]
```
- `PASSED` = Test succeeded
- `[3%]` = Progress indicator

### Expected Warnings

#### Warning 1: CrystalNN radius
```
UserWarning: CrystalNN: cannot locate an appropriate radius,
covalent or atomic radii will be used
```
- **Trigger**: Small molecules (H2O) or primitive cells
- **Why it's OK**: CrystalNN designed for crystals, falls back to covalent radii for molecules
- **Impact**: None - fallback method works correctly

#### Warning 2: Openbabel missing
```
RuntimeWarning: Molecule naming requires openbabel to be installed
with Python bindings.
```
- **Trigger**: Analyzing molecular structures
- **Why it's OK**: openbabel is optional, only for molecule naming
- **Impact**: None - geometry analysis works without it
- **Fix (optional)**: `pip install openbabel-python`

#### Warning 3: Matminer fingerprint
```
UserWarning: CrystalNN: cannot locate an appropriate radius...
```
- **Trigger**: Robocrys internal fingerprint calculation
- **Why it's OK**: Same as Warning 1, internal to robocrys
- **Impact**: None - OP calculations unaffected

### Failure Indicators

If you see:
```
FAILED server/tests/test_validators/test_constraints.py::test_name
ERROR collecting server/tests/test_validators/test_constraints.py
```

**Common causes**:
1. **ModuleNotFoundError**: Missing `PYTHONPATH=.`
   - Fix: `PYTHONPATH=. pytest ...`

2. **ImportError**: Missing dependencies
   - Fix: `pip install -r requirements.txt`

3. **AssertionError**: Code change broke test
   - Fix: Check test expectations vs actual behavior

---

## Performance Benchmarks

| Structure Size | Analysis Time | Use Case |
|---|---|---|
| Primitive cell (<10 atoms) | 1-5s | ✅ LLM iterative feedback |
| Small supercell (10-20 atoms) | 5-30s | ✓ Acceptable |
| 2x2x2 supercell (40+ atoms) | 60-180s | ⚠️ Final validation only |

**Total test suite runtime**:
- Fast machine: ~2 minutes
- Average machine: ~2.5 minutes
- Slow machine: ~3-4 minutes

**Variance**: ±20% is normal due to robocrystallographer's complexity

---

## Interpreting Results

### All Tests Passed ✅
```
================= 29 passed, 20 warnings in 153.54s ==================
```
- **Status**: ✅ Validation system fully functional
- **Action**: None required
- **Warnings**: Expected and documented

### Some Tests Failed ❌
```
================= 25 passed, 4 failed in 160.32s ==================
```
- **Status**: ❌ Code changes broke functionality
- **Action**:
  1. Review failed test names
  2. Check test output for AssertionError details
  3. Compare expected vs actual values
  4. Fix code or update test expectations

### Import Errors 🚫
```
ERROR collecting server/tests/test_validators/test_constraints.py
ModuleNotFoundError: No module named 'server'
```
- **Status**: ❌ Environment setup issue
- **Action**: Use `PYTHONPATH=. pytest ...`

---

## Advanced Usage

### Run Specific Test
```bash
PYTHONPATH=. pytest server/tests/test_validators/test_constraints.py::TestConstraintValidator::test_coordination_exact_match -v
```

### Show Print Statements
```bash
PYTHONPATH=. pytest server/tests/test_validators/ -v -s
```

### Short Traceback
```bash
PYTHONPATH=. pytest server/tests/test_validators/ -v --tb=short
```

### Stop on First Failure
```bash
PYTHONPATH=. pytest server/tests/test_validators/ -v -x
```

### Generate Test Report
```bash
PYTHONPATH=. pytest server/tests/test_validators/ -v --tb=short > test_report.txt 2>&1
```

### Run with Coverage
```bash
PYTHONPATH=. pytest server/tests/test_validators/ --cov=server/core/validators --cov-report=html
```

---

## Validation Workflow

### For Development
1. Make code changes
2. Run affected test suite: `pytest test_constraints.py -v`
3. Fix any failures
4. Run full suite: `pytest server/tests/test_validators/ -v`
5. Commit only if all tests pass

### For Release Verification
1. Clean environment: `rm -rf __pycache__ .pytest_cache`
2. Run full suite: `PYTHONPATH=. pytest server/tests/test_validators/ -v`
3. Verify: 29/29 passed
4. Document any new warnings
5. Update test report if needed

### For New Features
1. Write tests first (TDD)
2. Run tests (should fail initially)
3. Implement feature
4. Run tests until all pass
5. Add test documentation to `PHASE1_TEST_REPORT.md`

---

## Common Issues

### Issue 1: Tests pass but warnings increase
**Symptom**: Test count same, but 30 warnings instead of 20
**Cause**: New test structures triggering CrystalNN warnings
**Fix**: Document expected warning count in test docstring

### Issue 2: Slow test execution (>5 minutes)
**Symptom**: Tests taking much longer than expected
**Cause**: Large structures or supercells in tests
**Fix**: Use primitive cells for tests, document performance expectations

### Issue 3: Flaky tests (sometimes pass, sometimes fail)
**Symptom**: Same test passes/fails intermittently
**Cause**: Floating-point comparison without tolerance
**Fix**: Use `pytest.approx()` for float comparisons

---

## Test Data

### Structures Used
- **FCC Copper**: 2x2x2 supercell, cuboctahedral coordination
- **FCC Aluminum**: 2x2x2 supercell, for comparison tests
- **H2O Molecule**: 0D structure, dimensionality tests
- **Distorted structures**: Programmatically perturbed for tolerance tests

### No External Dependencies
- All test structures generated programmatically
- No need to download MP structures for unit tests
- MP structures only for examples (optional)

---

## Verification Checklist

After running tests, verify:

- [ ] 29/29 tests passed
- [ ] ~20 warnings (all documented as expected)
- [ ] Runtime: 2-4 minutes
- [ ] No ERROR or FAILED messages
- [ ] Warnings are UserWarning/RuntimeWarning (not Errors)

---

## Getting Help

### Test Documentation
- Detailed test descriptions: `docs/validation/PHASE1_TEST_REPORT.md`
- Implementation summary: `docs/validation/PHASE1_SUMMARY.md`
- Design rationale: `docs/validation/VALIDATION_DESIGN.md`

### Recent Test Outputs
- Full output: `docs/validation/pytest_output_detailed.txt`
- Test list: `docs/validation/pytest_test_list.txt`

### Example Usage
- Basic validation: `examples/validation_examples/basic_validation.py`
- Tolerance demo: `examples/validation_examples/phase1_tolerance_demo.py`
- Examples README: `examples/validation_examples/README.md`

---

**Last Updated**: 2025-10-01
**Test Suite Version**: Phase 1 Complete (29 tests)
**Expected Runtime**: ~2.5 minutes (147-180 seconds)
