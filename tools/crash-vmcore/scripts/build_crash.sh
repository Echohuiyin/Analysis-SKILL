#!/bin/bash
# build_crash.sh - Build crash utility from source
# Usage: ./build_crash.sh [--arch x86_64|arm64] [--clean]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_DIR="$(dirname "$SCRIPT_DIR")"
BIN_DIR="${TOOL_DIR}/bin"

ARCH="x86_64"
CLEAN=false
JOBS=$(nproc)

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
        *)
            echo "Unknown option: $1"
            exit 1
        ;;
    esac
done

echo "=== Building Crash Utility ==="
echo "Architecture: $ARCH"
echo "Jobs: $JOBS"
echo "Clean: $CLEAN"
echo "Output: $BIN_DIR"
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
CRASH_SRC="${TOOL_DIR}/crash-source"
echo
echo "[2/5] Getting crash source..."

if [ -d "$CRASH_SRC" ]; then
    if [ "$CLEAN" = true ]; then
        echo "Cleaning existing source..."
        rm -rf "$CRASH_SRC"
    else
        echo "Using existing source: $CRASH_SRC"
        cd "$CRASH_SRC"
        git pull || true
    fi
fi

if [ ! -d "$CRASH_SRC" ]; then
    echo "Cloning crash repository..."
    # Try SSH first (faster)
    if git clone git@github.com:crash-utility/crash.git "$CRASH_SRC" 2>/dev/null; then
        echo "✓ Cloned via SSH"
    else
        echo "SSH failed, using HTTPS..."
        git clone https://github.com/crash-utility/crash.git "$CRASH_SRC"
    fi
fi

cd "$CRASH_SRC"

# Build
echo
echo "[3/5] Building crash..."
echo "This may take 3-5 minutes for initial GDB compilation..."

if [ "$CLEAN" = true ]; then
    make clean 2>/dev/null || true
    rm -rf gdb-* 2>/dev/null || true
fi

START=$(date +%s)

if [ "$ARCH" = "x86_64" ]; then
    make -j$JOBS
elif [ "$ARCH" = "arm64" ]; then
    make CROSS_COMPILE=aarch64-linux-gnu- -j$JOBS
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

CRASH_VERSION=$(./crash --version 2>&1 | head -1)
GDB_VERSION=$(./crash --version 2>&1 | grep "GNU gdb" | awk '{print $4}')

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

mkdir -p "$BIN_DIR"
cp crash "$BIN_DIR/crash"
chmod +x "$BIN_DIR/crash"

echo "✓ Installed to: $BIN_DIR/crash"

# Summary
echo
echo "=== Build Summary ==="
echo "Source: $CRASH_SRC"
echo "Binary: $BIN_DIR/crash"
echo "Version: $CRASH_VERSION"
echo "GDB: $GDB_VERSION"
echo "Build Time: ${BUILD_TIME}s"
echo
echo "To use:"
echo "  $BIN_DIR/crash vmlinux vmcore.elf"
echo
echo "To configure for Analysis-SKILL:"
echo "  echo 'CRASH_BINARY=$BIN_DIR/crash' >> .env"