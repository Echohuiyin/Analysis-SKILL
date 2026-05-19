#!/bin/bash
# Run QEMU with JFFS2 mount test configuration
# Usage: run_qemu.sh --kernel <path> --initrd <path> [--arch <arch>] [--timeout <sec>]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source mount_test.sh which contains the actual test logic
source "$SCRIPT_DIR/mount_test.sh" "$@"