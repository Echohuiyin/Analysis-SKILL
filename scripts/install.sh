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
echo "[1/5] Creating virtual environment and installing MCP Python package..."

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "✓ Virtual environment created at $VENV_DIR"
fi

# Activate venv
source "$VENV_DIR/bin/activate"

# Install package (use python -m pip to avoid shebang path issues)
"$VENV_DIR/bin/python" -m pip install -e "$PROJECT_DIR[cli]" --quiet
echo "✓ MCP package installed in virtual environment"

# Deactivate venv
deactivate

# Step 2: Register MCP Server
echo ""
echo "[2/5] Registering MCP Server..."

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
echo "[3/5] Installing Skills..."
mkdir -p "$SKILLS_DIR"

SKILLS=("vmcore-analyzer" "lock-analyzer" "kernel-build" "kernel-fault-injection" "qemu-test"
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

# Step 4: RAG Infrastructure Setup
echo ""
echo "[4/5] RAG Infrastructure Setup..."

RAG_SCRIPTS="$PROJECT_DIR/skills/rag-case-retrieval/scripts"

# 4a. sqlite3 version check (Chroma requires >= 3.35.0)
echo ""
echo "  [4a] Checking sqlite3 version..."
SQLITE_VER=$("$VENV_DIR/bin/python" -c "import sqlite3; print(sqlite3.sqlite_version)" 2>/dev/null)
REQUIRED_SQLITE="3.35.0"

version_ge() {
    echo "$1" | awk -v req="$2" 'BEGIN {FS="."} {
        split(req, r, ".");
        if ($1 > r[1]) exit 0;
        if ($1 < r[1]) exit 1;
        if ($2 > r[2]) exit 0;
        if ($2 < r[2]) exit 1;
        if ($3 >= r[3]) exit 0;
        exit 1;
    }'
}

if [ -n "$SQLITE_VER" ] && version_ge "$SQLITE_VER" "$REQUIRED_SQLITE"; then
    echo "  ✓ sqlite3 $SQLITE_VER (meets Chroma >= $REQUIRED_SQLITE requirement)"
else
    echo "  ⚠ sqlite3 $SQLITE_VER is below Chroma requirement ($REQUIRED_SQLITE)"
    echo "  → Installing pysqlite3-binary as replacement..."
    "$VENV_DIR/bin/python" -m pip install pysqlite3-binary --quiet || echo "  ⚠ pysqlite3-binary install failed"
fi

# 4b. Install chromadb
echo ""
echo "  [4b] Installing chromadb..."
if "$VENV_DIR/bin/python" -m pip install chromadb --quiet 2>/dev/null; then
    echo "  ✓ chromadb installed"
else
    echo "  ⚠ chromadb installation failed — RAG retrieval will not work"
    echo "  → Install manually: $VENV_DIR/bin/python -m pip install chromadb"
fi

# 4c. Chroma local storage (PersistentClient mode, no Docker required)
echo ""
echo "  [4c] Chroma local storage setup..."
echo "  ℹ️  Using PersistentClient mode (local storage, no Docker required)"
echo "  → Default path: ~/.local/share/chroma_rag"
echo "  ✓ Chroma will use local persistent storage"

# 4d. Ollama + embedding model check
echo ""
echo "  [4d] Checking embedding service..."

OLLAMA_RUNNING=false
EMBEDDING_READY=false

if command -v ollama &> /dev/null; then
    # Check if ollama serve is running
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "  ✓ Ollama is running"
        OLLAMA_RUNNING=true
    else
        echo "  → Starting ollama serve in background..."
        ollama serve > /dev/null 2>&1 &
        sleep 2
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo "  ✓ Ollama started"
            OLLAMA_RUNNING=true
        else
            echo "  ⚠ Please start ollama manually: ollama serve"
        fi
    fi

    # Check/pull embedding model
    if [ "$OLLAMA_RUNNING" = true ]; then
        EMBED_MODEL="${EMBEDDING_MODEL:-nomic-embed-text}"
        if ollama list 2>/dev/null | grep -q "$EMBED_MODEL"; then
            echo "  ✓ Embedding model '$EMBED_MODEL' already pulled"
            EMBEDDING_READY=true
        else
            echo "  → Pulling embedding model '$EMBED_MODEL' (may take a few minutes)..."
            ollama pull "$EMBED_MODEL" && {
                echo "  ✓ Model '$EMBED_MODEL' pulled"
                EMBEDDING_READY=true
            } || {
                echo "  ⚠ Failed to pull '$EMBED_MODEL'. Try: ollama pull $EMBED_MODEL"
                echo "  → Alternative: set EMBEDDING_BASE_URL + EMBEDDING_API_KEY in .env for cloud API"
            }
        fi
    fi
