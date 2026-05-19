#!/bin/bash
# Create JFFS2 filesystem image for testing
# Usage: create_jffs2_image.sh [--source <dir>] [--size <MB>] [--output <file>]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR=""
IMAGE_SIZE=16  # Default 16MB
OUTPUT_FILE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --source)
            SOURCE_DIR="$2"
            shift 2
        ;;
        --size)
            IMAGE_SIZE="$2"
            shift 2
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

# Set defaults
if [ -z "$OUTPUT_FILE" ]; then
    OUTPUT_DIR="${OUTPUT_DIR:-jffs2_mount_$(date +%Y%m%d_%H%M%S)}"
    mkdir -p "$OUTPUT_DIR"
    OUTPUT_FILE="$OUTPUT_DIR/jffs2.img"
fi

SIZE_BYTES=$((IMAGE_SIZE * 1024 * 1024))

echo "Creating JFFS2 filesystem image..."
echo "  Size: ${IMAGE_SIZE}MB"
echo "  Output: $OUTPUT_FILE"

# Create source directory if not provided
if [ -z "$SOURCE_DIR" ]; then
    SOURCE_DIR="/tmp/jffs2_source_$(date +%s)"
    mkdir -p "$SOURCE_DIR"
    echo "Test file content" > "$SOURCE_DIR/test.txt"
    echo "Another file" > "$SOURCE_DIR/another.txt"
    mkdir -p "$SOURCE_DIR/subdir"
    echo "Subdirectory content" > "$SOURCE_DIR/subdir/file.txt"
    echo "  Source: $SOURCE_DIR (auto-created)"
else
    echo "  Source: $SOURCE_DIR"
fi

# Method 1: Use mkfs.jffs2 (preferred)
if command -v mkfs.jffs2 >/dev/null 2>&1; then
    echo "  Using mkfs.jffs2..."
    mkfs.jffs2 -r "$SOURCE_DIR" -o "$OUTPUT_FILE" \
               -e 0x10000 -p --pad="$SIZE_BYTES" 2>/dev/null || {
        echo "  mkfs.jffs2 failed, creating blank image"
        dd if=/dev/zero of="$OUTPUT_FILE" bs=1M count=$IMAGE_SIZE 2>/dev/null
    }
else
    echo "  mkfs.jffs2 not available, creating blank image"
    # Method 2: Create blank image for basic mount test
    dd if=/dev/zero of="$OUTPUT_FILE" bs=1M count=$IMAGE_SIZE 2>/dev/null
fi

# Verify image created
if [ -f "$OUTPUT_FILE" ]; then
    ACTUAL_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
    echo "✓ JFFS2 image created successfully"
    echo "  Location: $OUTPUT_FILE"
    echo "  Size: $ACTUAL_SIZE"

    # Save metadata
    cat > "${OUTPUT_FILE}.meta" << EOF
JFFS2 Image Metadata
====================
Created: $(date)
Source: $SOURCE_DIR
Size: $IMAGE_SIZE MB
Method: $(command -v mkfs.jffs2 >/dev/null 2>&1 && echo "mkfs.jffs2" || echo "blank")
EOF
else
    echo "✗ Failed to create JFFS2 image"
    exit 1
fi

# Cleanup auto-created source
if [ "$SOURCE_DIR" != "${SOURCE_DIR%%_$(date +%s)}" ]; then
    rm -rf "$SOURCE_DIR" 2>/dev/null || true
fi

exit 0