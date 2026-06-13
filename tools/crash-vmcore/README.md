# QEMU Vmcore Generation and Crash Analysis Guide

Complete toolkit for generating kernel vmcore via QEMU and analyzing with crash utility.

## Overview

This directory contains everything needed to:
1. Configure QEMU to generate crash-compatible vmcore files
2. Build and deploy crash utility (version 9.0.2+)
3. Analyze kernel crashes from QEMU dumps

## Directory Structure

```
crash-vmcore/
├── README.md              # This guide
├── docs/
│   ├── BUILD.md           # Crash compilation instructions
│   ├── DEPLOY.md          # Deployment and installation guide
│   ├── QEMU_VMCORE.md     # QEMU vmcore generation details
│   └── ANALYSIS.md        # Crash analysis howto
├── scripts/
│   ├── build_crash.sh     # Automated crash build script
│   ├── run_vmcore_test.sh # QEMU test with vmcore capture
│   └── install_deps.sh    # Dependency installation script
├── examples/
│   ├── crash_nullptr.c    # Example crash kernel module
│   ├── test_nullptr.sh    # Example test script
│   └── analyze_vmcore.sh  # Example analysis script
└── bin/
    └── crash              # Pre-built crash binary (if available)
```

## Quick Start

### 1. Install Dependencies

```bash
./scripts/install_deps.sh
```

### 2. Build Crash Utility

```bash
./scripts/build_crash.sh
```

Or manually:
```bash
git clone git@github.com:crash-utility/crash.git
cd crash
make -j8
```

### 3. Generate Vmcore via QEMU

```bash
# Build kernel with required configs
./scripts/build_kernel_for_vmcore.sh

# Run QEMU test
./scripts/run_vmcore_test.sh test_name kernel_image initramfs

# Or use existing script
bash examples/analyze_vmcore.sh vmlinux vmcore.elf
```

## Critical Requirements

### Kernel Config (for QEMU vmcore)

```bash
# Enable in kernel .config
CONFIG_FW_CFG_SYSFS=y          # QEMU fw_cfg interface
CONFIG_FW_CFG_SYSFS_CMDLINE=y  # fw_cfg command line support
CONFIG_CRASH_CORE=y            # Crash kernel core
CONFIG_DEBUG_INFO_DWARF4=y     # Debug symbols (DWARF4)
CONFIG_PANIC_ON_OOPS=y         # Panic on oops
```

Use kernel-build skill:
```bash
/kernel-build FW_CFG_SYSFS FW_CFG_SYSFS_CMDLINE DEBUG_INFO_DWARF4 PANIC_ON_OOPS CRASH_CORE --arch x86_64
```

### QEMU Parameters

```bash
qemu-system-x86_64 \
    -M q35,dump-guest-core=on \   # REQUIRED: q35 machine type
    -device vmcoreinfo \           # REQUIRED: vmcoreinfo device
    -smp 2 \
    -m 512M \
    -append "console=ttyS0 panic=10 oops=panic"
```

### Crash Version

**IMPORTANT**: Use crash 9.0.2+ for QEMU vmcore analysis.

| Version | QEMU vmcore Support |
|---------|---------------------|
| crash 8.0.4 (apt) | ✗ Segfault on QEMU dumps |
| crash 9.0.2+ (source) | ✓ Full analysis support |

## Why These Requirements?

### QEMU dump-guest-memory Issue

By default, QEMU's `dump-guest-memory` only dumps raw memory without:
- NT_VMCOREINFO ELF note (kernel symbols, page size)
- NT_PRSTATUS notes (CPU registers)
- Proper task structure metadata

### Solution: vmcoreinfo Device

Adding `-device vmcoreinfo` enables:
1. Kernel writes vmcoreinfo to QEMU fw_cfg
2. QEMU embeds NT_VMCOREINFO in dump file
3. Crash can properly analyze the dump

### Crash 9.0.2+ Fixes

The new version includes fixes for:
- x86_64 ELF vmcore handling
- bt command with QEMU-generated dumps
- Panic task determination from QEMU dumps

## Verification

### Check Vmcore Format

```bash
# Verify ELF notes present
readelf -n vmcore.elf | grep VMCOREINFO

# Should show:
# VMCOREINFO  0x00000c59  Unknown note type
# description data: OSRELEASE=... PAGESIZE=4096 ...
```

### Test Crash Analysis

```bash
./bin/crash vmlinux vmcore.elf

crash> sys      # Should show full system info
crash> bt       # Should show complete backtrace
crash> ps       # Should show process list
crash> log      # Should show kernel log
```

## Integration with Analysis-SKILL

### .env Configuration

```bash
# Use built crash binary
CRASH_BINARY=/path/to/crash-vmcore/bin/crash

# Or system-wide
sudo cp bin/crash /usr/local/bin/
CRASH_BINARY=/usr/local/bin/crash
```

### vmcore-analyzer Skill

```bash
/vmcore-analyzer vmlinux vmcore.elf
```

The skill will use the configured CRASH_BINARY.

## Common Issues

### Issue: Crash segfault

```
bt: read of stack at ... failed
Segmentation fault
```

**Solution**: Use crash 9.0.2+ (this toolkit provides it)

### Issue: VMCOREINFO not found

```bash
readelf -n vmcore.elf | grep VMCOREINFO
# No output
```

**Solution**: Add `-device vmcoreinfo` to QEMU command

### Issue: bt shows no symbols

```
#0 [ffff...] panic at ffffffff...
```

**Solution**: Ensure kernel built with `CONFIG_DEBUG_INFO_DWARF4=y`

### Issue: Module symbols missing

```
symbol not found: crash_nullptr_init
```

**Solution**: Use `mod -S` in crash to load module symbols

## References

- Crash GitHub: https://github.com/crash-utility/crash
- QEMU vmcoreinfo: https://github.com/qemu/qemu/blob/master/docs/specs/vmcoreinfo.rst
- Linux kernel vmcoreinfo: Documentation/ABI/testing/sysfs-kernel-vmcoreinfo