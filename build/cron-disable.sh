#!/bin/bash
# ============================================================
# 停用 Weather 本地部署 cron（Actions 復原後執行）
# ------------------------------------------------------------
# 僅移除 Weather 備用排程整段，不動到其他工作項目。
# 冪等：沒有的時候執行也不會有錯。
# ============================================================
set -uo pipefail

DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$DEPLOY_DIR/.." && pwd)"
START="# >>> Weather cron managed >>>"
TAG="# weather-deploy-cron"

echo "===================================================="
echo " 停用 Weather cron 備用排程  $(date +%Y/%m/%d\ %H:%M)"
echo "===================================================="

if crontab -l 2>/dev/null | grep -q "$TAG"; then
  # 移除整段（START 標記 ~ TAG 工作行）
  crontab -l 2>/dev/null | sed "/$START/,/$TAG/d" | crontab -
  echo "✅ 已停用 Weather 備用排程。"
else
  echo "（原本就沒有 Weather cron 工作項目）"
fi

mkdir -p "$REPO_ROOT/build/logs"
crontab -l > "$REPO_ROOT/build/logs/crontab.backup.$(date +%Y%m%d-%H%M%S).txt" 2>/dev/null || true

echo
echo "目前 crontab："
crontab -l 2>/dev/null | grep -v '^$' || echo "（crontab 為空）"
echo
echo "重新啟用：bash build/cron-enable.sh"
