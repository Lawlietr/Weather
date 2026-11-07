#!/bin/bash
# ============================================================
# 手動更新：Build ＋ 部署到 Cloudflare Pages
# ------------------------------------------------------------
# 用途：改完 災情/ 或 颱風/ 的 markdown 後，跑這支即可
#       「抓 CWA → 產出 public/ → 推到公開託管（Cloudflare Pages）」。
#
# 日誌：所有輸出同步寫入 build/logs/deploy-YYYY-MM-DD.log
#       若發生問題，之後可檢視除錯。
#
# 用法：
#   ./deploy.sh                       # 完整流程（build ＋ 部署到 Cloudflare Pages）
#   ./deploy.sh --build-only          # 只 build，不部署
#   ./deploy.sh --no-cf               # 只 build，不部署任何一站（罕用）
#   ./deploy.sh --gh                  # 額外推 GitHub Pages 鏡像（見下）
#   ./deploy.sh --preview             # build 後本機預覽，不部署
#
# ⚠️ GitHub Pages 鏡像（orphan `gh-pages` 分支）自 2026-11-07 起不再推送：
#   現行唯一上線通道＝Cloudflare Pages（由本地 cron 每 2 小時更新）。GitHub Actions 完全不使用（見 `.github/`）。
#   `--gh` 只留給「手動重建鏡像」用：需同時在 GitHub repo 重新啟用 Pages（branch 來源 gh-pages）才會真的上線。
#   （舊參數 `--no-gh` 保留為無作用別名——不推已是預設。）
#
# 需要環境變數（慣例：~/.zshrc source 的憑證集中檔 ~/.zshrc.secrets）：
#   CWA_API_KEY、CLOUDFLARE_API_TOKEN、CLOUDFLARE_ACCOUNT_ID
# 選用（僅 `--gh` 時）：GH_PAT（GitHub token；留空則改用本機 git remote github 的 SSH 推 gh-pages）
#
# 金鑰一律不進 repo、不寫進任何輸出檔案。
# ============================================================
set -euo pipefail

# 跳到 repo 根目錄（本腳本在 build/ 下）
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# --- Logging（所有輸出同步寫入 build/logs/） ---
LOG_DIR="$REPO_ROOT/build/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/deploy-$(date +%Y-%m-%d).log"
# 將所有輸出（stdout + stderr）透過 tee 同時寫入螢幕與日誌
exec > >(exec tee -a "$LOG_FILE") 2> >(exec tee -a "$LOG_FILE" >&2)

CF_PROJECT="weather"
GH_REPO="https://github.com/Lawlietr/Weather.git"
# `--gh` 時的推送憑證優先序：GH_PAT（token HTTPS）→ 本機 git remote github（SSH）→ https 預設。
GH_PUSH="$(git remote get-url github 2>/dev/null || echo "$GH_REPO")"
if [ -n "${GH_PAT:-}" ]; then
  GH_PUSH="https://x-access-token:${GH_PAT}@github.com/Lawlietr/Weather.git"
fi

BUILD_ONLY=0
NO_CF=0
# 鏡像推送改為預設關閉（2026-11-07：gh-pages 不再推）；要推得明確給 --gh。
PUSH_GH=0
PREVIEW=0

for arg in "$@"; do
  case "$arg" in
    --build-only) BUILD_ONLY=1 ;;
    --no-cf)      NO_CF=1 ;;
    --gh)         PUSH_GH=1 ;;
    --no-gh)      : ;;   # 已是預設，保留為相容別名（舊指令與舊文件仍可能帶這參數）
    --preview)    PREVIEW=1 ;;
    -h|--help)
      grep '^# *' "$0" | sed 's/^# *//'
      exit 0 ;;
    *) echo "未知參數：$arg（見 --help）" >&2; exit 1 ;;
  esac
done

# --- 檢查金鑰是否就位 ---
missing=()
for k in CWA_API_KEY CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID; do
  [ -n "${!k:-}" ] || missing+=("$k")
done
if [ "${#missing[@]}" -gt 0 ]; then
  echo "⚠️  缺少環境變數：${missing[*]}" >&2
  echo "   請寫入 ~/.zshrc.secrets（憑證集中檔）後 exec zsh 重載，或在 shell 內 export。" >&2
  exit 1
fi

echo "===================================================="
echo " Weather 手動更新  $(date +%Y/%m/%d\ %H:%M)"
echo " 根目錄：$REPO_ROOT"
echo "===================================================="

# --- [1/4] Build ---
echo
echo "==> [1/4] Build（抓 CWA + 產出 public/）"
./build/build.sh

if [ "$PREVIEW" -eq 1 ]; then
  echo
  echo "==> 本機預覽：http://localhost:8080  （Ctrl-C 結束）"
  ( cd public && python3 -m http.server 8080 )
  exit 0
