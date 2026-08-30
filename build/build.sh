#!/bin/bash
# 一鍵 build：CWA 檢查 → 自動建 venv、裝 python-markdown、產出 public/
# 若 CWA API 不可達，exit 1 阻止後續部署步驟
set -e
cd "$(dirname "$0")"

echo "==> CWA API 連線檢查..."
if [ -z "${CWA_API_KEY:-}" ]; then
  echo "⚠️  CWA_API_KEY 未設定，跳過 CWA 檢查（build 將使用舊快取）"
else
  _cwa_ok=0
  for _attempt in 1 2 3; do
    if curl -fsS -m 20 \
      "https://opendata.cwa.gov.tw/api/v1/rest/datastore/W-C0034-005?Authorization=${CWA_API_KEY}&format=JSON" \
      | grep -q "TropicalCyclones" 2>/dev/null; then
      echo "✓ CWA API 連線正常"
      _cwa_ok=1
      break
    else
      echo "⚠️  CWA 檢查第 ${_attempt}/3 次失敗，3 秒後重試..."
      sleep 3
    fi
  done
  if [ "$_cwa_ok" -ne 1 ]; then
    echo "❌ CWA API 連續 3 次連線失敗，build 中止"
    exit 1
  fi
fi

# --- venv ---
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q --upgrade pip
fi
.venv/bin/pip list 2>/dev/null | grep -qi '^markdown ' || .venv/bin/pip install -q markdown

# --- RSS 災情候選清單（半自動：只抓取＋結構化，相關性由人工審查；失敗不影響 build） ---
echo "==> 抓取 RSS 災情候選清單（build/rss_candidates.json）..."
.venv/bin/python rss.py || echo "⚠️  RSS 候選清單產出失敗，跳過（不影響 build）"

# --- build ---
.venv/bin/python site.py
