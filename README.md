# Kernel Analysis Skills Collection

This repository contains Claude Code skills for kernel compilation, QEMU testing, and JFFS2 filesystem analysis.

## Overview

Four independent and decoupled skills for kernel development workflow:

- **kernel-build**: Compile Linux kernels with custom configurations
- **qemu-test**: Boot kernels in QEMU for testing and verification
- **jffs2-analyzer**: Static analysis of JFFS2 filesystem images
- **jffs2-mount**: Mount JFFS2 images in QEMU for dynamic verification

All skills are **completely decoupled** - each skill operates independently without calling or depending on other skills.

## Skills

### 1. kernel-build Skill

**Location**: `skills/kernel-build/`

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

### 2. qemu-test Skill

**Location**: `skills/qemu-test/`

Boot kernels in QEMU and run automated tests.

**Key Features**:
- Multi-architecture QEMU support (ARM64/ARM32/x86_64)
- Minimal initramfs creation with busybox
- Module loading tests
- Automated test script execution

**Usage**:
```
/qemu-test --arch arm64 --kernel <path> --modules <path> [--script <path>]
```

**Examples**:
```
/qemu-test --arch arm64 --interactive
/qemu-test --script tests/jffs2_test.sh --timeout 60
/qemu-test --kernel arch/x86/boot/bzImage --arch x86_64
```

**Decoupled**: This skill does NOT call kernel-build. It expects user to provide pre-compiled kernel.

### 3. jffs2-analyzer Skill

**Location**: `skills/jffs2-analyzer/`

Static analysis of JFFS2 filesystem images without mounting.

**Key Features**:
- Parse JFFS2 node structures (dirent, inode, data)
- Extract metadata and file information
- Validate node checksums
- No kernel or QEMU required

**Usage**:
```
/jffs2-analyzer <jffs2-image> [--output <dir>] [--verbose]
```

**Examples**:
```
/jffs2-analyzer /path/to/jffs2.img
/jffs2-analyzer test.jffs2 --output analysis_results
```

**Decoupled**: Standalone Python-based analysis, no dependencies on kernel-build or qemu-test.

### 4. jffs2-mount Skill

**Location**: `skills/jffs2-mount/`

Mount JFFS2 filesystem images in QEMU for dynamic verification.

**Key Features**:
- Create JFFS2 test images (mkfs.jffs2 or blank)
- Setup MTD device in QEMU
- Load JFFS2 module and mount filesystem
- Verify mount success and file access

**Usage**:
```
/jffs2-mount --kernel <path> [--image <path>] [--size <MB>] [--mount-test]
```

**Examples**:
```
/jffs2-mount --kernel arch/arm64/boot/Image --mount-test
/jffs2-mount --kernel Image --image custom.jffs2 --arch arm64
/jffs2-mount --kernel bzImage --size 32 --content ./data
```

**Decoupled**: This skill is COMPLETELY INDEPENDENT from:
- kernel-build (requires user-provided kernel)
- qemu-test (has its own QEMU launch logic)
- jffs2-analyzer (complementary - analyze first, then mount)

**Workflow Integration**: Users can combine skills as needed:
```
# Option 1: Full workflow
/kernel-build JFFS2_FS --arch arm64 --cross
/jffs2-analyzer test.jffs2
/jffs2-mount --kernel arch/arm64/boot/Image --image test.jffs2

# Option 2: Each skill independently
/kernel-build UB --arch x86_64           # Just build
/qemu-test --arch arm64 --interactive    # Just boot
/jffs2-analyzer image.jffs2              # Just analyze
/jffs2-mount --kernel Image --mount-test # Just mount
```

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

### Busybox Installation (Critical for QEMU Testing)

The qemu-test skill requires busybox to create minimal initramfs. **For cross-architecture testing, you need architecture-matched busybox.**

#### Native Architecture (Simple Install)

For same-architecture testing (e.g., x86_64 host → x86_64 QEMU):

```bash
# Ubuntu/Debian
sudo apt install busybox-static

# CentOS/RHEL
sudo yum install busybox

# Verify static linking
ldd /bin/busybox
# Expected: "not a dynamic executable" (static)
```

#### Cross-Architecture Busybox Compilation

For cross-architecture testing (e.g., x86_64 host → ARM64/ARM32 QEMU), compile busybox for target architecture:

**Prerequisites**:
```bash
# Download busybox source
wget https://busybox.net/downloads/busybox-1.36.1.tar.bz2
tar -xjf busybox-1.36.1.tar.bz2
cd busybox-1.36.1
```

