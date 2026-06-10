# Kernel Test Validator Guide

## Overview

The `kernel-test-validator` skill validates kernel bug reproduction cases by compiling and testing in QEMU. It acts as a **kernel testing expert** that bridges kernel experts and automated testing.

## Purpose

1. Receive reproduction cases from kernel experts
2. Compile kernels with provided patches/configs
3. Test in QEMU virtual machines
4. Analyze results to determine if bug reproduces
5. Provide structured feedback for iteration

## Installation

This skill is integrated into the Analysis-SKILL project:

```bash
bash scripts/install.sh
```

## Usage

### Basic Invocation

```
/kernel-test-validator <case_file_or_description>
```

### Example 1: YAML Case File

Create a reproduction case file:

```yaml
# reproduction_case.yaml
case_id: "JFFS2-STRESS-001"
description: "JFFS2 filesystem corruption under concurrent write stress"
architecture: arm64
patches:
  - patches/jffs2_stress.patch
configs:
  - CONFIG_JFFS2_FS=m
  - CONFIG_DEBUG_FS=y
  - CONFIG_PANIC_ON_OOPS=y
test_script: tests/jffs2_concurrent_write.sh
expected_result: "Kernel panic with JFFS2 corruption message"
timeout: 180
```

Invoke:

```bash
/kernel-test-validator reproduction_case.yaml
```

### Example 2: Inline Chinese Description

```
/kernel-test-validator "复现用例：
- 补丁：添加 UB subsystem stress test 补丁（见 patches/ub_stress.patch）
- 配置：启用 CONFIG_UB=y, CONFIG_DEBUG_FS=y
- 测试：运行 tests/ub_crash.sh 脚本
- 预期：应触发 UB panic 错误信息
- 架构：arm64
- 超时：180秒"
```

### Example 3: Minimal Verification

```
/kernel-test-validator "Verify patches/kernel_panic.patch causes panic on arm64"
```

## Workflow

```
Input: Reproduction Case
  ↓
Step 1: Parse & Validate Case
  ↓
Step 2: Compile Kernel (via kernel-build)
  ↓
Step 3: Test in QEMU (via qemu-test)
  ↓
Step 4: Analyze Results
  ↓
Output: Validation Report
```

## Report Types

### Success Report

When bug is reproduced:

```
✓ SUCCESSFULLY REPRODUCED

Case ID: JFFS2-STRESS-001
Architecture: arm64

Evidence:
- Kernel panic triggered at fs/jffs2/write.c:89
- Log: "JFFS2: corruption detected in node 0x1234"

Test Duration: 45 seconds
Build Time: 3m 20s

Artifacts:
- Kernel Image: validation_outputs/JFFS2-STRESS-001/build/kernel_image
- Boot Log: validation_outputs/JFFS2-STRESS-001/test/boot.log
- Applied Patches: validation_outputs/JFFS2-STRESS-001/build/applied_patches.diff
```

### Failure Report

When bug is NOT reproduced:

```
✗ VALIDATION FAILED

Case ID: JFFS2-STRESS-001

Failure Analysis:
- Expected: "JFFS2 panic message"
- Observed: Clean boot, no errors

Recommendations for Kernel Expert:

1. Patch Issues:
   - Verify patch compatibility with kernel version 6.6
   - Check for missing dependencies

2. Config Issues:
   - CONFIG_JFFS2_FS=m may need CONFIG_JFFS2_FS_WRITEBUFFER=y
   - Add CONFIG_DEBUG_JFFS2=y for detailed logging

3. Test Method Issues:
   - Test timeout (60s) insufficient for stress test
   - Increase concurrent threads in test script

Please revise case with these suggestions.
```

## Integration with Other Skills

This skill depends on:

- `/kernel-build` - Kernel compilation
- `/qemu-test` - QEMU testing

**Workflow Order**:
1. `kernel-test-validator` parses the case
2. Invokes `/kernel-build` to compile
3. Invokes `/qemu-test` to test
4. `kernel-test-validator` analyzes results

## Supported Input Formats

| Format | Example | Use Case |
|--------|---------|----------|
| **YAML** | `case.yaml` | Structured, complete cases |
| **Inline Chinese** | `"复现用例：..."` | Quick, flexible input |
| **Minimal** | `"Verify patch X"` | Simple patch verification |

## Key Features

### Multi-Patch Handling

Apply patches in sequence:

```yaml
patches:
  - 0001_base_fix.patch
  - 0002_stress_test.patch
  - 0003_debug_output.patch
```

### Cross-Compilation

Automatic detection:

```yaml
architecture: arm32
defconfig: bcm2835_defconfig
```

Skill auto-detects cross-compilation from x86_64 host.

### Config Dependency Resolution

User provides `CONFIG_JFFS2_FS=m`, skill adds:

```
CONFIG_JFFS2_FS=m
CONFIG_JFFS2_FS_WRITEBUFFER=y  # Auto-detected dependency
CONFIG_FSI=y                   # Auto-detected dependency
```

## Output Structure

```
validation_outputs/
├── {case_id}/
│   ├── report.md             # Validation report
│   ├── build/
│   │   ├── kernel_image      # Compiled kernel
│   │   ├── applied_patches.diff
│   │   ├── build.log
│   │   └── config.txt        # Final .config
│   ├── test/
│   │   ├── boot.log          # QEMU output
│   │   ├── test_result.log   # Test results
│   │   ├── initramfs.cpio.gz
│   │   └── test_script.sh
│   └── artifacts/
│       ├── modules/          # Kernel modules
│       └── summary.txt       # Quick summary
```

## Best Practices

### For Kernel Experts (Input)

Provide clear cases:
1. Specify kernel version explicitly
2. List all configs including dependencies
3. Define expected result precisely (error message pattern)
4. Provide standalone test scripts
5. Include timeout estimates

### For Validation Skill (Output)

Generate actionable reports:
1. Clear success/failure status
2. Evidence excerpts from logs
3. Specific failure reasons
4. Concrete suggestions
5. All artifacts saved for review

## Error Handling

### Build Errors

**Patch Failed**:
```
ERROR: Patch application failed
Patch: patches/test.patch
Suggestions:
- Verify kernel version compatibility
- Check patch format
```

**Compilation Failed**:
```
ERROR: Kernel build failed
Location: fs/jffs2/super.c:245
Suggestions:
- Check missing dependencies
- Review CONFIG options
```

### Test Errors

**QEMU Boot Failed**:
```
ERROR: QEMU failed to boot
Suggestions:
- Check architecture compatibility
- Verify initramfs
```

**Timeout**:
```
WARNING: Test timeout (300s)
Suggestions:
- Increase timeout
- Check for hanging script
```

## Advanced Usage

### Pre-built Kernel

Skip compilation phase:

```bash
/kernel-test-validator --kernel arch/arm64/boot/Image test_script.sh
```

### Interactive Mode

For debugging:

```bash
/kernel-test-validator --interactive reproduction_case.yaml
```

### Custom Defconfig

```yaml
defconfig: bcm2835_defconfig  # ARM32 Raspberry Pi
architecture: arm32
```

## Summary

- **Role**: Kernel testing expert
- **Input**: Reproduction cases (patches, configs, tests)
- **Output**: Validation reports + feedback
- **Tools**: kernel-build + qemu-test
- **Goal**: Iterate until bug reproduces

Use this skill to validate reproduction cases and provide structured feedback for kernel expert iteration.
