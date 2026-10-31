#!/bin/bash
# ============================================================
# Weather 本地自動部署 — cron 進入點
# ------------------------------------------------------------
# 用途：唯一自動 build＋部署通道（台灣時間每小時整點，2026-10-23 起）。
#       由 cron 呼叫（見 cron.txt / cron-enable.sh）。
#
# 功能：
#   1. 載入金鑰（慣例來源＝~/.zshrc.secrets 憑證集中檔；build/deploy.env 只做兜底）
#   2. 執行 ./build/deploy.sh（抓 CWA + build + 推 CF / GitHub Pages）
#   3. 全程寫入 build/logs/ 日誌（最多保留 5 天，超時自動刪除）
#   4. flock 防止重疊執行
#
# 選用參數：
#   --selfcheck   僅驗證金鑰與網路/Cloudflare 可用性，不 build、不部署
#   --help        顯示說明
#
# 部署範圍：
#   預設＝完整部署（Cloudflare Pages ＋ GitHub Pages 的 gh-pages 分支）。
#   GitHub 推送不需要 GH_PAT：本機走 github remote（SSH）；若設了 GH_PAT 則改走 token HTTPS。
#   2026-10-23 起不再自動加 --no-gh：Actions 排程已停用，gh-pages 只能由本地 cron 推。
#   （只要 Cloudflare 時，手動執行加 --no-gh 即可。）
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

# 金鑰環境變數：cron 不讀 shell rc，所以一律 grep `^export VAR=` 行。依序找，先找到即採用。
# ~/.zshrc.secrets＝憑證集中檔（2026-10-29 起：token 太多，不再塞在 ~/.zshrc，改由 .zshrc source 此檔）。
SECRET_FILES=("$HOME/.zshrc.secrets" "$HOME/.zshrc" "$HOME/.bashrc")
KEY_FROM=""
for var in CWA_API_KEY CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID GH_PAT; do
  for sf in "${SECRET_FILES[@]}"; do
    [ -r "$sf" ] || continue
    val=$(grep -E "^export ${var}=" "$sf" 2>/dev/null | tail -1 | sed "s/^export ${var}=//;s/^['\"]//;s/['\"]$//")
    [ -n "$val" ] || continue
    export "$var"="$val"
    KEY_FROM="${KEY_FROM:+$KEY_FROM,}${var}←${sf}"
    break
  done
done

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') [cron] $*" >> "$LOG_FILE"; }

# ---- 日誌清理（最多保留 5 天） ----
cleanup_logs() {
  find "$LOG_DIR" -name 'deploy-cron-*.log' -mtime +5 -delete 2>/dev/null
  find "$LOG_DIR" -name 'deploy-*.log' -mtime +5 -delete 2>/dev/null
}

do_selfcheck() {
  log "SELFCHECK 開始"
  local ok=1
  # 金鑰
  for k in CWA_API_KEY CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID; do
    if [ -z "${!k:-}" ]; then log "SELFCHECK FAIL: 缺少 $k"; ok=0; fi
  done
  # 網路：CWA
  if curl -fsS -m 20 "https://opendata.cwa.gov.tw/api/v1/rest/datastore/W-C0034-005?Authorization=${CWA_API_KEY:-}&format=JSON" \
        | grep -q "TropicalCyclones" 2>/dev/null; then
    log "SELFCHECK OK:  CWA API 可連"
  else
    log "SELFCHECK FAIL: CWA API 不可連"; ok=0
  fi
  # 網路：Cloudflare API 驗證
  if curl -fsS -m 20 -X GET "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID:-}" \
        -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN:-}" \
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
# 優先序：1) ~/.zshrc.secrets 2) ~/.zshrc／~/.bashrc（舊慣例）3) build/deploy.env（本機 gitignore，只做兜底）。
# ⚠️ 三把金鑰都已從上面取得時不 source deploy.env：兩機那份內容不一致（開發機那份 2026-10-26 實測為失效 token、
#    部署機那份是不含值的模板），source 下去會用過時值覆寫，或觸發其中的 `:?` 防呆。
# ⚠️ deploy.env 內建 `: "${VAR:?…」"`：值為空時 bash 直接終止整個腳本，連 log 都來不及寫
#    （2026-10-29 22:00 起連續 18 期只在 cron 郵件留字、build/logs 空白，就是這個死法）。
#    所以缺金鑰一律在 source 之前先 log 再 exit 3。
if [ -n "${CWA_API_KEY:-}" ] && [ -n "${CLOUDFLARE_API_TOKEN:-}" ] && [ -n "${CLOUDFLARE_ACCOUNT_ID:-}" ]; then
  log "金鑰來源：${KEY_FROM:-無}（已齊全，不載入 deploy.env）"
else
  if [ ! -r "$DEPLOY_DIR/deploy.env" ]; then
    log "ERROR: 金鑰不全（已取：${KEY_FROM:-無}），且 $DEPLOY_DIR/deploy.env 不存在或不可讀（權限？）"
    echo "❌ 金鑰不全，且 $DEPLOY_DIR/deploy.env 不存在或不可讀：請確認 ~/.zshrc.secrets，或建立 deploy.env（chmod 600）" >&2
    exit 3
  fi
  missing=()
  for k in CWA_API_KEY CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID; do
    [ -n "${!k:-}" ] && continue
    grep -qE "^(export )?${k}=" "$DEPLOY_DIR/deploy.env" || missing+=("$k")
  done
  if [ "${#missing[@]}" -gt 0 ]; then
    log "ERROR: 找不到金鑰 ${missing[*]}（找過：${SECRET_FILES[*]} 與 $DEPLOY_DIR/deploy.env）"
    echo "❌ 缺少金鑰：${missing[*]}（請寫入 ~/.zshrc.secrets；日誌：$LOG_FILE）" >&2
    exit 3
  fi
  log "金鑰不全（已取：${KEY_FROM:-無}）→ 改用 $DEPLOY_DIR/deploy.env 兜底"
  # shellcheck disable=SC1090
  . "$DEPLOY_DIR/deploy.env"
fi

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

log "START（GH_PAT=${GH_PAT:+set}；金鑰來源：${KEY_FROM:-deploy.env}）"

# ---- 清理舊日誌 ----
cleanup_logs

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

# ---- 執行部署（2026-10-23 起一律完整部署：CF ＋ gh-pages）----
# GitHub Pages mirror 需由本地 cron 自己推（Actions 排程已停用，不再顺手推）。
# 注：gh-pages 推送失败会让 rc 非 0（CF 已先部署完成、站台不受影响），下趟即重试。
./build/deploy.sh >> "$LOG_FILE" 2>&1
rc=$?

if [ "$rc" -eq 0 ]; then
  log "END 成功 (rc=0)"
else
  log "END 失敗 (rc=$rc) —— 請檢視 $LOG_FILE"
fi
exit $rc
