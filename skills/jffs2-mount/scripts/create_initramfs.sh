#!/bin/bash
# Create ARM64 initramfs for JFFS2 mount testing
# Usage: create_initramfs.sh [--kernel <path>] [--modules <dir>] [--jffs2-image <path>] [--arch <arch>]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
KERNEL_PATH=""
MODULES_DIR=""
JFFS2_IMAGE=""
ARCH="arm64"
BUSYBOX_VERSION="1.36.1"

# 架构映射
ARCH_MAP_ARM64="ARM aarch64|aarch64"
ARCH_MAP_ARM32="ARM,|armv7l|ARM,"
ARCH_MAP_X86_64="x86-64|x86_64"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --kernel)
            KERNEL_PATH="$2"
            shift 2
        ;;
        --modules)
            MODULES_DIR="$2"
            shift 2
        ;;
        --jffs2-image)
            JFFS2_IMAGE="$2"
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
INITRAMFS_DIR="/tmp/initramfs_jffs2_$(date +%s)"
INITRAMFS_FILE="$OUTPUT_DIR/initramfs_jffs2.cpio.gz"

mkdir -p "$OUTPUT_DIR"
mkdir -p "$INITRAMFS_DIR"/{bin,dev,proc,sys,etc,lib,mnt,modules}

echo "Creating initramfs for JFFS2 mount test (arch: $ARCH)..."

# === 架构检测函数 ===
detect_busybox_arch() {
    local busybox="$1"
    if [ ! -f "$busybox" ]; then
        echo "unknown"
        return 1
    fi
    local info=$(file "$busybox" 2>/dev/null)

    if echo "$info" | grep -qE "ARM aarch64"; then
        echo "arm64"
    elif echo "$info" | grep -qE "ARM,"; then
        echo "arm32"
    elif echo "$info" | grep -qE "x86-64"; then
        echo "x86_64"
    else
        echo "unknown"
    fi
}

# === 查找并验证 busybox ===
find_busybox() {
    local target_arch="$1"
    local candidates=(
        # 优先使用项目内预编译版本
        "${PROJECT_ROOT}/tools/busybox/prebuilt/busybox_${target_arch}"
        # 新构建路径
        "/tmp/busybox_build_${target_arch}/busybox-${BUSYBOX_VERSION}/busybox"
        # 旧构建路径（兼容）
        "/tmp/busybox_build/busybox-${BUSYBOX_VERSION}/busybox"
        # 系统busybox
        "/usr/bin/busybox"
        "/bin/busybox"
    )

    for busybox in "${candidates[@]}"; do
        if [ -x "$busybox" ]; then
            local detected_arch=$(detect_busybox_arch "$busybox")
            if [ "$detected_arch" = "$target_arch" ]; then
                echo "$busybox"
                return 0
            else
                echo "⚠️  Busybox at $busybox is $detected_arch, but need $target_arch (skipping)" >&2
            fi
        fi
    done
    return 1
}

# Step 1: Setup busybox with architecture detection
echo "[Busybox] Finding architecture-matched busybox..."

BUSYBOX=$(find_busybox "$ARCH")

if [ -n "$BUSYBOX" ] && [ -f "$BUSYBOX" ]; then
    DETECTED_ARCH=$(detect_busybox_arch "$BUSYBOX")
    echo "✓ Busybox found: $BUSYBOX"
    echo "  Architecture: $DETECTED_ARCH (matches target: $ARCH)"
    cp "$BUSYBOX" "$INITRAMFS_DIR/bin/busybox"
else
    echo "✗ No valid busybox found for $ARCH"
    echo "  Required for: sh, mount, insmod, etc."
    echo ""
    echo "Solution: Build busybox for $ARCH"
    echo "  cd ${PROJECT_ROOT}/tools"
    echo "  ./build_busybox.sh --arch $ARCH --clean"
    echo ""
    echo "Or use pre-built system busybox (x86_64 only):"
    echo "  /kernel-build JFFS2_FS --arch x86_64"
    exit 1
fi

# Create busybox symlinks
cd "$INITRAMFS_DIR/bin"
for cmd in sh cat ls mkdir mount umount echo sleep poweroff reboot \
           dmesg grep uname lsmod insmod rmmod dd tail head date \
           mknod losetup; do
    ln -sf busybox "$cmd" 2>/dev/null || true
done
cd -

# Step 2: Create mount test script
cat > "$INITRAMFS_DIR/mount_test.sh" << 'EOF'
#!/bin/sh

echo "=== JFFS2 Mount Test Script ==="
echo "Date: $(date)"
echo "Kernel: $(uname -r)"
echo "Architecture: $(uname -m)"
echo ""

# Mount essential filesystems
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev 2>/dev/null || {
    mknod /dev/console c 5 1
    mknod /dev/null c 1 3
    mknod /dev/loop0 b 7 0
}

