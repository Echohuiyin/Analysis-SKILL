# JFFS2 Mount Skill (v1.0)

在QEMU虚拟机中挂载和测试JFFS2文件系统镜像。**专注于JFFS2挂载操作，不涉及内核编译。**

## 技能定位

本技能与其他技能完全解耦，不依赖：
- **kernel-build**: 内核编译（独立操作）
- **qemu-test**: QEMU启动（独立操作）
- **jffs2-analyzer**: 静态镜像分析（独立操作）

本技能专注于：**创建JFFS2镜像并在QEMU中挂载验证**

## 适用场景

触发此技能当用户要求：
- 在QEMU中挂载JFFS2文件系统
- 创建JFFS2测试镜像并挂载
- 测试JFFS2文件系统功能
- 验证JFFS2模块加载和挂载

**不适用于**：内核编译（用kernel-build）、静态镜像分析（用jffs2-analyzer）、纯QEMU启动测试（用qemu-test）

## 快速使用

```
/jffs2-mount [options]

Options:
  --kernel <path>        内核镜像路径（必须，不自动编译）
  --image <path>         JFFS2镜像文件路径（不指定则自动创建）
  --size <MB>            镜像大小（默认 16MB）
  --arch <arch>          架构：arm64, arm32, x86_64（默认 arm64）
  --content <dir>        源内容目录（创建镜像时使用）
  --mount-test           执行完整挂载测试流程
  --output <dir>         输出目录
```

示例：
- `/jffs2-mount --kernel arch/arm64/boot/Image --mount-test` - 使用指定内核执行完整挂载测试
- `/jffs2-mount --kernel Image --image test.jffs2 --arch arm64` - 挂载指定JFFS2镜像
- `/jffs2-mount --kernel bzImage --size 32 --content ./data` - 创建32MB镜像并测试

## 工作流程

### Step 1: 环境验证

**验证必要条件，不执行编译：**

```bash
# 1. 检查内核镜像存在性（用户提供或已编译）
if [ ! -f "$KERNEL_IMAGE" ]; then
    echo "ERROR: Kernel image not found: $KERNEL_IMAGE"
    echo "Solutions:"
    echo "  1. Use /kernel-build to compile kernel first"
    echo "  2. Provide kernel path: --kernel /path/to/Image"
    exit 1
fi

# 2. 检查架构匹配
file "$KERNEL_IMAGE" | grep -q "ARM aarch64" || {
    echo "ERROR: Kernel architecture mismatch"
    exit 1
}

# 3. 检查工具
which mkfs.jffs2 || {
    echo "WARN: mkfs.jffs2 not found, using dd to create mock image"
}
```

### Step 2: 创建JFFS2镜像（可选）

**如果用户未提供镜像，自动创建：**

```bash
# 创建源目录
mkdir -p /tmp/jffs2_source
echo "Test content" > /tmp/jffs2_source/test.txt
mkdir -p /tmp/jffs2_source/subdir

# 创建JFFS2镜像
if [ "$IMAGE_SIZE" ]; then
    SIZE_BYTES=$((IMAGE_SIZE * 1024 * 1024))
else
    SIZE_BYTES=$((16 * 1024 * 1024))  # Default 16MB
fi

# 方法1: 使用mkfs.jffs2（推荐）
if command -v mkfs.jffs2 >/dev/null; then
    mkfs.jffs2 -r /tmp/jffs2_source -o "$OUTPUT_DIR/jffs2.img" \
               -e 0x10000 -p --pad="$SIZE_BYTES"
else
    # 方法2: 创建空白镜像（仅测试挂载能力）
    dd if=/dev/zero of="$OUTPUT_DIR/jffs2.img" bs=1M count=$IMAGE_SIZE
fi
```

### Step 3: MTD设备配置（关键步骤）

**JFFS2挂载的核心依赖**：JFFS2需要MTD设备作为底层存储。

**MTD设备创建方法**：

| 方法 | 适用场景 | 命令 |
|------|---------|------|
| **block2mtd** | 将块设备转换为MTD | `modprobe block2mtd block_device erase_size` |
| **mtdram** | 虚拟RAM MTD设备 | `modprobe mtdram total_size erase_size` |
| **mtdblock** | MTD块设备模拟 | 内置模块，创建/dev/mtdblock* |

**完整MTD配置流程**：

