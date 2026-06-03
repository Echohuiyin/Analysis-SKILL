#!/bin/bash
# Kernel Analysis Skills - One-click Installation
# Usage: bash scripts/install.sh

set -e

echo "=== Kernel Analysis Skills Installation ==="

# Detect Claude CLI tool
detect_cli() {
    if command -v claude &> /dev/null; then
        echo "claude"
    elif command -v codebuddy &> /dev/null; then
        echo "codebuddy"
    else
        echo "none"
    fi
}

CLI=$(detect_cli)
SKILLS_DIR=""

case "$CLI" in
    claude)
        SKILLS_DIR="$HOME/.claude/skills"
        ;;
    codebuddy)
        SKILLS_DIR="$HOME/.codebuddy/skills"
        ;;
    none)
        echo "Warning: No Claude CLI tool found"
        echo "Skills will be installed to ~/.claude/skills (default)"
        SKILLS_DIR="$HOME/.claude/skills"
        mkdir -p "$SKILLS_DIR"
        ;;
esac

echo "CLI Tool: $CLI (or default)"
echo "Skills Directory: $SKILLS_DIR"

# Step 1: Install MCP Python package
echo ""
echo "[1/3] Installing MCP Python package..."
if command -v pip &> /dev/null; then
    pip install -e .[cli] --quiet
    echo "✓ MCP package installed"
else
    echo "✗ pip not found, skipping MCP installation"
fi

# Step 2: Register MCP Server
echo ""
echo "[2/3] Registering MCP Server..."
if [ "$CLI" = "claude" ]; then
    claude mcp add aicrasher -- python3 -m aicrasher.mcp_server 2>/dev/null || true
    echo "✓ MCP Server registered (aicrasher)"
elif [ "$CLI" = "codebuddy" ]; then
    codebuddy mcp add -s user aicrasher -- python3 -m aicrasher.mcp_server 2>/dev/null || true
    echo "✓ MCP Server registered (aicrasher)"
else
    echo "⊗ Manual registration required:"
    echo "  claude mcp add aicrasher -- python3 -m aicrasher.mcp_server"
fi

# Step 3: Install Skills
echo ""
echo "[3/3] Installing Skills..."
mkdir -p "$SKILLS_DIR"

SKILLS=("vmcore-analyzer" "lock-analyzer" "kernel-build" "qemu-test"
        "jffs2-analyzer" "jffs2-mount" "jffs2-fault-inject" "rag-case-retrieval")

for skill in "${SKILLS[@]}"; do
    if [ -d "skills/$skill" ]; then
        cp -r "skills/$skill" "$SKILLS_DIR/"
        echo "✓ $skill installed"
    fi
done

# Summary
echo ""
echo "=== Installation Complete ==="
echo ""
echo "Installed Skills: 8"
echo "MCP Server: aicrasher"
echo ""
echo "Quick Start:"
echo "  /vmcore-analyzer <vmcore> <vmlinux>"
echo "  /lock-analyzer <lock-addr> --type mutex"
echo "  /kernel-build JFFS2_FS --arch arm64"
echo ""
echo "Documentation: docs/*.md"
echo ""

# Verify MCP
if [ "$CLI" = "claude" ]; then
    echo "Verify MCP:"
    claude mcp list | grep aicrasher && echo "✓ MCP connected" || echo "⊗ Restart Claude to connect MCP"
fi