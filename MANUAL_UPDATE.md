# 手動更新指南（Manual Update）

本文件記錄「改完災情／颱風 markdown → build → 部署上線」的完整手動流程。
自動化排程（GitHub Actions / cron）見 `WORKFLOW.md` §7。

> 快速版：改完 markdown 後只跑一支指令即可上線：
> ```bash
> ./build/deploy.sh
> ```

---

## 0. 環境設定（接手時先跑一次）

```bash
# 1) 金鑰（已設在 ~/.zshrc；若沒有，手動 export）
export CWA_API_KEY="你的_CWA_API_KEY"
export CLOUDFLARE_API_TOKEN="你的_CLOUDFLARE_API_TOKEN"
export CLOUDFLARE_ACCOUNT_ID="你的_CLOUDFLARE_ACCOUNT_ID"

# 2) 重新開 shell，或 source 一次
source ~/.zshrc

# 3) 確認金鑰就位
echo "${CWA_API_KEY:+CWA_OK} ${CLOUDFLARE_API_TOKEN:+CF_TOKEN_OK} ${CLOUDFLARE_ACCOUNT_ID:+CF_ACCOUNT_OK}"

# 4) Node（wrangler 用；已透過 homebrew 安裝）
which node npx          # 應該都回傳路徑
```

> ⚠️ 金鑰**只存在本機執行環境**：不寫進輸出檔案、不進 repo、不進公開網站。
> 本指南的 `deploy.sh` 會檢查這三個變數，缺任何一個就中止。

---

## 1. 例行更新流程（每次都要做）

```bash
cd /Users/lawliet/opencode-Stuffs/Weather

# ① build（抓 CWA + 產出 public/）
./build/build.sh

# ② 本機預覽確認（選做，Ctrl-C 結束）
cd public && python3 -m http.server 8080
#   瀏覽器開 http://localhost:8080，重點看：
#   - 首頁 Hero（active 事件是否正確）
#   - CWA 區塊（颱風軌跡圖、警報特報、雨量）
#   - 手機寬度、兩套主題、/ja/ 日文版

# ③ 部署到兩個公開託管（一支指令搞定）
../build/deploy.sh          # 或寫完整路徑 ./build/deploy.sh

# ④ 記錄 markdown 改版到內部 Forgejo（版本控制）
git add -A
git commit -m "更新：事件名稱（日期）"
git push origin main
```

### 用 `deploy.sh` 的進階選項

```bash
./build/deploy.sh                       # 完整：build + Cloudflare + GitHub Pages
./build/deploy.sh --build-only          # 只 build，不部署
./build/deploy.sh --no-cf               # build + GitHub Pages，跳 Cloudflare
./build/deploy.sh --no-gh               # build + Cloudflare，跳 GitHub Pages
./build/deploy.sh --preview             # build 後本機預覽，不部署
```

---

## 2. 新增／更新事件流程

### 2.1 新增事件檔案

- **颱風**：`颱風/{YYYY}/{MM}/{MMDD}_{NN}_{中文名}_{國際命名}.md`
  （範例：`颱風/2026/07/0702_09_巴威_BAVI.md`）
- **非颱風**（低壓帶、西南風、梅雨…）：`災情/{YYYY}/{MM}/{MMDD}_{事件類型}_{事件名稱}.md`
  （範例：`災情/2026/08/0821_低壓帶_南台灣大雨.md`）

> 🕐 **時間意識（極度重要）**：寫災情前**先確認現實時間**（`date`）。
> 只記錄「目前正在發生」的事件；引用新聞時確認時效性、註明出處與日期。
> 每次修改檔案，在檔首基本資料表上方新增一筆 `最後修改：YYYY/M/D HH:mm`。
> 新進展**附加**在檔尾，不覆寫。

### 2.2 事件狀態生命周期

事件結束（颱風遠離／雨勢停止）後：把檔案的 active 標記改為 ended，
再 build 一次，Hero 就會切到下一個 active 事件。

---

## 3. 驗證檢查清單（每次 build 後）

- [ ] 輸出含 CWA 模式（`build.sh` 尾端印出 active / ended 事件數）
- [ ] 內部連結 0 斷鏈（中文檔名需 URL decode）
- [ ] **金鑰零外洩**：`public/` 內搜 `CWA_API_KEY`／`CLOUDFLARE` 應為 0
  ```bash
  grep -rl 'CWA_API_KEY\|CLOUDFLARE_API_TOKEN' public/ 2>/dev/null | head
  ```
- [ ] 雙語言輸出：`public/index.html` 與 `public/ja/index.html` 都存在
- [ ] 瀏覽器預覽：Hero、CWA 區塊、手機寬度、兩套主題、/ja/ 版
- [ ] 台灣輪廓：颱風卡 SVG 含本島＋澎湖／金門／馬祖／蘭嶼／綠島（11 個 polygon）

---

## 4. 失敗處理

| 症狀 | 處理 |
|------|------|
| CWA 回傳結構變動（KeyError／欄位缺失） | **先 dump 真實回傳結構再改解析**，勿照舊文件猜。差異對照見 `AGENTS.md` 與 `WORKFLOW.md` §5。 |
| SSL 錯誤 `CERTIFICATE_VERIFY_FAILED` | 已知問題，build 已改走 curl；改 `cwa.py` 的 `_get_json` 時**不要改回 urllib**。 |
| `wrangler` 找不到 | 用 `npx -y wrangler@latest …`（本機已裝 node，或 npx 自動抓）。 |
| GitHub Pages push 被拒 | 確認已 `source ~/.zshrc`、git 憑證正常（Mac 用 keychain）。 |
| deploy.sh 說缺少環境變數 | 重開 shell 或 `source ~/.zshrc` 讓金鑰生效。 |

---

## 5. 部署說明（兩個公開託管）

### Cloudflare Pages（主要通道）
- 專案：`weather`，自訂域名 `weather.avpclub.eu.org`、`weather.avpclub.uk`、`weather.larch.dpdns.org`（皆 proxied、自動 HTTPS）。
- 更新：`npx -y wrangler@latest pages deploy public --project-name weather`
- 憑證：`CLOUDFLARE_API_TOKEN`＋`CLOUDFLARE_ACCOUNT_ID`（在 `~/.zshrc`，不進 repo）。

### GitHub Pages（平行託管）
- 站點：<https://lawlietr.github.io/Weather/>（繁中）＋ `/ja/`（日文）。
- 只收 `public/`：orphan `gh-pages` 分支、不與 main 共享 history。
- 推送：`deploy.sh` 已在乾淨暫存目錄重做 orphan commit＋force push。

> 兩者為同一份 `public/` 的平行託管；`deploy.sh` 一次更新兩邊。

---

## 6. 排程自動化（選用，非本文件範圍）

- **GitHub Actions**：在 GitHub 伺服器上排程，不依賴本機開著。見 `WORKFLOW.md` §7。
- **cron（unix）**：本機或 Ubuntu LXC/VM 上排 `deploy.sh`。需該機器常醒著。
- **災情更新**：由 LLM Agent 在有颱風／災害時觸發（查資料 → 更新 markdown → build → push），平常不自動跑。

---

## 附：快速指令速查

```bash
./build/build.sh                          # 完整 build（抓 CWA + 產出 public/）
./build/deploy.sh                         # build + 部署到 CF 與 GitHub Pages
./build/deploy.sh --build-only            # 只 build
cd public && python3 -m http.server 8080  # 本機預覽
grep -rl 'CWA_API_KEY\|CLOUDFLARE' public/ # 金鑰零外洩檢查（應無輸出）
```
