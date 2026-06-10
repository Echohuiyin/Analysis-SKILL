# Kernel Deadlock Reproduction Scenario

This example demonstrates the collaboration between `kernel-testcase-generator` and `kernel-test-validator`.

## Problem Description

**Original Issue**: Kernel hung task detected in production environment

**Symptoms**:
- System hang with 2 processes blocked
- Vmcore captured shows mutex deadlock
- Subsystem: filesystem cache manager

## Step 1: Problem Analysis (vmcore-analyzer)

### Input
```
Vmcore file: /data/crash-dumps/2026-06-10/hung_task.vmcore
```

### Command
```bash
/vmcore-analyzer /data/crash-dumps/2026-06-10/hung_task.vmcore
```

### Analysis Results (Simulated)

```markdown
# Vmcore Analysis Report

## Crash Information
- **Type**: Hung task (blocked for >120s)
- **Kernel**: 6.6.0-openeuler
- **Architecture**: ARM64

## Blocked Tasks

### Task 1: cache_flush_worker (PID 1234)
- **State**: UNINTERRUPTIBLE
- **Blocked on**: mutex_cache_write (waiting)
- **Holding**: mutex_cache_read
- **Call trace**:
  ```
  mutex_lock(&mutex_cache_write)  ← blocked here
  flush_cache_entries()
  cache_flush_worker()
  ```

### Task 2: cache_read_worker (PID 1235)
- **State**: UNINTERRUPTIBLE
- **Blocked on**: mutex_cache_read (waiting)
- **Holding**: mutex_cache_write
- **Call trace**:
  ```
  mutex_lock(&mutex_cache_read)  ← blocked here
  read_cache_data()
  cache_read_worker()
  ```

## Root Cause

**Deadlock due to lock order violation**:
- Task 1: acquires mutex_cache_read → tries mutex_cache_write
- Task 2: acquires mutex_cache_write → tries mutex_cache_read
- **Classic ABBA deadlock pattern**

## Recommendations

1. Fix lock ordering: always acquire in same order (read → write)
2. Add lockdep validation
3. Create reproducer for testing
```

## Step 2: Case Construction (kernel-testcase-generator)

### Input to Generator

The vmcore analysis results above.

### Command
```bash
/kernel-testcase-generator

# User provides:
Input: vmcore_analysis_results (from Step 1)
Output directory: examples/kernel-deadlock-scenario/generated_case/
```

### Generated Output

See `generated_case/` directory for:
- `reproducer.c` - Kernel module creating ABBA deadlock
- `Makefile` - Build script
- `README.md` - Usage instructions
- `case.yaml` - Standard case format for validator
- `verification.log` - Self-verification results

### Generator's Design Decisions

1. **Reproducer Type**: Kernel module
   - Rationale: Direct control over mutex acquisition timing
   
2. **Configs**: CONFIG_LOCKDEP=y
   - Rationale: Enable lock dependency validation
   
3. **Expected Pattern**: "hung task blocked for >120s"
   - Rationale: Match kernel's hung task detection message

4. **Timeout**: 150 seconds
   - Rationale: Kernel's hung task timeout is 120s, add buffer

## Step 3: Validation (kernel-test-validator)

### Input to Validator

The `case.yaml` file from generator.

### Command
```bash
/kernel-test-validator examples/kernel-deadlock-scenario/generated_case/case.yaml
```

### Validation Process

```
1. Parse case → Extract parameters
   ✓ case_id: CACHE-DEADLOCK-001
   ✓ architecture: arm64
   ✓ reproducer: cache_deadlock_module.ko
   ✓ configs: CONFIG_LOCKDEP=y
   ✓ expected: "hung task blocked"
   ✓ timeout: 150s

2. Compile kernel (/kernel-build)
   ✓ CONFIG_LOCKDEP=y enabled
   ✓ CONFIG_DEBUG_MUTEXES=y (auto-added)
   ✓ Kernel compiled successfully
   ✓ reproducer.ko built

3. Test in QEMU (/qemu-test)
   ✓ Boot kernel with configs
   ✓ Load reproducer module
   ✓ Run for 150 seconds
   ✓ Collect boot.log

4. Analyze results
   ✓ Pattern found: "hung task: cache_thread1 blocked for >120s"
   ✓ Pattern found: "hung task: cache_thread2 blocked for >120s"
   ✓ Lockdep warning: "possible circular locking dependency detected"
   
   Result: ✓ REPRODUCED
```

