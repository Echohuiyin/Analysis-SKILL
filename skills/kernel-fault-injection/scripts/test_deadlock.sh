#!/bin/sh
# test_deadlock.sh - Initramfs test script for mutex ABBA deadlock
# This runs inside QEMU guest
# NOTE: Kernel must be configured with BOOTPARAM_HUNG_TASK_PANIC=y
# Hung task will trigger panic after timeout, capturing vmcore

echo "=== Mutex ABBA Deadlock Test ==="
echo "Loading crash_deadlock module..."
echo "Two threads will deadlock, hung task detector will find and trigger panic"
echo "This script will wait indefinitely - kernel panic will terminate QEMU"

# Set hung_task timeout for this specific test (60 seconds for deadlock)
echo 60 > /proc/sys/kernel/hung_task_timeout_secs

# Enable hung_task panic (should be already enabled via kernel config)
echo 1 > /proc/sys/kernel/hung_task_panic

echo "hung_task_panic enabled: $(cat /proc/sys/kernel/hung_task_panic)"
echo "hung_task_timeout: $(cat /proc/sys/kernel/hung_task_timeout_secs) seconds"

# Verify khungtaskd daemon is running
echo ""
echo "=== Hung Task Daemon Check ==="
if ls /proc/*/comm 2>/dev/null | xargs grep -l khungtaskd 2>/dev/null; then
    echo "khungtaskd daemon: Running ✓"
    KHUNGTASKD_PID=$(ls /proc/*/comm 2>/dev/null | xargs grep -l khungtaskd 2>/dev/null | head -1 | sed 's/\/proc\///;s/\/comm//')
    echo "PID: $KHUNGTASKD_PID"
else
    echo "khungtaskd daemon: NOT FOUND ✗"
    echo "WARNING: hung_task detector may not be working!"
fi

# Load the deadlock module
insmod /modules/crash_deadlock.ko

echo "Module loaded, threads deadlocked"
echo "Waiting for hung task detection and kernel panic..."
echo "DO NOT EXIT - let kernel panic capture vmcore"

# Monitor for hung_task messages every 10 seconds
# Expected message: "blocked for more than 60 seconds"
MONITOR_COUNT=0
while [ $MONITOR_COUNT -lt 18 ]; do
    sleep 10
    MONITOR_COUNT=$((MONITOR_COUNT + 1))
    ELAPSED=$((MONITOR_COUNT * 10))

    # Check task states (look for D state = uninterruptible sleep)
    echo ""
    echo "[$ELAPSED s] === Task State Check ==="
    ps aux 2>/dev/null | grep -E "insmod|deadlock" | head -5 || echo "ps not available"

    # Alternative: check /proc for blocked tasks
    BLOCKED_COUNT=0
    for pid_dir in /proc/[0-9]*; do
        if [ -f "$pid_dir/stat" ]; then
            STATE=$(awk '{print $3}' "$pid_dir/stat" 2>/dev/null)
            COMM=$(awk '{print $2}' "$pid_dir/comm" 2>/dev/null)
            if [ "$STATE" = "D" ]; then
                BLOCKED_COUNT=$((BLOCKED_COUNT + 1))
                echo "Blocked task (D state): PID=$(basename $pid_dir) COMM=$COMM"
            fi
        fi
    done
    echo "Total blocked tasks: $BLOCKED_COUNT"

    # Check for hung task detection
    if dmesg | grep -q "blocked for more than"; then
        echo ""
        echo "[$ELAPSED s] Hung task detected!"
        dmesg | grep "blocked for more than" | tail -5
        # Continue waiting for panic
        sleep 30
        break
    fi

    # Progress indicator
    echo "[$ELAPSED s] Waiting for hung_task detection (timeout=60s)..."
done

echo "WARNING: No panic after 180s - hung_task may not be enabled"
echo "Manual poweroff"
poweroff -f

# Threads are deadlocked, hung_task will panic after timeout
# No need to sleep - kernel will panic and kdump captures vmcore