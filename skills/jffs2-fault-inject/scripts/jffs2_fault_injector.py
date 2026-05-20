#!/usr/bin/env python3
"""
JFFS2 Fault Injection Tool

Inject controlled faults into JFFS2 filesystem images for testing
kernel error handling and recovery mechanisms.
"""

import argparse
import json
import os
import struct
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from enum import Enum

# JFFS2 constants
JFFS2_MAGIC_BITMASK = 0x1985
JFFS2_NODETYPE_INODE = 0xE002  # JFFS2_NODETYPE_INODE
JFFS2_NODETYPE_DIRENT = 0xE001  # JFFS2_NODETYPE_DIRENT
JFFS2_NODETYPE_CLEANMARKER = 0x2003
JFFS2_NODETYPE_PADDING = 0x2004
JFFS2_NODETYPE_SUMMARY = 0x2005
JFFS2_NODETYPE_XATTR = 0x2006
JFFS2_NODETYPE_XREF = 0x2007

NODE_TYPE_NAMES = {
    JFFS2_NODETYPE_INODE: "INODE",
    JFFS2_NODETYPE_DIRENT: "DIRENT",
    JFFS2_NODETYPE_CLEANMARKER: "CLEANMARKER",
    JFFS2_NODETYPE_PADDING: "PADDING",
    JFFS2_NODETYPE_SUMMARY: "SUMMARY",
    JFFS2_NODETYPE_XATTR: "XATTR",
    JFFS2_NODETYPE_XREF: "XREF",
}


class FaultType(Enum):
    """Supported fault injection types"""
    HDR_CRC_CORRUPT = "hdr_crc_corrupt"
    NODE_CRC_CORRUPT = "node_crc_corrupt"
    DATA_CRC_CORRUPT = "data_crc_corrupt"
    NAME_CRC_CORRUPT = "name_crc_corrupt"
    MAGIC_INVALID = "magic_invalid"
    NODETYPE_INVALID = "nodetype_invalid"
    TOTLEN_INVALID = "totlen_invalid"
    VERSION_ZERO = "version_zero"


FAULT_DESCRIPTIONS = {
    FaultType.HDR_CRC_CORRUPT: "Corrupt header CRC (offset +8)",
    FaultType.NODE_CRC_CORRUPT: "Corrupt node CRC",
    FaultType.DATA_CRC_CORRUPT: "Corrupt data CRC (INODE only)",
    FaultType.NAME_CRC_CORRUPT: "Corrupt name CRC (DIRENT only)",
    FaultType.MAGIC_INVALID: "Invalid magic number (0x1985 -> 0xDEAD)",
    FaultType.NODETYPE_INVALID: "Invalid node type",
    FaultType.TOTLEN_INVALID: "Invalid total length",
    FaultType.VERSION_ZERO: "Zero version number",
}


class JFFS2Node:
    """Represents a parsed JFFS2 node"""
    def __init__(self, offset: int, nodetype: int, totlen: int):
        self.offset = offset
        self.nodetype = nodetype
        self.totlen = totlen
        self.type_name = NODE_TYPE_NAMES.get(nodetype, f"UNKNOWN({nodetype:#x})")

    def __repr__(self):
        return f"JFFS2Node(offset=0x{self.offset:08x}, type={self.type_name}, len={self.totlen})"


