# Kernel Analysis Skills Collection

This repository contains Claude Code skills for kernel compilation, QEMU testing, JFFS2 filesystem analysis, and fault injection testing.

## Overview

Six independent and decoupled skills for kernel development workflow and case retrieval:

- **kernel-build**: Compile Linux kernels with custom configurations
- **qemu-test**: Boot kernels in QEMU for testing and verification
- **jffs2-analyzer**: Static analysis of JFFS2 filesystem images
- **jffs2-mount**: Mount JFFS2 images in QEMU for dynamic verification
- **jffs2-fault-inject**: Inject faults into JFFS2 images for testing
- **rag-case-retrieval**: RAG-based semantic case retrieval from vector database

All skills are **completely decoupled** - each skill operates independently without calling or depending on other skills.

## Skills

### 1. kernel-build Skill

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

**Output**:
- Kernel Image (arch/arm64/boot/Image, arch/x86/boot/bzImage)
- Kernel Modules (*.ko files)

**Important**: Kernel and modules must be compiled in the SAME build session to ensure version matching.

### 2. qemu-test Skill

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

**Examples**:
```
/qemu-test --arch arm64 --interactive
/qemu-test --script tests/jffs2_test.sh --timeout 60
/qemu-test --kernel arch/x86/boot/bzImage --arch x86_64
```

**Decoupled**: This skill does NOT call kernel-build. It expects user to provide pre-compiled kernel.

### 3. jffs2-analyzer Skill

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

**Examples**:
```
/jffs2-analyzer /path/to/jffs2.img
/jffs2-analyzer test.jffs2 --output analysis_results
```

**Decoupled**: Standalone Python-based analysis, no dependencies on kernel-build or qemu-test.

### 4. jffs2-mount Skill

**Location**: `skills/jffs2-mount/`

Mount JFFS2 filesystem images in QEMU for dynamic verification.

**Key Features**:
- Create JFFS2 test images (mkfs.jffs2 or blank)
- Setup MTD device in QEMU (mtdram method recommended)
- Load JFFS2 module and mount filesystem
- Verify mount success and file access

**Usage**:
```
/jffs2-mount --kernel <path> [--image <path>] [--size <MB>] [--mount-test]
```

**Examples**:
```
/jffs2-mount --kernel arch/arm64/boot/Image --mount-test
/jffs2-mount --kernel Image --image custom.jffs2 --arch arm64
/jffs2-mount --kernel bzImage --size 32 --content ./data
```

**Recommended**: Use mtdram instead of block2mtd to avoid loop device issues.

**Decoupled**: This skill is COMPLETELY INDEPENDENT from:
- kernel-build (requires user-provided kernel)
- qemu-test (has its own QEMU launch logic)
- jffs2-analyzer (complementary - analyze first, then mount)

### 5. jffs2-fault-inject Skill

**Location**: `skills/jffs2-fault-inject/`

Inject various faults into JFFS2 filesystem images for testing kernel fault handling.

**Key Features**:
- Inject CRC errors (hdr_crc, node_crc, data_crc, name_crc)
- Inject magic number corruption (0xDEAD)
- Inject invalid node types
- Generate fault injection report JSON
- Compatible with jffs2-analyzer for validation

**Usage**:
```
/jffs2-fault-inject --image <path> [--fault <type>] [--output <dir>]
```

**Fault Types**:
- `hdr_crc`: Corrupt node header CRC
- `node_crc`: Corrupt node structure CRC
- `data_crc`: Corrupt data payload CRC
- `name_crc`: Corrupt dirent name CRC
- `magic`: Invalid magic number (0xDEAD)
- `nodetype`: Invalid node type
- `version_zero`: Zero version field

**Examples**:
```
/jffs2-fault-inject --image normal.jffs2 --fault hdr_crc,node_crc,magic
/jffs2-fault-inject --image test.jffs2 --fault all --output fault_output
```

**Decoupled**: Standalone Python-based fault injection, can be used before jffs2-analyzer or jffs2-mount.

