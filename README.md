# Kernel Analysis Skills Collection

This repository contains Claude Code skills for kernel compilation, QEMU testing, JFFS2 filesystem analysis, vmcore crash dump analysis, and lock debugging.

## Overview

Nine independent skills for kernel development and debugging workflow:

- **kernel-build**: Compile Linux kernels with custom configurations
- **qemu-test**: Boot kernels in QEMU for testing and verification
- **jffs2-analyzer**: Static analysis of JFFS2 filesystem images
- **jffs2-mount**: Mount JFFS2 images in QEMU for dynamic verification
- **jffs2-fault-inject**: Inject faults into JFFS2 images for testing
- **rag-case-retrieval**: RAG-based semantic case retrieval from vector database
- **vmcore-analyzer**: Complete vmcore crash dump analysis workflow with MCP integration
- **lock-analyzer**: Analyze kernel locks (mutex/spinlock/semaphore) to find lock owners and detect deadlocks

## MCP Server Integration

This project includes an MCP Server (`aicrasher`) that provides crash analysis tools:

### MCP Tools (9 tools exposed)

| Tool | Purpose |
|------|---------|
| `analyze_crash` | Entry point: create session + collect baseline (sys/bt/log) |
| `create_crash_session` | Create crash session, returns session_id |
| `run_crash_command` | Execute single crash command in session |
| `run_crash_commands` | Execute multiple crash commands sequentially |
| `collect_baseline` | Collect sys, bt, log \| tail -n 100 |
| `export_command_log` | Export command history to JSONL |
| `close_crash_session` | Close session and cleanup |
| `search_knowledge_base` | Search local KB + Red Hat KB |
| `list_sessions` | List active sessions |

### MCP Server Installation

```bash
# Install MCP Python package
pip install -e .[cli]

# Register MCP Server with Claude Code
claude mcp add aicrasher -- python3 -m aicrasher.mcp_server
```

### Configuration

Copy `.env.example` to `.env` and configure:
- `CRASH_BINARY` - Path to crash utility (default: /usr/bin/crash)
- `CRASH_OUTPUT_MAX_CHARS` - Max chars per command output (default: 16384)
- `KNOWLEDGE_BASE_PATHS` - Local KB directories (colon-separated)

## Skills

### 1. vmcore-analyzer Skill (NEW)

**Location**: `skills/vmcore-analyzer/`

Complete 7-phase vmcore crash dump analysis workflow.

**Key Features**:
- MCP-powered crash session management
- Automatic command logging to JSONL
- Knowledge base integration (local + Red Hat KB)
- HTML report generation with `@cmd[]` references
- Scenario-specific analysis guides

**Workflow Phases**:
| Phase | Name | Output |
|-------|------|--------|
| Phase 0 | Environment check | MCP ready |
| Phase 1 | Baseline collection | sys/bt/log |
| Phase 2 | Panic type identification | Panic category |
| Phase 3 | Deep analysis | Root cause |
| Phase 4 | Community fix search | Fix commits (conditional) |
| Phase 5 | Mitigation analysis | Recommendations |
| Phase 6 | Report generation | HTML report |
| Phase 7 | Session cleanup | Session closed |

**Usage**:
```
/vmcore-analyzer <vmcore-path> <vmlinux-path> [kernel-src-path]
```

**Examples**:
```
/vmcore-analyzer /data/vmcore /data/vmlinux
/vmcore-analyzer /path/to/vmcore /path/to/vmlinux /path/to/kernel-src
```

### 2. lock-analyzer Skill (Updated)

**Location**: `skills/lock-analyzer/`

Analyze kernel locks using MCP tools.

**Key Features**:
- MCP integration for crash commands
- Mutex owner identification via `owner` field
- Spinlock contention analysis (ticket lock, qspinlock)
- Semaphore wait queue analysis
- Deadlock detection and circular dependency checking

**Lock Types Supported**:

| Lock Type | Structure | Owner Tracking | Use Case |
|-----------|-----------|----------------|----------|
| Mutex | `struct mutex` | ✅ `owner` field | Long critical sections, sleepable |
| Spinlock | `raw_spinlock_t` | ❌ Indirect via stack | Short critical sections, IRQ handlers |
| Semaphore | `struct semaphore` | ❌ Counting semaphore | Resource counting, synchronization |

**Usage**:
```
/lock-analyzer <lock-address> [--type mutex|spinlock|semaphore]
/lock-analyzer --deadlock-check
```

**Note**: Requires active crash session (created via MCP `analyze_crash` or `create_crash_session`).

