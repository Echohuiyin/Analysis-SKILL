# Kernel Analysis Skills

Claude Code skills for kernel development and debugging.

## Skills

| Skill | Description | Dependencies |
|-------|-------------|--------------|
| vmcore-analyzer | Vmcore crash dump analysis (7-phase workflow) | MCP Server |
| lock-analyzer | Kernel lock analysis (mutex/spinlock/semaphore) | MCP Server |
| kernel-build | Compile kernels with custom configs | GCC toolchain |
| kernel-fault-injection | Inject kernel faults → generate vmcore | kernel-build, qemu-test |
| qemu-test | Boot kernels in QEMU for testing | QEMU, busybox |
| jffs2-analyzer | Static analysis of JFFS2 images | Python |
| jffs2-mount | Mount JFFS2 in QEMU | QEMU, kernel |
| jffs2-fault-inject | Inject faults into JFFS2 images | Python |
| rag-case-retrieval | RAG-based case retrieval | chromadb, openai (Ollama optional) |

## Quick Start

```bash
# One-click installation
bash scripts/install.sh

# Verify installation
claude mcp list  # Should show 'aicrasher'
ls ~/.claude/skills/  # Should show skill directories
```

## Prerequisites

Before running install.sh, ensure:

| Requirement | Check Command | Notes |
|-------------|---------------|-------|
| Python 3.10+ | `python3 --version` | Required for all skills |
| Claude CLI | `which claude` | Install from [claude.ai/code](https://claude.ai/code) |
| crash utility | `which crash` | Required for vmcore/lock analysis (9.0.2+ for QEMU vmcore) |
| GCC toolchain | `which gcc` | Required for kernel-build |
| QEMU | `which qemu-system-*` | Required for qemu-test, kernel-fault-injection |
| socat | `which socat` | Required for QEMU monitor communication |
| (Optional) Ollama | `which ollama` | For local embedding (RAG) |

**RAG Skill Specific**:
- Local embedding: Install [Ollama](https://ollama.com) and pull model: `ollama pull nomic-embed-text`
- Cloud embedding: Set `EMBEDDING_BASE_URL` and `EMBEDDING_API_KEY` in `.env`

## Installation

### Recommended: One-Click Install

```bash
bash scripts/install.sh
```

This script automatically:
1. Creates a Python virtual environment (`.venv`) and installs the MCP package
2. Registers the `aicrasher` MCP server (supports both `claude` and `codebuddy` CLI tools)
3. Installs all 9 skills to the appropriate skills directory
4. Creates `.env` from `.env.example` if not present
5. Installs chromadb for RAG (uses local PersistentClient mode, no Docker required)
6. (Optional) Checks Ollama for local embedding

### Verify Installation

```bash
# Core environment check
python scripts/check_core.py

# RAG-specific check (optional)
python skills/rag-case-retrieval/scripts/check_environment.py

# Verify MCP
claude mcp list  # Should show 'aicrasher'

# Verify skills
ls ~/.claude/skills/  # Should show skill directories
```

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

# Kernel fault injection (generate vmcore)
/kernel-fault-injection nullptr --arch x86_64

# QEMU test
/qemu-test --arch arm64 --kernel arch/arm64/boot/Image

# RAG case retrieval (example)
# Import cases from ZIP
python ~/.claude/skills/rag-case-retrieval/scripts/import_from_zip.py --zip cases.zip

# Retrieve similar cases
python ~/.claude/skills/rag-case-retrieval/scripts/retrieve_cases.py "kernel panic"
```

## Documentation

- [vmcore-analyzer](docs/vmcore-analyzer-guide.md)
- [lock-analyzer](docs/lock-analyzer-guide.md)
- [kernel-build](docs/kernel-build-guide.md)
- [kernel-fault-injection](skills/kernel-fault-injection/SKILL.md)
- [qemu-test](docs/qemu-test-guide.md)
- [jffs2-skills](docs/jffs2-guide.md)
- [rag-case-retrieval](docs/rag-case-retrieval-guide.md)
- [crash-vmcore toolkit](tools/crash-vmcore/README.md) — QEMU vmcore generation guide

## Requirements

- Python 3.10+
- crash utility (for vmcore/lock analysis)
- GCC toolchain (for kernel-build)
- QEMU (for qemu-test)
- chromadb package (for rag-case-retrieval, uses local storage)
- (Optional) Ollama for local embedding (recommended, no data leakage)

## Troubleshooting

### MCP Server Connection Failed

If `claude mcp list` shows "Failed to connect":
```bash
# Check MCP Server status
claude mcp list

# Re-register MCP Server
claude mcp remove aicrasher
claude mcp add aicrasher -- .venv/bin/python -m aicrasher.mcp_server
```

### RAG Embedding Service

**Local Ollama (recommended)**:
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start service
ollama serve

# Pull embedding model
ollama pull nomic-embed-text

# Verify
curl http://localhost:11434/api/tags
```

**Cloud API**:
```bash
# Edit .env file
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_API_KEY=sk-your-key-here
```

### pip Install Issues

If pip install fails or installs to wrong location:
```bash
# Use python -m pip (recommended)
.venv/bin/python -m pip install chromadb

# Avoid using .venv/bin/pip directly (shebang issues)
```