### 6. rag-case-retrieval Skill

**Location**: `skills/rag-case-retrieval/`

RAG-based semantic case retrieval from Chroma vector database.

**Key Features**:
- Multi-source data import (PostgreSQL, JSON, CSV)
- Intelligent text chunking (semantic boundaries + overlap)
- OpenAI Embedding vectorization
- Chroma vector storage and retrieval
- Metadata filtering (time, category, tags)
- Structured JSON output (top-3 cases)

**Prerequisites**:
- Chroma Docker service running on localhost:8000
- OpenAI API Key configured
- Python dependencies: chromadb, openai, psycopg2-binary

**Usage**:
```
# Import cases from database
python skills/rag-case-retrieval/scripts/import_cases.py --source database

# Import from JSON file
python skills/rag-case-retrieval/scripts/import_cases.py --source json --file cases.json

# Retrieve similar cases
python skills/rag-case-retrieval/scripts/retrieve_cases.py "JWT认证失败" --top-k 3

# Retrieve with filters
python skills/rag-case-retrieval/scripts/retrieve_cases.py "性能优化" \
  --filters '{"category": "性能", "created_at": {"$gte": "2024-01-01"}}'
```

**Output Format**:
```json
{
  "query": "用户查询",
  "results": [
    {
      "id": "case_001",
      "title": "案例标题",
      "content": "案例内容",
      "similarity_score": 0.85,
      "metadata": {"category": "安全", "tags": ["JWT"]}
    }
  ],
  "summary": {
    "total_found": 3,
    "retrieval_time_ms": 245
  }
}
```

**Documentation**: See `docs/rag-case-retrieval-guide.md` for complete usage guide.

**Decoupled**: Standalone Python-based RAG system, no dependencies on other skills.

**Workflow Integration**: Users can combine skills as needed:
```
# Option 1: Full fault testing workflow
/kernel-build JFFS2_FS --arch arm64 --cross
/jffs2-fault-inject --image normal.jffs2 --fault hdr_crc,magic
/jffs2-analyzer corrupted.jffs2
/jffs2-mount --kernel arch/arm64/boot/Image --image corrupted.jffs2

# Option 2: Each skill independently
/kernel-build UB --arch x86_64           # Just build
/qemu-test --arch arm64 --interactive    # Just boot
/jffs2-analyzer image.jffs2              # Just analyze
/jffs2-fault-inject --image test.jffs2   # Just inject faults
/jffs2-mount --kernel Image --mount-test # Just mount

# Option 3: RAG case retrieval workflow
python skills/rag-case-retrieval/scripts/check_environment.py
python skills/rag-case-retrieval/scripts/import_cases.py --source database
python skills/rag-case-retrieval/scripts/retrieve_cases.py "查询文本" --top-k 3
```

Build the Linux kernel with custom CONFIG options (tested with openEuler kernel).

**Key Features**:
- ARM64/ARM32/x86_64 architecture support
- Native and cross-compilation
- Automatic toolchain detection
- Auto defconfig detection (prefers openeuler_defconfig)

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

**Output**:
- Kernel Image (arch/arm64/boot/Image, arch/x86/boot/bzImage)
- Kernel Modules (*.ko files)

**Important**: Kernel and modules must be compiled in the SAME build session to ensure version matching.

### qemu-test Skill

Boot kernels in QEMU and run automated tests.

**Key Features**:
- Multi-architecture QEMU support (ARM64/ARM32/x86_64)
- Minimal initramfs creation with busybox
- Module loading tests
- Automated test script execution

**Usage**:
```
/kemu-test --arch arm64 --kernel <path> --modules <path> [--script <path>]
```

**Examples**:
```
/qemu-test --arch arm64 --interactive
/qemu-test --script tests/jffs2_test.sh --timeout 60
/qemu-test --kernel arch/x86/boot/bzImage --arch x86_64
```

## Workflow Example

Complete build and test cycle:

```
# Step 1: Build kernel with module
/kernel-build JFFS2_FS --arch arm64 --cross

# Step 2: Test in QEMU
/qemu-test --arch arm64 --kernel arch/arm64/boot/Image --modules fs/jffs2/jffs2.ko
```

## Installation

### Prerequisites

**Build Requirements**:
- GCC toolchain (native or cross)
- Kernel source code (Linux kernel, openEuler kernel recommended)
- Build dependencies: bc, bison, flex, libssl-dev

**QEMU Requirements**:
- qemu-system-aarch64 (ARM64)
- qemu-system-arm (ARM32)
- qemu-system-x86_64 (x86_64)
- ARM64 static busybox for cross-architecture testing

**RAG Retrieval Requirements**:
- Python 3.8+
- Chroma Docker service (chromadb/chroma image)
- OpenAI API Key
- PostgreSQL client libraries (for database import)

**Cross-Compilation Toolchain** (Ubuntu/Debian):
```bash
sudo apt install gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu  # ARM64
sudo apt install gcc-arm-linux-gnueabi binutils-arm-linux-gnueabi  # ARM32
```

**QEMU Installation**:
```bash
sudo apt install qemu-system-arm qemu-system-x86
```

**RAG Dependencies**:
```bash
pip install chromadb openai psycopg2-binary
docker run -d -p 8000:8000 --name chroma chromadb/chroma
export OPENAI_API_KEY='your-api-key-here'
```

### Busybox Installation (Critical for QEMU Testing)

The qemu-test skill requires busybox to create minimal initramfs. **For cross-architecture testing, you need architecture-matched busybox.**

#### Native Architecture (Simple Install)

For same-architecture testing (e.g., x86_64 host → x86_64 QEMU):

```bash
# Ubuntu/Debian
sudo apt install busybox-static

# CentOS/RHEL
sudo yum install busybox

# Verify static linking
ldd /bin/busybox
# Expected: "not a dynamic executable" (static)
```

#### Cross-Architecture Busybox Compilation

For cross-architecture testing (e.g., x86_64 host → ARM64/ARM32 QEMU), compile busybox for target architecture:

**Prerequisites**:
```bash
# Download busybox source
wget https://busybox.net/downloads/busybox-1.36.1.tar.bz2
tar -xjf busybox-1.36.1.tar.bz2
cd busybox-1.36.1
```

**ARM64 Busybox**:
```bash
# Configure for ARM64
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- defconfig

# Enable static compilation
sed -i 's/# CONFIG_STATIC is not set/CONFIG_STATIC=y/' .config

# Build
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j$(nproc)

# Result: busybox (ARM64 static, ~969K)
file busybox
# Expected: ELF 64-bit LSB executable, ARM aarch64, version 1 (GNU/Linux), statically linked
```

**ARM32 Busybox**:
```bash
# Configure for ARM32
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabi- defconfig

# Enable static compilation
sed -i 's/# CONFIG_STATIC is not set/CONFIG_STATIC=y/' .config

# Build
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabi- -j$(nproc)

# Result: busybox (ARM32 static, ~900K)
file busybox
# Expected: ELF 32-bit LSB executable, ARM, version 1 (GNU/Linux), statically linked
```

**Installation for QEMU Testing**:
```bash
# Create directory for cross-arch busybox
mkdir -p ~/.local/share/qemu-busybox

# Copy compiled busybox
cp busybox ~/.local/share/qemu-busybox/busybox-arm64  # For ARM64
cp busybox ~/.local/share/qemu-busybox/busybox-arm32  # For ARM32

# Update create_initramfs.sh or use custom busybox path
# Option 1: Set BUSYBOX_PATH environment variable
export BUSYBOX_PATH=~/.local/share/qemu-busybox/busybox-arm64

# Option 2: Modify create_initramfs.sh to detect architecture
```

#### Architecture Compatibility Matrix