### 3. kernel-build Skill

**Location**: `skills/kernel-build/`

Build the Linux kernel with custom CONFIG options (tested with openEuler kernel).

**Key Features**:
- ARM64/ARM32/x86_64 architecture support
- Native and cross-compilation
- Automatic toolchain detection
- openeuler_defconfig base configuration

**Usage**:
```
/kernel-build <config-options> [--arch <arch>] [--cross] [--jobs <N>]
```

**Examples**:
```
/kernel-build CONFIG_JFFS2_FS=m --arch arm64 --cross
/kernel-build UB XCU_SCHEDULER --arch x86_64 --jobs 32
/kernel-build ARM64_MPAM --arch arm64 --cross --jobs 64
```

### 4. qemu-test Skill

**Location**: `skills/qemu-test/`

Boot kernels in QEMU and run automated tests.

**Key Features**:
- Multi-architecture QEMU support (ARM64/ARM32/x86_64)
- Minimal initramfs creation with busybox
- Module loading tests
- Automated test script execution

**Usage**:
```
/qemu-test --arch arm64 --kernel <path> --modules <path> [--script <path>]
```

### 5. jffs2-analyzer Skill

**Location**: `skills/jffs2-analyzer/`

Static analysis of JFFS2 filesystem images without mounting.

**Key Features**:
- Parse JFFS2 node structures (dirent, inode, data)
- Extract metadata and file information
- Validate node checksums
- No kernel or QEMU required

**Usage**:
```
/jffs2-analyzer <jffs2-image> [--output <dir>] [--verbose]
```

### 6. jffs2-mount Skill

**Location**: `skills/jffs2-mount/`

Mount JFFS2 filesystem images in QEMU for dynamic verification.

**Usage**:
```
/jffs2-mount --kernel <path> [--image <path>] [--size <MB>] [--mount-test]
```

### 7. jffs2-fault-inject Skill

**Location**: `skills/jffs2-fault-inject/`

Inject various faults into JFFS2 filesystem images for testing.

**Fault Types**:
- `hdr_crc`, `node_crc`, `data_crc`, `name_crc`
- `magic`, `nodetype`, `version_zero`

**Usage**:
```
/jffs2-fault-inject --image <path> [--fault <type>] [--output <dir>]
```

### 8. rag-case-retrieval Skill

**Location**: `skills/rag-case-retrieval/`

RAG-based semantic case retrieval from Chroma vector database.

**Usage**:
```
python skills/rag-case-retrieval/scripts/retrieve_cases.py "查询文本" --top-k 3
```

## Installation

### Prerequisites

**Build Requirements**:
- GCC toolchain (native or cross)
- Kernel source code
- Build dependencies: bc, bison, flex, libssl-dev

**QEMU Requirements**:
- qemu-system-aarch64, qemu-system-arm, qemu-system-x86_64
- ARM64 static busybox for cross-architecture testing

**MCP/Crash Requirements**:
- Python 3.10+
- crash utility (`/usr/bin/crash`)
- vmlinux (uncompressed debug kernel image)
- vmcore (crash dump file)

### Install MCP Package

```bash
# Install Python dependencies
pip install -e .[cli]

# Register MCP Server
claude mcp add aicrasher -- python3 -m aicrasher.mcp_server

# Verify registration
claude mcp list
```

### Install Skills

```bash
# Copy all skills to Claude Code skills directory
mkdir -p ~/.claude/skills
cp -r skills/* ~/.claude/skills/

# Verify installation
ls ~/.claude/skills/
```

## Directory Structure

