#!/bin/bash
# Busybox Cross-Compilation Helper Script
# Solves: architecture mismatch, interactive config, applet missing issues
# Usage: build_busybox.sh --arch <arch> [--output <path>] [--applets <list>] [--clean]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCH=""
OUTPUT_PATH=""
CUSTOM_APPLETS=""
BUSYBOX_VERSION="1.36.1"
# 优先使用项目内源码
BUNDLED_SOURCE="${SCRIPT_DIR}/busybox/busybox-${BUSYBOX_VERSION}.tar.bz2"
DOWNLOAD_URL="https://busybox.net/downloads/busybox-${BUSYBOX_VERSION}.tar.bz2"
CLEAN_BUILD=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --arch)
            ARCH="$2"
            shift 2
        ;;
        --output)
            OUTPUT_PATH="$2"
            shift 2
        ;;
        --applets)
            CUSTOM_APPLETS="$2"
            shift 2
        ;;
        --clean)
            CLEAN_BUILD=true
            shift
        ;;
        --help)
            echo "Usage: build_busybox.sh --arch <arch> [--output <path>] [--applets <list>] [--clean]"
            echo ""
            echo "Architectures: arm64, arm32, x86_64"
            echo "Output: Path to save compiled busybox (default: tools/busybox/prebuilt/busybox_<arch>)"
            echo "Applets: Comma-separated list of additional applets"
            echo "Clean: Remove previous build for this architecture before compiling"
            echo ""
            echo "Example:"
            echo "  build_busybox.sh --arch arm64"
            echo "  build_busybox.sh --arch arm64 --clean"
            echo "  build_busybox.sh --arch arm64 --output /tmp/busybox_arm64"
            echo "  build_busybox.sh --arch arm32 --applets wget,curl,vi"
            exit 0
        ;;
        *)
            echo "Unknown option: $1"
            exit 1
        ;;
    esac
done

if [ -z "$ARCH" ]; then
    echo "ERROR: --arch required"
    echo "Usage: build_busybox.sh --arch arm64|arm32|x86_64"
    exit 1
fi

# Map architecture to kernel ARCH and cross-compile prefix
case "$ARCH" in
    arm64|aarch64)
        KERNEL_ARCH="arm64"
        CROSS_COMPILE="aarch64-linux-gnu-"
        BUSYBOX_ARCH="aarch64"
    ;;
    arm32|arm)
        KERNEL_ARCH="arm"
        CROSS_COMPILE="arm-linux-gnueabi-"
        BUSYBOX_ARCH="arm"
    ;;
    x86_64|x86)
        KERNEL_ARCH="x86"
        CROSS_COMPILE=""
        BUSYBOX_ARCH="x86_64"
    ;;
    *)
        echo "ERROR: Unsupported architecture: $ARCH"
        exit 1
    ;;
esac

# Default output path - use prebuilt directory
if [ -z "$OUTPUT_PATH" ]; then
    OUTPUT_PATH="${SCRIPT_DIR}/busybox/prebuilt/busybox_${ARCH}"
fi

echo "=== Busybox Cross-Compilation Helper ==="
echo "  Target: $ARCH"
echo "  Kernel ARCH: $KERNEL_ARCH"
echo "  Cross-compile: $CROSS_COMPILE"
echo "  Output: $OUTPUT_PATH"
echo ""

# Check toolchain for cross-compilation
if [ -n "$CROSS_COMPILE" ]; then
    if ! command -v "${CROSS_COMPILE}gcc" >/dev/null; then
        echo "ERROR: Cross-compiler not found: ${CROSS_COMPILE}gcc"
        echo ""
        echo "Install toolchain:"
        case "$ARCH" in
            arm64) echo "  Ubuntu: sudo apt install gcc-aarch64-linux-gnu" ;;
            arm32) echo "  Ubuntu: sudo apt install gcc-arm-linux-gnueabi" ;;
        esac
        exit 1
    fi
    echo "✓ Cross-compiler found: ${CROSS_COMPILE}gcc"
fi

