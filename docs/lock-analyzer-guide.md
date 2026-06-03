# Lock Analyzer Skill 使用指导

## 概述

Lock Analyzer 是一个用于在 crash 工具中分析 Linux 内核锁的技能，帮助定位锁持有者和诊断死锁问题。

### 支持的锁类型

| 锁类型 | 内核结构 | 持有者追踪 | 适用场景 |
|--------|----------|-----------|----------|
| **Mutex** | `struct mutex` | ✅ 有 owner 字段 | 长临界区，可睡眠 |
| **Spinlock** | `raw_spinlock_t` | ❌ 无显式 owner | 短临界区，中断处理 |
| **Semaphore** | `struct semaphore` | ❌ 计数信号量 | 资源计数，同步 |

## 快速使用

### 命令格式

```bash
/lock-analyzer <锁地址> [--type mutex|spinlock|semaphore]
/lock-analyzer --deadlock-check
```

### 示例

```bash
# 分析 mutex 持有者
/lock-analyzer 0xffffffc00012345 --type mutex

# 分析 spinlock 竞争
/lock-analyzer 0xffffffc00012345 --type spinlock

# 死锁检测扫描
/lock-analyzer --deadlock-check
```

## 核心分析命令

### Mutex 分析

```bash
# 1. 查看 mutex 结构
crash> struct mutex 0xffffffc00012345

# 2. 获取持有者
crash> struct mutex.owner 0xffffffc00012345

# 3. 获取进程信息
crash> struct task_struct.pid,comm,state <owner_addr>

# 4. 获取堆栈
crash> bt <pid>

# 5. 查看等待列表
crash> struct mutex.wait_list 0xffffffc00012345
```

**注意**: owner 字段低 3 位是标志位，需要 `& ~0x7` 清除。

### Spinlock 分析

Spinlock 没有显式 owner，需要间接分析：

```bash
# 1. 检查 ticket lock 状态
crash> struct arch_spinlock_t.tickets <addr>
# head == tail: 未锁定
# tail > head: 已锁定，差值 = 等待者数量

# 2. 搜索 spin_lock 调用
crash> foreach bt | grep -B5 -A5 "spin_lock"

# 3. 检查每个 CPU 的当前进程
crash> struct cpu_rq
crash> set -c <cpu>
crash> bt
```

### Semaphore 分析

```bash
# 1. 查看计数
crash> struct semaphore.count <addr>
# count = 0: 已锁定
# count > 0: 可用

# 2. 查看等待者
crash> struct semaphore.sleepers <addr>
crash> struct semaphore.wait <addr>
```

### 死锁检测

```bash
# 1. 查找 D 状态进程
crash> ps -u | grep UN

# 2. 获取堆栈
crash> bt <pid>

# 3. 分析阻塞链
crash> struct task_struct.blocked_on <task_addr>
crash> struct mutex.owner <mutex_addr>

# 4. 检查 PI 链
crash> struct task_struct.pi_lockers <task_addr>

# 5. 构建依赖图
# A -> L1 -> B -> L2 -> C -> L3 -> A (循环)
```

## 辅助脚本

技能包含以下辅助脚本：

### analyze_mutex.sh

```bash
# 使用方法
./scripts/analyze_mutex.sh <mutex-address>

# 输出 crash 命令序列
# 生成 owner_info.txt, waiters.txt, stack_traces.txt
```

### find_lock_owner.sh

```bash
# 使用方法
./scripts/find_lock_owner.sh <lock-address> <lock-type>

# lock-type: mutex, spinlock, semaphore, auto
```

### deadlock_scan.sh

```bash
# 执行死锁扫描
./scripts/deadlock_scan.sh

# 生成 deadlock_analysis.txt 和 deadlock_visualizer.py
```

### lock_analyzer.py

```bash
# 解析 crash 输出生成报告
python scripts/lock_analyzer.py --input crash_output.txt --output report.md
```

## 内核版本差异

不同内核版本的 mutex 结构不同：

### Pre-4.8 内核

```c
struct mutex {
    atomic_t count;
    spinlock_t wait_lock;
    struct list_head wait_list;
    // 无 owner 字段
};
```

### 4.8+ 内核 (带 optimistic spinning)