```bash
# 在initramfs中的MTD设备配置脚本
cat > "$INITRAMFS_DIR/setup_mtd.sh" << 'EOF'
#!/bin/sh

echo "=== MTD Device Setup ==="

# Method 1: block2mtd (preferred for JFFS2 image files)
# Requires: loop device + block2mtd module
if [ -f /jffs2.img ] && [ -e /dev/loop0 ]; then
    echo "Setting up block2mtd device..."
    
    # Load block2mtd module
    insmod /modules/block2mtd.ko || {
        echo "Failed to load block2mtd"
        exit 1
    }
    
    # Setup loop device for JFFS2 image
    losetup /dev/loop0 /jffs2.img
    
    # Register block2mtd device
    # erase_size = 64KB (0x10000) typical for JFFS2
    echo "/dev/loop0,0x10000" > /sys/module/block2mtd/parameters/block2mtd
    
    # Wait for MTD device creation
    sleep 1
    
    # Check MTD device
    cat /proc/mtd
    
    echo "✓ block2mtd device created"
fi

# Method 2: mtdram (virtual RAM-based MTD)
# Useful for testing without real storage
if [ ! -e /dev/mtd0 ]; then
    echo "Setting up mtdram device..."
    
    insmod /modules/mtdram.ko total_size=16384 erase_size=64 || {
        echo "Failed to load mtdram"
    }
    
    sleep 1
    cat /proc/mtd
fi

# Verify MTD device exists
if [ -e /dev/mtd0 ] || [ -e /dev/mtdblock0 ]; then
    echo "✓ MTD device ready"
else
    echo "✗ No MTD device available"
    echo "Cannot mount JFFS2 without MTD"
    exit 1
fi
EOF
```

**MTD设备文件列表**：
```
/dev/mtd0       # MTD字符设备（raw access）
/dev/mtd0ro     # MTD只读字符设备
/dev/mtdblock0  # MTD块设备（block access）
```

**挂载JFFS2的两种方式**：

```bash
# 方式1: 挂载MTD块设备
mount -t jffs2 /dev/mtdblock0 /mnt/jffs2

# 方式2: 通过MTD字符设备挂载
mount -t jffs2 mtd0 /mnt/jffs2
```

### Step 4: 完整挂载测试脚本

**关键经验：模块加载 ≠ 功能可用，需配套MTD设备配置**

```bash
# 完整的JFFS2挂载测试脚本
cat > "$INITRAMFS_DIR/jffs2_mount_test.sh" << 'EOF'
#!/bin/sh

echo "=== JFFS2 Complete Mount Test ==="
echo "Date: $(date)"
echo "Kernel: $(uname -r)"

# Step 1: Load base modules
echo "[1/6] Loading MTD/JFFS2 modules..."
insmod /modules/mtd.ko          && echo "  ✓ mtd.ko"       || echo "  ✗ mtd.ko"
insmod /modules/mtd_blkdevs.ko  && echo "  ✓ mtd_blkdevs"  || echo "  ✗ mtd_blkdevs"
insmod /modules/mtdblock.ko     && echo "  ✓ mtdblock"     || echo "  ✗ mtdblock"
insmod /modules/block2mtd.ko    && echo "  ✓ block2mtd"    || echo "  ✗ block2mtd"
insmod /modules/jffs2.ko        && echo "  ✓ jffs2.ko"     || echo "  ✗ jffs2.ko"

lsmod | grep -E "mtd|jffs2"

# Step 2: Setup MTD device (CRITICAL for JFFS2)
echo "[2/6] Setting up MTD device..."
if [ -f /jffs2.img ]; then
    # Create loop device
    losetup /dev/loop0 /jffs2.img && echo "  ✓ Loop device: /dev/loop0"
    
    # Register block2mtd
    # Note: block2mtd parameter format varies by kernel version
    # Newer kernels: use /sys/class/block2mtd/
    # Older kernels: use direct device registration
    
    if [ -d /sys/class/block2mtd ]; then
        echo "/dev/loop0" > /sys/class/block2mtd/register
    else
        echo "/dev/loop0,65536" > /sys/module/block2mtd/parameters/block2mtd_devices
    fi
    
    sleep 1
fi

# Step 3: Check MTD device status
echo "[3/6] Verifying MTD device..."
cat /proc/mtd
ls -la /dev/mtd* /dev/mtdblock*

# Step 4: Check filesystem registration
echo "[4/6] Checking JFFS2 registration..."
cat /proc/filesystems | grep jffs2 && echo "  ✓ JFFS2 registered" || echo "  ✗ JFFS2 not registered"

# Step 5: Attempt mount
echo "[5/6] Mounting JFFS2..."
mkdir -p /mnt/jffs2

if [ -e /dev/mtdblock0 ]; then
    mount -t jffs2 /dev/mtdblock0 /mnt/jffs2 && \
        echo "  ✓ JFFS2 mounted on /mnt/jffs2" || \
        echo "  ✗ Mount failed"
elif [ -e /dev/mtd0 ]; then
    mount -t jffs2 mtd0 /mnt/jffs2 && \
        echo "  ✓ JFFS2 mounted via mtd0" || \
        echo "  ✗ Mount failed"
else
    echo "  ✗ No MTD device available for mount"
fi

# Step 6: Verify mount success
echo "[6/6] Verification..."
mount | grep jffs2
ls -la /mnt/jffs2/

echo ""
echo "=== Test Complete ==="
EOF
chmod +x "$INITRAMFS_DIR/jffs2_mount_test.sh"
```

