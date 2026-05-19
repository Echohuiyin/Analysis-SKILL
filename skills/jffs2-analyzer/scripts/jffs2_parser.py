#!/usr/bin/env python3
"""
JFFS2 Image Parser and Analyzer

Parse JFFS2 filesystem images and generate comprehensive analysis reports.
"""

import argparse
import json
import os
import struct
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import binascii


# JFFS2 Constants (from include/uapi/linux/jffs2.h)
JFFS2_MAGIC_BITMASK = 0x1985
JFFS2_EMPTY_BITMASK = 0xFFFF
JFFS2_DIRTY_BITMASK = 0x0000
JFFS2_SUM_MAGIC = 0x02851885

# Node Types
JFFS2_NODETYPE_DIRENT = 0xE001
JFFS2_NODETYPE_INODE = 0xE002
JFFS2_NODETYPE_CLEANMARKER = 0x2003
JFFS2_NODETYPE_PADDING = 0x2004
JFFS2_NODETYPE_SUMMARY = 0x2006
JFFS2_NODETYPE_XATTR = 0xE008
JFFS2_NODETYPE_XREF = 0xE009

# Compression Algorithms
JFFS2_COMPR_NONE = 0x00
JFFS2_COMPR_ZERO = 0x01
JFFS2_COMPR_RTIME = 0x02
JFFS2_COMPR_ZLIB = 0x06
JFFS2_COMPR_LZO = 0x07

COMPR_NAMES = {
    0x00: "NONE",
    0x01: "ZERO",
    0x02: "RTIME",
    0x03: "RUBINMIPS",
    0x04: "COPY",
    0x05: "DYNRUBIN",
    0x06: "ZLIB",
    0x07: "LZO"
}

# File Types (Dirent)
DT_UNKNOWN = 0
DT_FIFO = 1
DT_CHR = 2
DT_DIR = 4
DT_BLK = 6
DT_REG = 8
DT_LNK = 10
DT_SOCK = 12
DT_WHT = 14

DT_NAMES = {
    0: "UNKNOWN",
    1: "FIFO",
    2: "CHR",
    4: "DIR",
    6: "BLK",
    8: "REG",
    10: "LNK",
    12: "SOCK",
    14: "WHT"
}

# Xattr Prefixes
XATTR_PREFIXES = {
    1: "user",
    2: "security",
    3: "acl_access",
    4: "acl_default",
    5: "trusted"
}

# Node Type Names
NODE_TYPE_NAMES = {
    JFFS2_NODETYPE_DIRENT: "DIRENT",
    JFFS2_NODETYPE_INODE: "INODE",
    JFFS2_NODETYPE_CLEANMARKER: "CLEANMARKER",
    JFFS2_NODETYPE_PADDING: "PADDING",
    JFFS2_NODETYPE_SUMMARY: "SUMMARY",
    JFFS2_NODETYPE_XATTR: "XATTR",
    JFFS2_NODETYPE_XREF: "XREF"
}


def crc32(data: bytes) -> int:
    """Calculate CRC32 checksum"""
    return binascii.crc32(data) & 0xFFFFFFFF


class JFFS2Node:
    """Represents a parsed JFFS2 node"""

    def __init__(self, offset: int, block_index: int, raw_data: bytes):
        self.offset = offset
        self.block_index = block_index
        self.raw_data = raw_data
        self.magic = None
        self.nodetype = None
        self.totlen = None
        self.hdr_crc = None
        self.valid = False
        self.crc_errors = []
        self.node_data = {}

    def parse_header(self) -> bool:
        """Parse common node header"""
        if len(self.raw_data) < 12:
            return False

        # Parse header (little-endian)
        self.magic, self.nodetype, self.totlen, self.hdr_crc = struct.unpack_from(
            '<HHII', self.raw_data, 0
        )

        # Validate magic
        if self.magic != JFFS2_MAGIC_BITMASK:
            return False

        # Validate header CRC
        header_data = self.raw_data[:8]
        calc_crc = crc32(header_data)
        if calc_crc != self.hdr_crc:
            self.crc_errors.append({
                'field': 'hdr_crc',
                'expected': self.hdr_crc,
                'actual': calc_crc
            })
            return False

        # Check total length is reasonable
        if self.totlen < 12 or self.totlen > len(self.raw_data):
            self.crc_errors.append({
                'field': 'totlen',
                'issue': 'invalid_length',
                'value': self.totlen
            })
            return False

        self.valid = True
        return True

    def get_type_name(self) -> str:
        """Get node type name"""
        return NODE_TYPE_NAMES.get(self.nodetype, f"UNKNOWN({self.nodetype:#x})")


