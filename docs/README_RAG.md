# RAG Case Retrieval Skill

## Overview

The RAG Case Retrieval Skill provides a complete solution for semantic case retrieval using vector database technology. It enables importing cases from multiple data sources, generating embeddings, and retrieving the most relevant cases based on semantic similarity.

## Key Features

- ✅ **Multi-source Import**: PostgreSQL, JSON, CSV support
- ✅ **Intelligent Chunking**: Semantic boundary + overlap window
- ✅ **OpenAI Embedding**: text-embedding-3-small model
- ✅ **Chroma Integration**: Vector storage and retrieval
- ✅ **Metadata Filtering**: Time, category, tags filters
- ✅ **Structured Output**: JSON format with top-K results
- ✅ **Complete Pipeline**: Import → Embed → Store → Retrieve

## Architecture

```
┌──────────────┐
│  Data Source │ PostgreSQL / JSON / CSV
└──────┬───────┘
       │
       v
┌──────────────┐
│  Text Chunk  │ Semantic boundary + overlap
└──────┬───────┘
       │
       v
┌──────────────┐
│  Embedding   │ OpenAI text-embedding-3-small
└──────┬───────┘
       │
       v
┌──────────────┐
│   Chroma DB  │ Vector storage + HNSW index
└──────┬───────┘
       │
       v
┌──────────────┐
│   Retrieval  │ Semantic search + filtering
└──────┬───────┘
       │
       v
┌──────────────┐
│  JSON Output │ Top-K cases + metadata
└──────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
pip install chromadb openai psycopg2-binary
```

### 2. Start Chroma Service

```bash
# Docker (recommended)
docker run -d -p 8000:8000 --name chroma chromadb/chroma

# With persistence
docker run -d -p 8000:8000 -v ./chroma-data:/chroma/chroma chromadb/chroma
```

### 3. Configure OpenAI API Key

```bash
export OPENAI_API_KEY='your-api-key-here'
```

### 4. Environment Check

```bash
cd skills/rag-case-retrieval
python scripts/check_environment.py
```

Expected output:
```
============================================================
RAG案例检索 - 环境检查
============================================================

[1/4] 检查Python依赖...
  ✅ 所有依赖已安装

[2/4] 检查OpenAI配置...
  ✅ OpenAI API Key已配置

[3/4] 检查Chroma服务...
  ✅ Chroma服务连接正常

[4/4] 检查Collection状态...
  ⚠️  Collection 'cases' 不存在或为空
     需要先导入案例数据

============================================================
环境检查完成
============================================================
```

## Data Import

### From PostgreSQL Database

**Configure mapping in config.json**:
```json
{
  "database": {
    "type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "cases_db",
    "user": "your_user",
    "password": "your_password"
  },
  "import_mapping": {
    "id": "case_id",
    "title": "case_title",
    "content": "case_description",
    "category": "category_name",
    "tags": "tag_list"
  },
  "import_query": "SELECT * FROM cases WHERE created_at > '2020-01-01'"
}
```

**Import command**:
```bash
python scripts/import_cases.py --source database
```

### From JSON File

**JSON format**:
```json
[
  {
    "id": "case_001",
    "title": "JWT认证失败",
    "content": "生产环境部署后用户反馈...",
    "category": "安全",
    "tags": ["JWT", "认证"],
    "created_at": "2024-03-15T10:30:00Z"
  }
]
```

**Import command**:
```bash
python scripts/import_cases.py --source json --file cases.json
```

### From CSV File

**CSV format**:
```csv
id,title,content,category,created_at
case_001,JWT认证失败,生产环境...,安全,2024-03-15
case_002,数据库性能问题,查询响应...,性能,2024-03-20
```

**Import command**:
```bash
python scripts/import_cases.py --source csv --file cases.csv
```

### Import Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--chunk-size` | Text chunk size (chars) | 1000 |
| `--overlap` | Chunk overlap (chars) | 200 |
| `--collection` | Chroma collection name | cases |