**关键经验总结**：

| 经验 | 问题 | 解决方案 |
|------|------|---------|
| 架构匹配 | x86 busybox在ARM QEMU失败 | 交叉编译目标架构busybox |
| 模块版本 | 内核模块版本不匹配 | 同一次编译会话构建内核+模块 |
| MTD依赖 | JFFS2需要MTD设备 | 配置block2mtd或mtdram |
| 命令缺失 | 脚本命令not found | 启用完整busybox applets |
| 挂载失败 | 无MTD设备可挂载 | 先setup_mtd，再mount |

### Step 4: 创建ARM64 initramfs

**创建包含JFFS2测试功能的initramfs：**

```bash
# 使用预编译的ARM64 busybox（或自动下载）
BUSYBOX_ARM64="/tmp/busybox_arm64"

# 创建目录结构
INITRAMFS_DIR="/tmp/initramfs_jffs2"
mkdir -p "$INITRAMFS_DIR"/{bin,dev,proc,sys,etc,lib,mnt,modules}

# 安装busybox
cp "$BUSYBOX_ARM64" "$INITRAMFS_DIR/bin/busybox"
for cmd in sh cat ls mkdir mount umount insmod lsmod dmesg; do
    ln -sf busybox "$INITRAMFS_DIR/bin/$cmd"
done

# 创建mount测试脚本
cat > "$INITRAMFS_DIR/mount_test.sh" << 'EOF'
#!/bin/sh
echo "=== JFFS2 Mount Test ==="

# Load modules
insmod /modules/mtd.ko
insmod /modules/mtdblock.ko
insmod /modules/jffs2.ko

# Setup MTD device
# Create block2mtd mapping (if block device available)
if [ -f /jffs2.img ]; then
    # Use losetup to create loop device
    # losetup /dev/loop0 /jffs2.img
    # block2mtd /dev/loop0 0x10000
    echo "JFFS2 image ready"
fi

# Mount JFFS2
mount -t jffs2 /dev/mtdblock0 /mnt/jffs2 && \
    echo "✓ JFFS2 mounted successfully" || \
    echo "✗ Mount failed"

ls -la /mnt/jffs2
EOF

# 创建init脚本
cat > "$INITRAMFS_DIR/init" << 'EOF'
#!/bin/sh
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev

sh /mount_test.sh
dmesg | grep -i jffs2

poweroff -f
EOF

# 复制必要文件
cp "$JFFS2_IMAGE" "$INITRAMFS_DIR/jffs2.img"
cp fs/jffs2/jffs2.ko "$INITRAMFS_DIR/modules/"
cp drivers/mtd/*.ko "$INITRAMFS_DIR/modules/"

# 创建cpio.gz
cd "$INITRAMFS_DIR"
find . | cpio -o -H newc | gzip > "$OUTPUT_DIR/initramfs_jffs2.cpio.gz"
```

### Step 4: 启动QEMU挂载测试

**执行QEMU测试：**

```bash
# 根据架构选择QEMU命令
QEMU_CMD="qemu-system-aarch64"
KERNEL_CMD="console=ttyAMA0 root=/dev/ram rw"

# 启动QEMU
timeout 60 $QEMU_CMD \
    -M virt \
    -cpu cortex-a57 \
    -smp 2 \
    -m 512M \
    -nographic \
    -kernel "$KERNEL_IMAGE" \
    -initrd "$INITRAMFS" \
    -append "$KERNEL_CMD" \
    2>&1 | tee "$OUTPUT_DIR/mount_test.log"
```