fi

if [ "$BUILD_ONLY" -eq 1 ]; then
  echo
  echo "==> 完成（--build-only：已 build，未部署）。"
  echo "    預覽：cd public && python3 -m http.server 8080"
  exit 0
fi

# 兩邊都不推時明確告知，避免误以為已上線（鏡像預設關閉，所以 --no-cf 等於完全不部署）
if [ "$NO_CF" -eq 1 ] && [ "$PUSH_GH" -ne 1 ]; then
  echo
  echo "⚠️  [2/4] 跳過 Cloudflare（--no-cf）、[3/4] 也不推鏡像 → 本次沒有部署任何一站。"
  echo "    只 build 用 --build-only；要連鏡像一起推則加 --gh。"
  exit 0
fi

# --- [2/4] Cloudflare Pages（主要通道）---
if [ "$NO_CF" -ne 1 ]; then
  echo
  echo "==> [2/4] 部署到 Cloudflare Pages"
  # 明確 --branch main（＝專案 production branch）：wrangler 未指定時會從
  # 目前 git 分支推断，DEV 開發期間跑部署會只產預覽 alias、自訂域名不更新
  # （2026/9/16 實測）。內容仍來自目前 checkout（DEV 內容上生產＝刻意行為，見 AGENTS.md Git 節）。
  npx -y wrangler@latest pages deploy public --project-name "$CF_PROJECT" --branch main
else
  echo
  echo "==> [2/4] 跳過 Cloudflare（--no-cf）"
fi

# --- [3/4] GitHub Pages 鏡像（2026-11-07 起預設不推，僅 --gh 時推）---
if [ "$PUSH_GH" -eq 1 ]; then
  echo
  echo "==> [3/4] 部署到 GitHub Pages 鏡像（已明確指定 --gh）"
  # ⚠️ TMP 一律帶可辨識的前綴，且任何路徑退出都要清掉。
  #    本腳本是 set -euo pipefail：rsync／git commit／push 任一失敗就提前中止，屆時只有結尾那行
  #    rm -rf 不會執行 → /tmp 遺留一份完整 public/ 副本（2200+ 檔、每期數 MB，2026-11-07 前長期堆積）。
  #    EXIT trap 蓋住正常與失敗兩種退出；前綴 `weather-gh-pages.` 讓被 SIGKILL／斷電留下的殘骸可辨識，
  #    由 build/deploy-cron.sh 每期開工掃掉（見其 cleanup_tmp）。
  TMP="$(mktemp -d "${TMPDIR:-/tmp}/weather-gh-pages.XXXXXXXX")"
  trap 'rm -rf "$TMP"' EXIT
  rsync -a --delete --exclude '.DS_Store' public/ "$TMP/"
  git -C "$TMP" init -q -b gh-pages
  git -C "$TMP" add -A
  git -C "$TMP" commit -q -m "site update: $(date +%Y/%m/%d)"
  # 推送需重試。GitHub 偶發拒絕整個 ref：`cannot lock ref 'refs/heads/gh-pages': is at <sha>
  # but expected <sha>`（2026-11-04 20:00、2026-11-05 02:00／06:00／10:00 實測各一次）——
  # 遠端 ref 在「廣告 ref 給本地」與「上鎖」之間被别的程序動過，本地持的是舊值。
  # 重試會重新讀遠端 ref 狀態，實務上一試即成（下趟 cron 也常自行成功）。
  gh_pushed=0
  for gh_attempt in 1 2 3; do
    if git -C "$TMP" push -f "$GH_PUSH" gh-pages; then
      gh_pushed=1
      break
    fi
    echo "    gh-pages 推送失敗（第 $gh_attempt/3 次），5 秒後重試"
    sleep 5
  done
  if [ "$gh_pushed" -ne 1 ]; then
    echo "❌ gh-pages 連續 3 次推送失敗（Cloudflare 已部署完成，gh-pages mirror 未更新）"
    exit 1   # TMP 由上面的 EXIT trap 清理，不再手動 rm
  fi
  rm -rf "$TMP"
else
  echo
  echo "==> [3/4] 跳過 GitHub Pages 鏡像（2026-11-07 起預設不推；要手動重建鏡像才加 --gh）"
fi

# --- [4/4] 完成 ---
echo
echo "===================================================="
echo " ✅ 完成。上線網址（唯一通道＝Cloudflare Pages）："
echo "     Cloudflare：https://weather.avpclub.eu.org"
echo "     日文版：     https://weather.avpclub.eu.org/ja/"
if [ "$PUSH_GH" -eq 1 ]; then
  echo "     GitHub 鏡像（僅本次有推）：https://lawlietr.github.io/Weather/"
fi
echo "===================================================="
