# JFFS2 Analyzer 使用指南

静态分析 JFFS2 文件系统镜像。

## 快速使用

```bash
/jffs2-analyzer /path/to/jffs2.img
```

## 输出文件

| 文件 | 内容 |
|------|------|
| `jffs2_analysis_summary.md` | 人类可读报告 |
| `jffs2_structure.json` | 完整结构数据 |

## 分析内容

- 自动检测块大小（64KB/128KB）
- 扫描所有擦除块和节点
- 解析节点类型（DIRENT/INODE/XATTR/SUMMARY/CLEANMARKER）
- 验证 CRC 校验
- 构建目录树
- 检测异常（CRC错误、Magic无效、版本冲突）

## 异常类型

| 类型 | 严重性 | 说明 |
|------|--------|------|
| CRC错误 | HIGH | 数据损坏 |
| Magic无效 | CRITICAL | 非JFFS2节点 |
| 节点类型未知 | MEDIUM | 未识别类型 |
| 版本冲突 | MEDIUM | 重复版本号 |
| 孤儿目录项 | LOW | 引用缺失inode |

## 示例输出

```
Parsing JFFS2 image: /tmp/jffs2.img
File size: 1,048,576 bytes
Block size: 64KB
Block count: 16

Scan complete. Found 125 nodes
  Valid: 123
  Anomalies: 2
  Inodes: 42
```

## 限制

- 不解析 OOB 数据
- 不解压文件内容（只读分析）
- 需要 Python 3.x（无外部依赖）

## 与故障注入配合

```bash
# 注入故障后分析验证
/jffs2-fault-inject --image normal.jffs2 --fault hdr_crc,magic
/jffs2-analyzer corrupted.jffs2
```