### Step 5: 输出结果

**保存所有测试产物：**

```
outputs/
├── jffs2.img             # JFFS2镜像文件
├── initramfs_jffs2.cpio.gz # initramfs
├── modules/*.ko          # 内核模块
├── mount_test.log        # QEMU测试日志
└── summary.txt           # 测试摘要
```

## 输出组织

**强制输出结构：**

```bash
OUTPUT_DIR="${OUTPUT_DIR:-jffs2_mount_$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$OUTPUT_DIR/modules"
mkdir -p "$OUTPUT_DIR/logs"

# 保存镜像
[ -f "$JFFS2_IMAGE" ] && cp "$JFFS2_IMAGE" "$OUTPUT_DIR/jffs2.img"

# 保存initramfs
cp "$INITRAMFS_CPIO" "$OUTPUT_DIR/initramfs_jffs2.cpio.gz"

# 保存日志
cp "$QEMU_LOG" "$OUTPUT_DIR/mount_test.log"

# 生成摘要
cat > "$OUTPUT_DIR/summary.txt" << EOF
JFFS2 Mount Test Summary
========================
Date: $(date)
Kernel: $KERNEL_IMAGE
Image: $JFFS2_IMAGE ($(ls -lh $JFFS2_IMAGE))
Mount result: $MOUNT_STATUS
EOF
```

## 依赖处理

**本技能不编译内核，需要用户提供：**

- 已编译的内核镜像
- 或使用kernel-build技能先编译

**模块依赖处理：**

- 需要JFFS2模块：fs/jffs2/jffs2.ko
- 需要MTD模块：drivers/mtd/*.ko
- 如模块不存在，提示用户编译

## 错误处理

### 内核未提供
```
ERROR: Kernel image required but not found

Solutions:
1. Compile kernel: /kernel-build JFFS2_FS --arch arm64
2. Provide existing kernel: --kernel /path/to/Image
```

### 模块未编译
```
ERROR: JFFS2 modules not found in kernel tree

Check: ls fs/jffs2/*.ko
Solution: make ARCH=arm64 modules
```

### 挂载失败
```
Mount test failed. Check logs:
- mount_test.log for QEMU output
- dmesg for kernel messages

Common causes:
- JFFS2 image corruption
- Module load failure
- MTD device not configured
```

## 与其他技能的关系

| 技能 | 功能 | 关系 |
|------|------|------|
| kernel-build | 编译内核 | **前置依赖** - 用户需先编译内核 |
| qemu-test | 启动QEMU | **独立** - 本技能自带QEMU启动逻辑 |
| jffs2-analyzer | 静态分析镜像 | **互补** - 分析后可挂载验证 |

**完全解耦设计：**
- 不调用其他技能
- 不依赖其他技能的输出
- 独立的initramfs创建逻辑
- 独立的QEMU启动逻辑
- 独立的测试脚本

## 实现脚本

scripts目录包含：
- **create_jffs2_image.sh**: 创建JFFS2镜像
- **create_initramfs.sh**: 创建ARM64 initramfs（含busybox）
- **mount_test.sh**: 挂载测试脚本
- **run_qemu.sh**: QEMU启动脚本

## 使用示例

### 示例1：完整挂载测试流程

```
/jffs2-mount --kernel arch/arm64/boot/Image --mount-test
```

输出：
```
✓ Environment verified
  Kernel: arch/arm64/boot/Image (37M ARM64)
  Architecture: aarch64

✓ Step 1: Creating JFFS2 test image
  Source: /tmp/jffs2_source (created)
  Image: outputs/jffs2.img (16M)
  
✓ Step 2: Creating ARM64 initramfs
  Busybox: ARM64 static linked (1.1M)
  Modules: jffs2.ko, mtd.ko, mtdblock.ko
  
✓ Step 3: Running QEMU mount test
  QEMU: qemu-system-aarch64 (virt machine)
  Timeout: 60 seconds
  
✓ Mount test completed
  Result: JFFS2 mounted successfully
  Files visible: /mnt/jffs2/test.txt
```

### 示例2：使用现有镜像

```
/jffs2-mount --kernel Image --image custom.jffs2 --arch arm64
```

### 示例3：自定义内容镜像

```
/jffs2-mount --kernel bzImage --size 32 --content ./my_data
```