| Host Arch | QEMU Arch | Busybox Required | Size |
|-----------|-----------|------------------|------|
| x86_64 | x86_64 | x86_64 (native) | ~1.0M |
| x86_64 | ARM64 | ARM64 (cross-compile) | ~969K |
| x86_64 | ARM32 | ARM32 (cross-compile) | ~900K |
| ARM64 | ARM64 | ARM64 (native) | ~969K |
| ARM32 | ARM32 | ARM32 (native) | ~900K |

#### Common Busybox Issues

**Problem**: x86-64 busybox in ARM64 QEMU
```
/modules/jffs2.ko: line 1: ELF...: not found
insmod: can't insert '/modules/jffs2.ko': exec format error
```

**Solution**: Compile ARM64 static busybox (see above).

**Problem**: Dynamic-linked busybox missing libraries
```
/bin/sh: No such file or directory
init: exec failed: /bin/sh
```

**Solution**: Use static-linked busybox (`CONFIG_STATIC=y`).

### Installing Skills

Copy all 6 skill directories to Claude Code skills directory:
```bash
mkdir -p ~/.claude/skills
cp -r skills/kernel-build ~/.claude/skills/
cp -r skills/qemu-test ~/.claude/skills/
cp -r skills/jffs2-analyzer ~/.claude/skills/
cp -r skills/jffs2-mount ~/.claude/skills/
cp -r skills/jffs2-fault-inject ~/.claude/skills/
cp -r skills/rag-case-retrieval ~/.claude/skills/
```

**Verification**:
```bash
ls ~/.claude/skills/
# Expected: kernel-build qemu-test jffs2-analyzer jffs2-mount jffs2-fault-inject rag-case-retrieval
```

## Directory Structure

```
Analysis-SKILL/
├── README.md                       # 项目总览
├── skills/                         # 6个独立技能
│   ├── kernel-build/SKILL.md       # Skill 1: 内核编译
│   ├── qemu-test/SKILL.md          # Skill 2: QEMU启动
│   ├── jffs2-analyzer/SKILL.md     # Skill 3: JFFS2静态分析
│   ├── jffs2-mount/SKILL.md        # Skill 4: JFFS2挂载测试
│   ├── jffs2-fault-inject/SKILL.md # Skill 5: 故障注入
│   └── rag-case-retrieval/SKILL.md # Skill 6: RAG案例检索
├── docs/                           # 用户文档
│   ├── VERIFICATION_REPORT.md      # 验证报告（合并ARM32/ARM64）
│   ├── kernel-build-validation.md  # Kernel Build验证
│   ├── OPTIMIZATION_HISTORY.md     # 优化历程
│   ├── TESTING_ISSUES_AND_SOLUTIONS.md  # 测试问题总结
│   ├── cross_arch_busybox_analysis.md   # 跨架构busybox指南
│   ├── jffs2-analyzer-guide.md     # JFFS2 Analyzer使用指南
│   └ rag-case-retrieval-guide.md   # RAG检索使用指南
└── tools/                          # 辅助工具
```

## 文档说明

| 文档 | 内容 | 适合人群 |
|------|------|---------|
| VERIFICATION_REPORT.md | 端到端验证结果 | 查看测试状态 |
| kernel-build-validation.md | Kernel Build测试 | 内核编译验证 |
| OPTIMIZATION_HISTORY.md | Skills版本迭代 | 了解演进历史 |
| TESTING_ISSUES_AND_SOLUTIONS.md | 问题解决方案 | 排错参考 |
| cross_arch_busybox_analysis.md | Busybox编译指南 | 跨架构测试 |
| jffs2-analyzer-guide.md | Analyzer使用指南 | JFFS2分析入门 |
| rag-case-retrieval-guide.md | RAG检索完整指南 | 案例检索入门 |
│       ├── scripts/
## Skill Architecture & Decoupling

