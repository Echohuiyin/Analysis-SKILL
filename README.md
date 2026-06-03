# Kernel Analysis Skills

Claude Code skills for kernel development and debugging.

## Skills

| Skill | Description | Dependencies |
|-------|-------------|--------------|
| vmcore-analyzer | Vmcore crash dump analysis (7-phase workflow) | MCP Server |
| lock-analyzer | Kernel lock analysis (mutex/spinlock/semaphore) | MCP Server |
| kernel-build | Compile kernels with custom configs | GCC toolchain |
| qemu-test | Boot kernels in QEMU for testing | QEMU, busybox |
| jffs2-analyzer | Static analysis of JFFS2 images | Python |
| jffs2-mount | Mount JFFS2 in QEMU | QEMU, kernel |
| jffs2-fault-inject | Inject faults into JFFS2 images | Python |
| rag-case-retrieval | RAG-based case retrieval | Chroma DB |

## Quick Start

```bash
# One-click installation
bash scripts/install.sh

# Verify installation
claude mcp list  # Should show 'aicrasher'
ls ~/.claude/skills/  # Should show skill directories
```

## Installation

### 1. MCP Server (required for vmcore-analyzer & lock-analyzer)

```bash
pip install -e .[cli]
claude mcp add aicrasher -- python3 -m aicrasher.mcp_server
```

### 2. Skills

```bash
cp -r skills/* ~/.claude/skills/
```

### 3. Configuration

```bash
cp .env.example .env
# Edit .env if needed
```

## MCP Tools

| Tool | Description |
|------|-------------|
| analyze_crash | Create session + collect baseline |
| run_crash_command | Execute crash command |
| close_crash_session | Close session |

## Usage Examples

```bash
# Vmcore analysis
/vmcore-analyzer /path/to/vmcore /path/to/vmlinux

# Lock analysis (requires active crash session)
/lock-analyzer 0xffffffc00012345 --type mutex

# Kernel build
/kernel-build JFFS2_FS --arch arm64 --cross

# QEMU test
/qemu-test --arch arm64 --kernel arch/arm64/boot/Image
```

## Documentation

- [vmcore-analyzer](docs/vmcore-analyzer-guide.md)
- [lock-analyzer](docs/lock-analyzer-guide.md)
- [kernel-build](docs/kernel-build-guide.md)
- [qemu-test](docs/qemu-test-guide.md)
- [jffs2-skills](docs/jffs2-guide.md)
- [rag-case-retrieval](docs/rag-case-retrieval-guide.md)

## Requirements

- Python 3.10+
- crash utility (for vmcore/lock analysis)
- GCC toolchain (for kernel-build)
- QEMU (for qemu-test)
- Chroma DB (for rag-case-retrieval)