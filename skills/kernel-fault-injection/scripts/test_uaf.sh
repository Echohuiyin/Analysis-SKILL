#!/bin/sh
# test_uaf.sh - Initramfs test script for use-after-free (KASAN)
# Runs inside QEMU guest.
# Requires: kernel built with CONFIG_KASAN=y CONFIG_KASAN_INLINE=y
# Avoids busybox [ applet (broken in some builds); uses && / || chains instead.

echo "=== UAF (kref refcount leak) Test ==="
echo "Loading crash_uaf module..."
echo "Trigger: uaf_trigger runs ioctl 0->1->2->3 to free-then-use"
echo "KASAN should report use-after-free and panic"
echo ""

# Enable panic_on_oops so KASAN report -> vmcore capture
echo 1 > /proc/sys/kernel/panic_on_oops 2>/dev/null || true
echo "panic_on_oops: $(cat /proc/sys/kernel/panic_on_oops 2>/dev/null || echo n/a)"

# Make KASAN panic on first report (kasan.fault parameter)
# /sys/module/kasan/parameters/fault accepts: report | panic | panic_on_write
if [ -w /sys/module/kasan/parameters/fault ]; then
    echo panic > /sys/module/kasan/parameters/fault 2>/dev/null || true
    echo "kasan.fault: $(cat /sys/module/kasan/parameters/fault 2>/dev/null || echo n/a)"
fi
echo ""

# Load the UAF module
insmod /modules/crash_uaf.ko
echo "Module loaded, /dev/crash_uaf registered"
echo ""

# Run userspace trigger (static binary in /bin)
# Use ls to check existence (avoids [ applet), then exec
ls /bin/uaf_trigger >/dev/null 2>&1 && {
    echo "Running uaf_trigger..."
    /bin/uaf_trigger
    echo "uaf_trigger returned (KASAN should have panicked already)"
} || {
    echo "ERROR: /bin/uaf_trigger not found"
    echo "Falling back: no trigger, no UAF"
}

# KASAN should panic here. If not, wait briefly then report.
sleep 5
echo ""
echo "WARNING: KASAN did not panic within 5s"
dmesg | tail -n 40
poweroff -f
