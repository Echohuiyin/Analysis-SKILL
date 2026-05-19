# JFFS2 Structure Reference

## Magic Numbers

| Name | Value | Description |
|------|-------|-------------|
| JFFS2_MAGIC_BITMASK | 0x1985 | Valid JFFS2 node |
| JFFS2_OLD_MAGIC_BITMASK | 0x1984 | Old version marker |
| JFFS2_EMPTY_BITMASK | 0xFFFF | Empty/erased flash |
| JFFS2_DIRTY_BITMASK | 0x0000 | Dirty/deleted marker |
| JFFS2_SUM_MAGIC | 0x02851885 | Summary marker magic |

## Node Types

| Type | Code | Description |
|------|------|-------------|
| JFFS2_NODETYPE_DIRENT | 0xE001 | Directory entry |
| JFFS2_NODETYPE_INODE | 0xE002 | Inode (file/directory metadata) |
| JFFS2_NODETYPE_CLEANMARKER | 0x2003 | Eraseblock clean marker |
| JFFS2_NODETYPE_PADDING | 0x2004 | Padding node |
| JFFS2_NODETYPE_SUMMARY | 0x2006 | Summary node |
| JFFS2_NODETYPE_XATTR | 0xE008 | Extended attribute |
| JFFS2_NODETYPE_XREF | 0xE009 | Xattr reference |

**Type Flags**:
- `JFFS2_NODE_ACCURATE = 0x2000`: Bit indicates accurate node
- `JFFS2_COMPAT_MASK = 0xC000`: Compatibility flags

## Compression Algorithms

| Code | Name | Description |
|------|------|-------------|
| 0x00 | JFFS2_COMPR_NONE | No compression |
| 0x01 | JFFS2_COMPR_ZERO | Zero-data optimization |
| 0x02 | JFFS2_COMPR_RTIME | Real-time compression |
| 0x03 | JFFS2_COMPR_RUBINMIPS | Rubin MIPS algorithm |
| 0x04 | JFFS2_COMPR_COPY | Direct copy |
| 0x05 | JFFS2_COMPR_DYNRUBIN | Dynamic Rubin |
| 0x06 | JFFS2_COMPR_ZLIB | Zlib compression |
| 0x07 | JFFS2_COMPR_LZO | LZO compression |

## Xattr Prefix Types

| Prefix | Code | Usage |
|--------|------|-------|
| JFFS2_XPREFIX_USER | 1 | user.* namespace |
| JFFS2_XPREFIX_SECURITY | 2 | security.* namespace |
| JFFS2_XPREFIX_ACL_ACCESS | 3 | system.posix_acl_access |
| JFFS2_XPREFIX_ACL_DEFAULT | 4 | system.posix_acl_default |
| JFFS2_XPREFIX_TRUSTED | 5 | trusted.* namespace |

## File Type Codes (Dirent)

| Type | Code | Description |
|------|------|-------------|
| DT_UNKNOWN | 0 | Unknown type |
| DT_FIFO | 1 | FIFO |
| DT_CHR | 2 | Character device |
| DT_DIR | 4 | Directory |
| DT_BLK | 6 | Block device |
| DT_REG | 8 | Regular file |
| DT_LNK | 10 | Symbolic link |
| DT_SOCK | 12 | Socket |
| DT_WHT | 14 | Whiteout (unionfs) |

## Common Node Header Structure

All nodes start with this header (8 bytes minimum):

```
Offset  Size  Field
0       2     magic (jint16_t)
2       2     nodetype (jint16_t)
4       4     totlen (jint32_t)
8       4     hdr_crc (jint32_t)
```

**CRC Calculation**:
- `hdr_crc`: CRC32 of first 8 bytes (magic + nodetype + totlen)
- `node_crc`: CRC32 of entire node structure (excluding data)
- `data_crc`: CRC32 of compressed/actual data payload
- `name_crc`: CRC32 of dirent name

## INODE Node Structure

Size: 68 bytes header + data

```
Offset  Size  Field
0       2     magic
2       2     nodetype (= JFFS2_NODETYPE_INODE)
4       4     totlen
8       4     hdr_crc
12      4     ino (inode number)
16      4     version
20      4     mode (permissions + file type)
24      2     uid
26      2     gid
28      4     isize (total file size)
32      4     atime
36      4     mtime
40      4     ctime
44      4     offset (data offset in file)
48      4     csize (compressed size)
52      4     dsize (decompressed size)
56      1     compr (compression algorithm)
57      1     usercompr
58      2     flags
60      4     data_crc
64      4     node_crc
68      var   data[]
```

