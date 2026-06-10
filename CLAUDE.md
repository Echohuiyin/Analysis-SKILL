# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Project Structure

```
Analysis-SKILL/
├── src/aicrasher/      # MCP Server (9 tools)
├── skills/             # 8 Claude Code skills
├── docs/               # Skill guides
├── scripts/            # install.sh, crash_report_generator.py
└── pyproject.toml      # Python package config
```

## Skills

| Skill | MCP Required | Description |
|-------|--------------|-------------|
| vmcore-analyzer | Yes | Vmcore analysis |
| lock-analyzer | Yes | Lock debugging |
| kernel-build | No | Kernel compilation |
| qemu-test | No | QEMU testing |
| kernel-test-validator | No | Kernel reproduction validation |
| jffs2-* | No | JFFS2 analysis |
| rag-case-retrieval | No | Case retrieval |

## MCP Tools

| Tool | Purpose |
|------|---------|
| analyze_crash | Create session + baseline |
| run_crash_command | Execute command |
| close_crash_session | Cleanup |

## Important Rules

1. **Never use Bash for crash** - Always use MCP tools
2. **Close sessions** - Call close_crash_session after analysis
3. **Command logs auto-created** - Don't manually create JSONL
4. **Use crash_report_generator.py** - Don't write HTML directly

## Installation

```bash
bash scripts/install.sh
```

## Configuration

Copy `.env.example` to `.env`:
- CRASH_BINARY - Path to crash utility
- KNOWLEDGE_BASE_PATHS - KB directories