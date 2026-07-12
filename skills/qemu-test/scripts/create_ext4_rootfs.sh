#!/bin/bash
# Create an ext4 root filesystem image for QEMU kernel testing.
# Usage: create_ext4_rootfs.sh [--arch <arch>] [--output <path>] [--size-mb <MB>]
#                            [--test-script <path>] [--modules <path>] [--binaries <path>]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
BUSYBOX_VERSION="1.36.1"

ARCH="${ARCH:-x86_64}"
OUTPUT_FILE="/tmp/rootfs_${ARCH}.ext4"
SIZE_MB=128
TEST_SCRIPT=""
MODULES_DIR=""
BINARIES_DIR=""

detect_busybox_arch() {
    local busybox="$1"
    if [ ! -f "$busybox" ]; then
        echo "unknown"
        return 1
    fi
    local info
    info=$(file "$busybox" 2>/dev/null)
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

find_busybox() {
    local target_arch="$1"
    local candidates=(
        "${PROJECT_ROOT}/tools/busybox/prebuilt/busybox_${target_arch}"
        "/tmp/busybox_build_${target_arch}/busybox-${BUSYBOX_VERSION}/busybox"
        "/usr/bin/busybox"
        "/bin/busybox"
    )

    for busybox in "${candidates[@]}"; do
        if [ -x "$busybox" ]; then
            local detected_arch
            detected_arch=$(detect_busybox_arch "$busybox")
            if [ "$detected_arch" = "$target_arch" ]; then
                local host_arch
                host_arch=$(uname -m)
                local need_runtime_check=1
                if [ "$target_arch" = "arm64" ] && [ "$host_arch" != "aarch64" ]; then
                    need_runtime_check=0
                elif [ "$target_arch" = "arm32" ] && [ "$host_arch" != "armv7l" ] && [ "$host_arch" != "armv6l" ]; then
                    need_runtime_check=0
                elif [ "$target_arch" = "x86_64" ] && [ "$host_arch" != "x86_64" ] && [ "$host_arch" != "amd64" ]; then
                    need_runtime_check=0
                fi

                if [ "$need_runtime_check" = "1" ]; then
                    if ! "$busybox" sh -c true >/dev/null 2>&1; then
                        echo "⚠️  BusyBox at $busybox fails applet health check, skipping" >&2
                        continue
                    fi
                else
                    local bb_size
                    bb_size=$(stat -c%s "$busybox" 2>/dev/null || stat -f%z "$busybox" 2>/dev/null || echo 0)
                    if [ "$bb_size" -lt 100000 ]; then
                        echo "⚠️  BusyBox at $busybox is too small ($bb_size bytes), skipping" >&2
                        continue
                    fi
                fi
                echo "$busybox"
                return 0
            else
                echo "⚠️  BusyBox at $busybox is $detected_arch, but need $target_arch (skipping)" >&2
            fi
        fi
    done
    return 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --arch)
            ARCH="$2"
            OUTPUT_FILE="/tmp/rootfs_${ARCH}.ext4"
            shift 2
        ;;
        --output)
            OUTPUT_FILE="$2"
            shift 2
        ;;
        --size-mb)
            SIZE_MB="$2"
            shift 2
        ;;
        --test-script)
            TEST_SCRIPT="$2"
            shift 2
        ;;
        --modules)
            MODULES_DIR="$2"
            shift 2
        ;;
        --binaries)
            BINARIES_DIR="$2"
            shift 2
        ;;
        *)
            echo "Unknown option: $1"
            exit 1
        ;;
    esac
done

if ! command -v mke2fs >/dev/null 2>&1; then
    # mke2fs is in /usr/sbin or /sbin, not in normal user PATH
    for candidate in /usr/sbin/mke2fs /sbin/mke2fs /usr/local/sbin/mke2fs; do
        if [ -x "$candidate" ]; then
            export PATH="/usr/sbin:/sbin:/usr/local/sbin:$PATH"
            break
        fi
    done
fi

if ! command -v mke2fs >/dev/null 2>&1; then
    echo "ERROR: mke2fs not found (install: e2fsprogs)"
    exit 1
fi

echo "Creating ext4 rootfs for $ARCH..."

ROOT_DIR="$(mktemp -d "/tmp/rootfs_${ARCH}.XXXXXX")"
cleanup() {
    rm -rf "$ROOT_DIR"
}
trap cleanup EXIT