All 6 skills are **completely decoupled**:

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                             Independent Skills                                     │
├───────────────────────────────────────────────────────────────────────────────────┤
│  kernel-build  │ qemu-test    │ jffs2-analyzer │ jffs2-mount │ jffs2-fault-inject│ rag-case-retrieval │
│  ────────────  │ ──────────   │ ─────────────  │ ──────────  │ ───────────────── │ ──────────────────  │
│  Compile kernel│ Boot kernel  │ Static analysis│ Mount test  │ Inject faults     │ RAG retrieval       │
│  Output: Image │ Requires:Img │ Input: jffs2   │ Requires:   │ Input: jffs2      │ Input: query        │
│  + modules     │ (user prov)  │ Output: report │ Image+kernel│ Output: corrupted │ Output: JSON cases   │
│                │ Output: logs │                │ (user prov) │ jffs2 + report    │                     │
│  No calls to:  │ No calls to: │ No calls to:   │ No calls to:│ No calls to:      │ No calls to:        │
│  other skills  │ kernel-build │ other skills   │ other skills│ other skills      │ other skills        │
└───────────────────────────────────────────────────────────────────────────────────┘

Users combine skills as needed:
  Step 1: /kernel-build JFFS2_FS --arch arm64 (optional)
  Step 2: /jffs2-fault-inject --image test.jffs2 --fault hdr_crc,magic
  Step 3: /jffs2-analyzer corrupted.jffs2          (independent)
  Step 4: /jffs2-mount --kernel Image --mount      (independent)
  Step 5: /qemu-test --kernel Image                (independent)
  Step 6: python retrieve_cases.py "JWT认证失败"   (independent)