**Mode Field**: Interpreted as standard Unix mode:
- Bits 0-11: Permissions (rwxrwxrwx)
- Bits 12-15: File type (S_IFDIR, S_IFREG, etc.)

## DIRENT Node Structure

Size: 36 bytes header + name

```
Offset  Size  Field
0       2     magic
2       2     nodetype (= JFFS2_NODETYPE_DIRENT)
4       4     totlen
8       4     hdr_crc
12      4     pino (parent inode)
16      4     version
20      4     ino (child inode, 0 = deletion marker)
24      4     mctime
28      1     nsize (name length)
29      1     type (DT_REG, DT_DIR, etc.)
30      2     unused
32      4     node_crc
36      4     name_crc
40      var   name[nsize]
```

**Padding**: Dirent nodes are padded to 4-byte alignment.

## XATTR Node Structure

Size: 20 bytes header + data

```
Offset  Size  Field
0       2     magic
2       2     nodetype (= JFFS2_NODETYPE_XATTR)
4       4     totlen
8       4     hdr_crc
12      4     xid (xattr identifier)
16      4     version
20      1     xprefix (namespace)
21      1     name_len
22      2     value_len
24      4     data_crc
28      4     node_crc
32      var   data[name_len + value_len]
```

## XREF Node Structure

Size: 24 bytes total

```
Offset  Size  Field
0       2     magic
2       2     nodetype (= JFFS2_NODETYPE_XREF)
4       4     totlen
8       4     hdr_crc
12      4     ino (inode number)
16      4     xid (xattr identifier)
20      4     xseqno (sequence number)
24      4     node_crc
```

## SUMMARY Node Structure

Size: 24 bytes header + entries + marker

```
Offset  Size  Field
0       2     magic
2       2     nodetype (= JFFS2_NODETYPE_SUMMARY)
4       4     totlen
8       4     hdr_crc
12      4     sum_num (entry count)
16      4     cln_mkr (cleanmarker size)
20      4     padded (padding total)
24      4     sum_crc
28      4     node_crc
32      var   sum[] (summary entries)
```

**Summary Entry Types**:
- INODE: 8 bytes (nodetype, ino, version, offset, totlen)
- DIRENT: 16 bytes + name (nodetype, totlen, offset, pino, version, ino, nsize, type, name)
- XATTR: 16 bytes (nodetype, xid, version, offset, totlen)
- XREF: 8 bytes (nodetype, offset)

**Summary Marker** (at end of summary node):
```
Offset  Size  Field
0       4     offset (summary node offset)
4       4     magic (= JFFS2_SUM_MAGIC)
```

## CLEANMARKER Node Structure

Size: 8 bytes minimum

```
Offset  Size  Field
0       2     magic
2       2     nodetype (= JFFS2_NODETYPE_CLEANMARKER)
4       4     totlen (typically 8)
8       4     hdr_crc
```

May have padding up to block erase requirements.

## Node Reference States

Node flash_offset encodes state in low 2 bits:

| State | Code | Description |
|-------|------|-------------|
| REF_UNCHECKED | 0 | Not yet validated |
| REF_OBSOLETE | 1 | Obsolete/deleted |
| REF_PRISTINE | 2 | Clean, no GC needed |
| REF_NORMAL | 3 | Normal, may need GC |

**Offset Extraction**: `offset = flash_offset & ~3`

## Alignment Rules

1. All nodes are 4-byte aligned
2. Node length (`totlen`) includes padding
3. Minimum node size: sizeof(jffs2_raw_dirent) with empty name
4. Padding nodes fill gaps between nodes

## Inode Flags

| Flag | Code | Description |
|------|------|-------------|
| JFFS2_INO_FLAG_PREREAD | 1 | Read at mount time |
| JFFS2_INO_FLAG_USERCOMPR | 2 | User-specified compression |

## Eraseblock States

| State | Code | Description |
|-------|------|-------------|
| BLK_STATE_ALLFF | 0 | All 0xFF (erased) |
| BLK_STATE_CLEAN | 1 | Clean data |
| BLK_STATE_PARTDIRTY | 2 | Partially dirty |
| BLK_STATE_CLEANMARKER | 3 | Only CLEANMARKER |
| BLK_STATE_ALLDIRTY | 4 | Fully dirty |
| BLK_STATE_BADBLOCK | 5 | Bad block |