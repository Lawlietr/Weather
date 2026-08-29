# WORKFLOW：更新與部署工作流（Runbook）

> **讀者**：接手本專案的 agent 或人工操作者。
> **定位**：「怎麼做」的逐步流程。專案規範（檔案格式、CWA API 結構、設計原則）在
> `AGENTS.md` 與 `TODO.md`，本文件不重複，只引用。
> 最後更新：2026/8/28
> 
> **環境現況（2026/8/27）**：GitHub repo `Lawlietr/Weather` **已設為公開**（原私有）；`CWA_API_KEY`、
> `CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID` 已存入 **GitHub Actions Secrets**。公開網站由
> **Cloudflare Pages** 提供；GitHub Pages 已轉公開 mirror。Forgejo 與 GitHub **main 同步**（`git push origin main && git push github main`）。

---

## 0. 環境設定（接手時先跑一次）

1. 確認金鑰在環境變數中：
   ```bash
   python3 -c "import os; [print(k, 'OK' if os.getenv(k) else 'MISSING') for k in ('CWA_API_KEY','CLOUDFLARE_API_TOKEN','CLOUDFLARE_ACCOUNT_ID')]"
   ```
   若 MISSING：請使用者寫入 `~/.zshrc`（`export ...="..."`）或專案 `.env`（需在 `cwa.py` 加載入邏輯）。
   **手動路徑金鑰絕不可 commit。** 排程/CI 路徑的金鑰則存於 **GitHub Actions Secrets**
   （`gh secret list --repo Lawlietr/Weather` 檢視），不寫進程式碼。
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
⑥ 將 public/ 產物推到公開託管：Cloudflare Pages（`npx wrangler pages deploy public --project-name weather`）＋ GitHub Pages orphan 分支（步驟見 §6）
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
  severity: 🔴重大      # 🔴重大 | 🟡警戒 | 🟢一般（歷史分級；事件結束後不降級）
  counties: [南投, 屏東, ...]
  summary: 一兩句摘要
  sources: [新聞來源與日期]
  ---
  ```

### 2.2 事件狀態生命周期
- 事件發生 → 建檔，`status: active`。
- 首頁 Hero 區自動取 active 中「最後修改」最新者（`build/site.py` 邏輯，勿手動改首頁 HTML）。Hero 為**中性入口卡**（無 severity 色系/徽章）——「現在危不危險」由頂部「目前風險狀態列」回答。
- **目前風險狀態列**（red/yellow/green/unknown）：由 `build/cwa.py: current_risk_level()` 自動推導（生效中熱帶氣旋、未解除海上颱風警報、未解除災害天氣特報；已解除/END 跳過，雨量觀測值不計）。不需人工維護、不受事件 `status`/`severity` 影響——事件 ended 後若 CWA 仍有警報/特報，風險列仍會顯示 red。
- 事件結束後 → 把該檔 front matter 改為 `status: ended`，重 build；事件自動降級到 archive。`severity` 保留歷史分級不降級（徽章只顯示在事件詳情頁與封存清單）。

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
# ④ 雙語言輸出確認（兩套根頁都存在、語言切換連結正確）
ls public/index.html public/ja/index.html
# ⑤ 風險狀態列（由 CWA 自動推導；應與 build 日誌「目前風險：xxx」一致）
grep -o 'risk-bar risk-[a-z]*' public/index.html | head -1
# ⑥ 瀏覽器預覽（重點：風險狀態列、首頁 Hero、CWA 區塊、手機寬度、兩套主題、/ja/ 版）
cd public && python3 -m http.server 8080
```

## 4. 失敗處理

| 症狀 | 處置 |
|------|------|
| build 顯示「CWA none」 | 金鑰或網路問題。查 `CWA_API_KEY`、`curl` 直連測試。頁面會顯示 `cwa-fail` 警示卡，**不要**把警示卡 commit 進公開站（除非確實要公告資料中斷）。 |
| build 顯示「CWA partial」 | 單一來源失敗，其餘用快取舊值＋「舊資料」標註。重試一次；若持續，記錄是哪個 Data ID（錯誤訊息會寫出）。 |
| CWA 回傳結構變動（KeyError/欄位缺失） | **先 dump 真實回傳結構再改解析**，勿照舊文件猜。結構差異對照表在 `build/CWA_API.md`「實測差異」與本文件 §5。 |
| build 崩潰 `NoneType.__format__`（如 `:.1f`） | CWA forecast 欄位（`MaxWindSpeed`、`Pressure` 等）可能回傳 `null`。**格式化前必做 `None` 檢查**，參考 `build/cwa.py` L457-459 寫法。 |
| 需要爬 CWA 官網頁面（API 沒有該產品） | 用 Obscura（見 skill `/root/.pi/agent/skills/obscura/SKILL.md`，repo 相關頁面見 AGENTS.md「Obscura 無頭瀏覽器」）。 |
| SSL 錯誤 `CERTIFICATE_VERIFY_FAILED` | 已知問題（見 §5），build 已改走 curl；若你改動 `cwa.py` 的 `_get_json`，**不要改回 urllib**。 |