**ARM64 Busybox**:
```bash
# Configure for ARM64
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- defconfig

# Enable static compilation
sed -i 's/# CONFIG_STATIC is not set/CONFIG_STATIC=y/' .config

# Build
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j$(nproc)

# Result: busybox (ARM64 static, ~969K)
file busybox
# Expected: ELF 64-bit LSB executable, ARM aarch64, version 1 (GNU/Linux), statically linked
```

**ARM32 Busybox**:
```bash
# Configure for ARM32
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabi- defconfig

# Enable static compilation
sed -i 's/# CONFIG_STATIC is not set/CONFIG_STATIC=y/' .config

# Build
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabi- -j$(nproc)

# Result: busybox (ARM32 static, ~900K)
file busybox
# Expected: ELF 32-bit LSB executable, ARM, version 1 (GNU/Linux), statically linked
```

**Installation for QEMU Testing**:
```bash
# Create directory for cross-arch busybox
mkdir -p ~/.local/share/qemu-busybox

# Copy compiled busybox
cp busybox ~/.local/share/qemu-busybox/busybox-arm64  # For ARM64
cp busybox ~/.local/share/qemu-busybox/busybox-arm32  # For ARM32

# Update create_initramfs.sh or use custom busybox path
# Option 1: Set BUSYBOX_PATH environment variable
export BUSYBOX_PATH=~/.local/share/qemu-busybox/busybox-arm64

# Option 2: Modify create_initramfs.sh to detect architecture
```

#### Architecture Compatibility Matrix

| Host Arch | QEMU Arch | Busybox Required | Size |
|-----------|-----------|------------------|------|
| x86_64 | x86_64 | x86_64 (native) | ~1.0M |
| x86_64 | ARM64 | ARM64 (cross-compile) | ~969K |
| x86_64 | ARM32 | ARM32 (cross-compile) | ~900K |
| ARM64 | ARM64 | ARM64 (native) | ~969K |
| ARM32 | ARM32 | ARM32 (native) | ~900K |

#### Common Busybox Issues

**Problem**: x86-64 busybox in ARM64 QEMU
```
/modules/jffs2.ko: line 1: ELF...: not found
insmod: can't insert '/modules/jffs2.ko': exec format error
```

**Solution**: Compile ARM64 static busybox (see above).

**Problem**: Dynamic-linked busybox missing libraries
```
/bin/sh: No such file or directory
init: exec failed: /bin/sh
```

**Solution**: Use static-linked busybox (`CONFIG_STATIC=y`).

### Installing Skills

Copy all 4 skill directories to Claude Code skills directory:
```bash
mkdir -p ~/.claude/skills
cp -r skills/kernel-build ~/.claude/skills/
cp -r skills/qemu-test ~/.claude/skills/
cp -r skills/jffs2-analyzer ~/.claude/skills/
cp -r skills/jffs2-mount ~/.claude/skills/
```

**Verification**:
```bash
ls ~/.claude/skills/
# Expected: kernel-build qemu-test jffs2-analyzer jffs2-mount
```

## Directory Structure

```
Analysis-SKILL/
├── README.md                       # This file (updated 2026-05-18)
├── skills/
│   ├── kernel-build/               # Skill 1: Kernel compilation
│   │   ├── SKILL.md                # Skill definition
│   │   ├── OPTIMIZATION_SUMMARY.md # Build optimizations
│   │   └── VALIDATION_REPORT.md    # Validation results
│   ├── qemu-test/                  # Skill 2: QEMU boot testing
│   │   ├── SKILL.md                # Skill definition
│   │   ├── scripts/                # Helper scripts
│   │   │   ├── create_initramfs.sh
│   │   │   ├── boot_arm64.sh
│   │   │   ├── boot_arm32.sh
│   │   │   ├── boot_x86.sh
│   │   │   └── run_test.sh
│   │   └── references/
│   │       └── arch_configs.md     # Architecture-specific configs
│   ├── jffs2-analyzer/             # Skill 3: Static JFFS2 analysis
│   │   ├── SKILL.md                # Skill definition
│   │   ├── README.md               # Analyzer documentation
│   │   ├── scripts/
│   │   │   └── jffs2_parser.py     # Python parser implementation
│   │   └── references/
│   │       └── jffs2_structures.md # JFFS2 format reference
│   └── jffs2-mount/                # Skill 4: JFFS2 mount testing
│       ├── SKILL.md                # Skill definition
│       └── scripts/
│           ├── create_jffs2_image.sh    # JFFS2 image creation
│           ├── create_initramfs.sh      # Initramfs for mount test
│           ├── mount_test.sh            # Mount test execution
│           └── run_qemu.sh              # QEMU launch script
├── docs/
│   ├── E2E_VERIFICATION_REPORT.md  # End-to-end test report
│   └── cross_arch_busybox_analysis.md  # Busybox cross-arch solution
└── tools/                          # Additional utilities
```

