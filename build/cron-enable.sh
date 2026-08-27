#!/bin/bash
# ============================================================
# 安裝 Weather 本地部署 cron（對 Actions 的備用）
# ------------------------------------------------------------
# 預設「不啟用」。僅在 Actions 異常時執行此支來開啟排程。
# 重複執行會自動覆蓋既有 Weather 工作項目（冪等，不累積）。
#
# 前置：build/deploy.env 需存在（金鑰）。建議先跑：
#   bash build/deploy-cron.sh --selfcheck
# ============================================================
set -uo pipefail

DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$DEPLOY_DIR/.." && pwd)"
START="# >>> Weather cron managed >>>"
TAG="# weather-deploy-cron"

echo "===================================================="
echo " 安裝 Weather cron 備用排程  $(date +%Y/%m/%d\ %H:%M)"
echo "===================================================="

# 1. 檢查金鑰檔
if [ ! -r "$DEPLOY_DIR/deploy.env" ]; then
  echo "❌ $DEPLOY_DIR/deploy.env 不存在。請先建立（cron-enable 會從 ~/.zshrc 複製金鑰）" >&2
  exit 1
fi

# 2. 建議先自檢
echo
echo "==> 先做 selfcheck（驗證金鑰與網路，不部署）"
if ! "$DEPLOY_DIR/deploy-cron.sh" --selfcheck; then
  echo "⚠️  selfcheck 未通過，仍繼續安裝 cron，但排程執行可能會失敗。" >&2
  read -r -p "   輸入 y 繼續安裝，其他鍵取消： " ans
  [ "$ans" = "y" ] || { echo "已取消。"; exit 1; }
fi

# 3. 備份現有 crontab
mkdir -p "$REPO_ROOT/build/logs"
crontab -l > "$REPO_ROOT/build/logs/crontab.backup.$(date +%Y%m%d-%H%M%S).txt" 2>/dev/null \
  && echo "✓ 已備份現有 crontab 到 build/logs/" || echo "（原本沒有 crontab）"

# 4. 移除舊的 Weather 整段（冪等）後裝上新版
cleaned="$(crontab -l 2>/dev/null | sed "/$START/,/$TAG/d" || true)"
{ printf '%s\n' "$cleaned"
  echo "$START"
  echo "# Weather 本地部署備用（build/cron-enable.sh / cron-disable.sh 管理）"
  cat "$DEPLOY_DIR/cron.txt"
} | grep -v '^$' | crontab -

echo
echo "✅ 已安裝。目前 crontab："
crontab -l | grep -v '^$'
echo
echo "停用：bash build/cron-disable.sh"
