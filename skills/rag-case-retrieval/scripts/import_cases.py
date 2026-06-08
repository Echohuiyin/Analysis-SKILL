#!/usr/bin/env python3
"""
案例导入脚本 - 从数据源导入案例到Chroma向量库
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

def get_embeddings(texts: List[str], config: Dict) -> List[List[float]]:
    """生成文本向量 (使用本地OpenAI兼容服务)"""
    from openai import OpenAI

    embedding_config = config.get("embedding", {})
    base_url = embedding_config.get("base_url", "http://localhost:11434/v1")
    model = embedding_config.get("model", "bge-small-zh-v1.5")
    api_key = embedding_config.get("api_key", "not-required")
    timeout = embedding_config.get("timeout", 30)
    batch_size = embedding_config.get("batch_size", 100)

    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout
    )

    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            response = client.embeddings.create(
                model=model,
                input=batch
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)
        except Exception as e:
            raise Exception(f"Failed to generate embeddings from {base_url}: {str(e)}")

    return all_embeddings

def chunk_text(text: str, max_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
    """将长文本分块"""
    if len(text) <= max_size:
        return [{"text": text, "index": 0}]

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(text):
        end = start + max_size

        # 尝试在句子边界分块
        if end < len(text):
            # 向后查找句子结束符
            for sep in ['。', '！', '？', '.', '!', '?', '\n']:
                last_sep = text.rfind(sep, start, end)
                if last_sep > start + max_size // 2:
                    end = last_sep + 1
                    break

        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append({
                "text": chunk_text,
                "index": chunk_index
            })
            chunk_index += 1

        start = end - overlap if end < len(text) else end

    return chunks

def import_from_database(connection_config: Dict, query: str, mapping: Dict) -> List[Dict]:
    """从数据库导入案例"""
    import psycopg2
    from psycopg2.extras import RealDictCursor

    conn = psycopg2.connect(
        host=connection_config.get("host", "localhost"),
        port=connection_config.get("port", 5432),
        database=connection_config.get("database"),
        user=connection_config.get("user"),
        password=connection_config.get("password")
    )

    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(query)
    rows = cursor.fetchall()

    cases = []
    for row in rows:
        case = {
            "id": str(row.get(mapping.get("id", "id"))),
            "title": row.get(mapping.get("title", "title"), ""),
            "content": row.get(mapping.get("content", "content"), ""),
            "metadata": {}
        }

        # 添加可选字段
        for field in ["category", "tags", "created_at", "source", "author"]:
            if field in mapping and mapping[field] in row:
                case["metadata"][field] = row[mapping[field]]

        cases.append(case)

    cursor.close()
    conn.close()

    return cases

def import_from_json(file_path: str) -> List[Dict]:
    """从JSON文件导入案例"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "cases" in data:
        return data["cases"]
    else:
        raise ValueError("JSON格式不正确，期望列表或包含'cases'键的对象")

def import_from_csv(file_path: str, mapping: Dict) -> List[Dict]:
    """从CSV文件导入案例"""
    import csv

    cases = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            case = {
                "id": str(row.get(mapping.get("id", "id"), len(cases))),
                "title": row.get(mapping.get("title", "title"), ""),
                "content": row.get(mapping.get("content", "content"), ""),
                "metadata": {}
            }

            for field in ["category", "tags", "created_at"]:
                if field in mapping and mapping[field] in row:
                    case["metadata"][field] = row[mapping[field]]

            cases.append(case)

    return cases