class JFFS2DirentNode(JFFS2Node):
    """DIRENT node parser"""

    def parse(self) -> bool:
        if not self.parse_header():
            return False

        if self.nodetype != JFFS2_NODETYPE_DIRENT:
            return False

        if len(self.raw_data) < 40:
            return False

        # Parse DIRENT structure
        (pino, version, ino, mctime, nsize, dtype,
         unused1, unused2, node_crc, name_crc) = struct.unpack_from(
            '<IIIIBBHHII', self.raw_data, 12
        )

        # Extract name
        name_offset = 40
        if name_offset + nsize > len(self.raw_data):
            self.crc_errors.append({'field': 'name', 'issue': 'truncated'})
            return False

        name_data = self.raw_data[name_offset:name_offset + nsize]
        try:
            name = name_data.decode('utf-8', errors='replace')
        except:
            name = name_data.hex()

        # Validate node CRC (excluding data)
        node_struct = self.raw_data[:40]
        calc_node_crc = crc32(node_struct)
        if calc_node_crc != node_crc:
            self.crc_errors.append({
                'field': 'node_crc',
                'expected': node_crc,
                'actual': calc_node_crc
            })

        # Validate name CRC
        calc_name_crc = crc32(name_data)
        if calc_name_crc != name_crc:
            self.crc_errors.append({
                'field': 'name_crc',
                'expected': name_crc,
                'actual': calc_name_crc
            })

        self.node_data = {
            'pino': pino,
            'version': version,
            'ino': ino,
            'mctime': mctime,
            'nsize': nsize,
            'type': DT_NAMES.get(dtype, f"UNKNOWN({dtype})"),
            'type_code': dtype,
            'name': name,
            'is_deletion': ino == 0
        }

        return True


class JFFS2InodeNode(JFFS2Node):
    """INODE node parser"""

    def parse(self) -> bool:
        if not self.parse_header():
            return False

        if self.nodetype != JFFS2_NODETYPE_INODE:
            return False

        if len(self.raw_data) < 68:
            return False

        # Parse INODE structure
        fields = struct.unpack_from('<IIIIHHIIIIIIIIHHBHII', self.raw_data, 12)
        (ino, version, mode, uid, gid, isize, atime, mtime, ctime,
         offset, csize, dsize, compr, usercompr, flags,
         data_crc, node_crc) = fields

        # Validate node CRC
        node_struct = self.raw_data[:64]
        calc_node_crc = crc32(node_struct)
        if calc_node_crc != node_crc:
            self.crc_errors.append({
                'field': 'node_crc',
                'expected': node_crc,
                'actual': calc_node_crc
            })

        # Determine file type from mode
        file_type = self._get_file_type(mode)

        # Format times
        atime_str = datetime.fromtimestamp(atime).isoformat() if atime else None
        mtime_str = datetime.fromtimestamp(mtime).isoformat() if mtime else None
        ctime_str = datetime.fromtimestamp(ctime).isoformat() if ctime else None

        self.node_data = {
            'ino': ino,
            'version': version,
            'mode': f"{mode:08o}",
            'mode_raw': mode,
            'file_type': file_type,
            'uid': uid,
            'gid': gid,
            'isize': isize,
            'atime': atime_str,
            'mtime': mtime_str,
            'ctime': ctime_str,
            'data_offset': offset,
            'csize': csize,
            'dsize': dsize,
            'compr': COMPR_NAMES.get(compr, f"UNKNOWN({compr})"),
            'usercompr': COMPR_NAMES.get(usercompr, f"UNKNOWN({usercompr})"),
            'flags': flags,
            'data_crc': data_crc,
            'has_data': dsize > 0
        }

        return True

    def _get_file_type(self, mode: int) -> str:
        """Extract file type from mode field"""
        type_mask = mode & 0o170000
        type_map = {
            0o140000: "socket",
            0o120000: "symlink",
            0o100000: "file",
            0o060000: "block",
            0o040000: "directory",
            0o020000: "character",
            0o010000: "fifo"
        }
        return type_map.get(type_mask, "unknown")


