# JFFS2 Skills Guide

Three skills for JFFS2 filesystem testing.

## jffs2-analyzer

Static analysis without mounting.

```bash
/jffs2-analyzer <jffs2-image> [--output <dir>] [--verbose]
```

Output:
- Node structures (dirent, inode, data)
- File metadata
- CRC validation report

## jffs2-mount

Mount in QEMU for dynamic testing.

```bash
/jffs2-mount --kernel <path> [--image <path>] [--size <MB>] [--mount-test]
```

Options:
| Option | Description |
|--------|-------------|
| `--kernel` | Kernel image (required) |
| `--image` | JFFS2 image to mount |
| `--size` | MTD size in MB |
| `--mount-test` | Run mount verification |

Workflow:
1. Load MTD module
2. Create MTD device (mtdram)
3. Load JFFS2 module
4. Mount filesystem

## jffs2-fault-inject

Inject faults for testing kernel handling.

```bash
/jffs2-fault-inject --image <path> [--fault <type>] [--output <dir>]
```

Fault Types:
| Type | Description |
|------|-------------|
| `hdr_crc` | Header CRC corruption |
| `node_crc` | Node CRC corruption |
| `data_crc` | Data CRC corruption |
| `name_crc` | Name CRC corruption |
| `magic` | Magic number (0xDEAD) |
| `nodetype` | Invalid node type |
| `all` | All fault types |

## Workflow Example

```bash
# 1. Build kernel with JFFS2
/kernel-build JFFS2_FS --arch arm64 --cross

# 2. Create test image
/jffs2-mount --kernel Image --mount-test

# 3. Inject faults
/jffs2-fault-inject --image normal.jffs2 --fault hdr_crc,magic

# 4. Analyze corrupted image
/jffs2-analyzer corrupted.jffs2

# 5. Mount corrupted image in QEMU
/jffs2-mount --kernel Image --image corrupted.jffs2
```

## JFFS2 Node Types

| Type | Value | Description |
|------|-------|-------------|
| JFFS2_NODETYPE_DIRENT | 0x01 | Directory entry |
| JFFS2_NODETYPE_INODE | 0x02 | Inode metadata |
| JFFS2_NODETYPE_DATA | 0x03 | File data |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No MTD device | Load mtd.ko before jffs2.ko |
| Mount fails | Check JFFS2 module loaded |
| CRC errors | Expected for fault-injected images |