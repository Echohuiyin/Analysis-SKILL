# vmcore-analyzer Guide

Linux kernel vmcore crash dump analysis skill with MCP integration.

## Prerequisites

- crash utility: `sudo apt install crash`
- vmlinux (uncompressed debug kernel image)
- vmcore (crash dump file)
- MCP Server registered: `aicrasher`

## Usage

```bash
/vmcore-analyzer <vmcore-path> <vmlinux-path> [kernel-src-path]
```

## Workflow (7 Phases)

| Phase | Action |
|-------|--------|
| 0 | Environment check (MCP ready) |
| 1 | Baseline collection (sys/bt/log) |
| 2 | Panic type identification |
| 3 | Deep analysis |
| 4 | Community fix search (conditional) |
| 5 | Mitigation recommendations |
| 6 | HTML report generation |
| 7 | Session cleanup |

## Panic Types

| Type | Signature |
|------|-----------|
| Hung Task | `khungtaskd`, "blocked for more than" |
| Soft Lockup | "BUG: soft lockup" |
| Hard Lockup | "NMI watchdog: Watchdog detected hard LOCKUP" |
| BUG_ON | "kernel BUG at" |
| NULL Pointer | "unable to handle kernel NULL pointer" |
| OOM | "Out of memory and no killable processes" |

## Output

- `crash_report_TIME.html` - Analysis report
- `crash_cmd_log_TIME.jsonl` - Command log

## MCP Tools Used

- `analyze_crash` - Create session + baseline
- `run_crash_command` - Execute commands
- `export_command_log` - Export logs
- `close_crash_session` - Cleanup

## Tips

1. Always read phase guides from `references/phases/`
2. Use `@cmd[]` references in reports (saves tokens)
3. Close session after analysis
4. Provide kernel source for fix searching