---
name: rag-case-retrieval
description: |
  从Chroma向量数据库检索最相关的案例。当用户需要：
  - 查找相似案例或历史案例
  - 进行语义搜索
  - 从案例库中检索匹配内容
  - 进行RAG（检索增强生成）相关的查询

  使用此技能。即使没有明确提到"RAG"、"向量检索"或"案例检索"，只要语义上需要相似案例匹配就应触发。

compatibility:
  tools: [Bash, Read, Write, AskUserQuestion]
  dependencies:
    - chromadb
    - openai
    - python >= 3.8

---

# RAG案例检索技能

此技能提供完整的向量检索流程：从数据源导入案例到Chroma向量数据库，并支持语义检索返回最相关的案例。

## 前置条件

用户需要提供或系统已配置：
1. **Chroma服务地址**（默认：`http://localhost:8000`）
2. **嵌入服务**（支持本地或云端的OpenAI兼容API）
3. **案例数据源信息**（数据库连接或文件路径）
4. **Collection名称**（默认：`cases`）

### 支持的嵌入服务

此技能支持任何实现 OpenAI `/v1/embeddings` API 端点的服务，支持以下两种运行模式：

#### 模式一：本地服务模式（数据不外泄）

| 服务 | base_url | 模型示例 | 安装方式 |
|------|----------|----------|----------|
| **Ollama** (推荐) | `http://localhost:11434/v1` | `bge-small-zh-v1.5`, `nomic-embed-text`, `mxbai-embed-large` | `ollama pull bge-small-zh-v1.5` |
| **LocalAI** | `http://localhost:8080/v1` | 多种嵌入模型 | Docker部署 |
| **text-embeddings-inference** | `http://localhost:8080/v1` | Hugging Face模型 | Docker: `ghcr.io/huggingface/text-embeddings-inference` |
| **自定义本地服务** | `http://localhost:<port>/v1` | 任意兼容模型 | 自行部署 |

**隐私保证**: 本地模式下，所有文本数据仅在本地处理，不传输到外部网络。

#### 模式二：云服务模式（OpenAI兼容API）

| 服务类型 | base_url | api_key | 说明 |
|----------|----------|---------|------|
| OpenAI官方 | `https://api.openai.com/v1` | `sk-xxxxxx` | OpenAI嵌入API |
| 国内兼容服务 | `https://xxx.api.com/v1` | 对应API密钥 | 如阿里云、百度等兼容服务 |
| 自建云服务 | `https://your-server.com/v1` | 对应密钥 | 自建的服务器 |

**注意**: 云服务模式下，文本数据会发送到对应服务的服务器。

#### 配置示例

**本地 Ollama 配置（默认）**:
```json
{
  "embedding": {
    "base_url": "http://localhost:11434/v1",
    "model": "bge-small-zh-v1.5",
    "api_key": "not-required",
    "timeout": 30
  }
}
```

**本地 text-embeddings-inference 配置**:
```json
{
  "embedding": {
    "base_url": "http://localhost:8080/v1",
    "model": "BAAI/bge-small-zh-v1.5",
    "api_key": "not-required",
    "timeout": 60
  }
}
```

**OpenAI官方云服务配置**:
```json
{
  "embedding": {
    "base_url": "https://api.openai.com/v1",
    "model": "text-embedding-3-small",
    "api_key": "sk-your-openai-key",
    "timeout": 30
  }
}
```

**第三方云服务配置**:
```json
{
  "embedding": {
    "base_url": "https://api.example.com/v1",
    "model": "embedding-v1",
    "api_key": "your-api-key",
    "timeout": 30
  }
}
```

## 工作流程

### 步骤1: 环境检查与初始化

首先检查Chroma连接状态和依赖：

```python
# 使用 scripts/check_environment.py 检查环境
# 输出：连接状态、依赖状态、Collection信息
```

如果Chroma未运行或Collection不存在，引导用户初始化。

### 步骤2: 案例导入（首次使用或更新数据）

如果需要导入数据，执行 `scripts/import_cases.py`：

**输入要求**：
- 数据源类型：数据库/文件/API
- 必需字段：`id`, `title`, `content`
- 可选字段：`category`, `tags`, `created_at`, `metadata`

**处理逻辑**：
1. 从数据源读取案例
2. 分块（chunking）：大文档按段落或固定大小分块
3. 生成Embedding：使用配置的嵌入服务生成向量
4. 存储到Chroma：包含向量、原文、元数据

### 步骤3: 语义检索

用户查询后，执行 `scripts/retrieve_cases.py`：