```

## Key Technical Notes

### Critical Lessons from Testing

Based on ARM64 end-to-end verification (2026-05-18):

| Lesson | Issue | Solution |
|--------|-------|----------|
| **Architecture Matching** | x86-64 busybox fails in ARM64 QEMU | Cross-compile busybox for target arch |
| **Interactive Config** | `make defconfig` prompts hundreds of options | Use `make allnoconfig` + sed + `yes ""` |
| **Applet Missing** | Scripts fail: `command not found` | Enable all required applets in busybox |
| **Tail Options** | `tail -10` doesn't work | Enable `CONFIG_FEATURE_TAIL_USE_F` |
| **Module Version** | Kernel/module mismatch fails | Compile kernel+modules in same session |
| **MTD Dependency** | JFFS2 needs MTD device | Setup block2mtd/mtdram before mount |

### Busybox Requirements for QEMU Testing

**Minimum applets checklist** (based on real testing):

| Category | Applets | Purpose |
|----------|---------|---------|
| Shell | `sh`, `ash`, `test`, `[` | Script execution |
| Basic | `cat`, `ls`, `mkdir`, `sleep` | File operations |
| Mount | `mount`, `umount`, `mknod` | Filesystem |
| System | `poweroff`, `reboot`, `dmesg` | Control |
| Modules | `insmod`, `lsmod`, `rmmod` | Kernel modules |
| Info | `uname`, `grep`, `date` | Information |
| Logs | `tail` (with features) | Log viewing |

**Automated cross-compilation tool**: `tools/build_busybox.sh`

```bash
# Build ARM64 busybox with all required applets
./tools/build_busybox.sh --arch arm64

# Build with custom applets
./tools/build_busybox.sh --arch arm64 --applets wget,curl,vi
```

### Version Matching

**Critical**: Kernel and modules must have matching vermagic.

Problem example:
```
Kernel:  X.Y.Z-36583-gabc123-dirty
Module:  X.Y.Z+ (vermagic mismatch)
Result:  insmod fails with "invalid module format"
```

Solution: Build kernel and modules in single session (kernel-build skill does this correctly).

### MTD Dependency for JFFS2

JFFS2 requires MTD subsystem:
```
# Load MTD first, then JFFS2
insmod mtd.ko
insmod jffs2.ko
```

### Cross-Architecture Busybox

ARM64 QEMU requires ARM64-compiled busybox:
```
# Cross-compile busybox for ARM64
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- defconfig
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j$(nproc)
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- install
```

Result: ARM64 static busybox (~969K)

## Testing Examples

### JFFS2 Module Test

Build and test JFFS2 filesystem module:
```bash
# Build
/kernel-build JFFS2_FS --arch arm64 --cross

# Test
/qemu-test --arch arm64 --script tests/jffs2_load.sh
```

Expected output:
```
✓ mtd.ko loaded
✓ jffs2.ko loaded successfully
jffs2 147456 0 - Live 0xffffad6d0ec8a000
```

### RAG Case Retrieval Test

Import cases and perform semantic retrieval:
```bash
# Setup environment
cd skills/rag-case-retrieval
python scripts/check_environment.py

# Import cases from JSON
python scripts/import_cases.py --source json --file test_cases.json --collection cases

# Retrieve similar cases
python scripts/retrieve_cases.py "JWT认证失败案例" --top-k 3 --min-similarity 0.7
```

Expected output:
```json
{
  "status": "success",
  "query": "JWT认证失败案例",
  "results": [
    {
      "id": "case_001",
      "title": "JWT令牌过期处理不当",
      "similarity_score": 0.89
    }
  ],
  "summary": {
    "total_found": 3,
    "retrieval_time_ms": 245
  }
}
```

## Documentation

- **skills/kernel-build/SKILL.md**: Complete kernel-build skill definition
- **skills/qemu-test/SKILL.md**: Complete qemu-test skill definition
- **skills/jffs2-analyzer/SKILL.md**: JFFS2 static analysis skill
- **skills/jffs2-mount/SKILL.md**: JFFS2 mount testing skill
- **skills/jffs2-fault-inject/SKILL.md**: JFFS2 fault injection skill
- **skills/rag-case-retrieval/SKILL.md**: RAG case retrieval skill
- **docs/E2E_VERIFICATION_REPORT.md**: ARM64 end-to-end verification report
- **docs/cross_arch_busybox_analysis.md**: Cross-architecture busybox solution
- **docs/rag-case-retrieval-guide.md**: Complete RAG retrieval usage guide

## Contributing

To add new skills or improve existing ones:
1. Create skill directory under `skills/<skill-name>/`
2. Add SKILL.md with skill definition (frontmatter + content)
3. Include supporting scripts in `scripts/` subdirectory
4. Add documentation in `docs/`
5. Update README.md

## License

Linux kernel follows GPL v2 license.
Skills and tools in this repository are provided under MIT license.

## Authors

- Kernel Build Skill: Developed for Linux kernel cross-compilation workflow
- QEMU Test Skill: Created for kernel verification automation
- End-to-end validation: Completed 2026-05-18

## References

- Kernel Documentation: Documentation/process/coding-style.rst
- QEMU Documentation: https://www.qemu.org/docs/
## Verification Results

### ARM64 End-to-End Test ✅

| Item | Result | Details |
|------|--------|---------|
| Kernel | ✅ Pass | Image (37M) |
| jffs2.ko | ✅ Pass | Module load successful |
| MTD | ✅ Pass | mtd.ko + jffs2.ko loaded |
| QEMU Boot | ✅ Pass | Shell entered |

**Test Date**: 2026-05-18
**Report**: docs/E2E_VERIFICATION_REPORT.md

### ARM32 End-to-End Test ✅

| Item | Result | Details |
|------|--------|---------|
| Kernel | ✅ Pass | zImage (11M) |
| jffs2.ko | ✅ Pass | Module load successful (149K) |
| MTD | ✅ Pass | Built-in (CONFIG_MTD=y) |
| QEMU Boot | ✅ Pass | Shell entered |

**Key Difference**: ARM32 MTD is built-in, no need for mtd.ko module.
**Test Date**: 2026-05-18
**Report**: docs/ARM32_E2E_REPORT.md

### Architecture Comparison

| Feature | ARM64 | ARM32 |
|---------|-------|-------|
| Kernel Image | Image (37M) | zImage (11M) |
| jffs2.ko Size | 5.9M | 149K |
| MTD Config | Module (m) | Built-in (y) |
| Busybox Size | 969K | 2.1M |
| Toolchain | aarch64-linux-gnu- | arm-linux-gnueabi- |

