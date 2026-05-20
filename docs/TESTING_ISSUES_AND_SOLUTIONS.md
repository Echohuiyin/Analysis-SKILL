# JFFS2故障注入测试问题总结与解决方案

## 测试日期：2026-05-20

## 遇到的问题

### 问题1: busybox applets缺失

**问题描述**：
- QEMU测试时，init脚本执行失败
- 报错：`mknod: not found`, `losetup: not found`
- 现有busybox配置缺少必要applets

**根本原因**：
- busybox使用minimal配置，未启用全部applets
- ARM64静态busybox未包含mknod、losetup等MTD相关命令

**解决方案**：
1. 使用完整defconfig配置busybox
2. 启用静态编译(CONFIG_STATIC=y)
3. 确保包含以下applets：
   - mknod, losetup (MTD设备配置)
   - sh, ash (shell)
   - mount, umount, insmod, lsmod, rmmod (模块和挂载)
   - cat, ls, grep, echo, sleep, dmesg (基本命令)
   - poweroff, reboot (系统控制)
   - date, uname, head, tail, tr, test (辅助工具)

**修复步骤**：
```bash
# 编译完整ARM64静态busybox
cd /tmp/busybox-1.36.1
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- defconfig
sed -i 's/# CONFIG_STATIC is not set/CONFIG_STATIC=y/' .config
# 禁用有问题的TC模块
sed -i 's/CONFIG_TC=y/# CONFIG_TC is not set/' .config
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j$(nproc)
```

### 问题2: block2mtd需要loop设备支持

**问题描述**：
- losetup设置loop设备失败：`No such device or address`
- 无法将JFFS2镜像文件映射为MTD设备

**根本原因**：
- QEMU virt机器的内核可能缺少loop设备支持
- block2mtd参数格式在不同内核版本有变化
- 需要复杂的设备节点创建流程

**解决方案**：
使用mtdram替代block2mtd：
1. 启用内核配置：`CONFIG_MTD_MTDRAM=m`
2. 编译mtdram.ko模块
3. 直接在RAM中创建MTD设备，无需loop
4. 使用dd将镜像写入mtdblock设备

**修复步骤**：
```bash
# 启用mtdram
scripts/config --file .config --set-val CONFIG_MTD_MTDRAM m
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- modules

# 使用方式（在initramfs中）
insmod /modules/mtdram.ko total_size=16384 erase_size=64
dd if=/jffs2.img of=/dev/mtdblock0 bs=64K
mount -t jffs2 /dev/mtdblock0 /mnt/jffs2
```

### 问题3: TC模块编译失败

**问题描述**：
- busybox编译报错：`networking/tc.c` struct tc_cbq_wrropt未定义

**根本原因**：
- 内核头文件版本与busybox不兼容
- TC流量控制模块依赖复杂的内核网络结构

**解决方案**：
禁用TC模块：
```bash
sed -i 's/CONFIG_TC=y/# CONFIG_TC is not set/' .config
```

### 问题4: 内核模块签名验证失败

**问题描述**：
- 模块加载警告：`module verification failed: signature and/or required key missing - tainting kernel`

**根本原因**：
- 编译的模块没有签名
- 内核启用了模块签名验证

**影响**：
- 仅产生警告，不影响功能
- 内核被标记为tainted

**解决方案**：
- 生产环境应正确签名模块
- 测试环境可忽略此警告

## 最佳实践总结

### 推荐的JFFS2测试流程

```bash
# 1. 编译内核（启用mtdram）
/kernel-build JFFS2_FS MTDRAM --arch arm64 --cross

# 2. 编译完整busybox
cd /tmp/busybox-1.36.1
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- defconfig
sed -i 's/# CONFIG_STATIC is not set/CONFIG_STATIC=y/' .config
sed -i 's/CONFIG_TC=y/# CONFIG_TC is not set/' .config
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j$(nproc)

# 3. 创建initramfs（使用mtdram方式）
# 参见 jffs2-mount skill

# 4. 创建故障注入镜像
/jffs2-fault-inject --image normal.jffs2 --fault hdr_crc,node_crc,magic

# 5. 运行QEMU测试
/jffs2-mount --kernel Image --image corrupted.jffs2 --arch arm64
```

### 推荐的initramfs创建脚本

```bash
#!/bin/sh
# create_initramfs_mtdram.sh

BUSYBOX="/tmp/busybox-1.36.1/busybox"
INITRAMFS_DIR="/tmp/initramfs_mtdram"

mkdir -p "$INITRAMFS_DIR"/{bin,dev,proc,sys,etc,mnt,modules}

# 安装完整busybox
cp "$BUSYBOX" "$INITRAMFS_DIR/bin/busybox"
cd "$INITRAMFS_DIR/bin"
for applet in sh ash cat ls mkdir mount umount insmod lsmod rmmod dmesg \
              grep sed awk sleep mknod poweroff reboot echo uname date \
              head tail tr test losetup dd; do
    ln -sf busybox "$applet"
done

# 复制模块
cp /path/to/kernel/drivers/mtd/mtd.ko "$INITRAMFS_DIR/modules/"
cp /path/to/kernel/drivers/mtd/mtd_blkdevs.ko "$INITRAMFS_DIR/modules/"
cp /path/to/kernel/drivers/mtd/mtdblock.ko "$INITRAMFS_DIR/modules/"
cp /path/to/kernel/drivers/mtd/devices/mtdram.ko "$INITRAMFS_DIR/modules/"
cp /path/to/kernel/fs/jffs2/jffs2.ko "$INITRAMFS_DIR/modules/"

# 创建init
cat > "$INITRAMFS_DIR/init" << 'INIT_EOF'
#!/bin/sh
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev

insmod /modules/mtd.ko
insmod /modules/mtd_blkdevs.ko
insmod /modules/mtdblock.ko
insmod /modules/mtdram.ko total_size=16384 erase_size=64
insmod /modules/jffs2.ko

dd if=/jffs2.img of=/dev/mtdblock0 bs=64K
mount -t jffs2 /dev/mtdblock0 /mnt/jffs2
ls -la /mnt/jffs2
dmesg | grep JFFS2_FAULT

poweroff -f
INIT_EOF

chmod +x "$INITRAMFS_DIR/init"

# 打包
cd "$INITRAMFS_DIR"
find . | cpio -o -H newc | gzip > initramfs.cpio.gz
```

## 更新的Skill内容

### jffs2-mount skill更新

添加mtdram方式的设备配置：
- 新增mtdram模块加载
- 移除对loop设备的依赖
- 简化MTD设备创建流程

### qemu-test skill更新

更新busybox编译说明：
- 使用defconfig而非minimal配置
- 强制启用静态链接
- 禁用TC模块避免编译错误
- 明确applets要求列表

### 新增jffs2-fault-inject skill

故障注入功能：
- 支持多种故障类型注入
- 生成故障报告JSON
- 与jffs2-analyzer配合验证

## 参考资料

- busybox配置：`/tmp/busybox-1.36.1/.config`
- 测试日志：`/home/liumingrui/code/OLK-6.6/jffs2_fault_test_output/qemu_test/`
- 最终报告：`FINAL_REPORT.md`