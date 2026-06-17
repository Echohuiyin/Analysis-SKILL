# QEMU Vmcore 生成与分析指南

## 概述

本指南说明如何通过 QEMU 生成可被 crash 工具完整分析的 vmcore 文件。

## 前置条件

### 1. 内核配置

必需启用以下配置：

```bash
# fw_cfg/vmcoreinfo 支持（用于 QEMU 传递内核信息）
CONFIG_FW_CFG_SYSFS=y
CONFIG_FW_CFG_SYSFS_CMDLINE=y

# 调试符号
CONFIG_DEBUG_INFO_DWARF4=y

# Crash 核心
CONFIG_CRASH_CORE=y
CONFIG_PANIC_ON_OOPS=y
```

使用 kernel-build skill 时添加参数：

```bash
/kernel-build FW_CFG_SYSFS FW_CFG_SYSFS_CMDLINE DEBUG_INFO_DWARF4 PANIC_ON_OOPS CRASH_CORE --arch x86_64
```

### 2. Crash 工具版本

**重要：** 需要使用 crash 9.0.2+ 版本（旧版 8.0.4 在分析 QEMU vmcore 时会 segfault）

编译最新版本：

```bash
git clone git@github.com:crash-utility/crash.git ~/crash
cd ~/crash
sudo apt install -y libgmp-dev libmpfr-dev texinfo
make -j8
```

配置 vmcore-analyzer skill 使用新版本：

```bash
# .env 文件
CRASH_BINARY=/home/liumingrui/crash/crash
```

## QEMU 配置

### 关键参数

```bash
qemu-system-x86_64 \
    -M q35,dump-guest-core=on \      # q35 机器类型，启用内存转储
    -device vmcoreinfo \              # 关键：vmcoreinfo 设备
    -smp 2 \
    -m 512M \
    -nographic \
    -kernel <kernel_image> \
    -initrd <initramfs> \
    -append "console=ttyS0 panic=10 oops=panic" \
    -monitor unix:<socket>,server,nowait
```

### 参数说明

| 参数 | 作用 |
|------|------|
| `-M q35` | 正确的 x86_64 机器类型（避免 32 位 ELF 格式） |
| `-device vmcoreinfo` | 启用 NT_VMCOREINFO ELF note（crash 分析必需） |
| `dump-guest-core=on` | 允许内存转储 |
| `panic=10` | 崩溃后延迟 10 秒（给予转储时间） |
| `oops=panic` | Oops 时触发 panic |

## Vmcore 捕获流程

### 1. 创建 initramfs

```bash
# 使用 qemu-test skill
/qemu-test --create-initramfs \
    --arch x86_64 \
    --modules <test_module_path> \
    --test-script <test_script>
```

### 2. 启动 QEMU 并捕获

```bash
# 启动 QEMU
qemu-system-x86_64 \
    -M q35,dump-guest-core=on \
    -device vmcoreinfo \
    -kernel <kernel> \
    -initrd <initramfs> \
    -monitor unix:/tmp/qemu.sock,server,nowait \
    ...

# 崩溃后，通过 monitor 捕获
echo "dump-guest-memory /tmp/vmcore.elf" | socat - UNIX-CONNECT:/tmp/qemu.sock
```

### 3. 使用自动化脚本

```bash
bash test_outputs/run_vmcoreinfo_test.sh \
    <test_name> \
    <kernel_image> \
    <initramfs> \
    [timeout]
```

## Crash 分析验证

```bash
# 使用新编译的 crash
~/crash/crash vmlinux vmcore.elf

# 验证命令
crash> sys      # 系统信息
crash> bt       # 调用栈（完整模式）
crash> ps       # 进程列表
crash> log      # 内核日志
crash> mod      # 模块信息
```

## 成功标志

```
      KERNEL: vmlinux  [TAINTED]
    DUMPFILE: vmcore.elf
        CPUS: 2
      MEMORY: 511.5 MB
       PANIC: "Kernel panic - not syncing: Fatal exception"
         PID: <pid>
     COMMAND: "insmod"  # 或其他崩溃进程

bt 输出包含完整调用栈，如：
 #4 asm_exc_page_fault
    [exception RIP: crash_nullptr_init+51]
```

## 与旧版本对比

| 版本 | QEMU vmcore 分析 | 原因 |
|------|------------------|------|
| crash 8.0.4 | ✗ Segfault | x86_64 ELF vmcore 处理缺陷 |
| crash 9.0.2++ | ✓ 正常 | 修复了 bt 命令和 panic task 确定 |

## 已知限制

1. **模块符号** - crash 使用 vmlinux，不自动包含模块符号
   - 解决：使用 `mod -S` 命令加载模块符号

2. **KASLR** - vmcoreinfo 包含 KERNELOFFSET 信息，crash 自动处理

3. **Offline CPU** - 可能显示部分 CPU offline，不影响分析

## 相关文件

```
test_outputs/
├── run_vmcoreinfo_test.sh    # 推荐：包含 vmcoreinfo 设备
├── run_x86_vmcore_test.sh    # 旧版本（可参考）
└── vmcoreinfo_test/
    ├── vmcore.elf            # 生成的 vmcore
    └── boot.log              # 崩溃日志
```

## 参考

- QEMU vmcoreinfo: `/usr/share/doc/qemu-system-data/specs/vmcoreinfo.rst`
- Crash GitHub: https://github.com/crash-utility/crash
- Kernel fw_cfg: `drivers/firmware/qemu_fw_cfg.c`