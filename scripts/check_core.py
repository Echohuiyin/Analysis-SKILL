#!/usr/bin/env python3
"""
核心环境检查脚本 - 验证MCP Server、Skills安装、Python版本等
"""

import os
import sys
import subprocess
from pathlib import Path


def check_python_version():
    """检查Python版本（要求>=3.10）"""
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    if version.major >= 3 and version.minor >= 10:
        return True, f"Python {version_str} ✅"
    else:
        return False, f"Python {version_str} ❌ (需要>=3.10)"


def check_mcp_server():
    """检查MCP Server注册状态"""
    try:
        result = subprocess.run(
            ["claude", "mcp", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if "aicrasher" in result.stdout:
            # 检查是否连接成功
            if "✗ Failed to connect" in result.stdout:
                return False, "MCP Server已注册但连接失败"
            else:
                return True, "MCP Server 'aicrasher' 已注册 ✅"
        else:
            return False, "MCP Server未注册"
    except subprocess.TimeoutExpired:
        return False, "检查超时（Claude CLI可能未响应）"
    except FileNotFoundError:
        return False, "Claude CLI未安装"
    except Exception as e:
        return False, f"检查失败: {str(e)}"


def check_skills_installed():
    """检查Skills安装状态"""
    skills_dir = Path.home() / ".claude" / "skills"

    required_skills = [
        "vmcore-analyzer",
        "lock-analyzer",
        "kernel-build",
        "qemu-test",
        "jffs2-analyzer",
        "jffs2-mount",
        "jffs2-fault-inject",
        "rag-case-retrieval"
    ]

    if not skills_dir.exists():
        return False, f"Skills目录不存在: {skills_dir}"

    installed = []
    missing = []

    for skill in required_skills:
        skill_path = skills_dir / skill
        if skill_path.exists() and skill_path.is_dir():
            installed.append(skill)
        else:
            missing.append(skill)

    if missing:
        return False, f"缺少skills: {', '.join(missing)}"
    else:
        return True, f"已安装 {len(installed)} 个skills ✅"


def check_env_file():
    """检查.env配置文件"""
    # 从当前工作目录查找.env文件
    cwd = Path.cwd()
    env_file = cwd / ".env"

    if not env_file.exists():
        return False, ".env文件不存在（请从.env.example复制）"

    # 检查关键配置项
    required_keys = ["CRASH_BINARY"]
    missing_keys = []

    with open(env_file) as f:
        content = f.read()
        for key in required_keys:
            if key not in content or f"{key}=" not in content:
                missing_keys.append(key)

    if missing_keys:
        return False, f".env缺少配置: {', '.join(missing_keys)}"
    else:
        return True, ".env配置文件存在 ✅"


def check_venv():
    """检查虚拟环境"""
    # 从当前工作目录查找venv
    cwd = Path.cwd()
    venv_dir = cwd / ".venv"

    if not venv_dir.exists():
        return False, "虚拟环境不存在"

    # 检查关键文件
    python_bin = venv_dir / "bin" / "python"
    if not python_bin.exists():
        return False, "虚拟环境Python不存在"

    # 检查MCP包是否安装
    try:
        result = subprocess.run(
            [str(python_bin), "-c", "import aicrasher; print('ok')"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if "ok" in result.stdout:
            return True, "虚拟环境已创建，MCP包已安装 ✅"
        else:
            return False, "虚拟环境存在但MCP包未安装"
    except Exception as e:
        return False, f"检查失败: {str(e)}"


def main():
    print("=" * 60)
    print("Kernel Analysis Skills - 核心环境检查")
    print("=" * 60)

    checks = [
        ("Python版本", check_python_version),
        ("虚拟环境", check_venv),
        ("MCP Server", check_mcp_server),
        ("Skills安装", check_skills_installed),
        (".env配置", check_env_file),
    ]

    all_passed = True

    for i, (name, check_func) in enumerate(checks, 1):
        print(f"\n[{i}/{len(checks)}] 检查{name}...")
        success, msg = check_func()
        if success:
            print(f"  ✅ {msg}")
        else:
            print(f"  ❌ {msg}")
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 核心环境检查通过")
        print("\n可选检查:")
        print("  - RAG环境: python skills/rag-case-retrieval/scripts/check_environment.py")
    else:
        print("❌ 核心环境检查发现问题（请见上方详情）")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())