#!/bin/bash
# JFFS2 mount test execution script
# Usage: mount_test.sh [--kernel <path>] [--initrd <path>] [--timeout <sec>]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KERNEL_PATH=""
INITRD_PATH=""
TIMEOUT=60
ARCH="arm64"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --kernel)
            KERNEL_PATH="$2"
            shift 2
        ;;
        --initrd)
            INITRD_PATH="$2"
            shift 2
        ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
        ;;
        --arch)
            ARCH="$2"
            shift 2
        ;;
        *)
            echo "Unknown option: $1"
            exit 1
        ;;
    esac
done

OUTPUT_DIR="${OUTPUT_DIR:-jffs2_mount_$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$OUTPUT_DIR/logs"

LOG_FILE="$OUTPUT_DIR/logs/mount_test.log"

echo "=== JFFS2 Mount Test Execution ==="
echo "  Kernel: $KERNEL_PATH"
echo "  Initrd: $INITRD_PATH"
echo "  Timeout: $TIMEOUT seconds"
echo "  Architecture: $ARCH"
echo ""

# Verify inputs
if [ ! -f "$KERNEL_PATH" ]; then
    echo "ERROR: Kernel not found at $KERNEL_PATH"
    exit 1
fi

if [ ! -f "$INITRD_PATH" ]; then
    echo "ERROR: Initrd not found at $INITRD_PATH"
    exit 1
fi

# Verify kernel architecture
KERNEL_ARCH=$(file "$KERNEL_PATH" | grep -o "ARM aarch64\|x86-64\|ARM," | head -1)
echo "  Kernel type: $KERNEL_ARCH"

# Determine QEMU command based on architecture
QEMU_CMD=""
QEMU_MACHINE=""
QEMU_CPU=""
CONSOLE_PARAM=""

case "$ARCH" in
    arm64|aarch64)
        QEMU_CMD="qemu-system-aarch64"
        QEMU_MACHINE="virt"
        QEMU_CPU="cortex-a57"
        CONSOLE_PARAM="console=ttyAMA0"
    ;;
    arm32|arm)
        QEMU_CMD="qemu-system-arm"
        QEMU_MACHINE="virt"
        QEMU_CPU="cortex-a15"
        CONSOLE_PARAM="console=ttyAMA0"
    ;;
    x86_64|x86)
        QEMU_CMD="qemu-system-x86_64"
        QEMU_MACHINE=""
        QEMU_CPU=""
        CONSOLE_PARAM="console=ttyS0"
    ;;
    *)
        echo "ERROR: Unsupported architecture: $ARCH"
        exit 1
    ;;
esac

# Verify QEMU available
if ! command -v "$QEMU_CMD" >/dev/null; then
    echo "ERROR: $QEMU_CMD not found"
    echo "Install: apt install qemu-system-${ARCH}"
    exit 1
fi

echo "✓ Environment ready"
echo "  QEMU: $QEMU_CMD"

# Execute QEMU mount test
echo ""
echo "Starting QEMU mount test..."

QEMU_ARGS=(
    "-M" "$QEMU_MACHINE"
    "-cpu" "$QEMU_CPU"
    "-smp" "2"
    "-m" "512M"
    "-nographic"
    "-kernel" "$KERNEL_PATH"
    "-initrd" "$INITRD_PATH"
    "-append" "$CONSOLE_PARAM root=/dev/ram rw"
)

if [ "$ARCH" = "x86_64" ]; then
    # x86_64 doesn't need -M and -cpu for basic virt machine
    QEMU_ARGS=(
        "-smp" "2"
        "-m" "512M"
        "-nographic"
        "-kernel" "$KERNEL_PATH"
        "-initrd" "$INITRD_PATH"
        "-append" "$CONSOLE_PARAM root=/dev/ram rw"
    )
fi

timeout "$TIMEOUT" "$QEMU_CMD" "${QEMU_ARGS[@]}" 2>&1 | tee "$LOG_FILE" || {
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ]; then
        echo ""
        echo "⚠ Test completed (timeout reached)"
    else
        echo ""
        echo "✗ QEMU exited with code $EXIT_CODE"
    fi
}

# Analyze results
echo ""
echo "=== Test Results Analysis ==="

# Check for successful module load
if grep -q "jffs2.ko loaded" "$LOG_FILE"; then
    echo "✓ JFFS2 module loaded successfully"
else
    echo "✗ JFFS2 module load failed or not attempted"
fi

# Check for filesystem registration
if grep -q "JFFS2 registered" "$LOG_FILE"; then
    echo "✓ JFFS2 filesystem registered"
else
    echo "✗ JFFS2 filesystem not registered"
fi

# Check for mount attempt
if grep -q "JFFS2 Mount Test" "$LOG_FILE"; then
    echo "✓ Mount test script executed"
else
    echo "✗ Mount test script not executed"
fi

# Check kernel boot
if grep -q "Linux version" "$LOG_FILE"; then
    KERNEL_VER=$(grep "Linux version" "$LOG_FILE" | head -1 | awk '{print $3}')
    echo "✓ Kernel booted: $KERNEL_VER"
else
    echo "✗ Kernel boot failed"
fi

# Generate summary
SUMMARY_FILE="$OUTPUT_DIR/summary.txt"
cat > "$SUMMARY_FILE" << EOF
JFFS2 Mount Test Summary
========================
Date: $(date)
Kernel: $KERNEL_PATH
Initrd: $INITRD_PATH
Architecture: $ARCH
Timeout: $TIMEOUT seconds

Test Results:
- Kernel boot: $(grep -q "Linux version" "$LOG_FILE" && echo "SUCCESS" || echo "FAILED")
- JFFS2 module: $(grep -q "jffs2.ko loaded" "$LOG_FILE" && echo "LOADED" || echo "NOT LOADED")
- FS registration: $(grep -q "JFFS2 registered" "$LOG_FILE" && echo "REGISTERED" || echo "NOT REGISTERED")
- Mount test: $(grep -q "JFFS2 Mount Test" "$LOG_FILE" && echo "EXECUTED" || echo "NOT EXECUTED")

Output Files:
- Log: $LOG_FILE
- Summary: $SUMMARY_FILE
EOF

echo ""
echo "✓ Test complete"
echo "  Summary: $SUMMARY_FILE"
echo "  Log: $LOG_FILE"

exit 0