```c
struct mutex {
    atomic_long_t owner;    // 有 owner 字段
    atomic_t count;
    spinlock_t wait_lock;
    struct list_head wait_list;
    struct optimistic_spin_queue osq;
};
```

## 常见场景分析

### 场景 1: 找 mutex 持有者

**问题**: 进程卡在 mutex_lock，找出持有者

**步骤**:
1. `ps -u` 找 D 状态进程
2. `bt <pid>` 确认在 mutex_lock
3. `struct mutex.owner <addr>` 获取持有者
4. `struct task_struct.pid,comm <owner>` 确认持有者身份
5. `bt <owner_pid>` 分析持有者堆栈

### 场景 2: Spinlock 竞争诊断

**问题**: CPU 占用高，怀疑 spinlock 竞争

**步骤**:
1. `ps | grep RU` 找高 CPU 进程
2. `foreach bt | grep spin_lock` 找 spinlock 相关调用
3. `struct arch_spinlock_t.tickets <addr>` 检查锁状态
4. `bt -a` 检查所有 CPU 堆栈
5. 分析等待者数量和持有者线索

### 场景 3: 死锁诊断

**问题**: 多进程 D 状态，怀疑死锁

**步骤**:
1. `ps -u` 列出所有 D 状态进程
2. 对每个进程 `bt <pid>` 分析等待链
3. `struct task_struct.blocked_on` 获取等待的锁
4. `struct mutex.owner` 追踪持有者
5. 绘制依赖图，检测循环

## Mutex Flags 解码

owner 字段的低 3 位是标志：

| Flag | 值 | 含义 |
|------|-----|------|
| `MUTEX_FLAG_WAITERS` | 0x1 | 有等待者 |
| `MUTEX_FLAG_HANDOFF` | 0x2 | 锁交接进行中 |
| `MUTEX_FLAG_MCS` | 0x4 | MCS 锁使用中 |

获取真实 task_struct 指针：
```
owner_task = owner_field & ~0x7
```

## 输出文件结构

分析完成后生成的文件：

```
lock_analysis/
├── owner_info.txt      # 锁持有者详情
├── waiters.txt         # 等待任务列表
├── stack_traces.txt    # 堆栈跟踪
├── deadlock_chain.txt  # 死锁链（如有）
└── summary.md          # 分析总结报告
```

## 报告模板

生成的报告包含：

1. **锁信息**: 地址、类型、状态
2. **持有者**: PID、进程名、状态
3. **堆栈**: 持有者的函数调用链
4. **等待者**: 等待该锁的任务列表
5. **分析建议**: 问题诊断和解决建议

## 常用命令速查表

| 命令 | 用途 |
|------|------|
| `struct mutex <addr>` | 查看 mutex 结构 |
| `struct mutex.owner <addr>` | 获取 mutex 持有者 |
| `struct mutex.count <addr>` | 检查锁状态 (0=locked) |
| `struct task_struct <addr>` | 查看任务信息 |
| `bt <pid>` | 进程堆栈跟踪 |
| `bt -a` | 所有 CPU 堆栈 |
| `ps -u` | D 状态进程列表 |
| `foreach bt \| grep` | 批量搜索堆栈 |
| `struct arch_spinlock_t.tickets` | Spinlock ticket 状态 |
| `struct semaphore.count` | Semaphore 计数 |
| `struct task_struct.blocked_on` | 等待的锁 |
| `struct task_struct.pi_lockers` | PI 链 |

## 与其他技能配合

- `/kernel`: 获取内核源码上下文
- `/kdebug`: 高级内核调试
- `/qemu-test`: 测试带锁修复的内核

## 安装和配置

技能文件位于:
```
skills/lock-analyzer/
├── SKILL.md            # 主技能文档
└── scripts/
    ├── analyze_mutex.sh
    ├── find_lock_owner.sh
    ├── deadlock_scan.sh
    └── lock_analyzer.py
```

安装到 Claude Code:
```bash
# 复制到 ~/.claude/skills/
cp -r skills/lock-analyzer ~/.claude/skills/
```

## 注意事项

1. **检查内核版本**: 不同版本锁结构有差异
2. **清除 owner flags**: mutex.owner 低 3 位需清除
3. **Spinlock 无显式 owner**: 需通过堆栈推断
4. **Semaphore 不追踪 owner**: 只能分析等待队列
5. **优先级继承**: 检查 pi_lockers 检测 PI 死锁