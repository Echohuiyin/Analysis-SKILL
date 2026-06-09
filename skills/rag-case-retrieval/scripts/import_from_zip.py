#!/usr/bin/env python3
"""
ZIP包导入脚本 - 递归扫描ZIP包，提取内嵌Markdown文档导入到Chroma向量库
支持嵌套ZIP解压和Wiki文件名标题提取
"""

import os
import sys
import json
import time
import zipfile
import tempfile
import shutil
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

def extract_wiki_title_from_filename(file_path: str) -> str:
    """
    从Wiki风格文件名提取标题

    Wiki文件名特点：
    - 使用 `_` 或 `-` 或空格连接单词
    - 可能包含中文名称
    - 需要转换为可读标题格式

    转换规则：
    - 下划线、连字符转为空格
    - 首字母大写（英文）
    - 保留中文原样

    Args:
        file_path: 文件路径

    Returns:
        Wiki风格标题
    """
    filename = Path(file_path).stem

    # 常见Wiki格式转换
    # 移除序号前缀如 "001-", "01_", "第1章_" 等
    filename = re.sub(r'^[\d]+[-_]', '', filename)
    filename = re.sub(r'^第[\d]+[章节篇][-_]', '', filename)

    # 下划线和连字符转为空格
    filename = re.sub(r'[_\-]+', ' ', filename)

    # 清理多余空格
    filename = filename.strip()

    # 如果全为中文，直接返回
    if re.match(r'^[一-鿿]+$', filename):
        return filename

    # 英文首字母大写（单词级别）
    words = filename.split()
    title_words = []
    for word in words:
        # 保留全大写词（如API, HTTP）
        if word.isupper():
            title_words.append(word)
        else:
            title_words.append(word.capitalize())

    return ' '.join(title_words)

def extract_markdown_title(content: str, file_path: str) -> str:
    """
    从Markdown内容提取标题

    优先级：
    1. Wiki文件名（转换为可读标题格式）
    2. YAML frontmatter 中的 title 字段
    3. 第一个 # 标题
    4. 原始文件名

    Args:
        content: Markdown内容
        file_path: 文件路径

    Returns:
        标题字符串
    """
    # 优先使用Wiki文件名转换的标题
    wiki_title = extract_wiki_title_from_filename(file_path)
    if wiki_title and len(wiki_title) > 2:
        return wiki_title

    # 尝试提取YAML frontmatter中的title
    frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if frontmatter_match:
        frontmatter = frontmatter_match.group(1)
        title_match = re.search(r'^title:\s*(.+)$', frontmatter, re.MULTILINE)
        if title_match:
            return title_match.group(1).strip().strip('"').strip("'")

    # 尝试提取第一个 # 标题
    heading_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if heading_match:
        return heading_match.group(1).strip()

    # 最后使用原始文件名
    filename = Path(file_path).stem
    return filename

def extract_markdown_metadata(content: str) -> Dict[str, Any]:
    """
    从Markdown frontmatter提取元数据

    Args:
        content: Markdown内容

    Returns:
        元数据字典
    """
    metadata = {}

    # 提取YAML frontmatter
    frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if frontmatter_match:
        frontmatter = frontmatter_match.group(1)

        # 提取常见字段
        fields = ['date', 'category', 'tags', 'author', 'source', 'keywords']
        for field in fields:
            match = re.search(rf'^{field}:\s*(.+)$', frontmatter, re.MULTILINE)
            if match:
                value = match.group(1).strip().strip('"').strip("'")
                # 处理tags列表格式
                if field == 'tags' and value.startswith('['):
                    value = [t.strip().strip('"').strip("'") for t in value[1:-1].split(',')]
                metadata[field] = value

    return metadata

