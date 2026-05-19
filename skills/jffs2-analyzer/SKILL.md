---
name: jffs2-analyzer
description: Parse and analyze JFFS2 filesystem images. Use when the user provides a JFFS2 image file and wants to extract its structure, analyze metadata, detect anomalies, and generate detailed reports. Automatically triggers when user mentions JFFS2, jffs2 image, flash filesystem parsing, or asks to analyze binary filesystem images.
---

# JFFS2 Image Analyzer

Parse JFFS2 filesystem images and generate comprehensive analysis reports.

## What This Skill Does

Analyzes JFFS2 (Journalling Flash File System Version 2) binary images without OOB data:

1. **Image Structure Parsing**: Extract all nodes (INODE, DIRENT, XATTR, XREF, SUMMARY, CLEANMARKER)
2. **Block Mapping**: Identify eraseblocks and their state
3. **Inode Reconstruction**: Build inode cache and directory tree
4. **Anomaly Detection**: Identify corrupted nodes, CRC failures, version inconsistencies
5. **Report Generation**: Create summary report + structured JSON output

## Usage

```
/jffs2-analyzer <image-path>
```

Example:
- `/jffs2-analyzer /tmp/jffs2.img`
- `/jffs2-analyzer ./flash_backup.bin`

## Input Requirements

- **File**: Binary JFFS2 filesystem image (no OOB data)
- **Format**: Raw flash dump, typically 64KB-128KB eraseblock size
- **Path**: Absolute or relative path to the image file

## Output

Generates two files:

### 1. Summary Report (`jffs2_analysis_summary.md`)
- File system overview (size, block count, utilization)
- Node type distribution
- Inode statistics
- Directory tree structure
- Anomaly report (CRC errors, corrupted nodes, version conflicts)

### 2. JSON Data Structure (`jffs2_structure.json`)
Complete parsed structure including:
- Block information array
- Node array with detailed metadata
- Inode mapping (ino → nodes)
- Directory tree
- Anomaly list

## Workflow

When invoked, execute these steps:

### Step 1: Validate Input
```bash
# Check file exists
if [ ! -f "<image-path>" ]; then
    echo "ERROR: Image file not found: <image-path>"
    exit 1
fi

# Check file size
FILE_SIZE=$(stat -c%s "<image-path>")
echo "Image size: ${FILE_SIZE} bytes"
```

### Step 2: Detect Eraseblock Size
JFFS2 eraseblocks are typically 64KB (0x10000) or 128KB (0x20000).

Auto-detection logic:
- Try 64KB first (most common)
- Scan first block for CLEANMARKER (magic 0x1985, nodetype CLEANMARKER)
- If valid, use this size
- Otherwise try 128KB

### Step 3: Run Python Parser
Execute the bundled parser script:

```bash
python3 ~/.claude/skills/jffs2-analyzer/scripts/jffs2_parser.py \
    --image "<image-path>" \
    --block-size <detected-size> \
    --output-dir ./jffs2_analysis_output
```

The script performs:
- Block-by-block scanning
- Node parsing and CRC validation
- Inode cache building
- Directory tree reconstruction
- Anomaly detection

### Step 4: Generate Reports
Parser outputs:
- `jffs2_analysis_summary.md` - Human-readable summary
- `jffs2_structure.json` - Structured data

### Step 5: Present Results
Display summary report to user and indicate where JSON data is stored.

## Parser Script Features

The `jffs2_parser.py` script handles:

### Node Parsing
- **DIRENT**: Extract pino, ino, name, type, version
- **INODE**: Extract metadata (mode, uid, gid, times) + data location
- **XATTR**: Extract xid, prefix, name, value
- **XREF**: Extract ino-xid mappings
- **SUMMARY**: Parse summary entries for fast mount info
- **CLEANMARKER**: Validate block markers

### CRC Validation
Check all CRC fields:
- `hdr_crc`: Header integrity
- `node_crc`: Node structure integrity
- `data_crc`: Data payload integrity
- `name_crc`: Dirent name integrity

Report any CRC failures as anomalies.

### Version Analysis
Track node versions per inode:
- Identify latest valid version
- Detect obsolete versions
- Flag version conflicts (multiple same-version nodes)

### Anomaly Detection

Detect these anomalies:

1. **CRC Failures**
   - Type: `crc_error`
   - Severity: HIGH
   - Fields: node_offset, expected_crc, actual_crc

2. **Magic Number Invalid**
   - Type: `invalid_magic`
   - Severity: CRITICAL
   - Fields: offset, expected 0x1985, actual value

3. **Node Type Unknown**
   - Type: `unknown_nodetype`
   - Severity: MEDIUM
   - Fields: nodetype value, offset

4. **Version Conflict**
   - Type: `version_conflict`
   - Severity: MEDIUM
   - Multiple nodes with same ino+version

