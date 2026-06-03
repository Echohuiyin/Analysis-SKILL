#!/bin/bash
# Git Push Script - 使用SSH over HTTPS (端口443) 绕过防火墙
# 用法: ./git-push.sh [分支名，默认main]

BRANCH=${1:-main}

echo "推送到远程仓库 (分支: $BRANCH)..."
git push origin $BRANCH

if [ $? -eq 0 ]; then
    echo "✓ 推送成功!"
else
    echo "✗ 推送失败，请检查网络或SSH密钥"
    echo "提示: 如果SSH密钥未配置，运行: ssh-keygen -t ed25519 -C 'your_email@example.com'"
fi