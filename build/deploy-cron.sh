#!/bin/bash
# ============================================================
# Weather 本地自動部署 — cron 進入點
# ------------------------------------------------------------
# 用途：唯一自動 build＋部署通道（台灣時間每 2 小時整點，2026-10-24 起）。
#       由 cron 呼叫（見 cron.txt / cron-enable.sh）。
#
# 功能：
#   1. 載入金鑰（慣例來源＝~/.zshrc.secrets 憑證集中檔；build/deploy.env 只做兜底）
#   2. 執行 ./build/deploy.sh（抓 CWA ＋ build ＋ 推 Cloudflare Pages）
#   3. 全程寫入 build/logs/ 日誌（最多保留 5 天，超時自動刪除）
#   4. flock 防止重疊執行
#
# 選用參數：
#   --selfcheck   僅驗證金鑰與網路/Cloudflare 可用性，不 build、不部署
#   --help        顯示說明
#
# 部署範圍（2026-11-07 定案）：
#   預設＝只推 Cloudflare Pages（唯一上線通道）。
#   ⚠️ 不再推 GitHub Pages 鏡像（orphan `gh-pages` 分支）：推它就會觸發 GitHub 為 branch 來源 Pages
#      內建的 `pages build and deployment` workflow，而鏡像站不是正式管道。
#      `build/deploy.sh --gh` 只留給手動重建鏡像用，cron 不帶該參數。
#   GitHub Actions 完全不使用（2026-11-07 刪除 `.github/workflows/build.yml`）：
#      scheduler 不可靠（2026-10-23 實測 24 期只跑 10 期、間隔 185–424 分）。
#      日后若要自動觸發，首選是用 CF Worker Cron 打手動觸發（未實作）→ design/cf-cron.md。
# ============================================================
set -uo pipefail

DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$DEPLOY_DIR/.." && pwd)"
cd "$REPO_ROOT"

LOG_DIR="$REPO_ROOT/build/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/deploy-cron-$(date +%Y-%m-%d).log"
LOCK_FILE="/tmp/weather-deploy.lock"

# cron 環境 PATH 極簡，需補齊（含 node 與 python）。
# ⚠️ 不得寫死 node 的版本目錄名。pi 自帶的 node 升級會換掉目錄名（舊版會整個消失）：
#    2026-11-05 10:48 pi-node 由 node-v22.23.2-linux-x64 換成 node-v24.22.2-linux-x64，
#    寫死的 PATH 從當天 12:00 起連續 10 期在 deploy.sh 的 `npx -y wrangler` 得到 rc=127，
#    Cloudflare 與 GitHub Pages 兩個通道全停（deploy.sh 是 set -e，[2/4] 掛了 [3/4] 也不跑）。
#    改以 current 符號連結優先，再依版本由新到舊補上現存的 node-v*/bin 目錄。
PI_NODE_HOME="${HOME}/.local/share/pi-node"
node_path_candidates=("$PI_NODE_HOME/current/bin")
while IFS= read -r _d; do node_path_candidates+=("$_d"); done \
  < <(ls -d "$PI_NODE_HOME"/node-v*/bin 2>/dev/null | sort -Vr)
node_path_candidates+=("$HOME/.hermes/node/bin")
NODE_PATH_EXTRA=""
for _d in "${node_path_candidates[@]}"; do
  [ -x "$_d/node" ] || continue
  NODE_PATH_EXTRA="${NODE_PATH_EXTRA:+$NODE_PATH_EXTRA:}$_d"
done
export PATH="${NODE_PATH_EXTRA:+$NODE_PATH_EXTRA:}/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# 金鑰環境變數：cron 不讀 shell rc，所以一律 grep `^export VAR=` 行。依序找，先找到即採用。
# ~/.zshrc.secrets＝憑證集中檔（2026-10-29 起：token 太多，不再塞在 ~/.zshrc，改由 .zshrc source 此檔）。
SECRET_FILES=("$HOME/.zshrc.secrets" "$HOME/.zshrc" "$HOME/.bashrc")
KEY_FROM=""
for var in CWA_API_KEY CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID; do
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

