# RAG案例检索技能使用指南

## 概述

RAG案例检索技能提供完整的向量检索解决方案，支持从多种数据源导入案例到Chroma向量数据库，并基于语义相似度检索最相关的案例。

**核心功能**：
- ✅ 多数据源支持（PostgreSQL、JSON、CSV）
- ✅ 智能文本分块（语义边界 + 重叠窗口）
- ✅ OpenAI Embedding向量化
- ✅ Chroma向量存储与检索
- ✅ 元数据过滤（时间、分类、标签）
- ✅ 结构化JSON输出

## 快速开始

### 1. 环境准备

#### 安装依赖
```bash
pip install chromadb openai psycopg2-binary
```

#### 启动Chroma服务
```bash
# Docker方式（推荐）
docker run -d -p 8000:8000 --name chroma chromadb/chroma

# 或使用本地持久化
docker run -d -p 8000:8000 -v ./chroma-data:/chroma/chroma chromadb/chroma
```

#### 配置OpenAI API Key
```bash
export OPENAI_API_KEY='your-api-key-here'
```

### 2. 配置技能

编辑配置文件（首次使用会自动创建模板）：
```bash
# 配置文件位置：~/.claude/skills/rag-case-retrieval/config.json
```

关键配置项：
```json
{
  "chroma": {
    "host": "http://localhost:8000",
    "collection_name": "cases"
  },
  "embedding": {
    "model": "text-embedding-3-small"
  },
  "retrieval": {
    "default_top_k": 3,
    "min_similarity": 0.7
  },
  "database": {
    "type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "your_database",
    "user": "your_user",
    "password": "your_password"
  }
}
```

### 3. 环境检查

运行环境检查脚本验证配置：
```bash
cd skills/rag-case-retrieval
python scripts/check_environment.py
```

预期输出：
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

## 数据导入

### 从数据库导入

**配置数据源映射**（在config.json中）：
```json
{
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

**执行导入**：
```bash
python scripts/import_cases.py --source database --config ~/.claude/skills/rag-case-retrieval/config.json
```

### 从JSON文件导入

**JSON格式示例**：
```json
[
  {
    "id": "case_001",
    "title": "JWT令牌过期处理不当",
    "content": "在生产环境部署后，用户反馈频繁出现认证失败...",
    "category": "安全",
    "tags": ["JWT", "认证", "竞态条件"],
    "created_at": "2024-03-15T10:30:00Z"
  }
]
```

**执行导入**：
```bash
python scripts/import_cases.py --source json --file cases.json --collection cases
```

### 从CSV文件导入

**CSV格式示例**：
```csv
id,title,content,category,created_at
case_001,JWT认证失败,用户频繁认证失败...,安全,2024-03-15
case_002,数据库性能问题,查询响应时间过长...,性能,2024-03-20
```

**执行导入**：
```bash
python scripts/import_cases.py --source csv --file cases.csv --collection cases
```

### 导入参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--chunk-size` | 文本分块大小（字符） | 1000 |
| `--overlap` | 分块重叠大小（字符） | 200 |
| `--collection` | Chroma collection名称 | cases |
| `--config` | 配置文件路径 | ~/.claude/skills/rag-case-retrieval/config.json |

**分块策略**：
- 按语义边界分块（优先在句子结束符：。！？.!?\n处分割）
- 保持上下文连续性（重叠窗口）
- 避免过大块（影响检索精度）和过小块（丢失上下文）

### 导入统计输出

```
读取到 150 条案例
导入到Chroma (http://localhost:8000)...

导入完成:
  ✅ 成功: 148
  ❌ 失败: 2
  📦 总块数: 256

错误详情 (2 条):
  - case_123: Missing required field: content
  - case_145: Content too short
```

## 案例检索

### 基础检索

```bash
python scripts/retrieve_cases.py "JWT认证失败案例"
```

输出：
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

### 带过滤条件检索

**时间范围过滤**：
```bash
python scripts/retrieve_cases.py "性能优化" \
  --filters '{"created_at": {"$gte": "2024-01-01"}}'
```

**分类过滤**：
```bash
python scripts/retrieve_cases.py "安全漏洞" \
  --filters '{"category": "安全"}'
```

**标签过滤**：
```bash
python scripts/retrieve_cases.py "数据库问题" \
  --filters '{"tags": {"$contains": "MySQL"}}'
```