class JFFS2XattrNode(JFFS2Node):
    """XATTR node parser"""

    def parse(self) -> bool:
        if not self.parse_header():
            return False

        if self.nodetype != JFFS2_NODETYPE_XATTR:
            return False

        if len(self.raw_data) < 32:
            return False

        # Parse XATTR structure
        (xid, version, xprefix, name_len, value_len,
         data_crc, node_crc) = struct.unpack_from('<IIBBHHII', self.raw_data, 12)

        # Extract name and value
        data_offset = 32
        if data_offset + name_len + value_len > len(self.raw_data):
            self.crc_errors.append({'field': 'data', 'issue': 'truncated'})
            return False

        name_data = self.raw_data[data_offset:data_offset + name_len]
        value_data = self.raw_data[data_offset + name_len:data_offset + name_len + value_len]

        try:
            name = name_data.decode('utf-8', errors='replace')
            value = value_data.hex()  # Value can be binary
        except:
            name = name_data.hex()

        prefix = XATTR_PREFIXES.get(xprefix, f"unknown({xprefix})")

        self.node_data = {
            'xid': xid,
            'version': version,
            'prefix': prefix,
            'prefix_code': xprefix,
            'name': name,
            'name_len': name_len,
            'value_len': value_len,
            'value_hex': value
        }

        return True


class JFFS2XrefNode(JFFS2Node):
    """XREF node parser"""

    def parse(self) -> bool:
        if not self.parse_header():
            return False

        if self.nodetype != JFFS2_NODETYPE_XREF:
            return False

        if len(self.raw_data) < 28:
            return False

        # Parse XREF structure
        (ino, xid, xseqno, node_crc) = struct.unpack_from('<IIII', self.raw_data, 12)

        self.node_data = {
            'ino': ino,
            'xid': xid,
            'xseqno': xseqno
        }

        return True


class JFFS2CleanmarkerNode(JFFS2Node):
    """CLEANMARKER node parser"""

    def parse(self) -> bool:
        if not self.parse_header():
            return False

        if self.nodetype != JFFS2_NODETYPE_CLEANMARKER:
            return False

        self.node_data = {
            'size': self.totlen
        }

        return True


class JFFS2SummaryNode(JFFS2Node):
    """SUMMARY node parser"""

    def parse(self) -> bool:
        if not self.parse_header():
            return False

        if self.nodetype != JFFS2_NODETYPE_SUMMARY:
            return False

        if len(self.raw_data) < 32:
            return False

        # Parse SUMMARY header
        (sum_num, cln_mkr, padded, sum_crc, node_crc) = struct.unpack_from(
            '<IIIII', self.raw_data, 12
        )

        self.node_data = {
            'sum_num': sum_num,
            'cln_mkr': cln_mkr,
            'padded': padded,
            'sum_crc': sum_crc,
            'entries_offset': 32
        }

        # Note: Parsing summary entries is complex, skipped for now
        # They are parsed during scan but not stored

        return True


