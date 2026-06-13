# Crash Analysis Guide

## Basic Usage

### Load Vmcore

```bash
# Use crash binary
./bin/crash vmlinux vmcore.elf

# Or with full paths
/path/to/crash /path/to/vmlinux /path/to/vmcore.elf
```

### Verify Successful Load

```
crash 9.0.2++
      KERNEL: vmlinux
    DUMPFILE: vmcore.elf
        CPUS: 2
      MEMORY: 512 MB
       PANIC: "Kernel panic - not syncing: Fatal exception"
         PID: 86
     COMMAND: "insmod"
        TASK: ffff9a0581d1e580
         CPU: 0
       STATE: TASK_RUNNING (PANIC)
```

## Essential Commands

### System Information (`sys`)

```bash
crash> sys

      KERNEL: vmlinux
    DUMPFILE: vmcore.elf
        CPUS: 2 [OFFLINE: 1]
        DATE: Sat Jun 13 01:30:41 UTC 2026
      UPTIME: 00:00:05
LOAD AVERAGE: 0.08, 0.02, 0.01
       TASKS: 68
     RELEASE: 6.6.0-36583-g6cf1cf61b43c-dirty
     MACHINE: x86_64  (2200 Mhz)
      MEMORY: 511.5 MB
       PANIC: "Kernel panic - not syncing: Fatal exception"
```

### Backtrace (`bt`)

```bash
crash> bt

PID: 86  TASK: ffff9a0581d1e580  CPU: 0  COMMAND: "insmod"
 #0 [ffffa0bcc02d3b48] panic at ffffffff9f894940
 #1 [ffffa0bcc02d3bc8] oops_end at ffffffff9f83ba7a
 #2 [ffffa0bcc02d3be8] page_fault_oops at ffffffff9f8802c0
 #3 [ffffa0bcc02d3c68] exc_page_fault at ffffffffa06da60b
 #4 [ffffa0bcc02d3c90] asm_exc_page_fault at ffffffffa0801316
    [exception RIP: crash_nullptr_init+51]
    RIP: ffffffffc03df033  RSP: ffffa0bcc02d3d48  RFLAGS: 00000246
    RAX: 0000000000000026  RBX: ffffffffc03df010  RCX: 0000000000000000
    RDX: 0000000000000000  RSI: ffffa0bcc02d3c10
    R13: 0000000000000000   ← NULL pointer!
```

### Process List (`ps`)

```bash
crash> ps

      PID    PPID  CPU       TASK        ST  %MEM      VSZ      RSS  COMM
        0       0   0  ffffffffa120c900  RU   0.0        0        0  [swapper/0]
        1       0   1  ffff9a0581198000  IN   0.2     1672     1272  init
>      86       1   0  ffff9a0581d1e580  RU   0.1      612      384  insmod
```

The `>` marker indicates the panic task.

### Kernel Log (`log`)

```bash
crash> log

[    5.896375] Triggering NULL pointer dereference...
[    5.896375] BUG: kernel NULL pointer dereference, address: 0000000000000000
[    5.896375] Oops: 0002 [#1] PREEMPT SMP NOPTI
[    5.926600] Kernel panic - not syncing: Fatal exception
```

### Modules (`mod`)

```bash
crash> mod

     NAME        SIZE   FLAGS   FILE
    crash_nullptr  1024   LO   /modules/crash_nullptr.ko

crash> mod -S crash_nullptr

crash> bt
# Now shows module symbols
```

## Advanced Commands

### Memory Read (`rd`)

```bash
# Read kernel symbol
crash> rd init_task
ffffffffa120c900:  0000000000000000 ...

# Read physical address
crash> rd -p 0x1000

# Read with format
crash> rd -x ffffffffa120c900
ffffffffa120c900:  0x0000000000000000
```

### Symbol Lookup (`sym`)

```bash
crash> sym panic
ffffffff9f894650 (T) panic /home/liumingrui/code/OLK-6.6/kernel/panic.c: 280

crash> sym -l panic  # Show line info
crash> sym -M        # Module symbols
```

### Structure Display (`struct`)

```bash
crash> struct task_struct ffff9a0581d1e580

struct task_struct {
  state = 0,
  stack = 0xffffa0bcc02d4000,
  usage = {
    counter = 2
  },
  flags = 0x400000,
  ...
}

crash> struct task_struct.pid ffff9a0581d1e580
  pid = 86
```

