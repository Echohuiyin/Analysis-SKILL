#!/usr/bin/env python3
"""
环境检查脚本 - 验证Chroma连接和依赖
"""

import os
import sys
import json
from pathlib import Path

def check_dependencies():
    """检查Python依赖"""
    missing = []
    try:
        import chromadb
    except ImportError:
        missing.append("chromadb")

    try:
        import openai
    except ImportError:
        missing.append("openai")

    return missing

def check_chroma_connection(host="http://localhost:8000", timeout=5):
    """检查Chroma服务连接"""
    try:
        import chromadb
        client = chromadb.HttpClient(host=host.split("://")[1].split(":")[0],
                                     port=int(host.split(":")[-1]))
        client.heartbeat()
        return True, "Chroma服务连接正常"
    except Exception as e:
        return False, f"无法连接Chroma: {str(e)}"

def check_openai_key():
    """检查OpenAI API Key"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return False, "未设置OPENAI_API_KEY环境变量"
    if not api_key.startswith("sk-"):
        return False, "OPENAI_API_KEY格式可能不正确"
    return True, "OpenAI API Key已配置"

def check_collection(collection_name="cases", host="http://localhost:8000"):
    """检查Collection状态"""
    try:
        import chromadb
        client = chromadb.HttpClient(host=host.split("://://")[1].split(":")[0],
                                     port=int(host.split(":")[-1]))
        collection = client.get_collection(name=collection_name)
        count = collection.count()
        return True, {
            "name": collection_name,
            "count": count,
            "metadata": collection.metadata
        }
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 60)
    print("RAG案例检索 - 环境检查")
    print("=" * 60)

    # 1. 检查依赖
    print("\n[1/4] 检查Python依赖...")
    missing = check_dependencies()
    if missing:
        print(f"  ❌ 缺少依赖: {', '.join(missing)}")
        print(f"  安装命令: pip install {' '.join(missing)}")
        return 1
    print("  ✅ 所有依赖已安装")

    # 2. 检查OpenAI API Key
    print("\n[2/4] 检查OpenAI配置...")
    success, msg = check_openai_key()
    if success:
        print(f"  ✅ {msg}")
    else:
        print(f"  ❌ {msg}")
        print("  设置命令: export OPENAI_API_KEY='your-api-key'")
        return 1

    # 3. 检查Chroma连接
    print("\n[3/4] 检查Chroma服务...")
    config_path = Path.home() / ".claude" / "skills" / "rag-case-retrieval" / "config.json"
    host = "http://localhost:8000"
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
            host = config.get("chroma", {}).get("host", host)

    success, msg = check_chroma_connection(host)
    if success:
        print(f"  ✅ {msg}")
    else:
        print(f"  ❌ {msg}")
        print("  启动命令: docker run -d -p 8000:8000 chromadb/chroma")
        return 1

    # 4. 检查Collection
    print("\n[4/4] 检查Collection状态...")
    collection_name = "cases"
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
            collection_name = config.get("chroma", {}).get("collection_name", collection_name)

    success, result = check_collection(collection_name, host)
    if success:
        print(f"  ✅ Collection '{result['name']}' 存在")
        print(f"     - 文档数量: {result['count']}")
        if result.get('metadata'):
            print(f"     - 元数据: {result['metadata']}")
    else:
        print(f"  ⚠️  Collection '{collection_name}' 不存在或为空")
        print("     需要先导入案例数据")

    print("\n" + "=" * 60)
    print("环境检查完成")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())