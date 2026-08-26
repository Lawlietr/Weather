# WORKFLOW：更新與部署工作流（Runbook）

> **讀者**：接手本專案的 agent 或人工操作者。
> **定位**：「怎麼做」的逐步流程。專案規範（檔案格式、CWA API 結構、設計原則）在
> `AGENTS.md` 與 `TODO.md`，本文件不重複，只引用。
> 最後更新：2026/8/26

---

## 0. 環境設定（接手時先跑一次）

1. 確認 `CWA_API_KEY` 在環境變數中：
   ```bash
   python3 -c "import os; print('OK' if os.getenv('CWA_API_KEY') else 'MISSING')"
   ```
   若 MISSING：請使用者寫入 `~/.zshrc`（`export CWA_API_KEY="..."`）或專案 `.env`
   （需在 `cwa.py` 加載入邏輯）。**金鑰絕不可 commit。**
2. Python ≥ 3.14 環境即可；`build/build.sh` 會自動建 venv 並安裝唯一相依 `markdown`。
3. 試跑一次確認 pipeline 通：
   ```bash
   ./build/build.sh
   # 預期輸出：build 完成：N 個事件（active X / ended Y）｜CWA live
   ```

## 1. 例行更新流程（每次都要做）

```
① 更新 markdown 內容（災情/颱風檔案，規則見 AGENTS.md「檔案撰寫規則」）
② ./build/build.sh
③ 驗證（見 §3 檢查清單）
④ git add / commit（訊息用繁體中文，簡述本次更新）
⑤ git push origin main（內部 Forgejo）
⑥ （僅當 GitHub 公開 repo 已建立時）將 public/ 產物推送到 Pages 分支
```

- 更新時間戳：檔案內時間戳與 `最後修改：` 欄位一律用**系統當前時間**，先 `date` 確認。
- 新進展**附加在檔尾**，不覆寫既有內容（AGENTS.md 規則）。
- CWA 資料不需人工維護——build 時自動抓取；快取在 `build/cwa_cache.json`（已 gitignore）。

## 2. 新事件流程

### 2.1 新增事件檔案
- 檔名與目錄規則見 AGENTS.md「目錄與檔名」：
  - 颱風：`颱風/{YYYY}/{MM}/{MMDD}_{NN}_{中文名}_{國際命名}.md`
  - 非颱風：`災情/{YYYY}/{MM}/{MMDD}_{事件類型}_{事件名稱}.md`
- 開頭加 YAML front matter（build 直接讀取）：
  ```yaml
  ---
  status: active        # active | ended
  event: 2026 第 N 號颱風 中文名
  severity: 🔴重大      # 🔴重大 | 🟡警戒 | 🟢一般
  counties: [南投, 屏東, ...]
  summary: 一兩句摘要
  sources: [新聞來源與日期]
  ---
  ```

### 2.2 事件狀態生命周期
- 事件發生 → 建檔，`status: active`。
- 首頁 Hero 區自動取 active 中「最後修改」最新者（`build/site.py` 邏輯，勿手動改首頁 HTML）。
- 事件結束後 → 把該檔 front matter 改為 `status: ended`，重 build；事件自動降級到 archive。

## 3. 驗證檢查清單（每次 build 後）

```bash
# ① 輸出應含 CWA 模式
./build/build.sh | tee /tmp/build.log          # 預期「｜CWA live」
# ② 內部連結 0 斷鏈（注意中文檔名要 URL decode）
python3 - <<'EOF'
import re, os
from urllib.parse import unquote
bad = total = 0
for root, _, files in os.walk('public'):
    for f in files:
        if not f.endswith('.html'): continue
        html = open(os.path.join(root, f), encoding='utf-8').read()
        for l in re.findall(r'href="([^"#][^"]*)"', html):
            if l.startswith(('http','#','mailto')): continue
            total += 1
            if not os.path.exists(os.path.join(root, unquote(l.split('#')[0]))):
                bad += 1; print("斷:", f, "->", l)
print(f"內部連結 {total}，斷鏈 {bad}")
EOF
# ③ 金鑰零外洩（兩項都應為 0）
grep -rc "Authorization=" public/ | grep -v ":0" || echo "OK: 無 Authorization"
grep -rc "$CWA_API_KEY" public/ build/cwa_cache.json | grep -v ":0" || echo "OK: 無金鑰值"
# ④ 瀏覽器預覽（重點：首頁 Hero、CWA 區塊、手機寬度、兩套主題）
cd public && python3 -m http.server 8080
```