class JFFS2FaultInjector:
    """Inject controlled faults into JFFS2 images"""

    def __init__(self, image_path: str):
        self.image_path = image_path
        self.image_data: Optional[bytearray] = None
        self.block_size = 65536  # 64KB default
        self.nodes: List[JFFS2Node] = []
        self.fault_log: List[Dict] = []

    def load_image(self) -> bool:
        """Load and parse JFFS2 image"""
        try:
            with open(self.image_path, 'rb') as f:
                self.image_data = bytearray(f.read())
            print(f"Loaded image: {self.image_path} ({len(self.image_data)} bytes)")
            self._scan_nodes()
            print(f"Found {len(self.nodes)} JFFS2 nodes")
            return True
        except Exception as e:
            print(f"Error loading image: {e}")
            return False

    def _scan_nodes(self):
        """Scan image to identify all JFFS2 nodes"""
        offset = 0
        while offset < len(self.image_data) - 12:
            magic = struct.unpack_from('<H', self.image_data, offset)[0]

            if magic == JFFS2_MAGIC_BITMASK:
                nodetype = struct.unpack_from('<H', self.image_data, offset + 2)[0]
                totlen = struct.unpack_from('<I', self.image_data, offset + 4)[0]

                if totlen > 0 and totlen < 0x1000000 and offset + totlen <= len(self.image_data):
                    self.nodes.append(JFFS2Node(offset, nodetype, totlen))
                    offset += self._pad_length(totlen)
                else:
                    offset += 4
            elif magic == 0xFFFF:
                offset += 4
            else:
                offset += 4

    def _pad_length(self, length: int) -> int:
        """Calculate padded length (4-byte aligned)"""
        return (length + 3) & ~3

    def list_nodes(self, node_type_filter: str = None) -> None:
        """Print all found nodes"""
        print("\n=== JFFS2 Nodes in Image ===")
        inode_count = 0
        dirent_count = 0

        for node in self.nodes:
            if node_type_filter and node.type_name.lower() != node_type_filter.lower():
                continue
            print(f"  0x{node.offset:08x}: {node.type_name} (len={node.totlen})")
            if node.nodetype == JFFS2_NODETYPE_INODE:
                inode_count += 1
            elif node.nodetype == JFFS2_NODETYPE_DIRENT:
                dirent_count += 1

        print(f"\nTotal: {len(self.nodes)} nodes ({inode_count} INODE, {dirent_count} DIRENT)")

    def select_target_node(self, target_offset: int = None,
                           target_node_type: str = None) -> Optional[JFFS2Node]:
        """Select a target node for fault injection"""
        candidates = []

        for node in self.nodes:
            # Skip CLEANMARKER and PADDING nodes
            if node.nodetype in [JFFS2_NODETYPE_CLEANMARKER, JFFS2_NODETYPE_PADDING]:
                continue

            if target_offset is not None:
                if node.offset == target_offset:
                    return node
            elif target_node_type:
                if node.type_name.lower() == target_node_type.lower():
                    candidates.append(node)
            else:
                candidates.append(node)

        if candidates:
            # Return first candidate (or random if needed)
            return candidates[0]
        return None

    def inject_fault(self, fault_type: FaultType, target_offset: int = None,
                     target_node_type: str = None) -> Optional[Dict]:
        """
        Inject specified fault type

        Returns fault details dictionary
        """
        target_node = self.select_target_node(target_offset, target_node_type)
        if not target_node:
            print(f"No suitable target node found for fault injection")
            return None

        offset = target_node.offset
        result = self._apply_fault(fault_type, offset, target_node)

        if result:
            fault_record = {
                'fault_type': fault_type.value,
                'description': FAULT_DESCRIPTIONS[fault_type],
                'target_offset': offset,
                'target_node_type': target_node.type_name,
                'original_value': result['original'],
                'corrupted_value': result['corrupted'],
                'byte_offset': result['byte_offset'],
            }
            self.fault_log.append(fault_record)
            print(f"Injected {fault_type.value} at 0x{offset:08x}")
            print(f"  Byte offset: 0x{result['byte_offset']:08x}")
            print(f"  Original: {result['original']}")
            print(f"  Corrupted: {result['corrupted']}")
            return fault_record

        return None

    def _apply_fault(self, fault_type: FaultType, offset: int,
                     node: JFFS2Node) -> Optional[Dict]:
        """Apply specific fault at given offset"""
        result = {'byte_offset': 0, 'original': '', 'corrupted': ''}

        if fault_type == FaultType.HDR_CRC_CORRUPT:
            # Header CRC at offset +8
            byte_offset = offset + 8
            original = struct.unpack_from('<I', self.image_data, byte_offset)[0]
            corrupted = original ^ 0x00000001  # Flip one bit
            struct.pack_into('<I', self.image_data, byte_offset, corrupted)
            result = {
                'byte_offset': byte_offset,
                'original': f"0x{original:08x}",
                'corrupted': f"0x{corrupted:08x}"
            }

        elif fault_type == FaultType.NODE_CRC_CORRUPT:
            # node_crc location depends on node type
            if node.nodetype == JFFS2_NODETYPE_INODE:
                # INODE: node_crc at offset +60
                byte_offset = offset + 60
            elif node.nodetype == JFFS2_NODETYPE_DIRENT:
                # DIRENT: node_crc at offset +36
                byte_offset = offset + 36
            else:
                byte_offset = offset + 8

            original = struct.unpack_from('<I', self.image_data, byte_offset)[0]
            corrupted = original ^ 0x12345678
            struct.pack_into('<I', self.image_data, byte_offset, corrupted)
            result = {
                'byte_offset': byte_offset,
                'original': f"0x{original:08x}",
                'corrupted': f"0x{corrupted:08x}"
            }

        elif fault_type == FaultType.DATA_CRC_CORRUPT:
            # data_crc at offset +56 for INODE node
            if node.nodetype != JFFS2_NODETYPE_INODE:
                print("DATA_CRC_CORRUPT only applies to INODE nodes")
                return None

            byte_offset = offset + 56
            original = struct.unpack_from('<I', self.image_data, byte_offset)[0]
            corrupted = (original + 1) & 0xFFFFFFFF
            struct.pack_into('<I', self.image_data, byte_offset, corrupted)
            result = {
                'byte_offset': byte_offset,
                'original': f"0x{original:08x}",
                'corrupted': f"0x{corrupted:08x}"
            }

        elif fault_type == FaultType.NAME_CRC_CORRUPT:
            # name_crc at offset +40 for DIRENT
            if node.nodetype != JFFS2_NODETYPE_DIRENT:
                print("NAME_CRC_CORRUPT only applies to DIRENT nodes")
                return None

            byte_offset = offset + 40
            original = struct.unpack_from('<I', self.image_data, byte_offset)[0]
            corrupted = original ^ 0xFFFFFFFF
            struct.pack_into('<I', self.image_data, byte_offset, corrupted)
            result = {
                'byte_offset': byte_offset,
                'original': f"0x{original:08x}",
                'corrupted': f"0x{corrupted:08x}"
            }

        elif fault_type == FaultType.MAGIC_INVALID:
            byte_offset = offset
            original = struct.unpack_from('<H', self.image_data, byte_offset)[0]
            corrupted = 0xDEAD
            struct.pack_into('<H', self.image_data, byte_offset, corrupted)
            result = {
                'byte_offset': byte_offset,
                'original': f"0x{original:04x}",
                'corrupted': f"0x{corrupted:04x}"
            }

        elif fault_type == FaultType.NODETYPE_INVALID:
            byte_offset = offset + 2
            original = struct.unpack_from('<H', self.image_data, byte_offset)[0]
            corrupted = 0xFFFF
            struct.pack_into('<H', self.image_data, byte_offset, corrupted)
            result = {
                'byte_offset': byte_offset,
                'original': f"0x{original:04x}",
                'corrupted': f"0x{corrupted:04x}"
            }

        elif fault_type == FaultType.TOTLEN_INVALID:
            byte_offset = offset + 4
            original = struct.unpack_from('<I', self.image_data, byte_offset)[0]
            corrupted = 0xFFFFFFFF
            struct.pack_into('<I', self.image_data, byte_offset, corrupted)
            result = {
                'byte_offset': byte_offset,
                'original': f"0x{original:08x}",
                'corrupted': f"0x{corrupted:08x}"
            }

        elif fault_type == FaultType.VERSION_ZERO:
            # version at offset +16 for INODE, offset +20 for DIRENT
            if node.nodetype == JFFS2_NODETYPE_INODE:
                byte_offset = offset + 16
            elif node.nodetype == JFFS2_NODETYPE_DIRENT:
                byte_offset = offset + 20
            else:
                return None

            original = struct.unpack_from('<I', self.image_data, byte_offset)[0]
            corrupted = 0
            struct.pack_into('<I', self.image_data, byte_offset, corrupted)
            result = {
                'byte_offset': byte_offset,
                'original': f"{original}",
                'corrupted': f"{corrupted}"
            }

        return result

    def inject_multiple_faults(self, fault_types: List[FaultType],
                                target_node_type: str = None) -> List[Dict]:
        """Inject multiple faults into different nodes"""
        results = []
        used_offsets = set()

        for fault_type in fault_types:
            # Find unused node
            for node in self.nodes:
                if node.offset in used_offsets:
                    continue
                if target_node_type and node.type_name.lower() != target_node_type.lower():
                    continue

                # Check if fault type is compatible with node type
                if fault_type == FaultType.DATA_CRC_CORRUPT and node.nodetype != JFFS2_NODETYPE_INODE:
                    continue
                if fault_type == FaultType.NAME_CRC_CORRUPT and node.nodetype != JFFS2_NODETYPE_DIRENT:
                    continue

                result = self._apply_fault(fault_type, node.offset, node)
                if result:
                    fault_record = {
                        'fault_type': fault_type.value,
                        'description': FAULT_DESCRIPTIONS[fault_type],
                        'target_offset': node.offset,
                        'target_node_type': node.type_name,
                        'original_value': result['original'],
                        'corrupted_value': result['corrupted'],
                        'byte_offset': result['byte_offset'],
                    }
                    self.fault_log.append(fault_record)
                    results.append(fault_record)
                    used_offsets.add(node.offset)
                    print(f"Injected {fault_type.value} at 0x{node.offset:08x}")
                    break

        return results

    def save_corrupted_image(self, output_path: str) -> bool:
        """Save corrupted image to new file"""
        try:
            with open(output_path, 'wb') as f:
                f.write(self.image_data)
            print(f"Saved corrupted image: {output_path}")
            return True
        except Exception as e:
            print(f"Error saving image: {e}")
            return False

    def generate_fault_report(self, output_dir: str) -> str:
        """Generate JSON report of injected faults"""
        report = {
            'source_image': self.image_path,
            'image_size': len(self.image_data),
            'block_size': self.block_size,
            'total_nodes': len(self.nodes),
            'fault_count': len(self.fault_log),
            'faults': self.fault_log,
        }

        report_path = os.path.join(output_dir, 'faults.json')
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Generated fault report: {report_path}")
        return report_path

    def generate_summary(self) -> str:
        """Generate text summary of injected faults"""
        summary = f"""# JFFS2 Fault Injection Summary

## Source Image
- Path: {self.image_path}
- Size: {len(self.image_data)} bytes
- Nodes found: {len(self.nodes)}

## Injected Faults ({len(self.fault_log)})
"""
        for fault in self.fault_log:
            summary += f"""
### {fault['fault_type']}
- Node: {fault['target_node_type']} at 0x{fault['target_offset']:08x}
- Byte offset: 0x{fault['byte_offset']:08x}
- Original: {fault['original_value']}
- Corrupted: {fault['corrupted_value']}
"""
        return summary