# ---- /tmp 殘留清理 ----
# 兩個來源（兩者都只在異常退出時才會殘留）：
#   1. deploy.sh 的 gh-pages 暫存目錄 `${TMPDIR:-/tmp}/weather-gh-pages.XXXXXXXX`（只在手動跑
#      `deploy.sh --gh` 時才會建立；cron 預設不推鏡像就不會建立它）：
#      腳本內建 EXIT trap 會清，但進程被 SIGKILL（OOM）或機器斷電時 trap 不會執行——
#      殘留的是一份完整 public/ 副本（數 MB）。2026-11-07 之前的舊版無前綴（`mktemp -d` 直接產
#      `tmp.` ＋ 10 個亂碼字元）也無 trap，每次部署失敗就留一份。
#   2. agent 除錯用的暫存檔：一律寫在 /tmp/weather-scratch/（單一目錄，規則見 WORKFLOW.md §8 第 3 條），
#      這裡掃超過 2 天未動的舊檔。
# 呼叫時機：取得 flock 之後（保證不會刪到同期還在使用的東西）。
cleanup_tmp() {
  local tmpbase="${TMPDIR:-/tmp}"
  find "$tmpbase" -maxdepth 1 -name 'weather-gh-pages.*' -mmin +180 -exec rm -rf {} + 2>/dev/null
  # 舊版（無前綴）留下的 mktemp 目錄：只刪 3 天以上、名字形如 `tmp.` ＋ 8–12 個亂碼字元的目錄
  # （GNU mktemp 預設是 10 字元；2026-11-07 實測），不碰其他 tmp.* 命名
  find "$tmpbase" -maxdepth 1 -type d -regextype posix-extended \
    -regex '.*/tmp\.[A-Za-z0-9_-]{8,12}' -mtime +3 -exec rm -rf {} + 2>/dev/null
  find "$tmpbase/weather-scratch" -mindepth 1 -mtime +2 -delete 2>/dev/null
  # npx -y wrangler@latest 會為每個新 wrangler 版留一份快取（2026-11-07 實測 ~/.npm 366 MB、
  # 其中 ~/.npm/_npx 104 MB）。清掉 14 天沒再碰的 entries；整個 ~/.npm 超過 400 MB 時一次清光
  # （下趟會重抓 wrangler，多幾秒）。
  if [ -d "$HOME/.npm" ]; then
    find "$HOME/.npm/_npx" -maxdepth 1 -mindepth 1 -type d -mtime +14 -exec rm -rf {} + 2>/dev/null
    npm_mb=$(du -sm "$HOME/.npm" 2>/dev/null | cut -f1)
    if [ -n "${npm_mb:-}" ] && [ "$npm_mb" -gt 300 ]; then
      log "npm cache ${npm_mb} MB > 300 MB -> npm cache clean --force"
      npm cache clean --force >/dev/null 2>&1 || rm -rf "$HOME/.npm/_npx" 2>/dev/null
    fi
  fi
}

do_selfcheck() {
  log "SELFCHECK 開始"
  local ok=1
  # 金鑰
  for k in CWA_API_KEY CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID; do
    if [ -z "${!k:-}" ]; then log "SELFCHECK FAIL: 缺少 $k"; ok=0; fi
  done
  # node／npx（Cloudflare Pages 部署靠 `npx -y wrangler`，缺它就一定部署不出去）
  if command -v npx >/dev/null 2>&1 && command -v node >/dev/null 2>&1; then
    log "SELFCHECK OK:  node 可用（$(node -v 2>/dev/null || echo 版本未知)；$(command -v node)）"
  else
    log "SELFCHECK FAIL: cron PATH 找不到 node/npx（pi-node 目錄名改變？查 $PI_NODE_HOME）"; ok=0
  fi
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

# ---- node 前置檢查（缺 npx 時 Cloudflare 部署必失敗）----
if ! command -v npx >/dev/null 2>&1; then
  log "ERROR: cron PATH 找不到 npx（查過 $PI_NODE_HOME/current/bin 與 $PI_NODE_HOME/node-v*/bin）。PATH=$PATH"
  echo "❌ 找不到 npx：請確認 $PI_NODE_HOME 下的 node 目錄名（日誌：$LOG_FILE）" >&2
  exit 4
fi
log "node 就緒：$(node -v 2>/dev/null || echo 版本未知) ← $(command -v node)"

# ---- 防止重疊 ----
exec 9>"$LOCK_FILE"
if command -v flock >/dev/null 2>&1; then
  if ! flock -n 9; then
    log "SKIP: 已有執行進行中（lock 佔用）"
    echo "⏭️  已有部署進行中，本次跳過"
    exit 0
  fi
  # 取得 lock 後才設清除陷阱：結束（含部署失敗）即刪 lock 檔，
  # 避免 /tmp/weather-deploy.lock 每期跑完都留下一個 0 位元組空檔。
  # （`exec 9>"$LOCK_FILE"` 本身就建立該檔，舊版只在退出時不管它 → 長期在 /tmp 堆垃圾。）
  trap 'rm -f "$LOCK_FILE"' EXIT
fi

log "START（金鑰來源：${KEY_FROM:-deploy.env}；部署目標：Cloudflare Pages）"

# ---- 清理舊日誌與 /tmp 殘留 ----
cleanup_logs
cleanup_tmp

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

# ---- 執行部署（只推 Cloudflare Pages；gh-pages 鏡像與 Actions 自 2026-11-07 起不参與）----
./build/deploy.sh >> "$LOG_FILE" 2>&1
rc=$?

if [ "$rc" -eq 0 ]; then
  log "END 成功 (rc=0)"
else
  log "END 失敗 (rc=$rc) —— 請檢視 $LOG_FILE"
fi
exit $rc
