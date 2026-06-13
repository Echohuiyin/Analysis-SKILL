# QEMU Vmcore Generation Guide

## Overview

This document explains how to configure QEMU to generate vmcore files compatible with crash utility analysis.

## The Problem

Standard QEMU `dump-guest-memory` command produces raw ELF memory dump without:

1. **NT_VMCOREINFO** - Kernel metadata (symbols, page size, offsets)
2. **NT_PRSTATUS** - CPU register states
3. **Task structure info** - Process/thread information

Crash utility requires these ELF notes for proper analysis. Without them, crash may:
- Segfault during initialization
- Show incomplete backtraces
- Fail to determine panic task

## The Solution

### 1. Kernel Configuration

Enable fw_cfg interface for kernel-QEMU communication:

```bash
# Required configs
CONFIG_FW_CFG_SYSFS=y          # QEMU fw_cfg interface
CONFIG_FW_CFG_SYSFS_CMDLINE=y  # fw_cfg command line support
CONFIG_CRASH_CORE=y            # Crash kernel core
CONFIG_DEBUG_INFO_DWARF4=y     # Debug symbols
CONFIG_PANIC_ON_OOPS=y         # Panic on kernel oops
```

**How it works**:
- Kernel `crash_core.c` generates vmcoreinfo data
- `qemu_fw_cfg.c` driver writes data to QEMU fw_cfg device
- QEMU embeds data as NT_VMCOREINFO ELF note in dump

### 2. QEMU Configuration

```bash
qemu-system-x86_64 \
    -M q35,dump-guest-core=on \   # REQUIRED
    -device vmcoreinfo \           # REQUIRED
    -smp 2 \
    -m 512M \
    -nographic \
    -kernel vmlinux \
    -initrd initramfs.cpio.gz \
    -append "console=ttyS0 panic=10 oops=panic" \
    -monitor unix:/tmp/qemu.sock,server,nowait
```

**Key parameters**:

| Parameter | Purpose | Required |
|-----------|---------|----------|
| `-M q35` | x86_64 machine type (not `-M pc`) | Yes |
| `dump-guest-core=on` | Enable memory dump | Yes |
| `-device vmcoreinfo` | Kernel info to QEMU | Yes |
| `panic=10` | Delay before reboot | Recommended |
| `-monitor unix:...` | Control socket for dump | Yes |

## Vmcore Capture Process

### Manual Capture

```bash
# 1. Start QEMU with monitor socket
qemu-system-x86_64 -device vmcoreinfo -monitor unix:/tmp/qemu.sock,server,nowait ...

# 2. Wait for crash (kernel panic)

# 3. Capture vmcore via monitor
echo "dump-guest-memory /tmp/vmcore.elf" | socat - UNIX-CONNECT:/tmp/qemu.sock

# 4. Stop QEMU
echo "quit" | socat - UNIX-CONNECT:/tmp/qemu.sock
```

### Automated Script

```bash
#!/bin/bash
# run_vmcore_test.sh

MONITOR_SOCKET="/tmp/qemu_${TEST_NAME}.sock"
VMCORE_FILE="${OUTPUT_DIR}/vmcore.elf"

# Start QEMU
qemu-system-x86_64 -device vmcoreinfo -monitor unix:$MONITOR_SOCKET,server,nowait ...

# Monitor for crash
while true; do
    if grep -q "Kernel panic" boot.log; then
        echo "dump-guest-memory ${VMCORE_FILE}" | socat - UNIX-CONNECT:${MONITOR_SOCKET}
        echo "quit" | socat - UNIX-CONNECT:${MONITOR_SOCKET}
        break
    fi
    sleep 1
done
```

## Vmcore Format Analysis

### ELF Structure

```bash
$ readelf -h vmcore.elf
ELF Header:
  Class:                             ELF64
  Machine:                           Advanced Micro Devices X86-64
  Type:                              CORE (Core file)
```

### ELF Notes

```bash
$ readelf -n vmcore.elf

Displaying notes found at file offset 0x000001d8:
  Owner                Data size       Description
  CORE                 0x00000150      NT_PRSTATUS (prstatus structure)
  CORE                 0x00000150      NT_PRSTATUS (prstatus structure)
  VMCOREINFO           0x00000c59      Unknown note type: (0x00000000)
   description data: OSRELEASE=6.6.0... PAGESIZE=4096 SYMBOL(init_uts_ns)=...
```

### Vmcoreinfo Contents

The vmcoreinfo note contains:

```
OSRELEASE=6.6.0-36583-g6cf1cf61b43c-dirty
PAGESIZE=4096
SYMBOL(init_uts_ns)=ffffffffa146c740
SYMBOL(init_task)=ffffffffa120c900
KERNELOFFSET=1e800000
NUMBER(phys_base)=...
... (many more symbols and offsets)
```

## Machine Type Selection

### x86_64: Why q35 vs pc

| Machine Type | ELF Format | Crash Compatibility |
|--------------|------------|---------------------|
| `-M pc` | Intel 80386 (32-bit) | ✗ Wrong format |
| `-M q35` | x86-64 (64-bit) | ✓ Correct format |

```bash
# Check vmcore machine type
readelf -h vmcore.elf | grep Machine
# Should show: Advanced Micro Devices X86-64
# NOT: Intel 80386
```

### ARM64

```bash
qemu-system-aarch64 \
    -M virt,dump-guest-core=on \
    -device vmcoreinfo \
    -cpu cortex-a57 \
    -smp 2 \
    -m 512M \
    -append "console=ttyAMA0 panic=10"
```

## Troubleshooting

### Issue: VMCOREINFO note missing

```bash
readelf -n vmcore.elf | grep VMCOREINFO
# No output
```

**Causes**:
1. Missing `-device vmcoreinfo`
2. Kernel lacks `CONFIG_FW_CFG_SYSFS`

**Solution**:
```bash
# Add to QEMU
-device vmcoreinfo

# Rebuild kernel
/kernel-build FW_CFG_SYSFS FW_CFG_SYSFS_CMDLINE --arch x86_64
```

### Issue: Wrong ELF machine type

```bash
readelf -h vmcore.elf | grep Machine
# Machine: Intel 80386
```

**Cause**: Using `-M pc` instead of `-M q35`

**Solution**:
```bash
qemu-system-x86_64 -M q35 ...
```

### Issue: Vmcore empty or zero size

**Causes**:
1. QEMU rebooted before dump (panic=-1)
2. Crash didn't occur

**Solution**:
```bash
# Use panic delay
-append "console=ttyS0 panic=10 oops=panic"
```

## Alternative: Kdump/kexec

For production systems, kdump is more reliable:

```bash
# Kernel parameters
crashkernel=256M@32M

# Requires:
# - CONFIG_KEXEC=y
# - CONFIG_CRASH_DUMP=y
# - CONFIG_PROC_VMCORE=y

# Crash kernel boots after panic
# /proc/vmcore available in crash kernel
```

**Pros**: Standard format, full compatibility
**Cons**: Complex setup, requires crash kernel initramfs

## References

- QEMU vmcoreinfo spec: `/usr/share/doc/qemu-system-data/specs/vmcoreinfo.rst`
- Kernel fw_cfg driver: `drivers/firmware/qemu_fw_cfg.c`
- Kernel crash_core: `kernel/crash_core.c`