def parse_fault_types(fault_str: str) -> List[FaultType]:
    """Parse comma-separated fault type string"""
    fault_map = {
        'hdr_crc': FaultType.HDR_CRC_CORRUPT,
        'hdr_crc_corrupt': FaultType.HDR_CRC_CORRUPT,
        'node_crc': FaultType.NODE_CRC_CORRUPT,
        'node_crc_corrupt': FaultType.NODE_CRC_CORRUPT,
        'data_crc': FaultType.DATA_CRC_CORRUPT,
        'data_crc_corrupt': FaultType.DATA_CRC_CORRUPT,
        'name_crc': FaultType.NAME_CRC_CORRUPT,
        'name_crc_corrupt': FaultType.NAME_CRC_CORRUPT,
        'magic': FaultType.MAGIC_INVALID,
        'magic_invalid': FaultType.MAGIC_INVALID,
        'nodetype': FaultType.NODETYPE_INVALID,
        'nodetype_invalid': FaultType.NODETYPE_INVALID,
        'totlen': FaultType.TOTLEN_INVALID,
        'totlen_invalid': FaultType.TOTLEN_INVALID,
        'version': FaultType.VERSION_ZERO,
        'version_zero': FaultType.VERSION_ZERO,
    }

    types = []
    for part in fault_str.split(','):
        part = part.strip().lower()
        if part in fault_map:
            types.append(fault_map[part])
        else:
            print(f"Warning: Unknown fault type '{part}'")

    return types


