# Kernel Testcase Generator Skill Guide

## Overview

This skill acts as a kernel expert specializing in creating reproducible test cases based on kernel problem analysis results.

**Key Principle**: Trigger expected bugs from analysis, avoid coding errors that introduce side effects.

## When to Use

Use this skill when you need to:
- Create test cases to reproduce kernel bugs identified in analysis
- Generate reproducer code (kernel modules, user programs, or combined)
- Construct regression tests for kernel issues

## Input Sources

The skill accepts analysis results from:
- **Knowledge base search** (via `/rag-case-retrieval`)
- **Lock analysis** (via `/lock-analyzer`)
- **Vmcore crash analysis** (via `/vmcore-analyzer`)
- **Kernel logs** (dmesg, kernel messages)

## Workflow

### 1. Analyze Input Results

Before generating code, analyze:
- Root cause and triggering conditions
- Call stack leading to crash
- Specific subsystem involved
- Code path and conditions

### 2. Choose Reproducer Type

Automatically select appropriate type:

| Problem Type | Preferred Reproducer |
|--------------|---------------------|
| Race condition/deadlock | Kernel module |
| Syscall-triggered bug | User program |
| Filesystem/VFS bug | User program + mount ops |
| Memory corruption | Kernel module |
| Driver issue | Kernel module + user trigger |
| OOM/memory pressure | User program (malloc stress) |

### 3. Generate Reproducer Code

Output includes:
- `reproducer.c` - Main reproducer code
- `Makefile` - Build script
- `README.md` - Usage instructions
- `verification.log` - Self-verification results

### 4. Perform Self-Verification

Minimal verification:
- ✅ Code compiles successfully
- ✅ Module loads/unloads cleanly
- ✅ Program executes basic path
- ❌ Full bug reproduction (test expert's job)

## Core Principle: Trigger Expected Bug, Avoid Side Effects

### ✅ DO (Trigger Expected Bug)

- Trigger the specific bug identified in analysis
- Crash/hang occurs at analyzed location
- Bug triggered by specific conditions from analysis

### ❌ DON'T (Avoid Side Effects)

- Introduce random bugs from sloppy coding
- Uninitialized variables causing random crashes
- Wrong API usage leading to unrelated failures

### Example: NULL Pointer Dereference

**Correct implementation**:
```c
// Trigger NULL ptr at analyzed location
// Analysis shows: crash in ioctl handler, private_data not initialized in open

static int buggy_open(struct inode *inode, struct file *file) {
    // ✅ Intentionally NOT setting file->private_data
    return 0;  // Matches root cause from analysis
}

static long buggy_ioctl(struct file *file, unsigned int cmd, unsigned long arg) {
    struct my_device *dev = file->private_data;  // NULL as analyzed
    // ✅ Trigger crash at exact location from analysis
    return dev->ops->ioctl(dev, cmd, arg);
}
```

**Wrong implementation**:
```c
// Random NULL from coding error
static int helper_function(void) {
    struct device *dev = NULL;  // ❌ Random NULL, not from analysis
    return dev->some_field;  // This is sloppy coding, not reproducing bug
}
```

## Common Reproducer Patterns

### Pattern 1: Mutex Deadlock

```c
static DEFINE_MUTEX(mutex_A);
static DEFINE_MUTEX(mutex_B);

// Thread 1: mutex_A -> mutex_B
static int thread1_fn(void *data) {
    mutex_lock(&mutex_A);
    msleep(100);
    mutex_lock(&mutex_B);  // Deadlock if thread2 holds mutex_B
    ...
}

// Thread 2: mutex_B -> mutex_A (reverse order)
static int thread2_fn(void *data) {
    mutex_lock(&mutex_B);
    msleep(100);
    mutex_lock(&mutex_A);  // Deadlock!
    ...
}
```

### Pattern 2: Race Condition

```c
struct shared_data {
    int counter;  // No lock protection
};

static int race_thread(void *data) {
    // Multiple threads updating counter without lock
    shared_data.counter += delta;  // Race condition!
    if (shared_data.counter < 0) {
        BUG();  // Trigger BUG_ON as analyzed
    }
}
```

### Pattern 3: Combined Reproducer

Kernel module + user program:

```c
// Kernel module: Setup vulnerable state
static long reproducer_ioctl(struct file *file, unsigned int cmd, unsigned long arg) {
    return trigger_bug();
}

// User program: Trigger via ioctl
int main() {
    int fd = open("/dev/reproducer", O_RDWR);
    ioctl(fd, TRIGGER_CMD, 0);
    close(fd);
}
```

## Integration with Other Skills

Recommended workflow:
```
/vmcore-analyzer → Get root cause
  ↓
/lock-analyzer → Get lock details (if applicable)
  ↓
/rag-case-retrieval → Check historical cases
  ↓
/kernel-testcase-generator → Generate reproducer
  ↓
/kernel-test-validator → Test expert validates reproduction
```

## Output Requirements

When complete, skill provides:
1. Output directory path
2. Reproducer type chosen
3. Verification status (pass/fail)
4. Brief usage instructions
5. What test expert should verify next

## Example Usage

### Example 1: Mutex Deadlock

**Input**: Lock analysis showing AB-BA deadlock pattern

**Output**:
- Kernel module with two threads
- Threads acquire mutexes in reverse order
- Verification: module loads, threads start
- Location: `~/deadlock_reproducer/`

### Example 2: NULL Pointer Crash

**Input**: Vmcore analysis showing NULL dereference in ioctl handler

**Output**:
- Kernel module with buggy device driver
- User program triggers ioctl
- Verification: compilation successful
- Location: `~/nullptr_crash_reproducer/`

### Example 3: Race Condition

**Input**: Vmcore analysis showing BUG_ON from data corruption

**Output**:
- Kernel module with multiple threads
- Shared counter without lock protection
- Verification: BUG() triggered in dmesg
- Location: `~/race_condition_reproducer/`

## Tips for Effective Reproducers

1. **Minimal but precise**: Focus on exact triggering conditions
2. **Clear trigger point**: Code clearly shows where bug triggers
3. **Obvious failure symptom**: Crash/hang easily observable
4. **Match original conditions**: Kernel version, config, subsystem
5. **Self-contained**: No external setup needed

## Important Rules

1. Always ask for output directory if not specified
2. Read all analysis results before coding
3. Choose reproducer type based on problem characteristics
4. Focus on triggering conditions from analysis
5. Self-verification is minimal (compilation + basic load/run)
6. Don't do full testing (test expert handles that)
7. Generate complete README with instructions
8. Include debug tips for test expert

## See Also

- `/vmcore-analyzer` - Crash dump analysis
- `/lock-analyzer` - Lock contention analysis
- `/kernel-test-validator` - Test expert validation
- `/kernel-build` - Kernel compilation
- `/qemu-test` - QEMU testing