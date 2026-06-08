#!/usr/bin/env python3
"""
案例检索脚本 - 从Chroma向量库检索最相关的案例
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

def get_query_embedding(query: str, config: Dict) -> List[float]:
    """将查询文本转为向量 (使用本地OpenAI兼容服务)"""
    from openai import OpenAI

    embedding_config = config.get("embedding", {})
    base_url = embedding_config.get("base_url", "http://localhost:11434/v1")
    model = embedding_config.get("model", "bge-small-zh-v1.5")
    api_key = embedding_config.get("api_key", "not-required")
    timeout = embedding_config.get("timeout", 30)

    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout
    )

    try:
        response = client.embeddings.create(
            model=model,
            input=query
        )
        return response.data[0].embedding
    except Exception as e:
        raise Exception(f"Failed to generate embedding from {base_url}: {str(e)}")

def retrieve_cases(query_embedding: List[float],
                  collection_name: str = "cases",
                  host: str = "http://localhost:8000",
                  top_k: int = 3,
                  min_similarity: float = 0.7,
                  filters: Optional[Dict] = None) -> List[Dict]:
    """从Chroma检索最相关的案例"""
    import chromadb

    client = chromadb.HttpClient(host=host.split("://")[1].split(":")[0],
                                  port=int(host.split(":")[-1]))

    try:
        collection = client.get_collection(name=collection_name)
    except Exception as e:
        raise Exception(f"Collection '{collection_name}' 不存在: {str(e)}")

    # Chroma查询
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k * 3,  # 获取更多结果用于过滤
        where=filters if filters else None,
        include=["documents", "metadatas", "distances"]
    )

    # 处理结果
    cases = []
    seen_doc_ids = set()

    for i in range(len(results['ids'][0])):
        doc_id = results['metadatas'][0][i].get('doc_id')
        distance = results['distances'][0][i]

        # Chroma使用距离，转换为相似度 (1 - distance for cosine)
        similarity = 1 - distance

        # 过滤低相似度
        if similarity < min_similarity:
            continue

        # 合并同一文档的不同块
        if doc_id in seen_doc_ids:
            continue

        seen_doc_ids.add(doc_id)

        case = {
            "id": doc_id,
            "title": results['metadatas'][0][i].get('title', ''),
            "content": results['documents'][0][i],
            "similarity_score": round(similarity, 4),
            "metadata": {},
            "chunk_index": results['metadatas'][0][i].get('chunk_index', 0),
            "chunk_total": results['metadatas'][0][i].get('chunk_total', 1)
        }

        # 提取其他元数据
        for key, value in results['metadatas'][0][i].items():
            if key not in ['doc_id', 'title', 'chunk_index', 'chunk_total']:
                case['metadata'][key] = value

        cases.append(case)

        # 达到top_k数量就停止
        if len(cases) >= top_k:
            break

    return cases

def format_output(query: str, cases: List[Dict], config: Dict,
                  retrieval_time: float, embedding_time: float) -> Dict:
    """格式化输出结果"""
    output = {
        "status": "success" if cases else "no_results",
        "query": query,
        "retrieval_config": {
            "top_k": config.get("retrieval", {}).get("default_top_k", 3),
            "min_similarity": config.get("retrieval", {}).get("min_similarity", 0.7),
            "filters": config.get("filters", {}),
            "embedding_model": config.get("embedding", {}).get("model", "text-embedding-3-small")
        },
        "results": cases,
        "summary": {
            "total_found": len(cases),
            "above_threshold": len([c for c in cases if c['similarity_score'] >= config.get("retrieval", {}).get("min_similarity", 0.7)]),
            "returned": len(cases),
            "retrieval_time_ms": int(retrieval_time * 1000),
            "embedding_time_ms": int(embedding_time * 1000),
            "search_time_ms": int((retrieval_time - embedding_time) * 1000) if retrieval_time > embedding_time else 0
        }
    }

    # 如果没有结果，添加建议
    if not cases:
        output["message"] = f"未找到相似度高于{config.get('retrieval', {}).get('min_similarity', 0.7)}的结果"
        output["suggestions"] = [
            "尝试降低相似度阈值",
            "使用更通用的查询词",
            "检查过滤条件是否过于严格"
        ]

    return output

def main():
    """主函数 - 执行案例检索"""
    import argparse

    parser = argparse.ArgumentParser(description="从向量库检索案例")
    parser.add_argument("query", help="查询文本")
    parser.add_argument("--top-k", type=int, default=3, help="返回案例数量")
    parser.add_argument("--min-similarity", type=float, default=0.7, help="最小相似度阈值")
    parser.add_argument("--filters", help="过滤条件(JSON格式)")
    parser.add_argument("--output", help="输出文件路径")

    args = parser.parse_args()

    # 读取配置
    config_path = Path.home() / ".claude" / "skills" / "rag-case-retrieval" / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
    else:
        config = {
            "chroma": {"host": "http://localhost:8000"},
            "embedding": {
                "base_url": "http://localhost:11434/v1",
                "model": "bge-small-zh-v1.5",
                "api_key": "not-required",
                "timeout": 30
            },
            "retrieval": {"default_top_k": 3, "min_similarity": 0.7}
        }

    # 解析过滤条件
    filters = None
    if args.filters:
        filters = json.loads(args.filters)

    # 合并命令行参数
    top_k = args.top_k or config.get("retrieval", {}).get("default_top_k", 3)
    min_similarity = args.min_similarity or config.get("retrieval", {}).get("min_similarity", 0.7)

    chroma_host = config.get("chroma", {}).get("host", "http://localhost:8000")
    collection_name = config.get("chroma", {}).get("collection_name", "cases")
    embedding_model = config.get("embedding", {}).get("model", "text-embedding-3-small")

    print(f"查询: {args.query}")
    print(f"参数: top_k={top_k}, min_similarity={min_similarity}")

    # 生成查询向量
    print("\n生成查询向量...")
    start_embedding = time.time()
    query_embedding = get_query_embedding(args.query, config)
    embedding_time = time.time() - start_embedding
    print(f"  ✅ 完成 ({embedding_time:.2f}s)")

    # 检索案例
    print("\n检索案例...")
    start_retrieval = time.time()
    try:
        cases = retrieve_cases(
            query_embedding,
            collection_name=collection_name,
            host=chroma_host,
            top_k=top_k,
            min_similarity=min_similarity,
            filters=filters
        )
    except Exception as e:
        print(f"  ❌ 检索失败: {str(e)}")
        output = {
            "status": "error",
            "error_code": "RETRIEVAL_FAILED",
            "message": str(e)
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 1

    retrieval_time = time.time() - start_retrieval
    print(f"  ✅ 找到 {len(cases)} 条案例 ({retrieval_time:.2f}s)")

    # 格式化输出
    output = format_output(args.query, cases, config, retrieval_time, embedding_time)

    # 显示结果
    print("\n" + "=" * 60)
    print("检索结果:")
    print("=" * 60)

    for i, case in enumerate(cases, 1):
        print(f"\n[{i}] {case['title']}")
        print(f"  相似度: {case['similarity_score']:.2f}")
        print(f"  ID: {case['id']}")
        print(f"  内容预览: {case['content'][:200]}...")
        if case['metadata']:
            print(f"  元数据: {json.dumps(case['metadata'], ensure_ascii=False)}")

    # 保存到文件
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"\n结果已保存到: {args.output}")

    # 输出JSON
    print("\n完整JSON输出:")
    print(json.dumps(output, indent=2, ensure_ascii=False))

    return 0

if __name__ == "__main__":
    sys.exit(main())