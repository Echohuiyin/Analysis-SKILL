# Kernel Build & QEMU Test Skills

This repository contains Claude Code skills for building and testing Linux kernels with QEMU virtualization.

## Overview

Two complementary skills for kernel development workflow:

- **kernel-build**: Compile Linux kernels with custom configurations
- **qemu-test**: Boot kernels in QEMU for testing and verification

## Skills

### kernel-build Skill

Build the OLK-6.6 Linux kernel with custom CONFIG options.

**Key Features**:
- ARM64/ARM32/x86_64 architecture support
- Native and cross-compilation
- Automatic toolchain detection
- openeuler_defconfig base configuration

**Usage**:
```
/kernel-build <config-options> [--arch <arch>] [--cross] [--jobs <N>]
```

**Examples**:
```
/kernel-build CONFIG_JFFS2_FS=m --arch arm64 --cross
/kernel-build UB XCU_SCHEDULER --arch x86_64 --jobs 32
/kernel-build ARM64_MPAM --arch arm64 --cross --jobs 64
```

**Output**:
- Kernel Image (arch/arm64/boot/Image, arch/x86/boot/bzImage)
- Kernel Modules (*.ko files)

**Important**: Kernel and modules must be compiled in the SAME build session to ensure version matching.

### qemu-test Skill

Boot kernels in QEMU and run automated tests.

**Key Features**:
- Multi-architecture QEMU support (ARM64/ARM32/x86_64)
- Minimal initramfs creation with busybox
- Module loading tests
- Automated test script execution

**Usage**:
```
/kemu-test --arch arm64 --kernel <path> --modules <path> [--script <path>]
```

**Examples**:
```
/qemu-test --arch arm64 --interactive
/qemu-test --script tests/jffs2_test.sh --timeout 60
/qemu-test --kernel arch/x86/boot/bzImage --arch x86_64
```

## Workflow Example

Complete build and test cycle:

```
# Step 1: Build kernel with module
/kernel-build JFFS2_FS --arch arm64 --cross

# Step 2: Test in QEMU
/qemu-test --arch arm64 --kernel arch/arm64/boot/Image --modules fs/jffs2/jffs2.ko
```

## Installation

### Prerequisites

**Build Requirements**:
- GCC toolchain (native or cross)
- Kernel source code (OLK-6.6)
- Build dependencies: bc, bison, flex, libssl-dev

**QEMU Requirements**:
- qemu-system-aarch64 (ARM64)
- qemu-system-arm (ARM32)
- qemu-system-x86_64 (x86_64)
- ARM64 static busybox for cross-architecture testing

**Cross-Compilation Toolchain** (Ubuntu/Debian):
```bash
sudo apt install gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu  # ARM64
sudo apt install gcc-arm-linux-gnueabi binutils-arm-linux-gnueabi  # ARM32
```

**QEMU Installation**:
```bash
sudo apt install qemu-system-arm qemu-system-x86
```

### Installing Skills

Copy skill directories to Claude Code skills directory:
```bash
mkdir -p ~/.claude/skills
cp -r skills/kernel-build ~/.claude/skills/
cp -r skills/qemu-test ~/.claude/skills/
```

## Directory Structure

```
Analysis-SKILL/
├── README.md                       # This file
├── skills/
│   ├── kernel-build/
│   │   ├── SKILL.md                # Skill definition
│   │   ├── OPTIMIZATION_SUMMARY.md # Build optimizations
│   │   └── VALIDATION_REPORT.md    # Validation results
│   └── qemu-test/
│       ├── SKILL.md                # Skill definition
│       ├── scripts/                # Helper scripts
│       │   ├── create_initramfs.sh
│       │   ├── boot_arm64.sh
│       │   ├── boot_arm32.sh
│       │   ├── boot_x86.sh
│       │   └── run_test.sh
│       └── references/
│           └── arch_configs.md     # Architecture-specific configs
├── docs/
│   ├── E2E_VERIFICATION_REPORT.md  # End-to-end test report
│   └── cross_arch_busybox_analysis.md  # Busybox cross-arch solution
└── tools/                          # Additional utilities
```

## Key Technical Notes

### Version Matching

**Critical**: Kernel and modules must have matching vermagic.

Problem example:
```
Kernel:  6.6.0-36583-g6cf1cf61b43c-dirty
Module:  6.6.0+ (vermagic mismatch)
Result:  insmod fails with "invalid module format"
```

Solution: Build kernel and modules in single session (kernel-build skill does this correctly).

### MTD Dependency for JFFS2

JFFS2 requires MTD subsystem:
```
# Load MTD first, then JFFS2
insmod mtd.ko
insmod jffs2.ko
```

### Cross-Architecture Busybox

ARM64 QEMU requires ARM64-compiled busybox:
```
# Cross-compile busybox for ARM64
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- defconfig
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j$(nproc)
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- install
```

Result: ARM64 static busybox (~969K)

## Testing Examples

### JFFS2 Module Test

Build and test JFFS2 filesystem module:
```bash
# Build
/kernel-build JFFS2_FS --arch arm64 --cross

# Test
/qemu-test --arch arm64 --script tests/jffs2_load.sh
```

Expected output:
```
✓ mtd.ko loaded
✓ jffs2.ko loaded successfully
jffs2 147456 0 - Live 0xffffad6d0ec8a000
```

## Documentation

- **skills/kernel-build/SKILL.md**: Complete kernel-build skill definition
- **skills/qemu-test/SKILL.md**: Complete qemu-test skill definition
- **docs/E2E_VERIFICATION_REPORT.md**: ARM64 end-to-end verification report
- **docs/cross_arch_busybox_analysis.md**: Cross-architecture busybox solution

## Contributing

To add new skills or improve existing ones:
1. Create skill directory under `skills/<skill-name>/`
2. Add SKILL.md with skill definition (frontmatter + content)
3. Include supporting scripts in `scripts/` subdirectory
4. Add documentation in `docs/`
5. Update README.md

## License

OpenEuler Linux Kernel (OLK-6.6) follows GPL v2 license.
Skills and tools in this repository are provided under MIT license.

## Authors

- Kernel Build Skill: Developed for OLK-6.6 cross-compilation workflow
- QEMU Test Skill: Created for kernel verification automation
- End-to-end validation: Completed 2026-05-18

## References

- OLK-6.6 Repository: openEuler Linux Kernel 6.6
- Kernel Documentation: Documentation/process/coding-style.rst
- QEMU Documentation: https://www.qemu.org/docs/