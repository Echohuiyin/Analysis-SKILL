#!/bin/bash
# run_vmcore_test.sh - Run QEMU test with vmcore capture
# Usage: ./run_vmcore_test.sh <test_name> <kernel> <initramfs> [timeout] [--output <dir>]
#
# Generates vmcore compatible with crash 9.0.2+ analysis

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$(dirname "$TOOL_DIR")")"

TEST_NAME="$1"
KERNEL_IMAGE="$2"
INITRAMFS="$3"
TIMEOUT="${4:-60}"
OUTPUT_DIR=""

# Parse additional arguments
shift 4 2>/dev/null || true
while [[ $# -gt 0 ]]; do
    case $1 in
        --output)
            OUTPUT_DIR="$2"
            shift 2
        ;;
        *)
            shift
        ;;
    esac
done

if [ -z "$TEST_NAME" ] || [ -z "$KERNEL_IMAGE" ]; then
    echo "Usage: $0 <test_name> <kernel> <initramfs> [timeout] [--output <dir>]"
    exit 1
fi

# Set output directory (use --output if provided, otherwise default)
if [ -z "$OUTPUT_DIR" ]; then
    OUTPUT_DIR="${PROJECT_ROOT}/test_outputs/${TEST_NAME}"
fi

VMCORE_FILE="${OUTPUT_DIR}/vmcore.elf"
LOG_FILE="${OUTPUT_DIR}/boot.log"
MONITOR_SOCKET="${OUTPUT_DIR}/qemu_monitor.sock"

mkdir -p "$OUTPUT_DIR"
rm -f "$MONITOR_SOCKET" "$VMCORE_FILE"

echo "=== Vmcore Test: $TEST_NAME ==="
echo "Kernel: $KERNEL_IMAGE"
echo "Initramfs: ${INITRAMFS:-auto-create}"
echo "Output: $OUTPUT_DIR"
echo "Timeout: $TIMEOUT seconds"
echo

# Check kernel architecture
# bzImage format: "Linux kernel x86 boot executable bzImage"
# ELF format: "ELF 64-bit LSB executable, x86-64"
KERNEL_INFO=$(file "$KERNEL_IMAGE")

if echo "$KERNEL_INFO" | grep -qE "x86 boot executable|x86-64"; then
    KERNEL_ARCH="x86-64"
elif echo "$KERNEL_INFO" | grep -qE "ARM aarch64|ARM,"; then
    KERNEL_ARCH="ARM aarch64"
else
    echo "ERROR: Unknown kernel architecture: $KERNEL_INFO"
    exit 1
fi

if [ "$KERNEL_ARCH" = "x86-64" ]; then
    QEMU_CMD="qemu-system-x86_64"
    MACHINE="q35,dump-guest-core=on"
    CONSOLE="ttyS0"
elif [ "$KERNEL_ARCH" = "ARM aarch64" ]; then
    QEMU_CMD="qemu-system-aarch64"
    MACHINE="virt,dump-guest-core=on"
    CONSOLE="ttyAMA0"
else
    echo "ERROR: Unknown kernel architecture: $KERNEL_ARCH"
    exit 1
fi

echo "Architecture: $KERNEL_ARCH"
echo "QEMU: $QEMU_CMD -M $MACHINE"
echo

# Create initramfs if not provided
if [ -z "$INITRAMFS" ]; then
    echo "[Initramfs] Creating minimal initramfs..."
    INITRAMFS="/tmp/initramfs_${TEST_NAME}.cpio.gz"

    if [ -f "${PROJECT_ROOT}/skills/qemu-test/scripts/create_initramfs.sh" ]; then
        bash "${PROJECT_ROOT}/skills/qemu-test/scripts/create_initramfs.sh" \
            --arch "${KERNEL_ARCH/x86-64/x86_64}" \
            --output "$INITRAMFS"
    else
        echo "ERROR: create_initramfs.sh not found"
        exit 1
    fi
fi