```
Analysis-SKILL/
├── README.md                       # Project overview
├── pyproject.toml                  # Python package config (MCP)
├── .env.example                    # Environment config template
├── CLAUDE.md                       # Claude Code guidance
├── src/
│   └── aicrasher/                  # MCP Server core
│       ├── mcp_server.py           # FastMCP server (9 tools)
│       ├── crash_session.py        # Crash CLI session manager
│       ├── config.py               # Pydantic config
│       ├── knowledge_base.py       # KB search
│       └── ai_orchestrator.py      # OpenAI interaction
├── skills/                         # 8 skills
│   ├── vmcore-analyzer/            # NEW: Complete vmcore analysis
│   │   ├── SKILL.md                # 7-phase workflow
│   │   └── references/             # Analysis guides
│   │       ├── phases/             # Phase detail files
│   │       └── reference/          # Scenario guides
│   ├── lock-analyzer/              # Updated: MCP-powered lock analysis
│   │   └── SKILL.md                # Lock analysis workflow
│   ├── kernel-build/               # Kernel compilation
│   ├── qemu-test/                  # QEMU testing
│   ├── jffs2-analyzer/             # JFFS2 static analysis
│   ├── jffs2-mount/                # JFFS2 mount testing
│   ├── jffs2-fault-inject/         # Fault injection
│   └── rag-case-retrieval/         # RAG retrieval
├── scripts/                        # Helper scripts
│   ├── crash_report_generator.py   # HTML report generator
│   ├── setup.sh                    # One-click setup
│   └── build_busybox.sh            # Cross-arch busybox builder
├── docs/                           # User documentation
│   ├── lock-analyzer-guide.md      # Lock analyzer guide
│   ├── rag-case-retrieval-guide.md # RAG guide
│   └── jffs2-analyzer-guide.md     # JFFS2 guide
└── tools/                          # Build tools
    └── busybox/                    # Busybox binaries
```

## Workflow Examples

### Vmcore Analysis Workflow

```
# Step 1: Start vmcore analysis
/vmcore-analyzer /path/to/vmcore /path/to/vmlinux

# The skill will:
# - Create crash session via MCP
# - Collect baseline (sys, bt, log)
# - Identify panic type
# - Perform deep analysis
# - Search for fixes (if kernel bug)
# - Generate HTML report
# - Close session
```

### Lock Analysis Workflow

```
# Step 1: Create crash session (or use existing from vmcore-analyzer)
# Step 2: Analyze specific lock
/lock-analyzer 0xffffffc00012345 --type mutex

# Step 3: Check for deadlocks
/lock-analyzer --deadlock-check
```

### Kernel Build + QEMU Test Workflow

```
# Step 1: Build kernel with JFFS2 module
/kernel-build JFFS2_FS --arch arm64 --cross

# Step 2: Test in QEMU
/qemu-test --arch arm64 --kernel arch/arm64/boot/Image --modules fs/jffs2/jffs2.ko
```

### JFFS2 Analysis Workflow

```
# Step 1: Create test image
/jffs2-mount --kernel Image --mount-test

# Step 2: Inject faults
/jffs2-fault-inject --image normal.jffs2 --fault hdr_crc,magic

# Step 3: Analyze corrupted image
/jffs2-analyzer corrupted.jffs2
```

## Skill Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MCP Server Layer                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  aicrasher MCP Server (src/aicrasher/)                              │    │
│  │  - 9 crash analysis tools                                           │    │
│  │  - Session management                                               │    │
│  │  - Command logging                                                  │    │
│  │  - Knowledge base                                                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ MCP Tools
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Skill Layer                                     │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐    │
│  │ vmcore-       │ │ lock-         │ │ kernel-build  │ │ qemu-test     │    │
│  │ analyzer      │ │ analyzer      │ │               │ │               │    │
│  │ ───────────── │ │ ───────────── │ │ ───────────── │ │ ───────────── │    │
│  │ Uses MCP      │ │ Uses MCP      │ │ Compile       │ │ Boot kernel   │    │
│  │ Full workflow │ │ Lock focus    │ │ kernel        │ │ in QEMU       │    │
│  └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘    │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐    │
│  │ jffs2-        │ │ jffs2-mount   │ │ jffs2-fault-  │ │ rag-case-     │    │
│  │ analyzer      │ │               │ │ inject        │ │ retrieval     │    │
│  │ ───────────── │ │ ───────────── │ │ ───────────── │ │ ───────────── │    │
│  │ Static        │ │ Mount test    │ │ Fault inject  │ │ RAG search    │    │
│  │ analysis      │ │ in QEMU       │ │ corruption    │ │ vector DB     │    │
│  └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Contributing

To add new skills or improve existing ones:
1. Create skill directory under `skills/<skill-name>/`
2. Add SKILL.md with skill definition (frontmatter + content)
3. Include supporting scripts in `scripts/` subdirectory if needed
4. Add documentation in `docs/`
5. Update README.md

## License

- Linux kernel: GPL v2
- Skills and tools: MIT license
- MCP Server code: GPL-2.0-only

## References

- [crash utility](https://github.com/crash-utility/crash) - Linux kernel crash analysis
- [Model Context Protocol](https://modelcontextprotocol.io/) - AI tool protocol
- [FastMCP](https://github.com/jlowin/fastmcp) - Python MCP framework
- Kernel Documentation: Documentation/process/coding-style.rst
- QEMU Documentation: https://www.qemu.org/docs/