class JFFS2Parser:
    """Main JFFS2 image parser"""

    def __init__(self, image_path: str, block_size: int = 65536):
        self.image_path = image_path
        self.block_size = block_size
        self.blocks = []
        self.nodes = []
        self.inodes = defaultdict(list)
        self.dirents = defaultdict(list)
        self.xattrs = {}
        self.anomalies = []
        self.stats = {
            'total_nodes': 0,
            'valid_nodes': 0,
            'crc_errors': 0,
            'dirent_count': 0,
            'inode_count': 0,
            'xattr_count': 0,
            'xref_count': 0,
            'cleanmarker_count': 0,
            'summary_count': 0
        }

    def detect_block_size(self) -> int:
        """Auto-detect eraseblock size"""
        file_size = os.path.getsize(self.image_path)

        # Try 64KB and 128KB
        for test_size in [65536, 131072]:
            if file_size % test_size == 0:
                # Read first block
                with open(self.image_path, 'rb') as f:
                    data = f.read(test_size)

                # Look for CLEANMARKER at start
                if len(data) >= 12:
                    magic, nodetype = struct.unpack_from('<HH', data, 0)
                    if magic == JFFS2_MAGIC_BITMASK and nodetype == JFFS2_NODETYPE_CLEANMARKER:
                        return test_size

        # Default to 64KB
        return 65536

    def scan_block(self, block_index: int, block_data: bytes) -> Dict:
        """Scan a single eraseblock"""
        block_info = {
            'block_index': block_index,
            'offset': block_index * self.block_size,
            'size': self.block_size,
            'state': 'unknown',
            'nodes': [],
            'node_count': 0,
            'used_size': 0,
            'free_size': self.block_size,
            'cleanmarker': False,
            'is_empty': True
        }

        offset = 0

        while offset < len(block_data) - 12:
            # Check for empty space (0xFF)
            if block_data[offset:offset+2] == b'\xFF\xFF':
                # Empty space, skip to next potential node or end
                # Look for next non-0xFF byte
                next_node = offset + 2
                while next_node < len(block_data) and block_data[next_node] == 0xFF:
                    next_node += 1

                if next_node >= len(block_data):
                    break

                offset = next_node
                continue

            # Check for dirty space (0x00)
            if block_data[offset:offset+2] == b'\x00\x00':
                offset += 2
                continue

            # Try to parse node
            remaining_data = block_data[offset:]
            node = self._parse_node(offset, block_index, remaining_data)

            if node and node.valid:
                block_info['nodes'].append({
                    'offset': offset,
                    'type': node.get_type_name(),
                    'totlen': node.totlen,
                    'valid': node.valid
                })
                block_info['node_count'] += 1
                block_info['used_size'] += node.totlen
                block_info['free_size'] -= node.totlen
                block_info['is_empty'] = False

                if node.nodetype == JFFS2_NODETYPE_CLEANMARKER:
                    block_info['cleanmarker'] = True

                # Store node
                self.nodes.append(node)
                self.stats['total_nodes'] += 1
                self.stats['valid_nodes'] += 1

                # Track by inode
                if node.nodetype == JFFS2_NODETYPE_INODE:
                    ino = node.node_data.get('ino')
                    if ino:
                        self.inodes[ino].append(node)
                    self.stats['inode_count'] += 1

                elif node.nodetype == JFFS2_NODETYPE_DIRENT:
                    pino = node.node_data.get('pino')
                    if pino:
                        self.dirents[pino].append(node)
                    self.stats['dirent_count'] += 1

                elif node.nodetype == JFFS2_NODETYPE_XATTR:
                    xid = node.node_data.get('xid')
                    if xid:
                        self.xattrs[xid] = node
                    self.stats['xattr_count'] += 1

                elif node.nodetype == JFFS2_NODETYPE_XREF:
                    self.stats['xref_count'] += 1

                elif node.nodetype == JFFS2_NODETYPE_SUMMARY:
                    self.stats['summary_count'] += 1

                elif node.nodetype == JFFS2_NODETYPE_CLEANMARKER:
                    self.stats['cleanmarker_count'] += 1

                # Check for CRC errors
                if node.crc_errors:
                    for error in node.crc_errors:
                        self.anomalies.append({
                            'type': 'crc_error',
                            'severity': 'HIGH',
                            'block': block_index,
                            'offset': offset,
                            'node_type': node.get_type_name(),
                            'details': error
                        })
                    self.stats['crc_errors'] += len(node.crc_errors)

                # Move to next node (pad to 4-byte alignment)
                padded_len = (node.totlen + 3) & ~3
                offset += padded_len
            else:
                # Invalid node, skip
                offset += 4

        # Determine block state
        if block_info['cleanmarker'] and block_info['node_count'] == 1:
            block_info['state'] = 'cleanmarker'
        elif block_info['is_empty']:
            block_info['state'] = 'empty'
        elif block_info['used_size'] > 0:
            if block_info['used_size'] == block_info['size']:
                block_info['state'] = 'full'
            elif block_info['free_size'] < block_info['size'] * 0.1:
                block_info['state'] = 'mostly_used'
            else:
                block_info['state'] = 'partial'

        return block_info

    def _parse_node(self, offset: int, block_index: int, data: bytes) -> Optional[JFFS2Node]:
        """Parse a node based on its type"""
        # Check minimum size
        if len(data) < 12:
            return None

        # Parse header to get nodetype
        try:
            magic, nodetype = struct.unpack_from('<HH', data, 0)
        except:
            return None

        # Validate magic
        if magic != JFFS2_MAGIC_BITMASK:
            self.anomalies.append({
                'type': 'invalid_magic',
                'severity': 'CRITICAL',
                'block': block_index,
                'offset': offset,
                'details': {'expected': JFFS2_MAGIC_BITMASK, 'actual': magic}
            })
            return None

        # Create appropriate parser
        if nodetype == JFFS2_NODETYPE_DIRENT:
            node = JFFS2DirentNode(offset, block_index, data)
        elif nodetype == JFFS2_NODETYPE_INODE:
            node = JFFS2InodeNode(offset, block_index, data)
        elif nodetype == JFFS2_NODETYPE_XATTR:
            node = JFFS2XattrNode(offset, block_index, data)
        elif nodetype == JFFS2_NODETYPE_XREF:
            node = JFFS2XrefNode(offset, block_index, data)
        elif nodetype == JFFS2_NODETYPE_CLEANMARKER:
            node = JFFS2CleanmarkerNode(offset, block_index, data)
        elif nodetype == JFFS2_NODETYPE_SUMMARY:
            node = JFFS2SummaryNode(offset, block_index, data)
        elif nodetype == JFFS2_NODETYPE_PADDING:
            # Padding nodes are minimal
            node = JFFS2Node(offset, block_index, data)
            node.parse_header()
            node.node_data = {'padding': True}
            return node
        else:
            # Unknown node type
            self.anomalies.append({
                'type': 'unknown_nodetype',
                'severity': 'MEDIUM',
                'block': block_index,
                'offset': offset,
                'details': {'nodetype': nodetype}
            })
            return None

        # Parse the node
        if not node.parse():
            return None

        return node

    def parse(self) -> bool:
        """Parse entire JFFS2 image"""
        # Detect block size
        self.block_size = self.detect_block_size()

        file_size = os.path.getsize(self.image_path)
        block_count = file_size // self.block_size

        print(f"Parsing JFFS2 image: {self.image_path}")
        print(f"File size: {file_size} bytes")
        print(f"Block size: {self.block_size} bytes")
        print(f"Block count: {block_count}")

        # Read and scan each block
        with open(self.image_path, 'rb') as f:
            for block_idx in range(block_count):
                print(f"Scanning block {block_idx}/{block_count-1}...", end='\r')

                block_data = f.read(self.block_size)
                if len(block_data) < self.block_size:
                    print(f"Warning: Block {block_idx} truncated")
                    break

                block_info = self.scan_block(block_idx, block_data)
                self.blocks.append(block_info)

        print(f"\nScan complete. Found {self.stats['total_nodes']} nodes")

        # Post-processing: detect anomalies
        self._detect_version_conflicts()
        self._detect_orphan_dirents()

        return True

    def _detect_version_conflicts(self):
        """Detect nodes with conflicting versions"""
        for ino, node_list in self.inodes.items():
            versions = defaultdict(list)
            for node in node_list:
                version = node.node_data.get('version')
                if version:
                    versions[version].append(node)

            # Check for duplicates
            for version, nodes in versions.items():
                if len(nodes) > 1:
                    self.anomalies.append({
                        'type': 'version_conflict',
                        'severity': 'MEDIUM',
                        'details': {
                            'ino': ino,
                            'version': version,
                            'count': len(nodes),
                            'offsets': [n.offset for n in nodes]
                        }
                    })

    def _detect_orphan_dirents(self):
        """Detect dirents referencing non-existent inodes"""
        valid_inos = set(self.inodes.keys())
        valid_inos.add(1)  # Root inode always exists

        for pino, dirent_list in self.dirents.items():
            for dirent in dirent_list:
                ino = dirent.node_data.get('ino')
                if ino and ino != 0 and ino not in valid_inos:
                    self.anomalies.append({
                        'type': 'orphan_dirent',
                        'severity': 'LOW',
                        'details': {
                            'dirent_offset': dirent.offset,
                            'name': dirent.node_data.get('name'),
                            'referenced_ino': ino,
                            'parent_ino': pino
                        }
                    })

    def build_directory_tree(self) -> Dict:
        """Build directory tree structure"""
        tree = {}

        # Start with root (ino=1)
        if 1 in self.inodes:
            tree['/'] = {
                'ino': 1,
                'type': 'directory',
                'children': {}
            }

        # Process dirents
        for pino, dirent_list in self.dirents.items():
            # Find parent path
            parent_path = self._find_path(pino, tree)
            if not parent_path:
                continue

            # Get latest version for each name
            latest_dirents = {}
            for dirent in dirent_list:
                name = dirent.node_data.get('name')
                version = dirent.node_data.get('version')
                ino = dirent.node_data.get('ino')

                if name not in latest_dirents or version > latest_dirents[name]['version']:
                    latest_dirents[name] = {
                        'version': version,
                        'ino': ino,
                        'type': dirent.node_data.get('type'),
                        'is_deletion': dirent.node_data.get('is_deletion')
                    }

            # Add to tree
            parent_node = self._get_node_at_path(parent_path, tree)
            if parent_node:
                for name, info in latest_dirents.items():
                    if not info['is_deletion'] and info['ino'] != 0:
                        parent_node['children'][name] = {
                            'ino': info['ino'],
                            'type': info['type']
                        }

        return tree

    def _find_path(self, ino: int, tree: Dict) -> Optional[str]:
        """Find path for an inode"""
        if ino == 1:
            return '/'

        # BFS search
        def search(node, current_path):
            for name, child in node.get('children', {}).items():
                if child['ino'] == ino:
                    return f"{current_path}/{name}"
                if child['type'] == 'DIR':
                    result = search(child, f"{current_path}/{name}")
                    if result:
                        return result
            return None

        for path, root in tree.items():
            result = search(root, path)
            if result:
                return result

        return None

    def _get_node_at_path(self, path: str, tree: Dict) -> Optional[Dict]:
        """Get node at a specific path"""
        if path == '/':
            return tree.get('/')

        parts = path.strip('/').split('/')
        current = tree.get('/')

        for part in parts:
            if not current:
                return None
            current = current.get('children', {}).get(part)

        return current

    def generate_json(self) -> Dict:
        """Generate JSON structure"""
        # Build nodes array
        nodes_data = []
        for node in self.nodes:
            node_entry = {
                'offset': node.offset,
                'block_index': node.block_index,
                'type': node.get_type_name(),
                'magic': node.magic,
                'nodetype': node.nodetype,
                'totlen': node.totlen,
                'valid': node.valid,
                'crc_errors': len(node.crc_errors) > 0,
                'data': node.node_data
            }
            nodes_data.append(node_entry)

        # Build inode summary
        inodes_data = {}
        for ino, node_list in self.inodes.items():
            # Get latest version
            latest_node = None
            latest_version = 0

            for node in node_list:
                version = node.node_data.get('version', 0)
                if version > latest_version:
                    latest_version = version
                    latest_node = node

            if latest_node:
                inodes_data[ino] = {
                    'ino': ino,
                    'file_type': latest_node.node_data.get('file_type'),
                    'mode': latest_node.node_data.get('mode'),
                    'uid': latest_node.node_data.get('uid'),
                    'gid': latest_node.node_data.get('gid'),
                    'isize': latest_node.node_data.get('isize'),
                    'node_count': len(node_list),
                    'latest_version': latest_version,
                    'node_offsets': [n.offset for n in node_list]
                }

        # Build directory tree
        dir_tree = self.build_directory_tree()

        result = {
            'image_info': {
                'file_path': self.image_path,
                'file_size': os.path.getsize(self.image_path),
                'block_size': self.block_size,
                'block_count': len(self.blocks)
            },
            'blocks': self.blocks,
            'nodes': nodes_data,
            'inodes': inodes_data,
            'directory_tree': dir_tree,
            'anomalies': self.anomalies,
            'statistics': self.stats
        }

        return result

    def generate_summary_report(self) -> str:
        """Generate markdown summary report"""
        report = []

        # Header
        report.append("# JFFS2 Image Analysis Summary")
        report.append(f"\n**Image**: {self.image_path}")
        report.append(f"\n**Generated**: {datetime.now().isoformat()}")
        report.append("\n")

        # Image Overview
        report.append("## Image Overview")
        report.append(f"- File size: {os.path.getsize(self.image_path):,} bytes ({os.path.getsize(self.image_path) / 1024 / 1024:.2f} MB)")
        report.append(f"- Block size: {self.block_size:,} bytes ({self.block_size / 1024:.0f} KB)")
        report.append(f"- Block count: {len(self.blocks)}")
        report.append("\n")

        # Block Distribution
        report.append("## Block Distribution")
        state_counts = defaultdict(int)
        for block in self.blocks:
            state_counts[block['state']] += 1

        for state, count in sorted(state_counts.items()):
            pct = (count / len(self.blocks)) * 100
            report.append(f"- {state}: {count} blocks ({pct:.1f}%)")
        report.append("\n")

        # Node Distribution
        report.append("## Node Distribution")
        report.append(f"- Total nodes: {self.stats['total_nodes']}")
        report.append(f"- Valid nodes: {self.stats['valid_nodes']}")
        report.append(f"- INODE nodes: {self.stats['inode_count']}")
        report.append(f"- DIRENT nodes: {self.stats['dirent_count']}")
        report.append(f"- XATTR nodes: {self.stats['xattr_count']}")
        report.append(f"- XREF nodes: {self.stats['xref_count']}")
        report.append(f"- CLEANMARKER nodes: {self.stats['cleanmarker_count']}")
        report.append(f"- SUMMARY nodes: {self.stats['summary_count']}")
        report.append("\n")

        # Inode Statistics
        report.append("## Inode Statistics")
        report.append(f"- Total inodes: {len(self.inodes)}")

        # Count by type
        type_counts = defaultdict(int)
        for ino, node_list in self.inodes.items():
            if node_list:
                file_type = node_list[0].node_data.get('file_type', 'unknown')
                type_counts[file_type] += 1

        for ftype, count in sorted(type_counts.items()):
            report.append(f"- {ftype}: {count}")
        report.append("\n")

        # Directory Tree (simplified)
        report.append("## Directory Tree (First 2 Levels)")
        dir_tree = self.build_directory_tree()

        if '/' in dir_tree:
            report.append("```")
            report.append("/")
            children = dir_tree['/'].get('children', {})
            for name, info in sorted(children.items())[:10]:
                report.append(f"├── {name} (ino={info['ino']}, type={info['type']})")
            if len(children) > 10:
                report.append(f"└── ... ({len(children) - 10} more entries)")
            report.append("```")
        report.append("\n")

        # Anomaly Report
        report.append("## Anomaly Report")
        if self.anomalies:
            report.append(f"\n⚠️ **Found {len(self.anomalies)} anomalies:**\n")

            severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
            sorted_anomalies = sorted(self.anomalies,
                                      key=lambda x: severity_order.get(x['severity'], 4))

            for i, anomaly in enumerate(sorted_anomalies[:20], 1):  # Show top 20
                report.append(f"{i}. **{anomaly['type']}** ({anomaly['severity']})")
                if 'offset' in anomaly:
                    report.append(f"   - Block: {anomaly.get('block')}, Offset: {anomaly['offset']:#x}")
                details = anomaly.get('details', {})
                for key, value in details.items():
                    if isinstance(value, int):
                        report.append(f"   - {key}: {value:#x}")
                    else:
                        report.append(f"   - {key}: {value}")
                report.append("")

            if len(self.anomalies) > 20:
                report.append(f"... and {len(self.anomalies) - 20} more anomalies")
        else:
            report.append("\n✅ No anomalies detected")

        report.append("\n")

        # Recommendations
        report.append("## Recommendations")
        if self.stats['crc_errors'] > 0:
            report.append(f"- ⚠️ {self.stats['crc_errors']} CRC errors detected")
            report.append("  - Consider using `fsck.jffs2` for repair")

        unknown_count = sum(1 for a in self.anomalies if a['type'] == 'unknown_nodetype')
        if unknown_count > 0:
            report.append(f"- {unknown_count} unknown node types found")
            report.append("  - May indicate newer JFFS2 version or custom extensions")

        orphan_count = sum(1 for a in self.anomalies if a['type'] == 'orphan_dirent')
        if orphan_count > 0:
            report.append(f"- {orphan_count} orphan directory entries")
            report.append("  - Some files may have been partially deleted")

        valid_ratio = self.stats['valid_nodes'] / self.stats['total_nodes'] if self.stats['total_nodes'] > 0 else 0
        if valid_ratio < 0.95:
            report.append(f"- Valid node ratio: {valid_ratio:.2%}")
            report.append("  - High corruption rate, verify flash integrity")
        else:
            report.append(f"- Valid node ratio: {valid_ratio:.2%} (healthy)")

        return '\n'.join(report)