# Check for socat (required for monitor communication)
if ! command -v socat &> /dev/null; then
    echo "WARNING: socat not installed"
    echo "Install: sudo apt install socat"
fi

# Start QEMU with vmcoreinfo device
echo "[QEMU] Starting with vmcoreinfo device..."

$QEMU_CMD \
    -M "$MACHINE" \
    -device vmcoreinfo \
    -smp 2 \
    -m 512M \
    -nographic \
    -kernel "$KERNEL_IMAGE" \
    -initrd "$INITRAMFS" \
    -append "console=${CONSOLE} panic=10 oops=panic hung_task_panic=1 hung_task_timeout_secs=60" \
    -monitor unix:${MONITOR_SOCKET},server,nowait \
    > "$LOG_FILE" 2>&1 &

QEMU_PID=$!
echo "[QEMU] PID: $QEMU_PID"

# Wait for monitor socket
sleep 2
if [ ! -S "$MONITOR_SOCKET" ]; then
    echo "[ERROR] Monitor socket not created"
    cat "$LOG_FILE"
    exit 1
fi
echo "[Monitor] Socket ready"

# Monitor loop - capture vmcore on crash
START_TIME=$(date +%s)
CRASH_DETECTED=false

while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))

    if [ $ELAPSED -ge $TIMEOUT ]; then
        echo "[Monitor] Timeout reached"
        break
    fi

    if ! kill -0 $QEMU_PID 2>/dev/null; then
        echo "[Monitor] QEMU ended"
        break
    fi

    # Check for crash
    if grep -qE "Kernel panic|Oops -|unable to handle" "$LOG_FILE" 2>/dev/null; then
        if [ "$CRASH_DETECTED" = false ]; then
            echo "[Monitor] Crash detected at ${ELAPSED}s!"
            CRASH_DETECTED=true

            # Wait for vmcoreinfo to stabilize
            sleep 2

            # Capture vmcore via monitor
            echo "[Capture] Dumping guest memory..."
            if [ -S "$MONITOR_SOCKET" ]; then
                echo "dump-guest-memory ${VMCORE_FILE}" | socat - UNIX-CONNECT:${MONITOR_SOCKET} 2>/dev/null || true
                sleep 5
            fi

            # Stop QEMU
            echo "quit" | socat - UNIX-CONNECT:${MONITOR_SOCKET} 2>/dev/null || true
            sleep 1
            kill $QEMU_PID 2>/dev/null || true
            break
        fi
    fi

    sleep 1
done

# Cleanup
rm -f "$MONITOR_SOCKET"

# Results
echo
echo "=== Test Results ==="

if [ -s "$VMCORE_FILE" ]; then
    SIZE=$(ls -lh "$VMCORE_FILE" | awk '{print $5}')
    echo "✓ Vmcore: $VMCORE_FILE ($SIZE)"
    file "$VMCORE_FILE"

    # Check for VMCOREINFO
    echo
    echo "=== Vmcore Validation ==="
    NOTES=$(readelf -n "$VMCORE_FILE" 2>/dev/null | grep VMCOREINFO || echo "Not found")
    if [ "$NOTES" != "Not found" ]; then
        echo "✓ VMCOREINFO ELF note present (crash compatible)"
    else
        echo "⚠ VMCOREINFO missing - may not work with crash"
    fi
else
    echo "✗ Vmcore: Not captured"
fi

echo "Log: $LOG_FILE ($(wc -l < "$LOG_FILE") lines)"

# Crash evidence
echo
echo "=== Crash Evidence ==="
grep -E "Kernel panic|Oops|NULL pointer|BUG" "$LOG_FILE" | head -10 || echo "No crash found"

echo
echo "Test completed in ${ELAPSED}s"

# Suggest analysis command
if [ -s "$VMCORE_FILE" ]; then
    echo
    echo "=== Next Step ==="
    echo "Analyze with crash:"
    echo "  ${TOOL_DIR}/bin/crash ${KERNEL_IMAGE/vmlinux/} $VMCORE_FILE"
fi