**检索流程**：
1. 将用户查询转为向量（使用配置的嵌入服务）
2. Chroma向量相似度搜索（Top-K=3，可配置）
3. 结果重排序（按相似度得分）
4. 格式化为JSON输出

**检索参数**：
- `top_k`: 返回案例数量，默认3
- `min_similarity`: 最小相似度阈值，默认0.7
- `filters`: 元数据过滤条件（可选）
- `include_fields`: 返回字段列表

### 步骤4: 输出结构化结果

始终返回JSON格式：

```json
{
  "query": "用户查询文本",
  "retrieval_config": {
    "top_k": 3,
    "min_similarity": 0.7,
    "filters": {}
  },
  "results": [
    {
      "id": "case_001",
      "title": "案例标题",
      "content": "案例内容（或摘要）",
      "similarity_score": 0.85,
      "metadata": {
        "category": "分类",
        "tags": ["标签1", "标签2"],
        "created_at": "2024-01-01"
      },
      "chunk_index": 0
    }
  ],
  "summary": {
    "total_found": 3,
    "above_threshold": 3,
    "retrieval_time_ms": 245
  }
}
```

## 配置管理

配置存储在 `~/.claude/skills/rag-case-retrieval/config.json`：

```json
{
  "chroma": {
    "host": "http://localhost:8000",
    "collection_name": "cases"
  },
  "embedding": {
    "base_url": "http://localhost:11434/v1",
    "model": "bge-small-zh-v1.5",
    "api_key": "not-required",
    "timeout": 30,
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

### 配置说明

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `embedding.base_url` | 嵌入服务端点 | `http://localhost:11434/v1` |
| `embedding.model` | 嵌入模型名称 | `bge-small-zh-v1.5` |
| `embedding.api_key` | API密钥（本地服务通常不需要） | `not-required` |
| `embedding.timeout` | 请求超时（秒） | `30` |

首次使用时创建配置文件。

## 使用示例

**示例1: 基础检索**
```
用户: 查找关于用户认证失败的相关案例
助手: 执行检索...
[
  {
    "id": "auth_042",
    "title": "JWT令牌过期导致的认证失败",
    "similarity_score": 0.89,
    ...
  }
]
```

**示例2: 带过滤条件**
```
用户: 查找2024年的安全漏洞案例
助手: 应用时间过滤器...
filters: {"created_at": {"$gte": "2024-01-01"}}
```

**示例3: 更新案例库**
```
用户: 从新的数据库导入案例
助手: 执行导入流程...
- 读取源数据
- 生成向量
- 存储到Chroma
导入完成：150条案例已添加
```

## 错误处理

1. **Chroma连接失败**
   - 检查Docker服务状态
   - 验证端口配置
   - 提示启动命令：`docker run -p 8000:8000 chromadb/chroma`

2. **嵌入服务连接失败（本地服务）**
   - 验证嵌入服务是否运行（如 `ollama serve`）
   - 检查 `base_url` 配置是否正确
   - 确认模型已拉取（如 `ollama pull bge-small-zh-v1.5`）
   - 检查服务端口是否可访问

3. **嵌入服务连接失败（云服务）**
   - 验证 `base_url` 是否正确（确保包含 `/v1`）
   - 检查 `api_key` 是否有效
   - 确认账户配额是否充足
   - 检查网络连接是否正常

4. **模型不存在**
   - 本地服务: 使用 `ollama list` 查看可用模型
   - 云服务: 查阅服务商文档确认支持的模型名称
   - 或修改config.json中的 `embedding.model` 为可用模型

5. **向量维度不匹配**
   - 不同模型的向量维度不同（如 bge-small-zh: 512维，OpenAI: 1536维）
   - 如更换模型，需删除旧Collection并重新导入数据

6. **无匹配结果**
   - 降低相似度阈值
   - 扩大检索范围
   - 建议优化查询词

7. **导入失败**
   - 验证数据格式
   - 检查字段完整性
   - 提供数据清洗建议

## 最佳实践

1. **分块策略**
   - 按语义边界分块（段落、章节）
   - 保持上下文完整性
   - 避免过大的块（影响精度）

2. **查询优化**
   - 使用具体、描述性的查询
   - 包含关键实体和上下文
   - 可提供多个相关查询词

3. **结果使用**
   - 检查相似度得分
   - 验证案例相关性
   - 结合多个案例得出结论

4. **数据维护**
   - 定期更新案例库
   - 清理过期案例
   - 监控检索质量

## 扩展功能

- **混合检索**: 结合关键词和向量检索
- **重排序**: 使用Cross-Encoder精排
- **增量更新**: 支持增量添加新案例
- **多语言**: 支持中英文案例检索
- **版本控制**: 案例版本管理