def main():
    parser = argparse.ArgumentParser(description='JFFS2 Image Parser and Analyzer')
    parser.add_argument('image', help='JFFS2 image file path')
    parser.add_argument('--block-size', type=int, default=None,
                        help='Eraseblock size (auto-detected if not specified)')
    parser.add_argument('--output-dir', default='./jffs2_analysis_output',
                        help='Output directory for reports')
    parser.add_argument('--json-only', action='store_true',
                        help='Generate only JSON output')
    parser.add_argument('--summary-only', action='store_true',
                        help='Generate only summary report')

    args = parser.parse_args()

    # Validate input
    if not os.path.exists(args.image):
        print(f"ERROR: Image file not found: {args.image}")
        sys.exit(1)

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Parse image
    block_size = args.block_size if args.block_size else 65536
    jffs2_parser = JFFS2Parser(args.image, block_size)

    if not jffs2_parser.parse():
        print("ERROR: Failed to parse image")
        sys.exit(1)

    # Generate outputs
    if not args.summary_only:
        json_data = jffs2_parser.generate_json()
        json_path = os.path.join(args.output_dir, 'jffs2_structure.json')
        with open(json_path, 'w') as f:
            json.dump(json_data, f, indent=2)
        print(f"JSON data saved to: {json_path}")

    if not args.json_only:
        summary = jffs2_parser.generate_summary_report()
        summary_path = os.path.join(args.output_dir, 'jffs2_analysis_summary.md')
        with open(summary_path, 'w') as f:
            f.write(summary)
        print(f"Summary report saved to: {summary_path}")

    # Print quick stats
    print("\n=== Quick Statistics ===")
    print(f"Blocks scanned: {len(jffs2_parser.blocks)}")
    print(f"Nodes found: {jffs2_parser.stats['total_nodes']}")
    print(f"Valid nodes: {jffs2_parser.stats['valid_nodes']}")
    print(f"Anomalies: {len(jffs2_parser.anomalies)}")
    print(f"Inodes: {len(jffs2_parser.inodes)}")

    if jffs2_parser.anomalies:
        print("\n⚠️ Anomalies detected - check report for details")
    else:
        print("\n✅ No anomalies detected")


if __name__ == '__main__':
    main()