### Validation Report

See `validation_report.md` in `validation_outputs/CACHE-DEADLOCK-001/` directory.

## Iteration Example (If Validation Failed)

### Round 1 Failure (Hypothetical)

```markdown
# Validation Failed

Case ID: CACHE-DEADLOCK-001

## Failure Reasons

1. **Config Issues**:
   - Missing CONFIG_LOCKDEP=y
   - Kernel compiled without lock validation
   
2. **Test Method Issues**:
   - Timeout 60s too short (kernel hung task timeout is 120s)
   - Need at least 150s for detection
   
3. **Expected Pattern Issues**:
   - Looking for "deadlock detected"
   - Actual message: "hung task blocked"
   - Pattern mismatch

## Recommendations

1. Add CONFIG_LOCKDEP=y to case
2. Increase timeout to 150s
3. Update expected pattern to "hung task"
```

### Round 2 Success (After Iteration)

```markdown
# Validation Success

Case ID: CACHE-DEADLOCK-001-v2

## Reproduction Evidence

**Logs**:
```
[  120.123] hung task: cache_thread1 blocked for >120s
[  120.456] hung task: cache_thread2 blocked for >120s
[  121.789] lockdep: circular locking dependency detected
```

**Analysis**:
- ✓ Deadlock triggered as expected
- ✓ Hung task detected by kernel
- ✓ Lockdep correctly identified circular dependency
- ✓ Matches root cause from vmcore analysis

## Conclusion

Bug successfully reproduced. Reproduction process verified.

## Artifacts
- Boot log: validation_outputs/CACHE-DEADLOCK-001-v2/test/boot.log
- Kernel image: validation_outputs/CACHE-DEADLOCK-001-v2/build/kernel_image
- Applied reproducer: validation_outputs/CACHE-DEADLOCK-001-v2/build/reproducer.ko
```

## Skills Collaboration Summary

```
vmcore-analyzer (analysis)
      ↓
  Analysis results
      ↓
kernel-testcase-generator (construction)
      ↓
  Reproduction case (reproducer code + case.yaml)
      ↓
kernel-test-validator (validation)
      ↓
  ✓ SUCCESS → Done
  ✗ FAILURE → Feedback → generator refines → validator re-tests
```

## Key Points

1. **Role Separation**:
   - Generator: Expert in understanding and constructing
   - Validator: Expert in testing and validating

2. **Handoff Interface**:
   - Standard YAML format (case.yaml)
   - Structured metadata (case_id, configs, expected patterns)

3. **Iteration Loop**:
   - Validator provides specific feedback
   - Generator refines based on feedback
   - Repeat until success

4. **Integration Skills**:
   - Both use `/kernel-build`
   - Validator uses `/qemu-test`
   - Generator uses analysis skills as input

## Files in This Example

```
examples/kernel-deadlock-scenario/
├── scenario_description.md       (this file)
├── generated_case/                (generator output)
│   ├── reproducer.c               (test module code)
│   ├── Makefile                   (build script)
│   ├── README.md                  (usage instructions)
│   ├── case.yaml                  (standard case format)
│   └── verification.log           (self-check results)
└── validation_outputs/            (validator output)
    └── CACHE-DEADLOCK-001/
        ├── report.md              (validation report)
        ├── build/
        │   ├── kernel_image
        │   ├── reproducer.ko
        │   └── applied_patches.diff
        └── test/
            ├── boot.log           (QEMU output)
            ├── test_result.log
            └── summary.txt
```
