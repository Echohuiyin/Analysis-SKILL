#!/bin/bash
# Create minimal initramfs for QEMU kernel testing
# Usage: create_initramfs.sh [--test-script <path>] [--modules <path>] [--interactive]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="/tmp/initramfs_${ARCH:-arm64}"
OUTPUT_FILE="/tmp/initramfs.cpio.gz"

TEST_SCRIPT=""
MODULES_DIR=""
INTERACTIVE=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --test-script)
            TEST_SCRIPT="$2"
            shift 2
        ;;
        --modules)
            MODULES_DIR="$2"
            shift 2
        ;;
        --interactive)
            INTERACTIVE=1
            shift
        ;;
        --output)
            OUTPUT_FILE="$2"
            shift 2
        ;;
        *)
            echo "Unknown option: $1"
            exit 1
        ;;
    esac
done

echo "Creating minimal initramfs..."

# Clean and create directory structure
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"/{bin,dev,proc,sys,etc,lib,modules}

# Check for busybox
BUSYBOX=""
if command -v busybox &> /dev/null; then
    BUSYBOX=$(command -v busybox)
elif [ -f /bin/busybox ]; then
    BUSYBOX=/bin/busybox
else
    echo "ERROR: busybox not found. Please install busybox-static."
    echo "  Ubuntu/Debian: apt install busybox-static"
    echo "  CentOS/RHEL: yum install busybox"
    exit 1
fi

# Copy busybox (static linked version preferred)
if ldd "$BUSYBOX" 2>&1 | grep -q "not a dynamic executable"; then
    cp "$BUSYBOX" "$OUTPUT_DIR/bin/busybox"
else
    echo "Warning: busybox is not static-linked. May need additional libraries."
    cp "$BUSYBOX" "$OUTPUT_DIR/bin/busybox"
    # Copy required libraries (basic attempt)
    ldd "$BUSYBOX" | grep -o "/lib[^ ]*" | while read lib; do
        cp "$lib" "$OUTPUT_DIR/lib/" 2>/dev/null || true
    done
fi

# Create busybox symlinks
cd "$OUTPUT_DIR/bin"
for cmd in sh cat ls mkdir mount umount echo sleep poweroff reboot dmesg grep \
           uname lsmod insmod rmmod modprobe ifconfig ip route ping wget curl \
           vi less more head tail wc awk sed tr cut sort uniq diff find xargs; do
    ln -sf busybox "$cmd" 2>/dev/null || true
done
cd -

# Create init script
INIT_SCRIPT="$OUTPUT_DIR/init"
cat > "$INIT_SCRIPT" << 'EOF'
#!/bin/sh

# Mount essential filesystems
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev 2>/dev/null || {
    # Fallback: create minimal device nodes
    mknod /dev/console c 5 1
    mknod /dev/null c 1 3
    mknod /dev/tty c 5 0
}

# Setup basic environment
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
export HOME=/root
export TERM=linux

echo
echo "========================================="
echo "  Minimal Initramfs for Kernel Testing"
echo "========================================="
echo
echo "Kernel: $(uname -r)"
echo "Architecture: $(uname -m)"
echo "Boot time: $(date)"
echo

# Show kernel messages (last 20 lines)
echo "Recent kernel messages:"
dmesg | tail -20
echo

# Load modules if provided
if [ -d /modules ] && [ "$(ls -A /modules 2>/dev/null)" ]; then
    echo "Loading kernel modules..."
    for mod in /modules/*.ko; do
        if [ -f "$mod" ]; then
            insmod "$mod"
            echo "  Loaded: $(basename $mod)"
        fi
    done
    echo
fi

# Execute test script if provided
TEST_STATUS=0
if [ -f /test.sh ]; then
    echo "========================================="
    echo "  Running Test Script"
    echo "========================================="
    echo
    sh /test.sh
    TEST_STATUS=$?
    echo
    echo "Test completed with status: $TEST_STATUS"
    echo
fi

# Interactive mode or shutdown
if [ "$INTERACTIVE" = "1" ]; then
    echo "========================================="
    echo "  Interactive Mode"
    echo "========================================="
    echo
    echo "Type 'poweroff' or 'reboot' to exit."
    echo "Available commands: sh, ls, cat, dmesg, etc."
    echo
    exec /bin/sh
else
    echo "========================================="
    echo "  Automated Test Complete"
    echo "========================================="
    echo "Test status: $TEST_STATUS"
    echo "Shutting down..."
    echo

    # Give some time for output to be captured
    sleep 2

    # Power off
    poweroff -f
fi
EOF

chmod +x "$INIT_SCRIPT"

# Copy test script if provided
if [ -n "$TEST_SCRIPT" ] && [ -f "$TEST_SCRIPT" ]; then
    cp "$TEST_SCRIPT" "$OUTPUT_DIR/test.sh"
    chmod +x "$OUTPUT_DIR/test.sh"
    echo "Test script included: $TEST_SCRIPT"
fi

# Copy modules if provided
if [ -n "$MODULES_DIR" ] && [ -d "$MODULES_DIR" ]; then
    cp -r "$MODULES_DIR"/*.ko "$OUTPUT_DIR/modules/" 2>/dev/null || true
    echo "Modules included from: $MODULES_DIR"
fi

# Set interactive flag in init
if [ $INTERACTIVE -eq 1 ]; then
    sed -i 's/INTERACTIVE=0/INTERACTIVE=1/' "$INIT_SCRIPT"
fi

# Create basic device nodes (fallback)
mknod "$OUTPUT_DIR/dev/console" c 5 1 2>/dev/null || true
mknod "$OUTPUT_DIR/dev/null" c 1 3 2>/dev/null || true
mknod "$OUTPUT_DIR/dev/tty" c 5 0 2>/dev/null || true

# Create cpio archive
echo "Creating initramfs archive..."
cd "$OUTPUT_DIR"
find . | cpio -o -H newc 2>/dev/null | gzip > "$OUTPUT_FILE"
cd -

# Get size
SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)

echo
echo "✓ Initramfs created successfully"
echo "  Location: $OUTPUT_FILE"
echo "  Size: $SIZE"
echo "  Interactive: $INTERACTIVE"
if [ -n "$TEST_SCRIPT" ]; then
    echo "  Test script: $(basename $TEST_SCRIPT)"
fi
echo

# Cleanup
rm -rf "$OUTPUT_DIR"

exit 0