5. **Dirent Orphan**
   - Type: `orphan_dirent`
   - Severity: LOW
   - Dirent references non-existent inode

6. **Zero-Length Node**
   - Type: `zero_length`
   - Severity: HIGH
   - totlen field is 0 or invalid

7. **Overlap Corruption**
   - Type: `node_overlap`
   - Severity: HIGH
   - Nodes overlap in flash space

## JSON Output Structure

```json
{
  "image_info": {
    "file_path": "...",
    "file_size": 1048576,
    "block_size": 65536,
    "block_count": 16
  },
  "blocks": [
    {
      "block_index": 0,
      "offset": 0,
      "state": "clean",
      "nodes_count": 5,
      "used_size": 2048,
      "free_size": 63488,
      "node_offsets": [8, 128, 256, ...]
    }
  ],
  "nodes": [
    {
      "offset": 8,
      "block_index": 0,
      "type": "dirent",
      "magic": 0x1985,
      "totlen": 120,
      "crc_valid": true,
      "data": {
        "pino": 1,
        "ino": 2,
        "version": 1,
        "name": "test.txt",
        "type": "DT_REG"
      }
    }
  ],
  "inodes": {
    "1": {
      "ino": 1,
      "mode": "040755",
      "type": "directory",
      "nlink": 3,
      "nodes": [8, 256],
      "children": [2, 3, 4]
    }
  },
  "directory_tree": {
    "/": {
      "ino": 1,
      "children": {
        "test.txt": {"ino": 2, "type": "file"},
        "subdir": {"ino": 3, "type": "directory"}
      }
    }
  },
  "anomalies": [
    {
      "type": "crc_error",
      "severity": "HIGH",
      "offset": 128,
      "details": "INODE node_crc mismatch"
    }
  ],
  "statistics": {
    "total_nodes": 125,
    "dirent_count": 30,
    "inode_count": 85,
    "xattr_count": 10,
    "anomaly_count": 2,
    "valid_ratio": 0.98
  }
}
```

## Node Type Constants

Reference `references/jffs2_structures.md` for:
- Magic numbers (0x1985, 0xFFFF, 0x0000)
- Node type codes (DIRENT, INODE, XATTR, etc.)
- Compression algorithms (ZLIB, LZO, etc.)
- Structure field details

## Example Report Output

```markdown
# JFFS2 Image Analysis Summary

## Image Overview
- File: /tmp/jffs2.img
- Size: 1,048,576 bytes (1.0 MB)
- Block Size: 64 KB
- Block Count: 16

## Block Utilization
- Clean Blocks: 8 (50%)
- Dirty Blocks: 4 (25%)
- Free Blocks: 2 (12.5%)
- Bad Blocks: 2 (12.5%)

## Node Distribution
- INODE nodes: 85 (68%)
- DIRENT nodes: 30 (24%)
- XATTR nodes: 8 (6.4%)
- XREF nodes: 2 (1.6%)
- CLEANMARKER: 16 (valid)

## Inode Statistics
- Total Inodes: 42
- Files: 28
- Directories: 14
- Average file size: 4.2 KB

## Directory Tree
/
├── file1.txt (ino=2)
├── subdir/ (ino=3)
│   ├── file2.txt (ino=4)
│   └── file3.txt (ino=5)

## Anomaly Report
⚠️ Found 2 anomalies:

1. CRC Error (HIGH) at offset 0x40080
   - INODE node has corrupted data_crc
   - Expected: 0xABC123, Actual: 0xABC124

2. Orphan Dirent (LOW) at offset 0x20040
   - Dirent "missing.txt" references ino=999 (not found)

## Recommendations
- 2 nodes require data recovery
- Consider fsck.jffs2 for repair
```

## Error Handling

### Invalid Image
If magic number not found in first blocks:
```
ERROR: No valid JFFS2 magic (0x1985) detected
This may not be a JFFS2 image or uses non-standard format.
```

### Read Errors
If file cannot be read:
```
ERROR: Cannot read image file
Check file permissions and path.
```

### Corrupted Block
If block has no valid CLEANMARKER:
```
WARNING: Block 5 missing CLEANMARKER
May be partially erased or corrupted.
```

## Testing the Skill

After parsing, verify:
```bash
# Check output files exist
ls -lh ./jffs2_analysis_output/

# View summary
cat ./jffs2_analysis_output/jffs2_analysis_summary.md

# Examine JSON structure
jq '.statistics' ./jffs2_analysis_output/jffs2_structure.json
```

## Implementation Notes

### Performance
- Large images (>100MB): Parser may take 30-60 seconds
- Shows progress: "Parsing block 10/128..."

### Memory Usage
- Parser uses streaming approach
- JSON output can be large for many nodes
- Consider filtering if needed

### Limitations
- No OOB data parsing (as specified)
- Cannot decompress data payloads (read-only analysis)
- Does not validate actual file content integrity