else
    echo "  ⚠ Ollama not installed (recommended for local embedding)"
    echo "  → Install: curl -fsSL https://ollama.com/install.sh | sh"
    echo "  → Then: ollama pull nomic-embed-text"
    echo "  → Alternative: set EMBEDDING_BASE_URL + EMBEDDING_API_KEY in .env for cloud API"
fi

# 4e. Embedding config validation
echo ""
echo "  [4e] Validating embedding configuration..."

if [ -f "$PROJECT_DIR/.env" ]; then
    EMBED_URL=$(grep -E '^EMBEDDING_BASE_URL=' "$PROJECT_DIR/.env" 2>/dev/null | cut -d= -f2-)
    EMBED_KEY=$(grep -E '^EMBEDDING_API_KEY=' "$PROJECT_DIR/.env" 2>/dev/null | cut -d= -f2-)

    if [ -n "$EMBED_URL" ] && [ "$EMBED_URL" != "http://localhost:11434/v1" ]; then
        if [ -z "$EMBED_KEY" ] || [ "$EMBED_KEY" = "not-required" ]; then
            echo "  ⚠ EMBEDDING_BASE_URL set to '$EMBED_URL' but EMBEDDING_API_KEY is not configured"
            echo "  → Set EMBEDDING_API_KEY in .env for cloud embedding services"
        else
            echo "  ✓ Cloud embedding API configured"
        fi
    elif [ "$EMBEDDING_READY" = true ]; then
        echo "  ✓ Using local Ollama embedding ($EMBED_MODEL)"
    else
        echo "  ⚠ Using default localhost URL but Ollama is not ready"
        echo "  → Either install Ollama or configure cloud API in .env"
    fi
else
    echo "  ⚠ .env file not found, skipping embedding config validation"
fi

# Step 5: Environment Validation
echo ""
echo "[5/5] Running environment check..."

if [ -f "$PROJECT_DIR/scripts/check_core.py" ]; then
    "$VENV_DIR/bin/python" "$PROJECT_DIR/scripts/check_core.py" 2>&1 || {
        echo ""
        echo "  ⚠ Core environment check found issues (see above)"
        echo "  → Run manually: $VENV_DIR/bin/python $PROJECT_DIR/scripts/check_core.py"
    }

    # Optional: RAG-specific check
    if [ -f "$RAG_SCRIPTS/check_environment.py" ]; then
        echo ""
        echo "Optional: Check RAG environment..."
        "$VENV_DIR/bin/python" "$RAG_SCRIPTS/check_environment.py" 2>&1 || {
            echo ""
            echo "  ⚠ RAG environment check found issues (see above)"
            echo "  → Run manually: $VENV_DIR/bin/python $RAG_SCRIPTS/check_environment.py"
        }
    fi
else
    echo "  ⊗ check_core.py not found at $PROJECT_DIR/scripts"
fi

# Summary
echo ""
echo "=== Installation Complete ==="
echo ""
echo "Installed Skills: 9"
echo "MCP Server: aicrasher"
echo "Virtual Environment: $VENV_DIR"
echo ""
echo "Quick Start:"
echo "  /vmcore-analyzer <vmcore> <vmlinux>"
echo "  /lock-analyzer <lock-addr> --type mutex"
echo "  /kernel-build JFFS2_FS --arch arm64"
echo "  /kernel-fault-injection nullptr --arch x86_64"
echo ""
echo "Documentation: docs/*.md"
echo ""

# Optional: crash-vmcore toolkit info
CRASH_TOOLKIT="$PROJECT_DIR/tools/crash-vmcore"
if [ -d "$CRASH_TOOLKIT" ]; then
    echo "Crash-vmcore Toolkit:"
    echo "  Build crash 9.0.2+: bash $CRASH_TOOLKIT/scripts/build_crash.sh"
    echo "  See: $CRASH_TOOLKIT/README.md"
    echo ""
fi

# Verify MCP
if [ "$CLI" = "claude" ]; then
    echo "Verify MCP:"
    if claude mcp list | grep -q aicrasher; then
        echo "✓ MCP registered"
    else
        echo "⊗ MCP registration check failed"
        echo ""
        echo "Troubleshooting: If MCP fails to connect, try:"
        echo "  claude mcp remove aicrasher"
        echo "  claude mcp add aicrasher -- $MCP_CMD"
    fi
fi