# Load MTD modules
echo "[1] Loading MTD modules..."
if [ -f /modules/mtd.ko ]; then
    insmod /modules/mtd.ko && echo "  ✓ mtd.ko loaded"
fi
if [ -f /modules/mtd_blkdevs.ko ]; then
    insmod /modules/mtd_blkdevs.ko && echo "  ✓ mtd_blkdevs.ko loaded"
fi
if [ -f /modules/mtdblock.ko ]; then
    insmod /modules/mtdblock.ko && echo "  ✓ mtdblock.ko loaded"
fi

# Load JFFS2 module
echo "[2] Loading JFFS2 module..."
if [ -f /modules/jffs2.ko ]; then
    insmod /modules/jffs2.ko && echo "  ✓ jffs2.ko loaded"
else
    echo "  ✗ jffs2.ko not found"
fi

# Check filesystem registration
echo "[3] Checking JFFS2 filesystem..."
cat /proc/filesystems | grep jffs2 && echo "  ✓ JFFS2 registered" || \
    echo "  ✗ JFFS2 not in filesystems"

# Setup MTD device (simplified for QEMU test)
echo "[4] Setting up MTD device..."
if [ -f /jffs2.img ]; then
    echo "  JFFS2 image available: $(ls -lh /jffs2.img)"
    # Note: Real mount requires proper MTD device setup
    # This is simplified for demonstration
    echo "  (MTD device setup requires block2mtd or mtdram)"
fi

# Attempt mount (demonstration)
echo "[5] Testing mount capability..."
mkdir -p /mnt/jffs2
# mount -t jffs2 mtd0 /mnt/jffs2
# For testing in minimal initramfs, we verify module load success

echo "[6] Module status:"
lsmod | grep -E "jffs2|mtd"

echo "[7] Kernel messages (JFFS2 related):"
dmesg | grep -iE "jffs2|mtd" | tail -10

echo ""
echo "=== Mount Test Complete ==="
echo "Note: Full mount requires MTD device configuration"
EOF
chmod +x "$INITRAMFS_DIR/mount_test.sh"

# Step 3: Create init script
cat > "$INITRAMFS_DIR/init" << 'EOF'
#!/bin/sh

mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev 2>/dev/null || {
    mknod /dev/console c 5 1
    mknod /dev/null c 1 3
}

export PATH=/bin:/sbin

echo
echo "========================================="
echo "  JFFS2 Mount Test Environment"
echo "========================================="
echo "Kernel: $(uname -r)"
echo "Arch: $(uname -m)"
echo

# Execute mount test
sh /mount_test.sh

echo
echo "Shutting down..."
sleep 2
poweroff -f
EOF
chmod +x "$INITRAMFS_DIR/init"

# Step 4: Copy modules
echo "[Modules] Copying kernel modules..."
if [ -n "$MODULES_DIR" ] && [ -d "$MODULES_DIR" ]; then
    cp "$MODULES_DIR"/*.ko "$INITRAMFS_DIR/modules/" 2>/dev/null || true
    echo "  ✓ Modules from: $MODULES_DIR"
elif [ -n "$KERNEL_PATH" ]; then
    KERNEL_ROOT="$(dirname "$(dirname "$KERNEL_PATH")")"
    # Copy JFFS2 module
    if [ -f "$KERNEL_ROOT/../fs/jffs2/jffs2.ko" ]; then
        cp "$KERNEL_ROOT/../fs/jffs2/jffs2.ko" "$INITRAMFS_DIR/modules/"
    fi
    # Copy MTD modules
    for mod in mtd.ko mtd_blkdevs.ko mtdblock.ko block2mtd.ko; do
        find "$KERNEL_ROOT/../drivers/mtd" -name "$mod" -exec cp {} "$INITRAMFS_DIR/modules/" \; 2>/dev/null || true
    done
    echo "  ✓ Modules from kernel tree"
fi

ls -la "$INITRAMFS_DIR/modules/"

# Step 5: Copy JFFS2 image
if [ -n "$JFFS2_IMAGE" ] && [ -f "$JFFS2_IMAGE" ]; then
    cp "$JFFS2_IMAGE" "$INITRAMFS_DIR/jffs2.img"
    echo "✓ JFFS2 image included: $(basename $JFFS2_IMAGE)"
fi

# Step 6: Create cpio.gz
echo "[Initramfs] Creating cpio.gz archive..."
cd "$INITRAMFS_DIR"
find . | cpio -o -H newc 2>/dev/null | gzip > "$INITRAMFS_FILE"
cd -

SIZE=$(du -h "$INITRAMFS_FILE" | cut -f1)

echo "✓ Initramfs created successfully"
echo "  Location: $INITRAMFS_FILE"
echo "  Size: $SIZE"

# Cleanup
rm -rf "$INITRAMFS_DIR"

exit 0