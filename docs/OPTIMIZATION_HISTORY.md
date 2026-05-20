# Skills 优化历程

记录技能的版本迭代和关键优化。

## kernel-build Skill

### v2.0 (2026-05-16)
- 新增跨平台编译支持（`--cross` 参数）
- 自动工具链检测（aarch64/arm-linux-gnueabi）
- ARM32 defconfig自动回退（multi_v7_defconfig）
- 架构支持矩阵（ARM64/ARM32/x86_64）

### v1.5
- 添加编译进度跟踪
- 模块分类输出

### v1.0
- 基础架构支持

## qemu-test Skill

### 优化 (2026-05-18)
- Busybox架构自动检测
- 完整applet需求清单
- 常见问题诊断表格
- 交叉编译示例

## jffs2-mount Skill

### 优化 (2026-05-18)
- 完整MTD设备配置流程
- block2mtd/mtdram配置脚本
- 6步骤挂载测试脚本
- 关键经验总结表格

### 更新 (2026-05-20)
- 推荐mtdram替代block2mtd
- Busybox编译最佳实践
- TC模块禁用说明

## jffs2-fault-inject Skill

### 新增 (2026-05-20)
- CRC故障注入（hdr_crc/node_crc/data_crc/name_crc）
- Magic number注入（0xDEAD）
- 故障报告JSON生成
- 与jffs2-analyzer配合验证