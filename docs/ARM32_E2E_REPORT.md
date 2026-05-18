# ARM32 端到端验证报告

## 验证概览

**日期**: 2026-05-18
**架构**: ARM32 (armv7l)
**内核版本**: 6.6.0-36583-g6cf1cf61b43c-dirty
**验证状态**: ✅ 成功

## 验证过程

### 1. Kernel编译

- **配置**: multi_v7_defconfig + CONFIG_JFFS2_FS=m + CONFIG_MTD=y
- **工具链**: arm-linux-gnueabi-gcc 13.3.0
- **输出**: arch/arm/boot/zImage (11M)
- **版本**: 6.6.0-36583-g6cf1cf61b43c-dirty #13 SMP

### 2. 模块编译

- **jffs2.ko**: fs/jffs2/jffs2.ko (149K)
- **MTD**: Built-in (CONFIG_MTD=y)
- **版本**: vermagic: 6.6.0-36583-g6cf1cf61b43c-dirty ARMv7

### 3. ARM32 Busybox编译

- **源码**: busybox-1.36.1
- **配置**: defconfig + CONFIG_STATIC=y
- **输出**: busybox (2.1M, ARM EABI5, statically linked)

### 4. QEMU端到端测试

**启动日志关键片段**:
```
[    3.559218] jffs2: version 2.2. (NAND) (SUMMARY)  © 2001-2006 Red Hat, Inc.
✓ jffs2.ko loaded successfully
```

## 关键发现

### ARM32 vs ARM64差异

| 特性 | ARM32 | ARM64 |
|------|-------|-------|
| Kernel Image | zImage (11M) | Image (37M) |
| jffs2.ko | 149K | 5.9M |
| MTD配置 | Built-in (y) | Module (m) |
| Busybox | 2.1M | 969K |

### MTD Built-in优势

ARM32的MTD配置为built-in，意味着：
- 不需要先加载mtd.ko
- JFFS2可直接加载
- initramfs更小

## 输出文件

```
qemu_outputs_arm32_e2e_20260518_083530/
├── kernel_image       (11M)  - ARM32 zImage
├── initramfs.cpio.gz  (1.2M) - Minimal initramfs
├── modules/
│   └── jffs2.ko       (149K) - JFFS2模块
└── logs/
    └── arm32_boot.log        - 完整测试日志
```

## 验证结论

✅ **ARM32端到端验证完全成功**

1. Kernel和Module版本完全匹配
2. QEMU成功启动并进入shell
3. jffs2.ko成功加载（MTD built-in）
4. ARM32 static busybox编译成功