## 5. 已知陷阱（2026/8/26–8/27 實測確認）

1. **Python 3.14 的 urllib 對 CWA 憑證鏈 SSL 驗證失敗**（Missing Subject Key Identifier）→
   `build/cwa.py` 的 `_get_json` 用 `curl` subprocess，維持現狀。
2. **CWA 回傳結構與官方文件不同**（實測差異）：
   - `W-C0034-005`：`records.TropicalCyclones.TropicalCyclone[]`（多一層）；
     移動欄位是 `MovingSpeed/MovingDirection`；風圈 `Circle15ms/Circle25ms = {Radius: str}`。
   - `W-C0034-001`：CAP `parameter = [{valueName, value}]`；「解除」狀態看
     `typhoon-info` sections 的「警報類別」`END`（`alert_title` 含「解除」亦可）。
     ⚠️ 警報**全文不在 `typhoon-info`**（那裡只有「警報報數／警報類別／颱風編號」
     等元數據），實際內文在 `description.section[]`（命名與位置、強度與半徑、
     移速與預測、颱風動態、警戒區域及事項…等 8 個 section）。
   - `W-C0033-002`：`validTime = {startTime, endTime}`（無時區，視同 +08:00）；
     影響區域在 `hazard[].info.affectedAreas.location[].locationName`。
   - `O-A0002-001`：`Now.Precipitation` = **本日 0 時至目前累計**（不是 1 小時雨量）；
     1 小時用 `Past1hr`。值全為字串。
3. **`cwa_cache.json` 會把最後一次成功資料寫入本地**——gitignored，不要把它加進 commit；
   快取值為 `null`/缺失時 `cwa.py` 會跳過該來源，屬預期行為。
4. 公開 GitHub repo 只應收到 `public/` 靜態產物，**不收 markdown 原文與 build 腳本**
   （金鑰不進輸出已驗證，但流程上仍分開）。
5. **Actions 排程已停用（2026/8/29）**：GitHub Actions **已移除 `schedule`**，僅保留 `workflow_dispatch`（手動觸發）。
   停用原因：Actions runner（Azure `westus2`）到 CWA API 連線不穩定（curl 超時），
   導致 build 使用舊資料卻仍部署。`build/build.sh` 現已加入 CWA 前置檢查（3 次重試，
   失敗則 `exit 1` 阻止部署）。
   若需手動跑 Actions build：到 GitHub repo → Actions tab → "Build & Deploy" → "Run workflow"。
   本地 cron 備用（`build/deploy-cron.sh`，每 2 小時，`build/cron-enable.sh` 安裝）為主要自動更新通道。
   > 若日後要恢復 Actions 排程：確認 CWA API 可從海外連線（或改用 Cloudflare Worker 等中轉），
   > 再把 `schedule` 加回 `.github/workflows/build.yml` 即可。
6. **Cloudflare token 限區域或失效**：code 9109。去 CF 後台重開 token 並更新 GitHub Secret 即可；
   或改用本地 cron 備用（`build/cron-enable.sh`）。
7. **「產生時間」時區陷阱**：`build/site.py` 必須保持
   `datetime.now(timezone(timedelta(hours=8)))`（固定 UTC+8）。若改回不帶時區的 `datetime.now()`，
   本機（`Asia/Taipei`）build 時間正確，但 **Actions runner 是 UTC，會慢 8 小時**（2026/8/27 曾發生）。
   手動部署若發現右上角時間錯誤，多半是 Actions（UTC）跑的，下次或本機 build 即恢復。

## 6. 部署

> ⚡ 手動更新請直接看 `MANUAL_UPDATE.md`，部署用 `build/deploy.sh`（一支指令 build + 推 CF 與 GitHub Pages）。

- **內部**：`git push origin main` → Forgejo（`ssh://fg/lawliet/Weather.git`）。
- **GitHub Pages**（公開，2026/8/26 已上線）：
  - 站點：<https://lawlietr.github.io/Weather/>（繁中）、`/ja/`（日文）。
  - 公開 repo：`Lawlietr/Weather`（本機 remote 名 `github`）。**只收 `public/` 內容**：
    orphan `gh-pages` 分支、不與 main 共享 history（Markdown 原文、build 腳本、內部倉庫資訊一律不外流）。
  - 更新推送：
    ```bash
    ./build/build.sh
    TMP=$(mktemp -d) && rsync -a --delete --exclude '.DS_Store' public/ "$TMP/"
    git -C "$TMP" init -q -b gh-pages && git -C "$TMP" add -A
    git -C "$TMP" commit -q -m "site update: $(date +%Y/%m/%d)"
    git -C "$TMP" push -f "https://github.com/Lawlietr/Weather.git" gh-pages
    rm -rf "$TMP"
    ```
    （每次在乾淨暫存目錄重做 orphan commit＋force push，簡潔且保證 gh-pages 只含 `public/`。）

