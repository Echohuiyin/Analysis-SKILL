# Kernel Skills Integration Guide

## Overview

Two kernel skills work together to form a complete problem reproduction workflow:

1. **kernel-testcase-generator**: Kernel expert - constructs reproduction cases
2. **kernel-test-validator**: Testing expert - validates reproduction cases

## Skill Roles

### kernel-testcase-generator (Kernel Expert)

**Role**: Kernel problem analysis expert specializing in reproduction case construction

**Input**:
- Vmcore crash analysis results (`/vmcore-analyzer`)
- Lock analysis results (`/lock-analyzer`)
- Knowledge base search results (`/rag-case-retrieval`)
- Kernel log analysis (dmesg, kernel messages)

**Output**:
- Reproducible test case code (kernel module / user program)
- Build scripts (Makefile, build instructions)
- README with usage instructions

**Self-Verification**:
- Compilation check (required)
- Basic functionality check (load/unload for module, basic run for program)
- **NOT full testing** - just sanity check

**Key Principle**: "Trigger Expected Bug, Avoid Side Effects"
- Trigger the EXACT bug identified in analysis
- Don't introduce random bugs from coding errors

### kernel-test-validator (Testing Expert)

**Role**: Kernel testing expert specializing in reproduction validation

**Input**:
- Reproduction cases from kernel-testcase-generator
- Or cases from other kernel experts

**Output**:
- Validation report (success/failure)
- Evidence of reproduction (logs, crash details)
- Actionable feedback for iteration

**Validation Process**:
- Parse reproduction case
- Compile kernel with patches/configs (`/kernel-build`)
- Test in QEMU (`/qemu-test`)
- Analyze results against expected behavior
- Generate structured report

**Key Outputs**:
- **Success**: Reproduction evidence + process documentation
- **Failure**: Root cause analysis + recommendations for kernel expert

## Collaboration Workflow

### Standard Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Problem Analysis Phase                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
        /vmcore-analyzer (analyze crash dump)
                              ↓
        /lock-analyzer (if lock-related issue)
                              ↓
        /rag-case-retrieval (search similar cases)
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   Case Construction Phase                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
        /kernel-testcase-generator
                              ↓
        Output: reproduction_case/
          ├── reproducer.c (test code)
          ├── Makefile
          ├── README.md
          └── verification.log (self-check)
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                     Validation Phase                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
        /kernel-test-validator
                              ↓
        Validation Report:
          ✓ SUCCESS - bug reproduced
          ✗ FAILURE - needs iteration
                              ↓
        If FAILURE → feedback to testcase-generator
                              ↓
        Iterate until SUCCESS
```

### Iteration Loop

```
testcase-generator → produces case → test-validator validates

If validation FAILS:
  ↓
Validator provides feedback:
  - Missing config options
  - Timeout issues
  - Test method problems
  - Patch compatibility issues
  ↓
testcase-generator refines case
  ↓
test-validator re-validates
  ↓
Repeat until SUCCESS or clear blocker
```

## Interface Contract

### From testcase-generator to test-validator

**Expected Output Format**:

```yaml
# reproduction_case.yaml
case_id: "BUG-001-from-vmcore-analysis"
description: "Mutex deadlock in subsystem X"
source: "vmcore-analysis-2026-06-10"
architecture: arm64

# Generated test case
test_case_type: "kernel_module"  # or "user_program" or "combined"
patches:
  - reproducer.patch  # The generated test module
configs:
  - CONFIG_TEST_MODULE=y  # If needs special config
  - CONFIG_DEBUG_FS=y

# Test method
test_script: tests/run_reproducer.sh  # If needed
test_command: "dmesg | grep DEADLOCK"  # Expected check
expected_result: "Should trigger hung task deadlock within 30 seconds"
timeout: 60

# Metadata
generator_verification: "passed"  # Basic check done
generator_notes: "Self-verification: module loads/unloads cleanly"
```

### From test-validator back to testcase-generator (on failure)

**Feedback Format**:

```markdown
# Validation Feedback Report

## Case ID: BUG-001-from-vmcore-analysis

## Status: FAILED

## Failure Reasons

1. **Config Issues**:
   - Missing: CONFIG_LOCKDEP=y (needed for deadlock detection)
   - Missing: CONFIG_DEBUG_LOCK_ALLOC=y

2. **Test Method Issues**:
   - Timeout 60s too short for deadlock to trigger
   - Suggest: increase to 120s or add explicit trigger

3. **Expected Result Issues**:
   - Pattern "DEADLOCK" not appearing in dmesg
   - Actual: "hung task blocked for 120s"
   - Suggest: update expected pattern to match kernel message

## Recommendations

1. Add configs: CONFIG_LOCKDEP=y, CONFIG_DEBUG_LOCK_ALLOC=y
2. Increase timeout to 120 seconds
3. Update expected pattern to "hung task"
4. Add debug output in reproducer module

## Artifacts for Review

- Boot log: validation_outputs/BUG-001/test/boot.log
- Test result: validation_outputs/BUG-001/test/test_result.log

