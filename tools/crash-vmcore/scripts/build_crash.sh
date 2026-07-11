#!/bin/bash
# build_crash.sh - Build crash utility from source
# Usage: ./build_crash.sh [--arch x86_64|arm64] [--clean] [--source-dir <path>] [--output <path>] [--repo-url <url>] [--repo-ref <ref>]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_DIR="$(dirname "$SCRIPT_DIR")"
BIN_DIR="${TOOL_DIR}/bin"

ARCH="x86_64"
CLEAN=false
JOBS=$(nproc)
SOURCE_DIR=""
OUTPUT_PATH=""
REPO_URL="https://github.com/crash-utility/crash.git"
REPO_REF=""
CUSTOM_SOURCE_DIR=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --arch)
            ARCH="$2"
            shift 2
        ;;
        --clean)
            CLEAN=true
            shift
        ;;
        --jobs)
            JOBS="$2"
            shift 2
        ;;
        --source-dir)
            SOURCE_DIR="$2"
            CUSTOM_SOURCE_DIR=true
            shift 2
        ;;
        --output)
            OUTPUT_PATH="$2"
            shift 2
        ;;
        --repo-url)
            REPO_URL="$2"
            shift 2
        ;;
        --repo-ref)
            REPO_REF="$2"
            shift 2
        ;;
        --help)
            echo "Usage: ./build_crash.sh [--arch x86_64|arm64] [--clean] [--jobs N] [--source-dir <path>] [--output <path>] [--repo-url <url>] [--repo-ref <ref>]"
            echo ""
            echo "Defaults preserve crash-vmcore standalone behavior:"
            echo "  source-dir: ${TOOL_DIR}/crash-source"
            echo "  output:     ${BIN_DIR}/crash"
            exit 0
        ;;
        *)
            echo "Unknown option: $1"
            exit 1
        ;;
    esac
done

if [ -z "$SOURCE_DIR" ]; then
    SOURCE_DIR="${TOOL_DIR}/crash-source"
fi
if [ -z "$OUTPUT_PATH" ]; then
    OUTPUT_PATH="${BIN_DIR}/crash"
fi
SOURCE_DIR="$(mkdir -p "$(dirname "$SOURCE_DIR")" && cd "$(dirname "$SOURCE_DIR")" && pwd)/$(basename "$SOURCE_DIR")"
OUTPUT_PATH="$(mkdir -p "$(dirname "$OUTPUT_PATH")" && cd "$(dirname "$OUTPUT_PATH")" && pwd)/$(basename "$OUTPUT_PATH")"

echo "=== Building Crash Utility ==="
echo "Architecture: $ARCH"
echo "Jobs: $JOBS"
echo "Clean: $CLEAN"
echo "Source: $SOURCE_DIR"
echo "Output: $OUTPUT_PATH"
echo "Repo: $REPO_URL"
echo "Repo ref: ${REPO_REF:-default}"
echo

# Check dependencies
echo "[1/5] Checking dependencies..."
for dep in gcc make bison; do
    if ! command -v $dep &> /dev/null; then
        echo "ERROR: Missing dependency: $dep"
        echo "Run: ./scripts/install_deps.sh"
        exit 1
    fi
done
echo "✓ Dependencies OK"

# Clone source
CRASH_SRC="$SOURCE_DIR"
echo
echo "[2/5] Getting crash source..."

if [ -d "$CRASH_SRC" ]; then
    if [ "$CLEAN" = true ]; then
        if [ "$CUSTOM_SOURCE_DIR" = true ]; then
            echo "Cleaning existing build artifacts..."
            (
                cd "$CRASH_SRC"
                make clean 2>/dev/null || true
                find . -maxdepth 1 -type d -name 'gdb-*' -exec rm -rf {} + 2>/dev/null || true
            )
        else
            echo "Cleaning existing source..."
            rm -rf "$CRASH_SRC"
        fi
    else
        echo "Using existing source: $CRASH_SRC"
        if [ -d "$CRASH_SRC/.git" ]; then
            cd "$CRASH_SRC"
            git pull || true
        fi
    fi
fi

if [ ! -f "$CRASH_SRC/Makefile" ]; then
    echo "Cloning crash repository..."
    rm -rf "$CRASH_SRC"
    git clone "$REPO_URL" "$CRASH_SRC"
    if [ -n "$REPO_REF" ]; then
        (cd "$CRASH_SRC" && git checkout "$REPO_REF")
    fi
fi

cd "$CRASH_SRC"

# Build
echo
echo "[3/5] Building crash..."
echo "This may take 3-5 minutes for initial GDB compilation..."

if [ "$CLEAN" = true ]; then
    make clean 2>/dev/null || true
    find . -maxdepth 1 -type d -name 'gdb-*' -exec rm -rf {} + 2>/dev/null || true
fi

START=$(date +%s)

if [ "$ARCH" = "x86_64" ]; then
    make target=X86_64 -j$JOBS
elif [ "$ARCH" = "arm64" ]; then
    make target=ARM64 -j$JOBS
else
    echo "ERROR: Unsupported architecture: $ARCH"
    exit 1
fi

END=$(date +%s)
BUILD_TIME=$((END - START))

echo "✓ Build completed in ${BUILD_TIME}s"

# Verify
echo
echo "[4/5] Verifying build..."

if [ ! -f "crash" ]; then
    echo "ERROR: crash binary not found"
    exit 1
fi

CRASH_VERSION=$(./crash -v 2>&1 | head -1)
GDB_VERSION=$(./crash -v 2>&1 | grep "GNU gdb" | awk '{print $4}')

echo "Version: $CRASH_VERSION"
echo "GDB: $GDB_VERSION"
echo "Size: $(ls -lh crash | awk '{print $5}')"

# Check if it's the required version
if [[ "$CRASH_VERSION" == *"9.0"* ]]; then
    echo "✓ Version 9.0+ detected (QEMU vmcore compatible)"
else
    echo "⚠ Version may not support QEMU vmcore analysis"
fi

# Install to bin directory
echo
echo "[5/5] Installing..."

mkdir -p "$(dirname "$OUTPUT_PATH")"
cp crash "$OUTPUT_PATH"
chmod +x "$OUTPUT_PATH"

echo "✓ Installed to: $OUTPUT_PATH"

# Summary
echo
echo "=== Build Summary ==="
echo "Source: $CRASH_SRC"
echo "Binary: $OUTPUT_PATH"
echo "Version: $CRASH_VERSION"
echo "GDB: $GDB_VERSION"
echo "Build Time: ${BUILD_TIME}s"
echo
echo "To use:"
echo "  $OUTPUT_PATH vmlinux vmcore.elf"