## Skill Architecture & Decoupling

All 4 skills are **completely decoupled**:

```
┌─────────────────────────────────────────────────────────────┐
│                    Independent Skills                         │
├─────────────────────────────────────────────────────────────┤
│  kernel-build    │ qemu-test      │ jffs2-analyzer │ jffs2-mount │
│  ─────────────   │ ───────────    │ ─────────────  │ ─────────── │
│  Compile kernel  │ Boot kernel    │ Static analysis│ Mount test │
│  Output: Image   │ Requires: Image│ Input: jffs2   │ Requires:  │
│  + modules       │ (user provides)│ Output: report │ Image+kernel│
│                  │ Output: logs   │                │ (user prov) │
│  No calls to:    │ No calls to:   │ No calls to:   │ No calls to:│
│  other skills    │ kernel-build   │ other skills   │ other skills│
└─────────────────────────────────────────────────────────────┘

Users combine skills as needed:
  Step 1: /kernel-build JFFS2_FS --arch arm64 (optional)
  Step 2: /jffs2-analyzer image.jffs2          (independent)
  Step 3: /jffs2-mount --kernel Image --mount  (independent)
  Step 4: /qemu-test --kernel Image            (independent)
```

## Key Technical Notes

### Critical Lessons from Testing

Based on ARM64 end-to-end verification (2026-05-18):

| Lesson | Issue | Solution |
|--------|-------|----------|
| **Architecture Matching** | x86-64 busybox fails in ARM64 QEMU | Cross-compile busybox for target arch |
| **Interactive Config** | `make defconfig` prompts hundreds of options | Use `make allnoconfig` + sed + `yes ""` |
| **Applet Missing** | Scripts fail: `command not found` | Enable all required applets in busybox |
| **Tail Options** | `tail -10` doesn't work | Enable `CONFIG_FEATURE_TAIL_USE_F` |
| **Module Version** | Kernel/module mismatch fails | Compile kernel+modules in same session |
| **MTD Dependency** | JFFS2 needs MTD device | Setup block2mtd/mtdram before mount |

### Busybox Requirements for QEMU Testing

**Minimum applets checklist** (based on real testing):

| Category | Applets | Purpose |
|----------|---------|---------|
| Shell | `sh`, `ash`, `test`, `[` | Script execution |
| Basic | `cat`, `ls`, `mkdir`, `sleep` | File operations |
| Mount | `mount`, `umount`, `mknod` | Filesystem |
| System | `poweroff`, `reboot`, `dmesg` | Control |
| Modules | `insmod`, `lsmod`, `rmmod` | Kernel modules |
| Info | `uname`, `grep`, `date` | Information |
| Logs | `tail` (with features) | Log viewing |

**Automated cross-compilation tool**: `tools/build_busybox.sh`

```bash
# Build ARM64 busybox with all required applets
./tools/build_busybox.sh --arch arm64

# Build with custom applets
./tools/build_busybox.sh --arch arm64 --applets wget,curl,vi
```

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
## Verification Results

### ARM64 End-to-End Test ✅

| Item | Result | Details |
|------|--------|---------|
| Kernel | ✅ Pass | Image (37M), 6.6.0+ |
| jffs2.ko | ✅ Pass | Module load successful |
| MTD | ✅ Pass | mtd.ko + jffs2.ko loaded |
| QEMU Boot | ✅ Pass | Shell entered |

**Test Date**: 2026-05-18
**Report**: docs/E2E_VERIFICATION_REPORT.md

### ARM32 End-to-End Test ✅

| Item | Result | Details |
|------|--------|---------|
| Kernel | ✅ Pass | zImage (11M), 6.6.0+ |
| jffs2.ko | ✅ Pass | Module load successful (149K) |
| MTD | ✅ Pass | Built-in (CONFIG_MTD=y) |
| QEMU Boot | ✅ Pass | Shell entered |

**Key Difference**: ARM32 MTD is built-in, no need for mtd.ko module.
**Test Date**: 2026-05-18
**Report**: docs/ARM32_E2E_REPORT.md

### Architecture Comparison

| Feature | ARM64 | ARM32 |
|---------|-------|-------|
| Kernel Image | Image (37M) | zImage (11M) |
| jffs2.ko Size | 5.9M | 149K |
| MTD Config | Module (m) | Built-in (y) |
| Busybox Size | 969K | 2.1M |
| Toolchain | aarch64-linux-gnu- | arm-linux-gnueabi- |

