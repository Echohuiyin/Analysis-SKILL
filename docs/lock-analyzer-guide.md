# lock-analyzer Guide

Kernel lock analysis skill using MCP tools.

## Prerequisites

- Active crash session (from vmcore-analyzer or create_crash_session)
- MCP Server registered: `aicrasher`

## Usage

```bash
/lock-analyzer <lock-address> [--type mutex|spinlock|semaphore]
/lock-analyzer --deadlock-check
```

## Lock Types

| Type | Structure | Owner Tracking |
|------|-----------|----------------|
| Mutex | `struct mutex` | `owner` field |
| Spinlock | `raw_spinlock_t` | Indirect (stack) |
| Semaphore | `struct semaphore` | No owner |

## Mutex Analysis

```bash
# Get owner
struct mutex.owner <addr>
# Note: clear low 3 bits (flags): owner & ~0x7

# Get task info
struct task_struct.pid,comm,state <owner_addr>
bt <pid>

# Check state
struct mutex.count <addr>  # 0=locked, 1=unlocked
```

## Spinlock Analysis

```bash
# Check ticket lock
struct arch_spinlock_t.tickets <addr>
# head==tail: unlocked, tail>head: locked

# Find spinning tasks
foreach bt | grep spin_lock
```

## Semaphore Analysis

```bash
struct semaphore.count <addr>  # 0=locked, >0=available
struct semaphore.sleepers <addr>
```

## Deadlock Detection

```bash
ps -u                    # D-state tasks
foreach bt | grep mutex  # Find mutex patterns
struct task_struct.blocked_on <task_addr>
```

## Common Commands

| Task | Command |
|------|---------|
| Mutex owner | `struct mutex.owner <addr>` |
| Task info | `struct task_struct.pid,comm <addr>` |
| Stack trace | `bt <pid>` |
| Blocked tasks | `ps -u` |
| All stacks | `bt -a` |
| Spinlock state | `struct arch_spinlock_t.tickets <addr>` |

## Helper Scripts

- `analyze_mutex.sh` - Generate mutex analysis commands
- `find_lock_owner.sh` - Find lock owner for any type
- `deadlock_scan.sh` - Scan for deadlock scenarios

## Kernel Version Notes

- Pre-4.8: mutex has no `owner` field
- 4.8+: mutex has `atomic_long_t owner`

## Output Files

```
lock_analysis/
├── owner_info.txt      # Lock owner details
├── waiters.txt         # Waiting tasks
├── stack_traces.txt    # Stack traces
└── summary.md          # Analysis report
```