**组合过滤**：
```bash
python scripts/retrieve_cases.py "2024年安全案例" \
  --filters '{"$and": [{"category": "安全"}, {"created_at": {"$gte": "2024-01-01"}}]}'
```

### 检索参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--top-k` | 返回案例数量 | 3 |
| `--min-similarity` | 最小相似度阈值 | 0.7 |
| `--filters` | 元数据过滤条件（JSON格式） | 无 |
| `--output` | 输出文件路径 | 终端输出 |

### 相似度阈值建议

| 阈值范围 | 适用场景 |
|----------|----------|
| 0.8 - 1.0 | 高精度匹配，几乎完全一致 |
| 0.7 - 0.8 | 相关性强，内容高度相关（默认） |
| 0.6 - 0.7 | 中等相关性，有一定参考价值 |
| 0.5 - 0.6 | 低相关性，可能包含有用信息 |

### 无结果时的建议

当检索无结果时，系统会提供优化建议：
```json
{
  "status": "no_results",
  "message": "未找到相似度高于0.7的结果",
  "suggestions": [
    "尝试降低相似度阈值 (--min-similarity 0.6)",
    "使用更通用的查询词",
    "检查过滤条件是否过于严格"
  ],
  "best_match": {
    "similarity_score": 0.65,
    "title": "最接近的案例"
  }
}
```

## 过滤操作符参考

### 基础操作符

```python
# 相等
{"field": "value"}
{"field": {"$eq": "value"}}

# 不相等
{"field": {"$ne": "value"}}

# 包含（数组）
{"tags": {"$contains": "标签名"}}
{"tags": {"$in": ["标签1", "标签2"]}}
```

### 数值比较

```python
# 大于/大于等于
{"field": {"$gt": 10}}
{"field": {"$gte": 10}}

# 小于/小于等于
{"field": {"$lt": 100}}
{"field": {"$lte": 100}}
```

### 逻辑组合

```python
# AND逻辑
{"$and": [{"field1": "value1"}, {"field2": "value2"}]}

# OR逻辑
{"$or": [{"field1": "value1"}, {"field2": "value2"}]}
```

## 最佳实践

### 1. 查询优化

**具体描述性查询**（推荐）：
```
"JWT令牌刷新时出现的竞态条件导致认证失败"
```

**泛泛查询**（不推荐）：
```
"认证问题"
```

**包含关键实体**：
```
"MySQL数据库在高并发场景下的查询性能优化案例"
```

### 2. 分块策略

**推荐配置**：
- 文档大小 < 2000字符：不分块或大块（chunk_size=1500）
- 文档大小 2000-5000字符：中等块（chunk_size=1000, overlap=200）
- 文档大小 > 5000字符：小块（chunk_size=500, overlap=100）

**按语义边界分块**：
- 系统自动识别句子结束符（。！？.!?\n）
- 避免在句子中间分割
- 保持段落完整性

### 3. 数据维护

**定期更新**：
```bash
# 增量导入新案例
python scripts/import_cases.py --source json --file new_cases.json

# 检查collection状态
python scripts/check_environment.py
```

**清理过期案例**（需要手动操作Chroma）：
```python
import chromadb
client = chromadb.HttpClient(host="localhost", port=8000)
collection = client.get_collection("cases")
# 根据metadata过滤删除
collection.delete(where={"created_at": {"$lt": "2020-01-01"}})
```

### 4. 结果验证

检查相似度得分：
- 高相似度（> 0.8）：直接应用
- 中相似度（0.7-0.8）：参考并结合其他案例
- 低相似度（< 0.7）：谨慎使用，需人工验证

查看元数据匹配：
- 时间范围是否符合预期
- 分类/标签是否准确
- 来源可信度

## 错误处理

### Chroma连接失败

**症状**：
```
❌ 无法连接Chroma: Connection refused
```

**解决方案**：
```bash
# 检查Docker服务
docker ps | grep chroma

# 启动Chroma
docker run -d -p 8000:8000 chromadb/chroma

# 验证连接
curl http://localhost:8000/api/v1/heartbeat
```

### OpenAI API错误

**症状**：
```
❌ OpenAI API error: Invalid API key
```

**解决方案**：
```bash
# 验证API Key
echo $OPENAI_API_KEY

# 重新设置
export OPENAI_API_KEY='sk-...'

# 检查配额
# 访问 https://platform.openai.com/account/usage
```

### 导入失败