---
Please refine reproduction case based on above feedback.
```

## Skill Integration Points

### 1. kernel-build Integration

Both skills use `/kernel-build`:

- **testcase-generator**: For basic verification (compile test module)
- **test-validator**: For full kernel compilation with patches

**Usage**:
```
/kernel-build TEST_MODULE DEBUG_FS --arch arm64
```

### 2. qemu-test Integration

Only **test-validator** uses `/qemu-test`:

- testcase-generator does NOT run QEMU testing
- test-validator runs full QEMU validation

**Usage**:
```
/qemu-test --arch arm64 --script tests/reproducer.sh --timeout 120
```

### 3. Analysis Skills Integration

**testcase-generator** uses analysis skills:
- `/vmcore-analyzer` → extract root cause
- `/lock-analyzer` → understand lock contention
- `/rag-case-retrieval` → check similar historical cases

**test-validator** does NOT use analysis skills (works on provided cases)

## Example End-to-End Scenario

### Scenario: Mutex Deadlock from Vmcore

**Step 1: Problem Analysis**

```bash
# User provides vmcore
/vmcore-analyzer vmcore

# Analysis results:
- Crash type: hung task
- Blocked threads: 2 threads blocked on mutexes
- Deadlock chain: task1 holds mutexA waits mutexB, task2 holds mutexB waits mutexA
- Root cause: lock order violation in subsystem X
```

**Step 2: Case Generation**

```bash
/kernel-testcase-generator

# Input: vmcore analysis results
# Output: mutex_deadlock_reproducer/
#   ├── reproducer.c (kernel module with two threads)
#   ├── Makefile
#   ├── README.md
#   └── verification.log (module loads/unloads ✓)
```

**Step 3: Validation**

```bash
/kernel-test-validator mutex_deadlock_reproducer.yaml

# Input: generated reproduction case
# Process:
#   1. Parse case
#   2. /kernel-build LOCKDEP DEBUG_LOCK_ALLOC --arch arm64
#   3. /qemu-test --script run_deadlock_test.sh --timeout 120
#   4. Analyze: "hung task" appears ✓

# Output: Validation Report (SUCCESS)
#   - Evidence: "hung task blocked for >120s"
#   - Logs: boot.log shows deadlock messages
#   - Conclusion: Bug successfully reproduced
```

### Scenario: Race Condition (Iteration Required)

**Step 1-2: Same as above**

```bash
/vmcore-analyzer → /kernel-testcase-generator → race_condition_reproducer/
```

**Step 3: Validation (Round 1 - FAILED)**

```bash
/kernel-test-validator race_condition_reproducer.yaml

# Result: ✗ FAILED
#   - Expected: "race condition detected"
#   - Observed: clean boot, no race messages
#   - Reason: CONFIG_DEBUG_ATOMIC_SLEEP not enabled
#   - Timeout too short (10s), race takes longer to trigger
```

**Step 4: Iteration**

```bash
/kernel-testcase-generator

# Input: validator feedback
#   - Add CONFIG_DEBUG_ATOMIC_SLEEP=y
#   - Increase timeout to 30s
#   - Add debug output in race thread

# Output: race_condition_reproducer_v2/
```

**Step 5: Validation (Round 2 - SUCCESS)**

```bash
/kernel-test-validator race_condition_reproducer_v2.yaml

# Result: ✓ SUCCESS
#   - Evidence: "race condition detected in counter increment"
#   - Logs: shows concurrent updates without lock
```

## Best Practices

### For testcase-generator

1. **Clear case metadata**: Include case_id, description, source analysis
2. **Minimal self-verification**: Don't over-verify, leave full testing to validator
3. **Document design rationale**: Why this reproducer type, why these configs
4. **Provide test method suggestions**: How validator should test
5. **Include expected patterns**: Exact kernel messages to look for

### For test-validator

1. **Structured feedback**: Clear categories (config/test/patch issues)
2. **Specific recommendations**: Concrete config values, timeout numbers
3. **Evidence-based analysis**: Quote exact log excerpts
4. **Actionable suggestions**: Not generic "fix it", but "add CONFIG_X=y"
5. **Save all artifacts**: For generator to review

### For Workflow Integration

1. **Pass metadata through**: case_id, source analysis, generator notes
2. **Use standard format**: YAML case files for consistency
3. **Iteration tracking**: Version cases (v1, v2, v3) for iteration
4. **Clear handoff points**: Generator completes → Validator starts
5. **Feedback loop**: Validator → Generator → Validator until success

## Skill Dependencies Summary

```
testcase-generator dependencies:
  ├─ /vmcore-analyzer (input)
  ├─ /lock-analyzer (input)
  ├─ /rag-case-retrieval (input)
  └─ /kernel-build (for self-verification)

test-validator dependencies:
  ├─ testcase-generator output (input)
  ├─ /kernel-build (required)
  └─ /qemu-test (required)
```

## Summary

- **testcase-generator**: Expert in understanding and constructing
- **test-validator**: Expert in testing and validating
- **Workflow**: Analysis → Generate → Validate → Iterate
- **Goal**: Reliable reproduction with minimal iteration
- **Integration**: Standard YAML format, structured feedback, clear handoffs
