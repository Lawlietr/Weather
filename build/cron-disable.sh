#!/bin/bash
# ============================================================
# 停用 Weather 本地部署 cron（要暫停自動上線時執行；本地 cron 是目前唯一自動通道）
# ------------------------------------------------------------
# 僅移除 Weather 備用排程整段，不動到其他工作項目。
# 冪等：沒有的時候執行也不會有錯。
# ============================================================
set -uo pipefail

DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$DEPLOY_DIR/.." && pwd)"
START="# >>> Weather cron managed >>>"
TAG="# weather-deploy-cron"
TS="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$REPO_ROOT/build/logs"

# 先備份「移除前」的 crontab。舊版把備份放在移除動作之後 → 備份檔永远是移除後的狀態
# （2026-11-07 於開發機實測：2026-08-27／10-31／11-07 三份 crontab.backup.* 全是 0 位元組），
# 無法用來恢復。現在 before/after 兩份都留，恢復用 before。
crontab -l > "$REPO_ROOT/build/logs/crontab.before.$TS.txt" 2>/dev/null || true

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

crontab -l > "$REPO_ROOT/build/logs/crontab.after.$TS.txt" 2>/dev/null || true
echo "crontab 備份：build/logs/crontab.before.$TS.txt（移除前，恢復用）與 crontab.after.$TS.txt（移除後）"

echo
echo "目前 crontab："
crontab -l 2>/dev/null | grep -v '^$' || echo "（crontab 為空）"
echo
echo "重新啟用：bash build/cron-enable.sh"
