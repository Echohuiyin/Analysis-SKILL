#!/bin/sh
# test_deadlock.sh - Initramfs test script for mutex ABBA deadlock
# This runs inside QEMU guest

echo "=== Mutex ABBA Deadlock Test ==="
echo "Loading crash_deadlock module..."
echo "Two threads will deadlock, hung task detector will find after 120s"

insmod /modules/crash_deadlock.ko

echo "Module loaded, threads deadlocked"
echo "Waiting for hung task detection..."

# Threads are deadlocked, wait for hung task timeout
sleep 130

# Hung task should trigger panic by now
echo "Hung task timeout should have triggered panic"