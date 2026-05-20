# 跨架构 Busybox 编译指南

解决 x86_64 主机编译 ARM64/ARM32 QEMU 使用的 busybox。

## 问题现象

在 ARM64 QEMU 中使用 x86_64 busybox 会报错：
```
Failed to execute /init (error -8)
Kernel panic - not syncing: No working init found
```

**原因**: ELF架构不匹配（x86-64 binary 在 ARM64 CPU 上无法执行）

## 快速解决方案

### ARM64 Busybox

```bash
# 下载源码
wget https://busybox.net/downloads/busybox-1.36.1.tar.bz2
tar -xjf busybox-1.36.1.tar.bz2
cd busybox-1.36.1

# 配置
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- defconfig
sed -i 's/# CONFIG_STATIC is not set/CONFIG_STATIC=y/' .config
sed -i 's/CONFIG_TC=y/# CONFIG_TC is not set/' .config

# 编译
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j$(nproc)

# 验证
file busybox
# 输出: ELF 64-bit LSB executable, ARM aarch64, statically linked
```

### ARM32 Busybox

```bash
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabi- defconfig
sed -i 's/# CONFIG_STATIC is not set/CONFIG_STATIC=y/' .config
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabi- -j$(nproc)
```

## 必要 Applets

| 类别 | 命令 | 用途 |
|------|------|------|
| Shell | sh, ash | 脚本执行 |
| 基本 | cat, ls, mkdir, sleep | 文件操作 |
| 挂载 | mount, umount, mknod, dd | 文件系统 |
| 系统 | poweroff, reboot, dmesg | 控制 |
| 模块 | insmod, lsmod, rmmod | 内核模块 |

## 创建 Symlinks

```bash
for applet in sh ash cat ls mkdir mount umount insmod lsmod rmmod \
              dmesg grep sleep poweroff reboot echo dd mknod; do
    ln -sf busybox "$INITRAMFS/bin/$applet"
done
```

## 架构匹配表

| Host | QEMU | Busybox | Size |
|------|------|---------|------|
| x86_64 | x86_64 | x86_64 (native) | ~1.0M |
| x86_64 | ARM64 | ARM64 (cross) | ~969K |
| x86_64 | ARM32 | ARM32 (cross) | ~900K |

## 工具链安装

```bash
# Ubuntu/Debian
sudo apt install gcc-aarch64-linux-gnu    # ARM64
sudo apt install gcc-arm-linux-gnueabi    # ARM32
```