def clean_markdown_content(content: str) -> str:
    """
    清理Markdown内容

    - 移除frontmatter
    - 移除代码块标记（保留内容）
    - 移除图片链接
    - 移除HTML标签
    - 规范化空白

    Args:
        content: 原始Markdown内容

    Returns:
        清理后的纯文本
    """
    # 移除YAML frontmatter
    content = re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, flags=re.DOTALL)

    # 移除代码块标记（保留代码内容）
    content = re.sub(r'```[\w]*\n', '', content)
    content = re.sub(r'```', '', content)

    # 移除行内代码标记
    content = re.sub(r'`([^`]+)`', r'\1', content)

    # 移除图片链接
    content = re.sub(r'!\[.*?\]\(.*?\)', '', content)

    # 移除链接，保留文本
    content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)

    # 移除HTML标签
    content = re.sub(r'<[^>]+>', '', content)

    # 移除多余的标题标记
    content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)

    # 移除列表标记
    content = re.sub(r'^[\*\-\+]\s+', '', content, flags=re.MULTILINE)
    content = re.sub(r'^\d+\.\s+', '', content, flags=re.MULTILINE)

    # 规范化空白
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = content.strip()

    return content

def recursive_extract_zip(zip_path: str, extract_dir: str, depth: int = 0,
                          max_depth: int = 10) -> List[str]:
    """
    递归解压ZIP文件，处理嵌套ZIP

    Args:
        zip_path: ZIP文件路径
        extract_dir: 解压目标目录
        depth: 当前递归深度
        max_depth: 最大递归深度

    Returns:
        解压出的所有文件路径列表
    """
    if depth > max_depth:
        print(f"  ⚠️ 达到最大递归深度 {max_depth}，跳过: {zip_path}")
        return []

    extracted_files = []
    current_dir = os.path.join(extract_dir, f"level_{depth}")

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # 创建当前层级的目录
            os.makedirs(current_dir, exist_ok=True)

            for member in zf.namelist():
                # 跳过目录
                if member.endswith('/'):
                    continue

                # 解压文件
                target_path = os.path.join(current_dir, member)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)

                with zf.open(member) as source:
                    with open(target_path, 'wb') as target:
                        target.write(source.read())

                extracted_files.append(target_path)

                # 如果是ZIP文件，递归解压
                if member.lower().endswith('.zip'):
                    nested_files = recursive_extract_zip(
                        target_path,
                        extract_dir,
                        depth + 1,
                        max_depth
                    )
                    extracted_files.extend(nested_files)

    except zipfile.BadZipFile as e:
        print(f"  ⚠️ 无效ZIP文件: {zip_path} - {str(e)}")
    except Exception as e:
        print(f"  ⚠️ 解压失败: {zip_path} - {str(e)}")

    return extracted_files

def scan_markdown_files(directory: str) -> List[str]:
    """
    扫描目录中的所有Markdown文件

    Args:
        directory: 目录路径

    Returns:
        Markdown文件路径列表
    """
    md_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.md'):
                md_files.append(os.path.join(root, file))
    return md_files

