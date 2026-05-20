---
name: jffs2-fault-inject
description: Inject controlled faults into JFFS2 filesystem images for testing kernel error handling. Use when user wants to create corrupted JFFS2 images, test fault injection scenarios, or verify kernel fault detection capabilities. Supports CRC corruption, structure damage, and content corruption fault types.
---

# JFFS2 Fault Injection Skill

Inject controlled faults into JFFS2 filesystem images for kernel error handling testing.

## What This Skill Does

Creates corrupted JFFS2 images by injecting specific faults at precise locations:

1. **CRC Faults**: Header CRC, node CRC, data CRC, name CRC corruption
2. **Structure Faults**: Invalid magic number, invalid node type, invalid total length
3. **Content Faults**: Version number corruption, data truncation

## Usage

```
/jffs2-fault-inject --image <path> --fault <fault-types> [--output <path>]
```

Options:
- `--image` (required): Path to normal JFFS2 image
- `--fault`: Fault type(s) to inject (comma-separated)
- `--output`: Output path for corrupted image
- `--node-type`: Target specific node type (inode, dirent)
- `--offset`: Target specific node offset (hex)
- `--list`: List nodes in image without injecting

## Fault Types

| Type | Description | Effect | Detection Point |
|------|-------------|--------|----------------|
| `hdr_crc_corrupt` | Header CRC corruption | Node rejected during scan | scan.c:764 |
| `node_crc_corrupt` | Node CRC corruption | Node rejected during scan | scan.c:1012/1060 |
| `data_crc_corrupt` | Data CRC corruption | Read returns EIO | read.c:124 |
| `name_crc_corrupt` | Name CRC corruption | Dirent rejected | scan.c:1087 |
| `magic_invalid` | Invalid magic (0x1985→0xDEAD) | Node skipped | scan.c:749 |
| `nodetype_invalid` | Invalid node type | Compatibility handling | scan.c:903 |
| `totlen_invalid` | Invalid total length | Length check fails | scan.c:780 |
| `version_zero` | Zero version number | Version conflict | scan.c |

## Workflow

### Step 1: Load and Parse Image

```bash
python3 scripts/jffs2_fault_injector.py --image normal.jffs2 --list
```

Output shows all JFFS2 nodes with their offsets and types.

### Step 2: Inject Faults

```bash
# Single fault
/jffs2-fault-inject --image normal.jffs2 --fault hdr_crc_corrupt --output corrupted.jffs2

# Multiple faults (different nodes)
/jffs2-fault-inject --image normal.jffs2 --fault hdr_crc,node_crc,data_crc --output multi.jffs2

# Target specific node type
/jffs2-fault-inject --image normal.jffs2 --fault data_crc_corrupt --node-type inode --output corrupted.jffs2

# Target specific offset
/jffs2-fault-inject --image normal.jffs2 --fault magic_invalid --offset 0x1000 --output corrupted.jffs2
```

### Step 3: Verify Injection

```bash
/jffs2-analyzer corrupted.jffs2
```

The analyzer should detect the injected faults as anomalies.

## Output Files

- `corrupted.jffs2`: Corrupted JFFS2 image
- `faults.json`: Detailed fault injection report
- Console summary: Fault injection details

## Integration with Other Skills

### Full Testing Workflow

```
Step 1: /jffs2-mount --kernel Image --size 16
  → Creates normal.jffs2

Step 2: /jffs2-fault-inject --image normal.jffs2 --fault hdr_crc,node_crc
  → Creates corrupted.jffs2 + faults.json

Step 3: /kernel-build JFFS2_FS --arch arm64 --cross
  → Compiles kernel with enhanced diagnostics

Step 4: /qemu-test --arch arm64 --kernel Image --script fault_test.sh
  → Boots QEMU, mounts corrupted image, captures diagnostics

Step 5: /jffs2-analyzer corrupted.jffs2
  → Analyzes corrupted image structure
```

## Example Output

```
$ /jffs2-fault-inject --image test.jffs2 --fault hdr_crc_corrupt --output corrupted.jffs2

Loaded image: test.jffs2 (16777216 bytes)
Found 42 JFFS2 nodes

Injecting faults: ['hdr_crc_corrupt']
Injected hdr_crc_corrupt at 0x00001008
  Byte offset: 0x00001010
  Original: 0xabc12345
  Corrupted: 0xabc12346

Saved corrupted image: corrupted.jffs2
Generated fault report: ./faults.json

=== JFFS2 Fault Injection Summary ===
Source: test.jffs2
Faults injected: 1

hdr_crc_corrupt:
  Node: INODE at 0x00001008
  Original CRC: 0xabc12345
  Corrupted CRC: 0xabc12346
```

## Error Handling

### No Suitable Node
```
Error: No suitable target node found for fault injection
Solution: Use --list to see available nodes, or try different --node-type
```

### Image Not Found
```
Error: Cannot read image file
Solution: Check file path and permissions
```

### Fault Type Incompatible
```
Warning: DATA_CRC_CORRUPT only applies to INODE nodes
Solution: Use --node-type inode or select different fault type
```