# Clean previous build if requested
BUILD_DIR="/tmp/busybox_build_${ARCH}"
if [ "$CLEAN_BUILD" = true ]; then
    echo "[Clean] Removing previous build for $ARCH..."
    rm -rf "$BUILD_DIR"
    rm -f "$OUTPUT_PATH"
    echo "✓ Cleaned: $BUILD_DIR and $OUTPUT_PATH"
fi

# Download busybox if not exists - prefer bundled source
if [ ! -d "$BUILD_DIR/busybox-${BUSYBOX_VERSION}" ]; then
    echo "[Source] Getting busybox source..."
    mkdir -p "$BUILD_DIR"
    cd "$BUILD_DIR"

    # 优先使用项目内源码
    if [ -f "$BUNDLED_SOURCE" ]; then
        echo "✓ Using bundled source: $BUNDLED_SOURCE"
        cp "$BUNDLED_SOURCE" "busybox-${BUSYBOX_VERSION}.tar.bz2"
    else
        if [ ! -f "busybox-${BUSYBOX_VERSION}.tar.bz2" ]; then
            echo "  Bundled source not found, downloading..."
            wget -q "$DOWNLOAD_URL" || {
                echo "ERROR: Failed to download busybox"
                exit 1
            }
        fi
    fi

    tar xf "busybox-${BUSYBOX_VERSION}.tar.bz2"
    echo "✓ Source extracted: $BUILD_DIR/busybox-${BUSYBOX_VERSION}"
fi

cd "$BUILD_DIR/busybox-${BUSYBOX_VERSION}"

# Step 1: Create minimal configuration (avoid interactive prompts)
echo "[Config] Creating minimal configuration..."
make ARCH=$KERNEL_ARCH CROSS_COMPILE=$CROSS_COMPILE allnoconfig >/dev/null 2>&1

# Step 2: Enable static linking (critical for initramfs)
echo "[Config] Enabling static linking..."
sed -i 's/# CONFIG_STATIC is not set/CONFIG_STATIC=y/' .config

# Step 3: Enable required applets based on key experience
# Core applets needed for QEMU kernel testing
CORE_APPLETS=(
    # Shell and scripting
    "ASH" "SH_IS_ASH" "TEST" "ECHO" "SLEEP"

    # Basic file operations
    "CAT" "LS" "HEAD" "TAIL" "MKDIR" "RM" "CP" "MV"

    # System operations
    "MOUNT" "UMOUNT" "MKNOD" "LOSETUP"

    # System control
    "POWEROFF" "REBOOT" "DMESG"

    # Module operations (for kernel testing)
    "INSMOD" "LSMOD" "RMMOD"

    # Information
    "UNAME" "GREP" "DATE" "TRUE" "FALSE"
)

echo "[Config] Enabling core applets (${#CORE_APPLETS[@]} items)..."
for applet in "${CORE_APPLETS[@]}"; do
    sed -i "s/# CONFIG_${applet} is not set/CONFIG_${applet}=y/" .config
done

# Enable tail features (fixes "tail: invalid option" issue)
sed -i 's/# CONFIG_FEATURE_TAIL_USE_F is not set/CONFIG_FEATURE_TAIL_USE_F=y/' .config

# Enable shell math support (fixes "$((arith)) is disabled" in init scripts
sed -i 's/# CONFIG_FEATURE_SH_MATH is not set/CONFIG_FEATURE_SH_MATH=y/' .config
sed -i 's/# CONFIG_FEATURE_SH_MATH_64 is not set/CONFIG_FEATURE_SH_MATH_64=y/' .config

# Enable standalone shell mode (faster applet dispatch, no PATH lookups)
sed -i 's/# CONFIG_FEATURE_SH_STANDALONE is not set/CONFIG_FEATURE_SH_STANDALONE=y/' .config
sed -i 's/# CONFIG_FEATURE_SH_NOFORK is not set/CONFIG_FEATURE_SH_NOFORK=y/' .config

