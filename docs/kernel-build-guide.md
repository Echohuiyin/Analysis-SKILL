# kernel-build Guide

Compile Linux kernels with custom CONFIG options.

## Prerequisites

- GCC toolchain (native or cross)
- Kernel source code
- Build dependencies: `bc bison flex libssl-dev`

```bash
# Cross-compilation toolchain
sudo apt install gcc-aarch64-linux-gnu  # ARM64
sudo apt install gcc-arm-linux-gnueabi  # ARM32
```

## Usage

```bash
/kernel-build <config-options> [--arch <arch>] [--cross] [--jobs <N>]
```

## Examples

```bash
# Enable JFFS2 as module
/kernel-build JFFS2_FS --arch arm64 --cross

# Multiple configs
/kernel-build UB XCU_SCHEDULER --arch x86_64 --jobs 32

# ARM64 MPAM
/kernel-build ARM64_MPAM --arch arm64 --cross --jobs 64
```

## Options

| Option | Description |
|--------|-------------|
| `--arch` | Target architecture (arm64/arm32/x86_64) |
| `--cross` | Use cross-compilation |
| `--jobs` | Parallel jobs (default: nproc) |

## Config Format

- `CONFIG_NAME` - Enable as built-in
- `CONFIG_NAME=m` - Enable as module
- `CONFIG_NAME=n` - Disable

## Output

- Kernel Image: `arch/arm64/boot/Image`, `arch/x86/boot/bzImage`
- Modules: `*.ko` files

## Important

- Compile kernel and modules in **same session** for version matching
- Uses `openeuler_defconfig` as base

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Missing toolchain | Install cross-compiler |
| Version mismatch | Rebuild kernel+modules together |
| Config not applied | Check spelling, use `make menuconfig` |