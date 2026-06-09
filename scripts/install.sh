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

# Get project directory (where this script is located)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

# Step 1: Create and activate virtual environment
echo ""
echo "[1/3] Creating virtual environment and installing MCP Python package..."

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "✓ Virtual environment created at $VENV_DIR"
fi

# Activate venv
source "$VENV_DIR/bin/activate"

# Install package
pip install -e "$PROJECT_DIR[cli]" --quiet
echo "✓ MCP package installed in virtual environment"

# Deactivate venv
deactivate

# Step 2: Register MCP Server
echo ""
echo "[2/3] Registering MCP Server..."

MCP_CMD="$VENV_DIR/bin/python -m aicrasher.mcp_server"

if [ "$CLI" = "claude" ]; then
    # Remove existing registration if present, then add new one
    claude mcp remove aicrasher 2>/dev/null || true
    claude mcp add aicrasher -- "$MCP_CMD"
    echo "✓ MCP Server registered (aicrasher)"
elif [ "$CLI" = "codebuddy" ]; then
    codebuddy mcp remove -s user aicrasher 2>/dev/null || true
    codebuddy mcp add -s user aicrasher -- "$MCP_CMD"
    echo "✓ MCP Server registered (aicrasher)"
else
    echo "⊗ Manual registration required:"
    echo "  claude mcp add aicrasher -- $MCP_CMD"
fi

# Step 3: Install Skills
echo ""
echo "[3/3] Installing Skills..."
mkdir -p "$SKILLS_DIR"

SKILLS=("vmcore-analyzer" "lock-analyzer" "kernel-build" "qemu-test"
        "jffs2-analyzer" "jffs2-mount" "jffs2-fault-inject" "rag-case-retrieval")

for skill in "${SKILLS[@]}"; do
    if [ -d "$PROJECT_DIR/skills/$skill" ]; then
        # Remove old version if exists
        rm -rf "$SKILLS_DIR/$skill" 2>/dev/null || true
        cp -r "$PROJECT_DIR/skills/$skill" "$SKILLS_DIR/"
        echo "✓ $skill installed"
    fi
done

# Create .env if not exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "✓ .env created from .env.example"
fi

# Summary
echo ""
echo "=== Installation Complete ==="
echo ""
echo "Installed Skills: 8"
echo "MCP Server: aicrasher"
echo "Virtual Environment: $VENV_DIR"
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
    claude mcp list | grep aicrasher && echo "✓ MCP registered" || echo "⊗ Check MCP registration"
fi