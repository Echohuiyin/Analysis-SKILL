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
| rag-case-retrieval | RAG-based case retrieval | Chroma DB, openai |

## Quick Start

```bash
# One-click installation
bash scripts/install.sh

# Verify installation
claude mcp list  # Should show 'aicrasher'
ls ~/.claude/skills/  # Should show skill directories
```

## Installation

### Recommended: One-Click Install

```bash
bash scripts/install.sh
```

This script automatically:
1. Creates a Python virtual environment (`.venv`) and installs the MCP package
2. Registers the `aicrasher` MCP server (supports both `claude` and `codebuddy` CLI tools)
3. Installs all 8 skills to the appropriate skills directory
4. Creates `.env` from `.env.example` if not present

### Manual Installation

**1. MCP Server** (required for vmcore-analyzer & lock-analyzer)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[cli]"
# Remove existing registration first if present
claude mcp remove aicrasher 2>/dev/null || true
claude mcp add aicrasher -- .venv/bin/python -m aicrasher.mcp_server
deactivate
```

**2. Skills**

```bash
rm -rf ~/.claude/skills/*/ 2>/dev/null || true
cp -r skills/* ~/.claude/skills/
```

For `codebuddy` CLI, replace `~/.claude/skills/` with `~/.codebuddy/skills/`.

**3. Configuration**

```bash
cp .env.example .env
# Edit .env — configure LLM API credentials and crash binary path
```

## MCP Tools

| Tool | Description |
|------|-------------|
| analyze_crash | One-shot: create session + collect baseline (sys, bt, log) |
| create_crash_session | Create a crash debugging session |
| run_crash_command | Execute a single crash CLI command |
| run_crash_commands | Execute multiple crash commands sequentially |
| collect_baseline | Collect baseline diagnostics (sys, bt, log) |
| close_crash_session | Close and clean up a crash session |
| export_command_log | Export all recorded commands to JSONL |
| search_knowledge_base | Search local KB and Red Hat KB for relevant articles |
| list_sessions | List all active crash sessions |

## Usage Examples

```bash
# Vmcore analysis
/vmcore-analyzer /path/to/vmcore /path/to/vmlinux

# Lock analysis (requires active crash session)
/lock-analyzer --type mutex 0xffffffc00012345

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
- Chroma DB + openai (for rag-case-retrieval)