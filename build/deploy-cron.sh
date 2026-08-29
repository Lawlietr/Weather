#!/bin/bash
# ============================================================
# Weather 本地自動部署 — cron 進入點
# ------------------------------------------------------------
# 用途：GitHub Actions 異常時的本地備用排程執行腳本。
#       由 cron 呼叫（見 cron.txt / cron-enable.sh）。
#
# 功能：
#   1. 載入 build/deploy.env（金鑰，gitignore，不進 repo）
#   2. 執行 ./build/deploy.sh（抓 CWA + build + 推 CF / GitHub Pages）
#   3. 全程寫入 build/logs/ 日誌
#   4. flock 防止重疊執行
#
# 選用參數：
#   --selfcheck   僅驗證金鑰與網路/Cloudflare 可用性，不 build、不部署
#   --help        顯示說明
#
# 部署範圍：
#   若 deploy.env 設了 GH_PAT → 完整部署（Cloudflare + GitHub Pages）
#   若未設 GH_PAT            → 僅 Cloudflare（--no-gh）
#         （GitHub Pages 已轉私有 mirror 且目前 404，以 Cloudflare 為主）
# ============================================================
set -uo pipefail

DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$DEPLOY_DIR/.." && pwd)"
cd "$REPO_ROOT"

LOG_DIR="$REPO_ROOT/build/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/deploy-cron-$(date +%Y-%m-%d).log"
LOCK_FILE="/tmp/weather-deploy.lock"

# cron 環境 PATH 極簡，需補齊（含 node 與 python）
export PATH="/root/.local/share/pi-node/node-v22.23.2-linux-x64/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') [cron] $*" >> "$LOG_FILE"; }

do_selfcheck() {
  log "SELFCHECK 開始"
  local ok=1
  # 金鑰
  for k in CWA_API_KEY CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID; do
    if [ -z "${!k:-}" ]; then log "SELFCHECK FAIL: 缺少 $k"; ok=0; fi
  done
  # 網路：CWA
  if curl -fsS -m 20 "https://opendata.cwa.gov.tw/api/v1/rest/datastore/W-C0034-005?Authorization=${CWA_API_KEY}&format=JSON" \
        | grep -q "TropicalCyclones" 2>/dev/null; then
    log "SELFCHECK OK:  CWA API 可連"
  else
    log "SELFCHECK FAIL: CWA API 不可連"; ok=0
  fi
  # 網路：Cloudflare API 驗證
  if curl -fsS -m 20 -X GET "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}" \
        -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
        | grep -q "\"success\":true" 2>/dev/null; then
    log "SELFCHECK OK:  Cloudflare API token 有效"
  else
    log "SELFCHECK FAIL: Cloudflare token 無效或網路不通"; ok=0
  fi
  if [ "$ok" -eq 1 ]; then
    log "SELFCHECK 通過 — 可安全啟用 cron"
    echo "✅ selfcheck 通過"
    return 0
  else
    echo "❌ selfcheck 有失敗項目，請先修正 deploy.env 或網路" >&2
    return 1
  fi
}

# ---- 參數 ----
case "${1:-}" in
  --selfcheck)
    do_selfcheck
    exit $?
    ;;
  --help|-h)
    grep '^# *' "$0" | sed 's/^# *\?//'
    exit 0
    ;;
  *)
    if [ "${1:-}" != "" ]; then
      echo "未知參數：$1" >&2
      exit 1
    fi
    ;;
esac

# ---- 載入金鑰 ----
if [ ! -r "$DEPLOY_DIR/deploy.env" ]; then
  log "ERROR: $DEPLOY_DIR/deploy.env 不存在或不可讀（權限？）"
  echo "❌ $DEPLOY_DIR/deploy.env 不存在或不可讀，請先建立並 chmod 600" >&2
  exit 3
fi
# shellcheck disable=SC1090
. "$DEPLOY_DIR/deploy.env"

missing=()
for k in CWA_API_KEY CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID; do
  [ -n "${!k:-}" ] || missing+=("$k")
done
if [ "${#missing[@]}" -gt 0 ]; then
  log "ERROR: 缺少環境變數 ${missing[*]}"
  echo "❌ 缺少金鑰：${missing[*]}" >&2
  exit 3
fi

# ---- 防止重疊 ----
exec 9>"$LOCK_FILE"
if command -v flock >/dev/null 2>&1; then
  if ! flock -n 9; then
    log "SKIP: 已有執行進行中（lock 佔用）"
    echo "⏭️  已有部署進行中，本次跳過"
    exit 0
  fi
fi

log "START（GH_PAT=${GH_PAT:+set}）"

# ---- CWA 前置檢查（避免 build 失敗卻仍部署舊資料） ----
if [ -n "${CWA_API_KEY:-}" ]; then
  _cwa_ok=0
  for _attempt in 1 2 3; do
    if curl -fsS -m 20 \
      "https://opendata.cwa.gov.tw/api/v1/rest/datastore/W-C0034-005?Authorization=${CWA_API_KEY}&format=JSON" \
      | grep -q "TropicalCyclones" 2>/dev/null; then
      log "CWA 檢查通過（第 ${_attempt} 次）"
      _cwa_ok=1
      break
    else
      log "CWA 檢查第 ${_attempt}/3 次失敗，3 秒後重試"
      sleep 3
    fi
  done
  if [ "$_cwa_ok" -ne 1 ]; then
    log "CWA API 連續 3 次失敗，中止部署"
    echo "❌ CWA API 連續 3 次失敗，中止部署"
    exit 1
  fi
else
  log "⚠️  CWA_API_KEY 未設定，跳過 CWA 檢查"
fi

# ---- 決定部署範圍 ----
if [ -n "${GH_PAT:-}" ]; then
  ./build/deploy.sh >> "$LOG_FILE" 2>&1
  rc=$?
else
  ./build/deploy.sh --no-gh >> "$LOG_FILE" 2>&1
  rc=$?
fi

if [ "$rc" -eq 0 ]; then
  log "END 成功 (rc=0)"
else
  log "END 失敗 (rc=$rc) —— 請檢視 $LOG_FILE"
fi
exit $rc
