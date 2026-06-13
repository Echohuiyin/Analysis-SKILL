# Crash Utility Build Guide

## Prerequisites

### Ubuntu/Debian

```bash
sudo apt install -y \
    build-essential \
    gcc g++ \
    libncurses-dev \
    zlib1g-dev \
    liblzo2-dev \
    libsnappy-dev \
    libzstd-dev \
    bison \
    wget \
    patch \
    texinfo \
    libgmp-dev \
    libmpfr-dev
```

### Fedora/RHEL

```bash
sudo dnf install -y \
    gcc gcc-c++ \
    ncurses-devel \
    zlib-devel \
    lzo-devel \
    snappy-devel \
    libzstd-devel \
    bison \
    wget \
    patch \
    texinfo \
    gmp-devel \
    mpfr-devel
```

## Build Process

### Step 1: Clone Source

```bash
# Option A: HTTPS (may be slow)
git clone https://github.com/crash-utility/crash.git

# Option B: SSH (recommended, faster)
git clone git@github.com:crash-utility/crash.git
```

### Step 2: Compile

```bash
cd crash

# Clean previous build (if exists)
make clean

# Build (takes 3-5 minutes for initial GDB compilation)
make -j$(nproc)
```

### Step 3: Verify

```bash
./crash --version

# Expected output:
# crash 9.0.2++
# Copyright (C) 2002-2026  Red Hat, Inc.
# ...
# GNU gdb (GDB) 16.2
```

### Step 4: Install (Optional)

```bash
# System-wide installation
sudo cp crash /usr/local/bin/crash-9.0.2
sudo ln -sf /usr/local/bin/crash-9.0.2 /usr/local/bin/crash

# Or keep in project directory
mkdir -p /path/to/project/tools/crash-vmcore/bin
cp crash /path/to/project/tools/crash-vmcore/bin/
```

## Build Options

### Compression Support

```bash
# Build with LZO compression support
make lzo

# Build with Snappy compression support
make snappy

# Build with ZSTD compression support
make zstd

# Build with all compression libraries
make lzo snappy zstd
```

### Cross-Compilation

Build crash for different architectures:

```bash
# ARM64 crash (for analyzing ARM64 vmcores on x86_64 host)
make CROSS_COMPILE=aarch64-linux-gnu- -j$(nproc)

# Note: Cross-compilation requires cross-compiled GDB
# This is more complex and usually not needed
# Recommended: Use native crash on each architecture
```

## Build Troubleshooting

### Error: GMP/MPFR Missing

```
configure: error: Building GDB requires GMP 4.2+, and MPFR 3.1.0+.
```

**Solution**:
```bash
sudo apt install libgmp-dev libmpfr-dev
make clean && make
```

### Error: texinfo Missing

```
make: *** [doc/bfd.info] Error 127
```

**Solution**:
```bash
sudo apt install texinfo
make clean && make
```

### Error: Network Issues (GDB Download)

```
fatal: unable to access 'https://ftp.gnu.org/gnu/gdb/'
```

**Solution**: 
- Use `git clone git@github.com:crash-utility/crash.git` (SSH is faster)
- Or download GDB tarball manually and extract to `gdb-16.2/` directory

## Build Artifacts

```
crash/
├── crash                  # Main binary (176M with GDB 16.2)
├── crashlib.a             # Crash library
├── gdb-16.2/              # Embedded GDB source
│   └── gdb/               # GDB build directory
└── extensions/            # Extension modules source
```

## Version Comparison

| Version | Source | GDB Version | QEMU Vmcore Support |
|---------|--------|-------------|---------------------|
| 8.0.4 | apt package | 10.2 | ✗ Segfault |
| 9.0.2++ | git master | 16.2 | ✓ Full support |

## Key Features in 9.0.2+

- Fixed x86_64 bt command with QEMU ELF dumps
- Fixed panic task determination from QEMU dumps
- GDB 16.2 integration
- Better DWARF support
- Improved kernel 7.1+ support

## Build Time Estimates

| System | Jobs | Time |
|--------|------|------|
| 8-core CPU | -j8 | ~4 min |
| 16-core CPU | -j16 | ~3 min |
| 32-core CPU | -j32 | ~2.5 min |

Initial build includes GDB compilation. Subsequent rebuilds are faster (~30s).