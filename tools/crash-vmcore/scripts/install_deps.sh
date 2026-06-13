#!/bin/bash
# install_deps.sh - Install crash build dependencies
# Usage: ./install_deps.sh [--arch x86_64|arm64]

set -e

ARCH="${1:-x86_64}"

echo "=== Installing Crash Build Dependencies ==="
echo "Architecture: $ARCH"
echo

# Detect distribution
if command -v apt &> /dev/null; then
    DISTRO="ubuntu"
    PKG_MANAGER="apt"
elif command -v dnf &> /dev/null; then
    DISTRO="fedora"
    PKG_MANAGER="dnf"
elif command -v yum &> /dev/null; then
    DISTRO="rhel"
    PKG_MANAGER="yum"
else
    echo "ERROR: Unknown distribution"
    exit 1
fi

echo "Distribution: $DISTRO"
echo

# Ubuntu/Debian packages
UBUNTU_PKGS=(
    build-essential
    gcc
    g++
    libncurses-dev
    zlib1g-dev
    liblzo2-dev
    libsnappy-dev
    libzstd-dev
    bison
    wget
    patch
    texinfo
    libgmp-dev
    libmpfr-dev
)

# Fedora/RHEL packages
FEDORA_PKGS=(
    gcc
    gcc-c++
    ncurses-devel
    zlib-devel
    lzo-devel
    snappy-devel
    libzstd-devel
    bison
    wget
    patch
    texinfo
    gmp-devel
    mpfr-devel
)

# Install packages
case "$PKG_MANAGER" in
    apt)
        echo "Installing via apt..."
        sudo apt update
        sudo apt install -y "${UBUNTU_PKGS[@]}"
        ;;
    dnf)
        echo "Installing via dnf..."
        sudo dnf install -y "${FEDORA_PKGS[@]}"
        ;;
    yum)
        echo "Installing via yum..."
        sudo yum install -y "${FEDORA_PKGS[@]}"
        ;;
esac

# Cross-compilation toolchain (optional)
if [ "$ARCH" = "arm64" ] && [ "$(uname -m)" != "aarch64" ]; then
    echo
    echo "Installing ARM64 cross toolchain..."
    case "$PKG_MANAGER" in
        apt)
            sudo apt install -y gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu
            ;;
        dnf|yum)
            sudo $PKG_MANAGER install -y gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu
            ;;
    esac
fi

if [ "$ARCH" = "arm32" ] && [ "$(uname -m)" != "arm" ]; then
    echo
    echo "Installing ARM32 cross toolchain..."
    case "$PKG_MANAGER" in
        apt)
            sudo apt install -y gcc-arm-linux-gnueabi binutils-arm-linux-gnueabi
            ;;
        dnf|yum)
            sudo $PKG_MANAGER install -y gcc-arm-linux-gnu binutils-arm-linux-gnu
            ;;
    esac
fi

echo
echo "=== Verifying Installation ==="

# Check essential tools
for tool in gcc g++ make bison; do
    if command -v $tool &> /dev/null; then
        echo "✓ $tool: $(command -v $tool)"
    else
        echo "✗ $tool: NOT FOUND"
    fi
done

# Check libraries
echo
echo "Library check:"
case "$PKG_MANAGER" in
    apt)
        dpkg -l | grep -E "libgmp-dev|libmpfr-dev|libncurses-dev" | awk '{print "✓", $2}'
        ;;
    dnf|yum)
        rpm -qa | grep -E "gmp-devel|mpfr-devel|ncurses-devel" | sed 's/^/✓ /'
        ;;
esac

echo
echo "=== Dependencies Installed ==="
echo "Ready to build crash utility"
echo "Run: ./scripts/build_crash.sh"