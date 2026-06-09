#!/usr/bin/env python3
"""
环境检查脚本 - 验证Chroma连接和依赖
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict

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

def check_embedding_service(config: Dict):
    """检查嵌入服务连接"""
    from openai import OpenAI

    embedding_config = config.get("embedding", {})
    base_url = embedding_config.get("base_url", "http://localhost:11434/v1")
    model = embedding_config.get("model", "bge-large-zh")
    api_key = embedding_config.get("api_key", "not-required")
    timeout = embedding_config.get("timeout", 30)

    # 测试连接通过生成一个测试嵌入
    try:
        client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout
        )

        response = client.embeddings.create(
            model=model,
            input="test"
        )

        if response.data and len(response.data) > 0:
            embedding_dim = len(response.data[0].embedding)
            return True, f"嵌入服务连接正常 (模型: {model}, 维度: {embedding_dim}, 端点: {base_url})"
        else:
            return False, f"嵌入服务响应异常: 未返回向量数据"

    except Exception as e:
        error_msg = str(e)
        suggestions = []

        if "Connection refused" in error_msg or "connect" in error_msg.lower():
            suggestions = [
                "请确保嵌入服务正在运行",
                f"检查 {base_url} 是否可访问",
                "如果是Ollama: ollama serve",
                "如果是text-embeddings-inference: 检查Docker容器状态"
            ]
        elif "model" in error_msg.lower() and "not found" in error_msg.lower():
            suggestions = [
                f"请拉取模型: ollama pull {model}",
                f"或修改config.json中的embedding.model为可用模型"
            ]
        else:
            suggestions = [
                f"检查服务配置: {base_url}",
                "验证模型名称是否正确",
                "检查服务日志"
            ]

        return False, f"无法连接嵌入服务: {error_msg}\n建议:\n" + "\n".join(f"  - {s}" for s in suggestions)

def check_collection(collection_name="cases", host="http://localhost:8000"):
    """检查Collection状态"""
    try:
        import chromadb
        client = chromadb.HttpClient(host=host.split("://")[1].split(":")[0],
                                     port=int(host.split(":")[-1]))
        collection = client.get_collection(name=collection_name)
        count = collection.count()
        metadata = collection.metadata or {}
        return True, {
            "name": collection_name,
            "count": count,
            "metadata": metadata,
            "distance_metric": metadata.get("hnsw:space", "unknown"),
            "embedding_model": metadata.get("embedding_model", "unknown"),
            "embedding_dimension": metadata.get("embedding_dimension", "unknown"),
            "vectorization_strategy": metadata.get("vectorization_strategy", "unknown")
        }
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 60)
    print("RAG案例检索 - 环境检查")
    print("=" * 60)

    # 先读取配置
    config_path = Path.home() / ".claude" / "skills" / "rag-case-retrieval" / "config.json"
    config = {}
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
        print(f"配置文件: {config_path}")
    else:
        config = {
            "embedding": {
                "base_url": "http://localhost:11434/v1",
                "model": "bge-large-zh",
                "api_key": "not-required",
                "timeout": 30,
                "dimension": 1024
            },
            "vectorization": {
                "head_chars": 400,
                "title_injection": True
            }
        }
        print("配置文件: 未找到，使用默认配置")

    # 显示配置信息
    embedding_config = config.get("embedding", {})
    vec_config = config.get("vectorization", {})
    print(f"\n当前配置:")
    print(f"  嵌入模型: {embedding_config.get('model', 'bge-large-zh')}")
    print(f"  向量维度: {embedding_config.get('dimension', 1024)}")
    print(f"  向量化策略: 定长 (头{vec_config.get('head_chars', 400)}字符 + 标题注入)")

    # 1. 检查依赖
    print("\n[1/4] 检查Python依赖...")
    missing = check_dependencies()
    if missing:
        print(f"  ❌ 缺少依赖: {', '.join(missing)}")
        print(f"  安装命令: pip install {' '.join(missing)}")
        return 1
    print("  ✅ 所有依赖已安装")

    # 2. 检查嵌入服务
    print("\n[2/4] 检查嵌入服务...")
    success, msg = check_embedding_service(config)
    if success:
        print(f"  ✅ {msg}")
    else:
        print(f"  ❌ {msg}")
        return 1

    # 3. 检查Chroma连接
    print("\n[3/4] 检查Chroma服务...")
    host = config.get("chroma", {}).get("host", "http://localhost:8000")

    success, msg = check_chroma_connection(host)
    if success:
        print(f"  ✅ {msg}")
    else:
        print(f"  ❌ {msg}")
        print("  启动命令: docker run -d -p 8000:8000 chromadb/chroma")
        return 1

    # 4. 检查Collection
    print("\n[4/4] 检查Collection状态...")
    collection_name = config.get("chroma", {}).get("collection_name", "cases")

    success, result = check_collection(collection_name, host)
    if success:
        print(f"  ✅ Collection '{result['name']}' 存在")
        print(f"     - 文档数量: {result['count']}")
        print(f"     - 距离度量: {result.get('distance_metric', 'cosine')}")
        print(f"     - 嵌入模型: {result.get('embedding_model', 'unknown')}")
        print(f"     - 向量维度: {result.get('embedding_dimension', 'unknown')}")
        print(f"     - 向量化策略: {result.get('vectorization_strategy', 'unknown')}")
    else:
        print(f"  ⚠️  Collection '{collection_name}' 不存在或为空")
        print("     需要先导入案例数据")

    print("\n" + "=" * 60)
    print("环境检查完成")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())