mkdir -p "$ROOT_DIR"/{bin,sbin,etc,proc,sys,dev,tmp,run,var/tmp,var/log,root,modules,usr/bin,usr/sbin}
chmod 1777 "$ROOT_DIR/tmp" "$ROOT_DIR/var/tmp"

BUSYBOX=$(find_busybox "$ARCH")
if [ -z "$BUSYBOX" ] || [ ! -f "$BUSYBOX" ]; then
    echo "ERROR: No valid BusyBox found for $ARCH"
    echo "Solution: bash ${PROJECT_ROOT}/tools/build_busybox.sh --arch $ARCH --clean"
    exit 1
fi

DETECTED_ARCH=$(detect_busybox_arch "$BUSYBOX")
echo "✓ BusyBox found: $BUSYBOX"
echo "  Architecture: $DETECTED_ARCH"
cp "$BUSYBOX" "$ROOT_DIR/bin/busybox"
chmod +x "$ROOT_DIR/bin/busybox"

cd "$ROOT_DIR/bin"
for cmd in sh ash cat ls mkdir mount umount echo sleep poweroff reboot dmesg grep \
           uname lsmod insmod rmmod modprobe ifconfig ip route ping wget curl \
           vi less more head tail wc awk sed tr cut sort uniq diff find xargs \
           test "[" true false expr seq chmod mknod sync; do
    ln -sf busybox "$cmd" 2>/dev/null || true
done
cd - >/dev/null

cat > "$ROOT_DIR/init" << 'EOF'
#!/bin/sh

mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev 2>/dev/null || {
    mknod /dev/console c 5 1
    mknod /dev/null c 1 3
    mknod /dev/tty c 5 0
}

mkdir -p /tmp /run /var/tmp /var/log /root
chmod 1777 /tmp /var/tmp
mknod /dev/loop-control c 10 237 2>/dev/null || true
for i in $(seq 0 31); do
    mknod /dev/loop${i} b 7 ${i} 2>/dev/null || true
done

export PATH=/bin:/sbin:/usr/bin:/usr/sbin
export HOME=/root

echo
echo "========================================="
echo "  ext4 RootFS for Kernel Testing"
echo "========================================="
uname -r
uname -m
echo

if test -f /test.sh; then
    echo "========================================="
    echo "  Running Test Script"
    echo "========================================="
    sh /test.sh
else
    if ls /modules/*.ko 2>/dev/null; then
        echo "Loading kernel modules..."
        for mod in /modules/*.ko; do
            insmod "$mod"
            echo "  Loaded: $mod"
        done
    fi
    echo "Automated test complete"
    sleep 2
    poweroff -f
fi
EOF
chmod +x "$ROOT_DIR/init"

if [ -n "$TEST_SCRIPT" ] && [ -f "$TEST_SCRIPT" ]; then
    cp "$TEST_SCRIPT" "$ROOT_DIR/test.sh"
    chmod +x "$ROOT_DIR/test.sh"
    echo "Test script included: $TEST_SCRIPT"
fi

if [ -n "$MODULES_DIR" ] && [ -d "$MODULES_DIR" ]; then
    cp -r "$MODULES_DIR"/*.ko "$ROOT_DIR/modules/" 2>/dev/null || true
    echo "Modules included from: $MODULES_DIR"
fi

if [ -n "$BINARIES_DIR" ] && [ -d "$BINARIES_DIR" ]; then
    cp "$BINARIES_DIR"/* "$ROOT_DIR/bin/" 2>/dev/null || true
    chmod +x "$ROOT_DIR/bin/"* 2>/dev/null || true
    echo "Binaries included from: $BINARIES_DIR"
fi

mknod "$ROOT_DIR/dev/console" c 5 1 2>/dev/null || true
mknod "$ROOT_DIR/dev/null" c 1 3 2>/dev/null || true
mknod "$ROOT_DIR/dev/tty" c 5 0 2>/dev/null || true

mkdir -p "$(dirname "$OUTPUT_FILE")"
rm -f "$OUTPUT_FILE"

echo "Creating ext4 image..."
mke2fs -q -t ext4 -d "$ROOT_DIR" "$OUTPUT_FILE" "${SIZE_MB}M"

if [ ! -s "$OUTPUT_FILE" ]; then
    echo "ERROR: rootfs image not created: $OUTPUT_FILE"
    exit 1
fi

SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
echo
echo "✓ ext4 rootfs created"
echo "  Path: $OUTPUT_FILE"
echo "  Size: $SIZE"
echo "  Arch: $ARCH"