def main():
    parser = argparse.ArgumentParser(
        description='Inject faults into JFFS2 filesystem images',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Fault Types:
  hdr_crc_corrupt    - Corrupt header CRC
  node_crc_corrupt   - Corrupt node CRC
  data_crc_corrupt   - Corrupt data CRC (INODE only)
  name_crc_corrupt   - Corrupt name CRC (DIRENT only)
  magic_invalid      - Invalid magic number
  nodetype_invalid   - Invalid node type
  totlen_invalid     - Invalid total length
  version_zero       - Zero version number

Examples:
  # Single fault injection
  %(prog)s --image normal.jffs2 --fault hdr_crc_corrupt --output corrupted.jffs2

  # Multiple faults
  %(prog)s --image normal.jffs2 --fault hdr_crc,node_crc --output multi_corrupted.jffs2

  # Target specific node type
  %(prog)s --image normal.jffs2 --fault data_crc_corrupt --node-type inode --output corrupted.jffs2

  # List nodes only
  %(prog)s --image normal.jffs2 --list
"""
    )

    parser.add_argument('--image', '-i', required=True,
                        help='Path to JFFS2 image file')
    parser.add_argument('--fault', '-f',
                        help='Fault type(s) to inject (comma-separated)')
    parser.add_argument('--output', '-o',
                        help='Output path for corrupted image')
    parser.add_argument('--node-type', '-n',
                        help='Target node type (inode, dirent)')
    parser.add_argument('--offset',
                        help='Target node offset (hex, e.g. 0x100)')
    parser.add_argument('--list', '-l', action='store_true',
                        help='List nodes in image')
    parser.add_argument('--output-dir', '-d',
                        help='Output directory for reports')

    args = parser.parse_args()

    # Initialize injector
    injector = JFFS2FaultInjector(args.image)

    if not injector.load_image():
        sys.exit(1)

    # List mode
    if args.list:
        injector.list_nodes(args.node_type)
        sys.exit(0)

    # Fault injection mode
    if not args.fault:
        print("Error: No fault type specified (use --fault)")
        parser.print_help()
        sys.exit(1)

    if not args.output:
        # Auto-generate output name
        base = Path(args.image).stem
        args.output = f"{base}_corrupted.jffs2"
        print(f"Output will be: {args.output}")

    # Parse fault types
    fault_types = parse_fault_types(args.fault)
    if not fault_types:
        print("Error: No valid fault types")
        sys.exit(1)

    print(f"\nInjecting faults: {[f.value for f in fault_types]}")

    # Parse offset if provided
    target_offset = None
    if args.offset:
        try:
            target_offset = int(args.offset, 0)
        except ValueError:
            print(f"Error: Invalid offset format: {args.offset}")
            sys.exit(1)

    # Inject faults
    if len(fault_types) == 1:
        injector.inject_fault(fault_types[0], target_offset, args.node_type)
    else:
        injector.inject_multiple_faults(fault_types, args.node_type)

    # Save corrupted image
    injector.save_corrupted_image(args.output)

    # Generate report
    output_dir = args.output_dir or os.path.dirname(args.output) or '.'
    if output_dir == '.':
        output_dir = f"jffs2_fault_output_{os.path.basename(args.output).replace('.jffs2', '')}"
        os.makedirs(output_dir, exist_ok=True)

    injector.generate_fault_report(output_dir)

    # Print summary
    print("\n" + injector.generate_summary())

    print(f"\nOutput files:")
    print(f"  Corrupted image: {args.output}")
    print(f"  Fault report: {output_dir}/faults.json")


if __name__ == '__main__':
    main()