def parse_markdown_file(file_path: str, source_zip: str) -> Dict[str, Any]:
    """
    解析单个Markdown文件

    Args:
        file_path: Markdown文件路径
        source_zip: 来源ZIP文件路径

    Returns:
        案例字典
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()

        # 提取标题
        title = extract_markdown_title(raw_content, file_path)

        # 提取元数据
        metadata = extract_markdown_metadata(raw_content)

        # 清理内容
        clean_content = clean_markdown_content(raw_content)

        # 添加来源信息
        metadata['source_file'] = file_path
        metadata['source_zip'] = source_zip
        metadata['extracted_at'] = datetime.now().isoformat()

        # 生成唯一ID（使用相对路径）
        rel_path = Path(file_path).relative_to(Path(file_path).parents[3])
        case_id = str(rel_path).replace('/', '_').replace('\\', '_').replace('.md', '')

        return {
            "id": case_id,
            "title": title,
            "content": clean_content,
            "metadata": metadata,
            "raw_path": file_path
        }

    except Exception as e:
        print(f"  ⚠️ 解析失败: {file_path} - {str(e)}")
        return None

def get_embeddings(texts: List[str], config: Dict) -> List[List[float]]:
    """生成文本向量"""
    from openai import OpenAI

    embedding_config = config.get("embedding", {})
    base_url = embedding_config.get("base_url", "http://localhost:11434/v1")
    model = embedding_config.get("model", "bge-large-zh")
    api_key = embedding_config.get("api_key", "not-required")
    timeout = embedding_config.get("timeout", 60)
    batch_size = embedding_config.get("batch_size", 50)

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
            print(f"    向量化进度: {min(i + batch_size, len(texts))}/{len(texts)}")
        except Exception as e:
            raise Exception(f"向量化失败: {str(e)}")

    return all_embeddings

def prepare_fixed_length_text(title: str, content: str, config: Dict) -> str:
    """准备定长文本用于向量化"""
    vec_config = config.get("vectorization", {})
    head_chars = vec_config.get("head_chars", 400)
    title_injection = vec_config.get("title_injection", True)

    title = title.strip() if title else ""
    content = content.strip() if content else ""

    if title_injection and title:
        text = f"{title}\n\n{content[:head_chars]}"
    else:
        text = content[:head_chars]

    return text

def store_to_chroma(cases: List[Dict], config: Dict,
                   collection_name: str = "cases",
                   host: str = "http://localhost:8000") -> Dict:
    """将案例存储到Chroma"""
    import chromadb

    client = chromadb.HttpClient(host=host.split("://")[1].split(":")[0],
                                  port=int(host.split(":")[-1]))

    embedding_model = config.get("embedding", {}).get("model", "bge-large-zh")
    embedding_dimension = config.get("embedding", {}).get("dimension", 1024)

    # 创建或获取collection
    try:
        collection = client.get_collection(name=collection_name)
        print(f"  使用已有Collection: {collection_name}")
    except:
        collection = client.create_collection(
            name=collection_name,
            metadata={
                "hnsw:space": "cosine",
                "description": "案例检索向量库",
                "embedding_model": embedding_model,
                "embedding_dimension": embedding_dimension,
                "vectorization_strategy": "fixed_length",
                "created_at": datetime.now().isoformat()
            }
        )
        print(f"  创建新Collection: {collection_name}")

    stats = {
        "total_cases": len(cases),
        "successful": 0,
        "failed": 0,
        "errors": []
    }

    # 准备数据
    all_ids = []
    all_texts = []
    all_metadatas = []
    all_documents = []

    for case in cases:
        if not case.get("id") or not case.get("content"):
            stats["failed"] += 1
            stats["errors"].append({
                "case_id": case.get("id", "unknown"),
                "error": "缺少必需字段"
            })
            continue

        # 定长文本
        vector_text = prepare_fixed_length_text(
            case.get("title", ""),
            case.get("content", ""),
            config
        )

        # 元数据
        metadata = {
            "doc_id": case["id"],
            "title": case.get("title", "")[:500],
            "content_length": len(case.get("content", "")),
            "vector_strategy": "fixed_length"
        }

        for key, value in case.get("metadata", {}).items():
            if isinstance(value, (str, int, float, bool)):
                metadata[key] = value
            elif isinstance(value, list):
                metadata[key] = json.dumps(value)

        all_ids.append(case["id"])
        all_texts.append(vector_text)
        all_metadatas.append(metadata)
        all_documents.append(case.get("content", "")[:2000])

        stats["successful"] += 1

    # 批量生成向量
    if all_texts:
        print(f"\n  生成向量...")
        all_embeddings = get_embeddings(all_texts, config)

        # 存储到Chroma
        print(f"  存储到Chroma...")
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
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="递归扫描ZIP包，提取Markdown文档导入到Chroma向量库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --zip cases.zip
  %(prog)s --zip archive.zip --collection docs
  %(prog)s --zip /path/to/zips/*.zip

功能:
  - 递归解压嵌套ZIP文件
  - 提取所有.md文件
  - 解析Markdown标题和frontmatter
  - 定长向量化导入Chroma
        """
    )
    parser.add_argument("--zip", required=True, nargs='+', help="ZIP文件路径（支持多个）")
    parser.add_argument("--collection", default="cases", help="Collection名称")
    parser.add_argument("--max-depth", type=int, default=10, help="ZIP递归解压最大深度")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--keep-temp", action="store_true", help="保留临时解压文件")

    args = parser.parse_args()

    # 读取配置
    if args.config:
        with open(args.config) as f:
            config = json.load(f)
    else:
        config_path = Path.home() / ".claude" / "skills" / "rag-case-retrieval" / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
        else:
            config = {
                "embedding": {
                    "base_url": "http://localhost:11434/v1",
                    "model": "bge-large-zh",
                    "dimension": 1024
                },
                "vectorization": {
                    "head_chars": 400,
                    "title_injection": True
                }
            }

    # 打印配置
    print("=" * 60)
    print("ZIP包Markdown导入")
    print("=" * 60)
    print(f"嵌入模型: {config.get('embedding', {}).get('model', 'bge-large-zh')}")
    print(f"向量维度: {config.get('embedding', {}).get('dimension', 1024)}")
    print(f"最大递归深度: {args.max_depth}")
    print("=" * 60)

    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="rag_zip_extract_")
    print(f"\n临时目录: {temp_dir}")

    all_cases = []
    total_md_files = 0

    # 处理每个ZIP文件
    for zip_path in args.zip:
        zip_path = Path(zip_path)
        if not zip_path.exists():
            print(f"\n⚠️ ZIP文件不存在: {zip_path}")
            continue

        print(f"\n处理ZIP: {zip_path.name}")

        # 递归解压
        print(f"  递归解压...")
        extracted_files = recursive_extract_zip(
            str(zip_path),
            temp_dir,
            depth=0,
            max_depth=args.max_depth
        )
        print(f"  解压文件数: {len(extracted_files)}")

        # 扫描Markdown文件
        md_files = scan_markdown_files(temp_dir)
        print(f"  Markdown文件数: {len(md_files)}")
        total_md_files += len(md_files)

        # 解析Markdown文件
        print(f"  解析Markdown...")
        for md_file in md_files:
            case = parse_markdown_file(md_file, str(zip_path))
            if case:
                all_cases.append(case)

    print(f"\n总计提取Markdown文件: {total_md_files}")
    print(f"有效案例数: {len(all_cases)}")

    if not all_cases:
        print("\n❌ 未提取到有效案例")
        if not args.keep_temp:
            shutil.rmtree(temp_dir)
        return 1

    # 存储到Chroma
    chroma_host = config.get("chroma", {}).get("host", "http://localhost:8000")
    print(f"\n导入到Chroma ({chroma_host})...")
    start_time = time.time()
    stats = store_to_chroma(
        all_cases,
        config=config,
        collection_name=args.collection,
        host=chroma_host
    )
    elapsed = time.time() - start_time

    # 输出统计
    print("\n" + "=" * 60)
    print("导入完成:")
    print(f"  ✅ 成功: {stats['successful']}")
    print(f"  ❌ 失败: {stats['failed']}")
    print(f"  ⏱️  耗时: {elapsed:.2f}s")

    if stats['errors']:
        print(f"\n错误详情 ({len(stats['errors'])} 条):")
        for error in stats['errors'][:5]:
            print(f"  - {error.get('case_id', 'unknown')}: {error.get('error', 'unknown')}")

    # 清理临时目录
    if not args.keep_temp:
        shutil.rmtree(temp_dir)
        print(f"\n已清理临时目录")
    else:
        print(f"\n临时目录保留: {temp_dir}")

    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())