- **Cloudflare Pages**（公開，2026/8/26 已上線，**主要更新通道**）：
  - 專案：`weather`（子域名 `weather-9kb.pages.dev`），自訂域名 ×3（皆已掛上，proxied on、自動 HTTPS）：
    - `weather.avpclub.eu.org`
    - `weather.avpclub.uk`
    - `weather.larch.dpdns.org`
  - **更新只需一條指令**（不需再碰 DNS，CNAME 已固定指向專案）：
    ```bash
    npx -y wrangler@latest pages deploy public --project-name weather
    ```
    需環境變數 `CLOUDFLARE_API_TOKEN`＋`CLOUDFLARE_ACCOUNT_ID`（已設在 `~/.zshrc`，金鑰不進 repo）。
  - 自訂域名 DNS 紀錄（如重建需重設）：三個 zone 各一筆 CNAME `weather.* → weather-9kb.pages.dev`（proxied on）。
  - 與 GitHub Pages 為**同一份 `public/` 的平行託管**；兩边都要更新時，先 build 一次、再分別跑上面的兩個推送流程。

## 7. 排程與自動更新

- **手動**：`MANUAL_UPDATE.md`（改 markdown → `./build/deploy.sh` → 上線）。
- **本地 cron（主力，每 2 小時）**：本機或 Ubuntu LXC/VM 排 `build/deploy-cron.sh`。
  - **安裝**：`bash build/cron-enable.sh`（冪等，重複執行會覆蓋舊排程）。
  - **停用**：`bash build/cron-disable.sh`。
  - **自檢**：`bash build/deploy-cron.sh --selfcheck`（驗證金鑰與網路，不部署）。
  - **金鑰**：`build/deploy.env`（gitignore、600，由 `deploy-cron.sh` 載入；cron 不載入 `.zshrc`）；需該機器常醒著。
  - **CWA 檢查**：執行前會先檢查 CWA 可用性（3 次重試，失敗中止），不會推舊資料。
  - **日誌**：全程寫入 `build/logs/deploy-cron-YYYY-MM-DD.log`，方便除錯。
- **GitHub Actions（手動 dispatch，備援）**：僅保留 `workflow_dispatch`（2026/8/29 起停用排程）。
  到 GitHub repo → Actions tab → "Build & Deploy" → "Run workflow"。
- **更新 agent**：負責「查 CWA API/新聞 → 更新 markdown → build → push」。
  輸入就是本文件 §1～§3；agent 不需懂解析細節，照 check 清單驗收即可。
- **地圖紅警層（CWA，2026/8/28 定案，待實作）**：全自動——build 時抓 CWA（特報/雨量站/氣旋）合成 `map.geo.json` 與地圖頁，掛在**現有每 2 小時排程**上，不新增排程/agent/金鑰；陸地紅區靠 gazetteer（鄉鎮級靜態 JSON，存 repo）轉換特報文字。細節見 `TODO.md` §2a；災情新聞點層（§2b）維持人工把關。

---

## 8. Agent 效率規範（2026/8/28 血淚教訓：一次災情更新花了 1 小時）

**核心原則：先查既有資料，再決定要不要重新抓。重複查詢是浪費金錢（token/API 額度）。**

1. **開工前必查三處（按順序，找到就停）**：
   1. **repo 現有檔案**：`颱風/` `災情/` 裡的既有事件檔已含軌跡、警報時程、雨量——更新時**只補差異**，不重寫既有內容。
   2. **context-mode 知識庫**：`ctx_search`（前幾天的 API 結構、抓取結果都自動存了）；`ctx_stats` 可看存了什麼。
   3. **`cwa_cache.json`**（gitignored 本機快取）：上一次 build 的 CWA 資料。
2. **只查會變的**：颱風位置/強度（每 3~6 小時才變）、當前警報狀態（`Warning_Content.js` 或 W-C0034-001 最後一報）、當日雨量。**不重查**：生成時間、歷史軌跡（已入檔）、API 結構（已入檔＋§5）、RSS 來源清單（`build/rss_sources.json`）。
3. **同一資料一個 session 只查一次**：查到的 JSON 存 `/tmp`，後續用本機檔案處理（python），不重複 curl/RSS 全量掃描。
4. **RSS 掃描一次就夠**：關鍵詞命中 0~2 條即停，不要換關鍵詞重掃、不要同一 feed 掃多輪。
5. **寫檔一次成型**：長內容分段寫或先存 `/tmp` 再 `cp`，避免 write 工具 output token 截斷重來（8/28 實測發生）。
6. **完成定義**：git status 乾淨（或 diff 已確認）＋ build ＋ deploy ＋ 推 `origin` 與 `github`。deploy 之後不要再做「驗證」式查詢。

## 附：快速指令參考

```bash
./build/build.sh                          # 完整 build（抓 CWA + 產出 public/）
cd public && python3 -m http.server 8080  # 本機預覽
git log --oneline -5                      # 近期更新紀錄
```
