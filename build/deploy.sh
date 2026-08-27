#!/bin/bash
# ============================================================
# 手動更新：Build + 部署到 Cloudflare Pages 與 GitHub Pages
# ------------------------------------------------------------
# 用途：改完 災情/ 或 颱風/ 的 markdown 後，跑這支即可
#       「抓 CWA → 產出 public/ → 推到兩個公開託管」。
#
# 用法：
#   ./deploy.sh                       # 完整流程（build + CF + GitHub Pages）
#   ./deploy.sh --build-only          # 只 build，不部署
#   ./deploy.sh --no-cf               # build + GitHub Pages，跳過 Cloudflare
#   ./deploy.sh --no-gh               # build + Cloudflare，跳過 GitHub Pages
#   ./deploy.sh --preview             # build 後本機預覽，不部署
#
# 需要環境變數（在 ~/.zshrc / ~/.bashrc 已設定）：
#   CWA_API_KEY、CLOUDFLARE_API_TOKEN、CLOUDFLARE_ACCOUNT_ID
# 選用：GH_PAT（GitHub 個人存取憑證，用於推私有 GitHub Pages mirror；留空則跳過）
#
# 金鑰一律不進 repo、不寫進任何輸出檔案。
# ============================================================
set -euo pipefail

# 跳到 repo 根目錄（本腳本在 build/ 下）
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

CF_PROJECT="weather"
GH_REPO="https://github.com/Lawlietr/Weather.git"
# GitHub Pages 為私有 repo，推送需憑證。若環境變數 GH_PAT 有值，
# 自動改走 x-access-token 驗證（手動與 cron 部署皆適用）。
GH_PUSH="$GH_REPO"
if [ -n "${GH_PAT:-}" ]; then
  GH_PUSH="https://x-access-token:${GH_PAT}@github.com/Lawlietr/Weather.git"
fi

BUILD_ONLY=0
NO_CF=0
NO_GH=0
PREVIEW=0

for arg in "$@"; do
  case "$arg" in
    --build-only) BUILD_ONLY=1 ;;
    --no-cf)      NO_CF=1 ;;
    --no-gh)      NO_GH=1 ;;
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
  echo "   請先在 ~/.zshrc（或 ~/.bashrc）設定後重開 shell。" >&2
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

# --- [2/4] Cloudflare Pages（主要通道）---
if [ "$NO_CF" -ne 1 ]; then
  echo
  echo "==> [2/4] 部署到 Cloudflare Pages"
  npx -y wrangler@latest pages deploy public --project-name "$CF_PROJECT"
else
  echo
  echo "==> [2/4] 跳過 Cloudflare（--no-cf）"
fi

# --- [3/4] GitHub Pages（orphan gh-pages 分支）---
if [ "$NO_GH" -ne 1 ]; then
  echo
  echo "==> [3/4] 部署到 GitHub Pages（orphan gh-pages）"
  TMP="$(mktemp -d)"
  rsync -a --delete --exclude '.DS_Store' public/ "$TMP/"
  git -C "$TMP" init -q -b gh-pages
  git -C "$TMP" add -A
  git -C "$TMP" commit -q -m "site update: $(date +%Y/%m/%d)"
  git -C "$TMP" push -f "$GH_PUSH" gh-pages
  rm -rf "$TMP"
else
  echo
  echo "==> [3/4] 跳過 GitHub Pages（--no-gh）"
fi

# --- [4/4] 完成 ---
echo
echo "===================================================="
echo " ✅ 完成。上線網址："
echo "     Cloudflare：https://weather.avpclub.eu.org"
echo "     GitHub：   https://lawlietr.github.io/Weather/"
echo "     日文版：     https://weather.avpclub.eu.org/ja/"
echo "===================================================="