def store_to_chroma(cases: List[Dict], config: Dict,
                   collection_name: str = "cases",
                   host: str = "http://localhost:8000", chunk_size: int = 1000,
                   overlap: int = 200) -> Dict:
    """将案例存储到Chroma"""
    import chromadb

    client = chromadb.HttpClient(host=host.split("://")[1].split(":")[0],
                                  port=int(host.split(":")[-1]))

    embedding_model = config.get("embedding", {}).get("model", "bge-small-zh-v1.5")

    # 创建或获取collection
    try:
        collection = client.get_collection(name=collection_name)
    except:
        collection = client.create_collection(
            name=collection_name,
            metadata={
                "description": "案例检索向量库",
                "embedding_model": embedding_model,
                "created_at": datetime.now().isoformat()
            }
        )

    stats = {
        "total_cases": len(cases),
        "total_chunks": 0,
        "successful": 0,
        "failed": 0,
        "errors": []
    }

    # 处理每个案例
    all_ids = []
    all_embeddings = []
    all_metadatas = []
    all_documents = []

    for case in cases:
        try:
            # 验证必需字段
            if not case.get("id") or not case.get("content"):
                stats["failed"] += 1
                stats["errors"].append({
                    "case_id": case.get("id", "unknown"),
                    "error": "Missing required fields"
                })
                continue

            # 分块
            chunks = chunk_text(case["content"], chunk_size, overlap)

            # 生成向量
            texts = [chunk["text"] for chunk in chunks]
            embeddings = get_embeddings(texts, config)

            # 准备数据
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_id = f"{case['id']}_chunk_{i}"

                metadata = {
                    "doc_id": case["id"],
                    "title": case.get("title", ""),
                    "chunk_index": i,
                    "chunk_total": len(chunks)
                }

                # 添加额外元数据
                if "metadata" in case:
                    for key, value in case["metadata"].items():
                        if isinstance(value, (str, int, float, bool)):
                            metadata[key] = value

                all_ids.append(chunk_id)
                all_embeddings.append(embedding)
                all_metadatas.append(metadata)
                all_documents.append(chunk["text"])

            stats["total_chunks"] += len(chunks)
            stats["successful"] += 1

        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append({
                "case_id": case.get("id", "unknown"),
                "error": str(e)
            })

    # 批量添加到Chroma
    if all_ids:
        batch_size = 100
        for i in range(0, len(all_ids), batch_size):
            collection.add(
                ids=all_ids[i:i + batch_size],
                embeddings=all_embeddings[i:i + batch_size],
                metadatas=all_metadatas[i:i + batch_size],
                documents=all_documents[i:i + batch_size]
            )

    return stats

def main():
    """主函数 - 从命令行或配置文件读取参数"""
    import argparse

    parser = argparse.ArgumentParser(description="导入案例到Chroma向量库")
    parser.add_argument("--source", help="数据源类型: database, json, csv")
    parser.add_argument("--file", help="JSON或CSV文件路径")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--collection", default="cases", help="Collection名称")
    parser.add_argument("--chunk-size", type=int, default=1000, help="分块大小")
    parser.add_argument("--overlap", type=int, default=200, help="分块重叠")

    args = parser.parse_args()

    # 读取配置
    if args.config:
        with open(args.config) as f:
            config = json.load(f)
    else:
        # 尝试从默认配置读取
        config_path = Path.home() / ".claude" / "skills" / "rag-case-retrieval" / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
        else:
            print("❌ 未找到配置文件，请使用--config参数或创建默认配置")
            return 1

    # 读取案例
    cases = []

    if args.source == "json" and args.file:
        print(f"从JSON文件导入: {args.file}")
        cases = import_from_json(args.file)
    elif args.source == "csv" and args.file:
        print(f"从CSV文件导入: {args.file}")
        mapping = config.get("import_mapping", {})
        cases = import_from_csv(args.file, mapping)
    elif args.source == "database":
        print("从数据库导入...")
        db_config = config.get("database", {})
        query = config.get("import_query", "SELECT * FROM cases")
        mapping = config.get("import_mapping", {})
        cases = import_from_database(db_config, query, mapping)
    else:
        print("❌ 请指定数据源类型和文件路径")
        return 1

    print(f"读取到 {len(cases)} 条案例")

    # 存储到Chroma
    chroma_host = config.get("chroma", {}).get("host", "http://localhost:8000")

    print(f"导入到Chroma ({chroma_host})...")
    stats = store_to_chroma(
        cases,
        config=config,
        collection_name=args.collection,
        host=chroma_host,
        chunk_size=args.chunk_size,
        overlap=args.overlap
    )

    # 输出统计
    print("\n导入完成:")
    print(f"  ✅ 成功: {stats['successful']}")
    print(f"  ❌ 失败: {stats['failed']}")
    print(f"  📦 总块数: {stats['total_chunks']}")

    if stats['errors']:
        print(f"\n错误详情 ({len(stats['errors'])} 条):")
        for error in stats['errors'][:5]:  # 只显示前5个
            print(f"  - {error['case_id']}: {error['error']}")

    return 0

if __name__ == "__main__":
    sys.exit(main())