# Step 4: Add custom applets if specified
if [ -n "$CUSTOM_APPLETS" ]; then
    echo "[Config] Adding custom applets: $CUSTOM_APPLETS"
    IFS=',' read -ra EXTRA_APPLETS <<< "$CUSTOM_APPLETS"
    for applet in "${EXTRA_APPLETS[@]}"; do
        APPLET_UPPER=$(echo "$applet" | tr '[:lower:]' '[:upper:]')
        sed -i "s/# CONFIG_${APPLET_UPPER} is not set/CONFIG_${APPLET_UPPER}=y/" .config
    done
fi

# Step 5: Resolve config dependencies (avoid interactive prompts)
echo "[Config] Resolving dependencies..."
yes "" | make ARCH=$KERNEL_ARCH CROSS_COMPILE=$CROSS_COMPILE oldconfig >/dev/null 2>&1

# Verify key applets are enabled
echo "[Verify] Checking applets configuration..."
CHECK_APPLETS="ASH CAT LS MOUNT INSMOD DMESG POWEROFF TEST TAIL DATE"
for applet in $CHECK_APPLETS; do
    if grep -q "^CONFIG_${applet}=y" .config; then
        echo "  ✓ CONFIG_${applet}=y"
    else
        echo "  ✗ CONFIG_${applet} missing"
    fi
done

# Step 6: Compile busybox
echo "[Build] Compiling busybox..."
START_TIME=$(date +%s)
make ARCH=$KERNEL_ARCH CROSS_COMPILE=$CROSS_COMPILE -j$(nproc) 2>&1 | \
    grep -E "CC|LD|LINK|Error|error:" | tail -20

END_TIME=$(date +%s)
BUILD_TIME=$((END_TIME - START_TIME))

if [ ! -f "busybox" ]; then
    echo "✗ Build failed"
    exit 1
fi

# Step 7: Verify binary
echo "[Verify] Checking compiled busybox..."
BUSYBOX_INFO=$(file busybox)
echo "  $BUSYBOX_INFO"

# Check architecture match
if [ "$ARCH" = "arm64" ]; then
    if echo "$BUSYBOX_INFO" | grep -q "ARM aarch64"; then
        echo "  ✓ Architecture matches: ARM64"
    else
        echo "  ✗ Architecture mismatch!"
        exit 1
    fi
elif [ "$ARCH" = "arm32" ]; then
    if echo "$BUSYBOX_INFO" | grep -q "ARM,"; then
        echo "  ✓ Architecture matches: ARM32"
    else
        echo "  ✗ Architecture mismatch!"
        exit 1
    fi
elif [ "$ARCH" = "x86_64" ]; then
    if echo "$BUSYBOX_INFO" | grep -q "x86-64"; then
        echo "  ✓ Architecture matches: x86_64"
    else
        echo "  ✗ Architecture mismatch!"
        exit 1
    fi
fi

# Check static linking
if echo "$BUSYBOX_INFO" | grep -q "statically linked"; then
    echo "  ✓ Static linking confirmed"
else
    echo "  ✗ Not statically linked (may fail in initramfs)"
fi

# Step 8: Copy to output
echo "[Output] Saving busybox..."
mkdir -p "$(dirname $OUTPUT_PATH)"
cp busybox "$OUTPUT_PATH"
chmod +x "$OUTPUT_PATH"

# Get size
SIZE=$(du -h "$OUTPUT_PATH" | cut -f1)
echo "✓ Busybox saved: $OUTPUT_PATH ($SIZE)"
echo ""
echo "=== Build Summary ==="
echo "  Architecture: $ARCH"
echo "  Build time: ${BUILD_TIME}s"
echo "  Applets: ${#CORE_APPLETS[@]} core + ${EXTRA_APPLETS:-0} custom"
echo "  Static: yes"
echo "  Location: $OUTPUT_PATH"
echo ""

# Step 9: Show usage
echo "Usage in initramfs:"
echo "  cp $OUTPUT_PATH initramfs/bin/busybox"
echo "  cd initramfs/bin && ln -sf busybox sh"
echo ""
echo "For QEMU testing:"
echo "  /qemu-test --arch $ARCH --kernel <Image> --initrd <initramfs>"
echo ""

exit 0