# qemu-test Guide

Boot kernels in QEMU for testing and verification.

## Prerequisites

- QEMU: `qemu-system-aarch64`, `qemu-system-arm`, `qemu-system-x86_64`
- Busybox (static, architecture-matched)

```bash
sudo apt install qemu-system-arm qemu-system-x86
```

## Usage

```bash
/qemu-test --arch <arch> --kernel <path> [--modules <path>] [--script <path>]
```

## Examples

```bash
# Interactive boot
/qemu-test --arch arm64 --interactive

# With test script
/qemu-test --arch arm64 --script tests/jffs2_test.sh --timeout 60

# With modules
/qemu-test --arch arm64 --kernel Image --modules jffs2.ko
```

## Options

| Option | Description |
|--------|-------------|
| `--arch` | Architecture (arm64/arm32/x86_64) |
| `--kernel` | Kernel image path |
| `--modules` | Kernel modules path |
| `--script` | Test script to run |
| `--timeout` | Timeout in seconds |
| `--interactive` | Enter interactive shell |

## Busybox Requirements

Cross-architecture testing requires architecture-matched busybox:

| Host | QEMU | Busybox |
|------|------|---------|
| x86_64 | x86_64 | Native |
| x86_64 | ARM64 | ARM64 static |
| x86_64 | ARM32 | ARM32 static |

Build busybox:
```bash
./tools/build_busybox.sh --arch arm64
```

## Architecture Images

| Arch | Image Path |
|------|------------|
| ARM64 | `arch/arm64/boot/Image` |
| ARM32 | `arch/arm/boot/zImage` |
| x86_64 | `arch/x86/boot/bzImage` |

## Test Scripts

Place test scripts in kernel source `tests/` directory.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Exec format error | Use correct arch busybox |
| Module not loading | Kernel/module version mismatch |
| No shell | Check busybox is static |