## Case Retrieval

### Basic Retrieval

```bash
python scripts/retrieve_cases.py "JWT认证失败案例"
```

Output:
```json
{
  "status": "success",
  "query": "JWT认证失败案例",
  "results": [
    {
      "id": "case_001",
      "title": "JWT令牌过期处理不当",
      "content": "在生产环境部署后...",
      "similarity_score": 0.89,
      "metadata": {
        "category": "安全",
        "tags": ["JWT", "认证"]
      }
    }
  ],
  "summary": {
    "total_found": 3,
    "retrieval_time_ms": 245
  }
}
```

### Filtered Retrieval

**Time filter**:
```bash
python scripts/retrieve_cases.py "性能优化" \
  --filters '{"created_at": {"$gte": "2024-01-01"}}'
```

**Category filter**:
```bash
python scripts/retrieve_cases.py "安全漏洞" \
  --filters '{"category": "安全"}'
```

**Combined filter**:
```bash
python scripts/retrieve_cases.py "2024年安全案例" \
  --filters '{"$and": [{"category": "安全"}, {"created_at": {"$gte": "2024-01-01"}}]}'
```

### Retrieval Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--top-k` | Number of cases to return | 3 |
| `--min-similarity` | Minimum similarity threshold | 0.7 |
| `--filters` | Metadata filters (JSON) | None |
| `--output` | Output file path | Terminal |

## Similarity Thresholds

| Range | Use Case |
|-------|----------|
| 0.8 - 1.0 | High precision, near-exact matches |
| 0.7 - 0.8 | Strong relevance (default) |
| 0.6 - 0.7 | Moderate relevance |
| 0.5 - 0.6 | Low relevance, may need validation |

## Text Chunking Strategy

### Semantic Boundary Chunking

- **Priority**: Split at sentence endings (。！？.!?\n)
- **Maintain context**: Overlap window between chunks
- **Avoid**: Large chunks (lose precision) or small chunks (lose context)

### Chunking Parameters

```json
{
  "chunking": {
    "strategy": "semantic",
    "max_chunk_size": 1000,
    "overlap": 200,
    "min_chunk_size": 100
  }
}
```

**Recommended settings**:
- Documents < 2000 chars: Single chunk or large (1500)
- Documents 2000-5000 chars: Medium (1000 + 200 overlap)
- Documents > 5000 chars: Small (500 + 100 overlap)

## Configuration File

Location: `~/.claude/skills/rag-case-retrieval/config.json`

```json
{
  "chroma": {
    "host": "http://localhost:8000",
    "collection_name": "cases",
    "timeout": 30
  },
  "embedding": {
    "model": "text-embedding-3-small",
    "batch_size": 100
  },
  "retrieval": {
    "default_top_k": 3,
    "min_similarity": 0.7
  },
  "chunking": {
    "max_chunk_size": 1000,
    "overlap": 200
  }
}
```

## Error Handling

### Chroma Connection Failed

**Error**: `无法连接Chroma: Connection refused`

**Solution**:
```bash
# Check Docker service
docker ps | grep chroma

# Start Chroma
docker run -d -p 8000:8000 chromadb/chroma

# Verify connection
curl http://localhost:8000/api/v1/heartbeat
```

### OpenAI API Error

**Error**: `OpenAI API error: Invalid API key`

**Solution**:
```bash
# Verify API key
echo $OPENAI_API_KEY

# Reset API key
export OPENAI_API_KEY='sk-...'

# Check quota
# Visit https://platform.openai.com/account/usage
```

### Import Failed

**Error**: `Missing required field: content`

**Solution**:
- Verify data format (required: id, title, content)
- Check field mapping configuration
- Clean data: remove empty values, fix formats

## Performance Optimization

### Batch Processing