## 4. 失敗處理

| 症狀 | 處置 |
|------|------|
| build 顯示「CWA none」 | 金鑰或網路問題。查 `CWA_API_KEY`、`curl` 直連測試。頁面會顯示 `cwa-fail` 警示卡，**不要**把警示卡 commit 進公開站（除非確實要公告資料中斷）。 |
| build 顯示「CWA partial」 | 單一來源失敗，其餘用快取舊值＋「舊資料」標註。重試一次；若持續，記錄是哪個 Data ID（錯誤訊息會寫出）。 |
| CWA 回傳結構變動（KeyError/欄位缺失） | **先 dump 真實回傳結構再改解析**，勿照舊文件猜。結構差異對照表在 AGENTS.md 與本文件 §5。 |
| 需要爬 CWA 官網頁面（API 沒有該產品） | 用 Obscura（設定見 AGENTS.md「Obscura 無頭瀏覽器工具」）。 |
| SSL 錯誤 `CERTIFICATE_VERIFY_FAILED` | 已知問題（見 §5），build 已改走 curl；若你改動 `cwa.py` 的 `_get_json`，**不要改回 urllib**。 |

## 5. 已知陷阱（2026/8/26 實測確認）

1. **Python 3.14 的 urllib 對 CWA 憑證鏈 SSL 驗證失敗**（Missing Subject Key Identifier）→
   `build/cwa.py` 的 `_get_json` 用 `curl` subprocess，維持現狀。
2. **CWA 回傳結構與官方文件不同**（實測差異）：
   - `W-C0034-005`：`records.TropicalCyclones.TropicalCyclone[]`（多一層）；
     移動欄位是 `MovingSpeed/MovingDirection`；風圈 `Circle15ms/Circle25ms = {Radius: str}`。
   - `W-C0034-001`：CAP `parameter = [{valueName, value}]`；「解除」狀態看
     `typhoon-info` sections 的「警報類別」`END`（`alert_title` 含「解除」亦可）。
   - `W-C0033-002`：`validTime = {startTime, endTime}`（無時區，視同 +08:00）；
     影響區域在 `hazard[].info.affectedAreas.location[].locationName`。
   - `O-A0002-001`：`Now.Precipitation` = **本日 0 時至目前累計**（不是 1 小時雨量）；
     1 小時用 `Past1hr`。值全為字串。
3. **`cwa_cache.json` 會把最後一次成功資料寫入本地**——gitignored，不要把它加進 commit；
   快取值為 `null`/缺失時 `cwa.py` 會跳過該來源，屬預期行為。
4. 公開 GitHub repo 只應收到 `public/` 靜態產物，**不收 markdown 原文與 build 腳本**
   （金鑰不進輸出已驗證，但流程上仍分開）。

## 6. 部署

- **內部**（目前唯一）：`git push origin main` → Forgejo（`ssh://fg/lawliet/Weather.git`）。
- **GitHub Pages**（公開，尚未建立）：
  - 公開 repo 只放 `public/` 內容（站點根目錄），build 產物已是相對路徑、可直接放子路徑。
  - 目前手動：本機 build → 推靜態產物到 Pages 分支。
  - 後續可加 GitHub Actions（見 §7）。

## 7. 未來：agent 自動更新 + GitHub Actions（設計意向，未實作）

- **更新 agent**：負責「查 CWA API/新聞 → 更新 markdown → build → push」。
  輸入就是本文件 §1～§3；agent 不需懂解析細節，照 check 清單驗收即可。
- **GitHub Actions 三種用法**（依風險由低到高，屆時再選）：
  1. **純部署**：靜態產物 push 到 Pages 分支時自動 publish（Pages 內建，零設定）。
     金鑰完全不碰 GitHub。
  2. **CI 跑 build**：build 在 Actions 執行，`CWA_API_KEY` 放 GitHub secret。
     輸出仍靜態、金鑰不進產物，但金鑰會出現在 CI 環境——權衡後再定。
  3. **定時排程（cron）**：自動每週/每日 build。⚠️ 與現行「手動更新」原則衝突，
     啟用前需重新拍板 TODO.md 的核心原則。

---

## 附：快速指令參考

```bash
./build/build.sh                          # 完整 build（抓 CWA + 產出 public/）
cd public && python3 -m http.server 8080  # 本機預覽
git log --oneline -5                      # 近期更新紀錄
```