### Disassembly (`dis`)

```bash
# Disassemble function
crash> dis panic

# Disassemble around crash address
crash> dis ffffffffc03df033 10

# Disassemble module function
crash> dis crash_nullptr_init
```

## Module Analysis

### Load Module Symbols

```bash
# Load all modules from vmcore
crash> mod -S

# Load specific module
crash> mod -S crash_nullptr

# Show module details
crash> mod -d crash_nullptr
```

### Analyze Module Crash

```bash
crash> bt
 #4 [ffffa0bcc02d3c90] asm_exc_page_fault
    [exception RIP: crash_nullptr_init+51]

crash> dis crash_nullptr_init
0xffffffffc03df033:  c7 04 25 00 00 00 00  movl $0x2a,0x0
                              ↑ NULL pointer write!

crash> struct module ffffffffc03df010
```

## Task Analysis

### Examine Panic Task

```bash
crash> set
  PID: 86
  COMMAND: "insmod"
  TASK: ffff9a0581d1e580
  CPU: 0
  STATE: TASK_RUNNING (PANIC)

crash> bt -a  # All threads in task

crash> task_struct ffff9a0581d1e580
```

### Examine Other Tasks

```bash
crash> set 1  # Switch to PID 1
crash> bt

crash> foreach bt  # bt for all tasks

crash> ps -a | grep "ST\|RU"  # Active tasks
```

## Crash Diagnosis Checklist

### 1. Identify Panic Type

```bash
crash> log | grep -E "panic|Oops|BUG"

# Common patterns:
# "Kernel panic - not syncing" → System halted
# "Oops: 0002" → NULL pointer dereference
# "BUG: soft lockup" → CPU stuck
# "blocked for more than" → Hung task
```

### 2. Find Crash Location

```bash
crash> bt | grep "exception RIP"

# Example:
# [exception RIP: crash_nullptr_init+51]
# RIP: ffffffffc03df033
```

### 3. Disassemble Crash Code

```bash
crash> dis -l <RIP_address> 20

# Look for:
# - NULL pointer access (address 0)
# - Invalid memory access
# - Function call to bad address
```

### 4. Examine Registers

```bash
crash> bt

# Check key registers:
# RIP = crash address
# RSP = stack pointer
# RAX/RBX/... = general registers
# R13 = often NULL in our crash
```

### 5. Verify Memory State

```bash
# Check if address is valid
crash> vtop <virtual_address>

# Check page tables
crash> ptov <physical_address>
```

## Minimal Mode

When crash can't fully analyze vmcore, it enters minimal mode:

```bash
crash 8.0.4 --minimal vmlinux vmcore.elf

NOTE: minimal mode commands: log, dis, rd, sym, eval, set, extend and exit
```

**Limited commands but still useful for basic analysis.**

**Solution**: Use crash 9.0.2+ for full mode.

## Tips and Tricks

### Save Analysis Results

```bash
crash> log > /tmp/kernel_log.txt
crash> bt > /tmp/backtrace.txt
crash> ps > /tmp/processes.txt
```

### Batch Commands

```bash
# Run commands from file
crash> < commands.txt

# Or pipe
echo -e "sys\nbt\nquit" | crash vmlinux vmcore.elf
```

### Debug Flags

```bash
# Show internal state
crash> set -v

# Show memory mapping
crash> kmem -p
```

## Integration with vmcore-analyzer Skill

```bash
/vmcore-analyzer vmlinux vmcore.elf

# Skill uses configured CRASH_BINARY
# See .env: CRASH_BINARY=/path/to/crash
```

## Common Errors

### "no debugging data available"

**Cause**: Kernel not built with debug symbols

**Solution**:
```bash
/kernel-build DEBUG_INFO_DWARF4 --arch x86_64
```

### "segmentation fault"

**Cause**: Using crash 8.0.x with QEMU vmcore

**Solution**: Use crash 9.0.2+ (provided in this toolkit)

### "cannot resolve symbol"

**Cause**: Module symbols not loaded

**Solution**:
```bash
crash> mod -S <module_name>
```

### "invalid format"

**Cause**: Vmcore without NT_VMCOREINFO

**Solution**: Add `-device vmcoreinfo` to QEMU