Import large datasets in batches:
```bash
python scripts/import_cases.py --source json --file batch1.json
python scripts/import_cases.py --source json --file batch2.json
```

### Embedding Cost Optimization

- Batch embedding generation (batch_size=100)
- Avoid duplicate imports
- Use incremental updates

### Retrieval Speed

- Reduce top_k (default 3 is sufficient)
- Use precise filters to narrow scope
- Chroma uses HNSW index (already optimized)

## Advanced Features

### Hybrid Retrieval

Combine keyword and vector search:
```python
# Vector retrieval for candidates
candidates = retrieve_cases(query, top_k=10)

# Keyword filtering
filtered = [c for c in candidates if "JWT" in c['title']]
```

### Cross-Encoder Reranking

Use Cross-Encoder for precision ranking:
```python
from sentence_transformers import CrossEncoder

# Vector retrieval
candidates = retrieve_cases(query, top_k=10)

# Cross-Encoder reranking
model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
scores = model.predict([(query, c['content']) for c in candidates])
reranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
```

### Multi-language Support

OpenAI `text-embedding-3-small` supports multiple languages automatically. No extra configuration needed for Chinese/English mixed content.

## File Structure

```
skills/rag-case-retrieval/
├── SKILL.md                      # Skill definition
├── config.json                   # Configuration template
├── scripts/
│   ├── check_environment.py      # Environment validation
│   ├── import_cases.py           # Data import
│   └── retrieve_cases.py         # Case retrieval
├── references/
│   └── schema.md                 # Data structure definition
└── evals/
    └── evals.json                # Test cases
```

## Documentation

- **SKILL.md**: Complete skill definition and workflow
- **schema.md**: Data structure specifications
- **rag-case-retrieval-guide.md**: Comprehensive user guide (in docs/)
- **README_RAG.md**: Quick reference (this file)

## Testing

Test cases in `evals/evals.json`:

1. **Basic Retrieval**: "查找JWT认证失败案例"
2. **Data Import**: "从PostgreSQL导入新案例"
3. **Filtered Retrieval**: "检索2024年性能案例（相似度>0.8）"

## Troubleshooting

### Checklist

1. **Environment check**
   ```bash
   python scripts/check_environment.py
   ```

2. **Collection status**
   ```python
   import chromadb
   client = chromadb.HttpClient()
   collection = client.get_collection("cases")
   print(f"Documents: {collection.count()}")
   ```

3. **OpenAI connection**
   ```python
   from openai import OpenAI
   client = OpenAI()
   response = client.embeddings.create(
       model="text-embedding-3-small",
       input="test"
   )
   print(response.data[0].embedding[:5])
   ```

### Common Issues

**Q: Why are results inaccurate?**
A:
- Check query specificity
- Verify chunking parameters
- Confirm similarity threshold
- Check data quality

**Q: How to improve retrieval speed?**
A:
- Reduce top_k
- Use precise filters
- Chroma already uses HNSW index

**Q: Why can't find imported cases?**
A:
- Run environment check
- Verify collection.count()
- Check chunking correctness
- Confirm embedding generation

**Q: How to delete incorrect cases?**
A:
```python
import chromadb
client = chromadb.HttpClient()
collection = client.get_collection("cases")
collection.delete(ids=["case_001_chunk_0"])
```

## References

- **Chroma Docs**: https://docs.trychroma.com/
- **OpenAI Embedding**: https://platform.openai.com/docs/guides/embeddings
- **Skill Guide**: docs/rag-case-retrieval-guide.md
- **Data Schema**: skills/rag-case-retrieval/references/schema.md

## Version History

- **v1.0 (2026-06-02)**: Initial release
  - PostgreSQL/JSON/CSV support
  - Intelligent chunking
  - OpenAI Embedding integration
  - Chroma vector retrieval
  - Structured JSON output

## License

MIT License

## Authors

RAG Case Retrieval Skill - Developed for semantic case matching workflow