**症状**：
```
❌ Missing required field: content
```

**解决方案**：
- 验证数据格式（必需字段：id, title, content）
- 检查字段映射配置
- 清洗数据：去除空值、修正格式

**症状**：
```
❌ Content too short
```

**解决方案**：
- 设置最小块大小：`config.chunking.min_chunk_size = 100`
- 合并短文档
- 过滤无效数据

## 性能优化

### 批量处理

导入大量数据时：
```bash
# 分批导入，避免API限制
python scripts/import_cases.py --source json --file batch1.json
python scripts/import_cases.py --source json --file batch2.json
```

### Embedding缓存

OpenAI Embedding有成本，建议：
- 导入时批量生成（batch_size=100）
- 避免重复导入相同案例
- 使用增量更新而非全量重建

### 检索优化

提升检索速度：
- 减少top_k数量（默认3已足够）
- 使用精确过滤条件减少检索范围
- Chroma使用HNSW索引，查询速度已优化

## 扩展功能

### 混合检索

结合关键词和向量检索：
```python
# 先向量检索获取候选
candidates = retrieve_cases(query, top_k=10)

# 再关键词过滤
filtered = [c for c in candidates if "JWT" in c['title']]
```

### 重排序

使用Cross-Encoder精排（需额外实现）：
```python
# 向量检索获取候选
candidates = retrieve_cases(query, top_k=10)

# Cross-Encoder重排序
from sentence_transformers import CrossEncoder
model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
scores = model.predict([(query, c['content']) for c in candidates])
reranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
```

### 多语言支持

中英文案例混合检索：
- OpenAI `text-embedding-3-small` 支持多语言
- 无需额外配置，自动处理

## 故障排查

### 检查清单

1. **环境检查**
   ```bash
   python scripts/check_environment.py
   ```

2. **查看collection状态**
   ```python
   import chromadb
   client = chromadb.HttpClient()
   collection = client.get_collection("cases")
   print(f"文档数: {collection.count()}")
   ```

3. **测试OpenAI连接**
   ```python
   from openai import OpenAI
   client = OpenAI()
   response = client.embeddings.create(
       model="text-embedding-3-small",
       input="test"
   )
   print(response.data[0].embedding[:5])
   ```

4. **查看导入日志**
   - 检查errors字段
   - 验证数据格式
   - 确认字段映射

### 常见问题

**Q: 为什么检索结果不准确？**
A:
- 检查查询词是否具体
- 验证分块参数是否合理
- 确认相似度阈值设置
- 检查数据质量和完整性

**Q: 如何提高检索速度？**
A:
- 减少top_k数量
- 使用精确过滤条件
- Chroma已使用HNSW索引优化

**Q: 导入数据后为什么检索不到？**
A:
- 运行环境检查确认导入成功
- 检查collection.count()
- 验证分块是否正确
- 确认embedding生成成功

**Q: 如何删除错误的案例？**
A:
```python
import chromadb
client = chromadb.HttpClient()
collection = client.get_collection("cases")
collection.delete(ids=["case_001_chunk_0", "case_001_chunk_1"])
```

## 参考资料

### 文件位置

```
skills/rag-case-retrieval/
├── SKILL.md                      # 技能主文档
├── config.json                   # 配置文件
├── scripts/
│   ├── check_environment.py      # 环境检查
│   ├── import_cases.py           # 数据导入
│   └── retrieve_cases.py         # 案例检索
├── references/
│   └── schema.md                 # 数据结构定义
└── evals/
    └── evals.json                # 测试案例
```

### Chroma文档

- 官方文档：https://docs.trychroma.com/
- API参考：https://docs.trychroma.com/api-reference
- Python SDK：https://github.com/chroma-core/chroma

### OpenAI Embedding

- 模型文档：https://platform.openai.com/docs/guides/embeddings
- 价格参考：https://openai.com/pricing
- 最佳实践：https://platform.openai.com/docs/guides/embeddings/best-practices

## 版本历史

- **v1.0 (2026-06-02)**：初始版本
  - 支持PostgreSQL/JSON/CSV数据源
  - 智能分块策略
  - OpenAI Embedding集成
  - Chroma向量检索
  - 结构化JSON输出

## 反馈与支持

如有问题或建议，请：
1. 查看本文档的故障排查部分
2. 运行环境检查脚本诊断问题
3. 查看技能目录下的schema.md了解数据结构
4. 联系技能维护者获取支持