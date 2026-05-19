# JFFS2 Analyzer Skill

Analyze JFFS2 filesystem images and extract detailed structure information.

## Installation

This skill is installed in the Claude Code skills directory. To use it:

1. Restart Claude Code session to load the skill
2. Use `/jffs2-analyzer <image-path>` to invoke

## Quick Start

```bash
# In Claude Code session
/jffs2-analyzer /path/to/jffs2.img
```

## What This Skill Does

Given a JFFS2 binary image (without OOB data), this skill:

1. **Auto-detects eraseblock size** (64KB or 128KB)
2. **Scans all eraseblocks** and extracts nodes
3. **Parses node structures** (DIRENT, INODE, XATTR, XREF, SUMMARY, CLEANMARKER)
4. **Validates CRC checksums** for each node
5. **Builds inode cache** and directory tree
6. **Detects anomalies**:
   - CRC errors
   - Invalid magic numbers
   - Unknown node types
   - Version conflicts
   - Orphan directory entries

7. **Generates two outputs**:
   - `jffs2_analysis_summary.md` - Human-readable report
   - `jffs2_structure.json` - Complete structured data

## Output Files

### Summary Report (`jffs2_analysis_summary.md`)

Contains:
- Image overview (size, block count)
- Block distribution by state
- Node type statistics
- Inode statistics
- Directory tree visualization
- Anomaly report with severity levels
- Recommendations for repair

### JSON Structure (`jffs2_structure.json`)

Complete parsed data including:
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
      "node_count": 5,
      "used_size": 2048,
      "free_size": 63488
    }
  ],
  "nodes": [
    {
      "offset": 8,
      "block_index": 0,
      "type": "DIRENT",
      "totlen": 120,
      "valid": true,
      "data": {
        "pino": 1,
        "ino": 2,
        "name": "test.txt",
        "type": "REG"
      }
    }
  ],
  "inodes": {
    "1": {
      "ino": 1,
      "file_type": "directory",
      "mode": "040755",
      "uid": 0,
      "gid": 0,
      "isize": 4096,
      "node_count": 5
    }
  },
  "directory_tree": {
    "/": {
      "ino": 1,
      "children": {
        "file.txt": {"ino": 2, "type": "REG"}
      }
    }
  },
  "anomalies": [
    {
      "type": "crc_error",
      "severity": "HIGH",
      "offset": 128,
      "details": {...}
    }
  ],
  "statistics": {
    "total_nodes": 125,
    "valid_nodes": 123,
    "crc_errors": 2
  }
}
```

## Node Types Supported

| Type | Description |
|------|-------------|
| DIRENT | Directory entry (file name, parent inode) |
| INODE | File metadata (permissions, times, data location) |
| XATTR | Extended attributes |
| XREF | Extended attribute references |
| SUMMARY | Fast mount summaries |
| CLEANMARKER | Eraseblock markers |

## Anomaly Detection

The skill detects these anomaly types:

1. **CRC Errors** (HIGH) - Corrupted node data
2. **Invalid Magic** (CRITICAL) - Not a valid JFFS2 node
3. **Unknown Node Type** (MEDIUM) - Unrecognized node type
4. **Version Conflicts** (MEDIUM) - Duplicate version numbers
5. **Orphan Dirents** (LOW) - Dirents referencing missing inodes

## Example Usage

### Basic Analysis
```bash
/jffs2-analyzer /tmp/flash_backup.img
```

Output:
```
Parsing JFFS2 image: /tmp/flash_backup.img
File size: 1,048,576 bytes
Block size: 64KB
Block count: 16

Scan complete. Found 125 nodes

JSON data saved to: ./jffs2_analysis_output/jffs2_structure.json
Summary report saved to: ./jffs2_analysis_output/jffs2_analysis_summary.md

Quick Statistics:
  Blocks scanned: 16
  Nodes found: 125
  Valid nodes: 123
  Anomalies: 2
  Inodes: 42
```

### Large Images
For large images (>100MB), parsing may take 30-60 seconds. Progress is shown:
```
Scanning block 10/128...
```

## Technical Details

### Eraseblock Size Detection

The parser auto-detects block size by:
1. Checking if file size is divisible by 64KB or 128KB
2. Looking for CLEANMARKER at block start
3. Defaulting to 64KB if uncertain

### CRC Validation

All CRC fields are validated:
- `hdr_crc`: Header (magic + nodetype + totlen)
- `node_crc`: Entire node structure
- `data_crc`: Data payload
- `name_crc`: Dirent names

### Version Tracking

The parser tracks node versions per inode to identify:
- Latest valid version
- Obsolete versions
- Version conflicts

### Directory Tree Building

Reconstructs directory tree by:
1. Starting from root (ino=1)
2. Processing dirents by parent inode
3. Resolving latest versions
4. Building hierarchical structure

## Requirements

- Python 3.x
- No external dependencies (uses only stdlib)

## Limitations

- Cannot parse OOB data (as designed)
- Cannot decompress file data (read-only analysis)
- Summary entries are not fully parsed (complex structure)

## Troubleshooting

### "No valid JFFS2 magic detected"
- Verify the file is a JFFS2 image
- Check if it contains OOB data (this tool expects no OOB)
- Try different block size with `--block-size 131072`

### "Block truncated"
- File size not divisible by block size
- Possible incomplete image

### Many anomalies detected
- Flash corruption
- Power failure during write
- Consider running `fsck.jffs2`

## Integration with JFFS2 Analysis

This skill complements the `jffs2_analysis.md` documentation in the OLK-6.6 repository:
- Theory and structure from `jffs2_analysis.md`
- Practical parsing with this skill
- Full coverage of JFFS2 internals

## Advanced Usage

### Custom Block Size
If auto-detection fails, specify manually:

```bash
# In skill invocation, the parser accepts --block-size
python3 ~/.claude/skills/jffs2-analyzer/scripts/jffs2_parser.py \
  --image /tmp/jffs2.img \
  --block-size 131072
```

### JSON-Only Output
For automated processing:

```bash
python3 ~/.claude/skills/jffs2-analyzer/scripts/jffs2_parser.py \
  --image /tmp/jffs2.img \
  --json-only
```

## Future Enhancements

Potential future additions:
- Summary entry parsing
- Data decompression (for content verification)
- Bad block detection
- Wear leveling analysis
- Comparison between multiple images