# rag-case-retrieval Guide

RAG-based semantic case retrieval from vector database.

## Prerequisites

```bash
pip install chromadb openai psycopg2-binary

# Start Chroma
docker run -d -p 8000:8000 --name chroma chromadb/chroma

# Set API key
export OPENAI_API_KEY='your-key'
```

## Usage

### Import Cases

```bash
# From PostgreSQL
python scripts/import_cases.py --source database --table cases

# From JSON file
python scripts/import_cases.py --source json --file cases.json

# From CSV
python scripts/import_cases.py --source csv --file cases.csv
```

### Retrieve Cases

```bash
python scripts/retrieve_cases.py "query text" --top-k 3

# With filters
python scripts/retrieve_cases.py "性能优化" \
  --filters '{"category": "性能", "created_at": {"$gte": "2024-01-01"}}'
```

## Output Format

```json
{
  "query": "JWT认证失败",
  "results": [
    {
      "id": "case_001",
      "title": "JWT令牌过期处理",
      "content": "...",
      "similarity_score": 0.89
    }
  ]
}
```

## Configuration

Edit `config.json`:

| Field | Description |
|-------|-------------|
| `chroma.host` | Chroma server URL |
| `chroma.collection_name` | Collection name |
| `embedding.model` | OpenAI model |
| `chunk.size` | Text chunk size |
| `chunk.overlap` | Overlap size |

## Text Chunking

Automatic chunking with:
- Semantic boundary detection
- Overlap window for context

## Metadata Filters

Supported operators:
- `$eq`, `$ne` - Equality
- `$gt`, `$gte`, `$lt`, `$lte` - Comparison
- `$in`, `$nin` - Array membership

## Scripts

| Script | Purpose |
|--------|---------|
| `import_cases.py` | Import from sources |
| `retrieve_cases.py` | Semantic search |
| `check_environment.py` | Verify setup |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Chroma connection failed | Check Docker running |
| Embedding error | Verify API key |
| No results | Import cases first |