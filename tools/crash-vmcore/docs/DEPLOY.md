# Crash Deployment Guide

## Installation Options

### Option 1: System-wide Installation

```bash
# Copy to system bin directory
sudo cp crash /usr/local/bin/crash-9.0.2

# Create symlink
sudo ln -sf /usr/local/bin/crash-9.0.2 /usr/local/bin/crash

# Verify
/usr/local/bin/crash --version
```

**Pros**: Available for all users, easy to use
**Cons**: Requires sudo, affects system-wide

### Option 2: Project-local Installation

```bash
# Copy to project tools directory
mkdir -p /path/to/Analysis-SKILL/tools/crash-vmcore/bin
cp crash /path/to/Analysis-SKILL/tools/crash-vmcore/bin/

# Update .env
echo "CRASH_BINARY=/path/to/Analysis-SKILL/tools/crash-vmcore/bin/crash" >> .env
```

**Pros**: No sudo required, version controlled
**Cons**: Need to configure path

### Option 3: User Directory Installation

```bash
# Copy to user bin
mkdir -p ~/bin
cp crash ~/bin/

# Add to PATH (in ~/.bashrc)
export PATH=$HOME/bin:$PATH
```

**Pros**: User-level control
**Cons**: Per-user setup

## Configuration

### Analysis-SKILL .env

```bash
# .env file configuration
CRASH_BINARY=/home/liumingrui/crash/crash

# Timeout settings
CRASH_TIMEOUT_SECONDS=300
CRASH_OUTPUT_MAX_CHARS=16384
CRASH_BATCH_OUTPUT_MAX_CHARS=32768
```

### vmcore-analyzer Skill

The skill reads CRASH_BINARY from .env:
```bash
# In skill execution
crash_binary = os.getenv('CRASH_BINARY', '/usr/bin/crash')
```

## Verification

### Test Crash Binary

```bash
# Basic test
$CRASH_BINARY --version

# Live system test (requires root)
sudo $CRASH_BINARY

# Vmcore test
$CRASH_BINARY vmlinux vmcore.elf
```

### Test with vmcore-analyzer

```bash
/vmcore-analyzer vmlinux vmcore.elf
```

## Dependencies

### Runtime Dependencies

Crash binary requires these runtime libraries:

```
libncurses.so.6
libz.so.1
libreadline.so.8
libtinfo.so.6
liblzo2.so.2     # Optional (if built with lzo)
libsnappy.so.1   # Optional (if built with snappy)
libzstd.so.1     # Optional (if built with zstd)
```

### Check Dependencies

```bash
ldd crash

# Or for static binary
file crash
# Should show: statically linked (ideal for portability)
```

## Portability

### Static Binary (Recommended)

If crash is compiled with static linking, it's portable across systems:

```bash
# Check if static
file crash | grep "statically linked"

# Static binary has no external dependencies
```

### Dynamic Binary

If crash has dynamic dependencies:

```bash
# List required libraries
ldd crash

# Package dependencies with crash
tar -czf crash-bundle.tar.gz crash $(ldd crash | grep -o '/lib[^ ]*' | head -10)
```

## Multi-Architecture Setup

For analyzing vmcores from different architectures:

```
/usr/local/bin/
├── crash               # Symlink to default (x86_64)
├── crash-x86_64        # x86_64 version
├── crash-arm64         # ARM64 version (cross-compiled)
└── crash-arm32         # ARM32 version
```

```bash
# Select specific version
export CRASH_BINARY=/usr/local/bin/crash-arm64
/vmcore-analyzer arm64_vmlinux arm64_vmcore.elf
```

## Update Process

### Check for Updates

```bash
cd ~/crash
git fetch
git log HEAD..origin/master --oneline
```

### Rebuild Latest

```bash
cd ~/crash
git pull
make clean
make -j$(nproc)

# Re-install
sudo cp crash /usr/local/bin/crash-9.0.2
```

## Cleanup

### Remove Old Version

```bash
# Remove apt-installed version (optional)
sudo apt remove crash

# Or keep both and use new one via .env
```

### Build Artifacts Cleanup

```bash
cd ~/crash
make clean
rm -rf gdb-16.2/  # Removes downloaded GDB source (save space)
```

## Integration Checklist

- [ ] Crash compiled successfully
- [ ] Version verified (9.0.2+)
- [ ] Binary copied to target location
- [ ] .env CRASH_BINARY configured
- [ ] vmcore-analyzer skill tested
- [ ] QEMU vmcore analysis verified