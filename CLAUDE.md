# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

Kernel Analysis Skills Collection is a toolkit for Linux kernel development and debugging that provides:

1. **Skills** - 8 Claude Code skills for various kernel tasks
2. **MCP Server** - `aicrasher` server exposing 9 crash analysis tools

The project supports:
- Kernel compilation (kernel-build)
- QEMU testing (qemu-test)
- JFFS2 filesystem analysis (jffs2-analyzer, jffs2-mount, jffs2-fault-inject)
- Vmcore crash dump analysis (vmcore-analyzer)
- Lock debugging (lock-analyzer)
- RAG case retrieval (rag-case-retrieval)

## Build & Installation

```bash
# Install MCP Python package (required for vmcore-analyzer and lock-analyzer)
pip install -e .[cli]

# Register MCP Server with Claude Code
claude mcp add aicrasher -- python3 -m aicrasher.mcp_server

# Verify MCP registration
claude mcp list

# One-click setup (alternative)
bash scripts/setup.sh
```

## Key Commands

```bash
# Start MCP Server (stdio transport)
python3 -m aicrasher.mcp_server
# or via entry point
aicrasher-mcp

# Generate HTML report from Markdown + command log
python scripts/crash_report_generator.py crash_report.md -l crash_cmd_log.jsonl -o crash_report.html
```

## Architecture

### MCP Server Layer (src/aicrasher/)

Core modules:
- `mcp_server.py` - FastMCP server exposing 9 tools
- `crash_session.py` - Manages `crash` CLI via pexpect, auto-logs commands to JSONL
- `config.py` - Pydantic config from .env files
- `knowledge_base.py` - Local KB + Red Hat KB search
- `ai_orchestrator.py` - OpenAI interaction for CLI analyze mode

### Skill Layer (skills/)

- `vmcore-analyzer/` - Complete 7-phase vmcore analysis workflow
  - Uses MCP tools for crash session management
  - Includes detailed phase guides and scenario analysis files
  
- `lock-analyzer/` - Kernel lock analysis
  - Uses MCP tools for crash commands
  - Mutex, spinlock, semaphore support
  
- Other skills (kernel-build, qemu-test, etc.) are standalone

## MCP Tools Reference

| Tool | Description |
|------|-------------|
| `analyze_crash` | Create session + collect baseline (sys/bt/log) |
| `create_crash_session` | Create crash session, returns session_id |
| `run_crash_command` | Execute single crash command |
| `run_crash_commands` | Execute multiple commands sequentially |
| `collect_baseline` | Collect sys, bt, log \| tail -n 100 |
| `export_command_log` | Export command history to JSONL |
| `close_crash_session` | Close session and cleanup |
| `search_knowledge_base` | Search local KB + Red Hat KB |
| `list_sessions` | List active sessions |

## Skill Dependencies

- **vmcore-analyzer**: Requires aicrasher MCP Server
- **lock-analyzer**: Requires aicrasher MCP Server (needs crash session)
- **kernel-build**: Standalone (requires GCC toolchain)
- **qemu-test**: Standalone (requires QEMU and busybox)
- **jffs2-***: Standalone Python-based
- **rag-case-retrieval**: Standalone (requires Chroma DB)

## Important Patterns

### Command Logging (MCP)

All crash commands are auto-logged to JSONL format:
```json
{"cmd": "bt", "output": "...", "success": true}
```

Report generator uses `@cmd[command]` syntax to reference outputs, saving ~40-50% AI output tokens.

### Session Management

- Sessions must be explicitly closed via `close_crash_session` after analysis
- Signal handlers and atexit ensure cleanup even on abrupt termination
- Always use MCP tools for crash operations - never use Bash to call crash directly

### Vmcore Analysis Workflow

When user asks to analyze vmcore:
1. Load `skills/vmcore-analyzer/SKILL.md`
2. Follow 7-phase workflow
3. Read phase-specific guides from `references/phases/`
4. Use MCP tools for all crash operations
5. Generate HTML report via `crash_report_generator.py`

### Lock Analysis Workflow

When user asks to analyze locks:
1. Check for existing crash session (from vmcore-analyzer or user)
2. If no session, use MCP `create_crash_session` first
3. Identify lock type via `struct` command
4. Analyze based on lock type (mutex/spinlock/semaphore)
5. Check for deadlocks if requested

## Configuration

Copy `.env.example` to `.env` and configure:
- `CRASH_BINARY` - Path to crash utility (default: /usr/bin/crash)
- `CRASH_OUTPUT_MAX_CHARS` - Max chars per command output (default: 16384)
- `CRASH_BATCH_OUTPUT_MAX_CHARS` - Max chars for batch commands (default: 32768)
- `KNOWLEDGE_BASE_PATHS` - Local KB directories (colon-separated)

## Skill Installation Locations

```bash
# Claude Code
cp -r skills/* ~/.claude/skills/

# Verify
ls ~/.claude/skills/
```

## MCP Server Registration

```bash
# Claude Code
claude mcp add aicrasher -- python3 -m aicrasher.mcp_server
```

## Code Style Guidelines

- Python code follows standard PEP 8
- Skill files (SKILL.md) use YAML frontmatter with `name`, `description`, `version`
- Reference documents use Markdown format
- No emojis unless user explicitly requests

## Important Notes

1. **Never use Bash to call crash directly** - Always use MCP tools
2. **Always close crash sessions** - Use `close_crash_session` after analysis
3. **Command logs are auto-created** - Don't manually create JSONL files
4. **Reports use script generator** - Don't write HTML directly, use `crash_report_generator.py`