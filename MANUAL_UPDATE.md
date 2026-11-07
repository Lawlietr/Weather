# 手動更新指南（Manual Update）

本文件記錄「改完災情／颱風 markdown → build → 部署上線」的完整手動流程。
自動化排程與完整 runbook 見 `WORKFLOW.md`（**本地 cron 是唯一的自動通道**，GitHub Actions 已完全不使用；cron 細節見 `LOCAL_CRON.md`）。

> 快速版：改完 markdown 後只跑一支指令即可上線：
> ```bash
> ./build/deploy.sh
> ```
>
> **環境現況（2026-11-07）**：公開網站**只由 Cloudflare Pages 提供**（自訂域名 ×3）。
> GitHub Pages 鏡像已停用（不再推 `gh-pages`）、GitHub Actions 已完全不使用（`build.yml` 已刪）。
> 金鑰存在本機 `~/.zshrc.secrets`（手動與 cron 同一來源）。
> 三個 git remote（Forgejo／GitHub／Codeberg）的 **repo 代碼與 markdown** 仍同步推 `main`，
> 但那只是版本控制，**不產生網站**。

---

## 0. 環境設定（接手時先跑一次）

```bash
# 1) 金鑰（已設在 ~/.zshrc.secrets，由 ~/.zshrc source；若沒有，手動 export）
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
./build/deploy.sh                       # 完整：build ＋ 部署到 Cloudflare Pages
./build/deploy.sh --build-only          # 只 build，不部署
./build/deploy.sh --no-cf               # 不部署任何一站（等同只 build）
./build/deploy.sh --gh                  # 額外推 GitHub Pages 鏡像（已停用，見 §5）
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
> 每次修改檔案，把檔首基本資料表上方的**那一行** `最後修改：YYYY/M/D HH:mm` **原地更新**
> （**不要新增行**，舊慣例已廢）；新進展**附加**在檔尾，不覆寫。

### 2.2 事件狀態生命周期

完整規則（含 ended→active 復活）見 `WORKFLOW.md` §2.2。簡版：事件結束後把
`status` 改為 `ended`，重 build，Hero 自動切到下一個 active 事件。

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
| CWA 回傳結構變動（KeyError／欄位缺失） | **先 dump 真實回傳結構再改解析**，勿照舊文件猜。差異對照見 `build/CWA_API.md` 與 `WORKFLOW.md` §5。 |
| SSL 錯誤 `CERTIFICATE_VERIFY_FAILED` | 已知問題，build 已改走 curl；改 `cwa.py` 的 `_get_json` 時**不要改回 urllib**。 |
| `wrangler` 找不到 | 用 `npx -y wrangler@latest …`（本機已裝 node，或 npx 自動抓）。cron 的 PATH 已內建 node 候選路徑（見 `LOCAL_CRON.md` §6 第 7 條）。 |
| 執行 `--gh` 時 push 被拒 | 確認已 `source ~/.zshrc.secrets`、本機 `github` remote 的 SSH 可用（或設 `GH_PAT` 走 token）。 |
| deploy.sh 說缺少環境變數 | 重開 shell，或 `source ~/.zshrc.secrets` 讓金鑰生效。 |

---

## 5. 部署說明（唯一通道＝Cloudflare Pages）

### Cloudflare Pages
- 專案：`weather`，自訂域名 `weather.avpclub.eu.org`、`weather.avpclub.uk`、`weather.larch.dpdns.org`（皆 proxied、自動 HTTPS）。
- 更新：`npx -y wrangler@latest pages deploy public --project-name weather --branch main`
- 憑證：`CLOUDFLARE_API_TOKEN`＋`CLOUDFLARE_ACCOUNT_ID`（在 `~/.zshrc.secrets` 憑證集中檔，不進 repo）。

### GitHub Pages（2026-11-07 起停用，不再是部署目標）
- `deploy.sh` 預設**不推** `gh-pages`；镜像站 `lawlietr.github.io/Weather/` 的内容停在最後一期（2026-11-07）。
- 为何停用：推 `gh-pages` 會觸發 GitHub 為 branch 來源 Pages 內建的 `pages build and deployment` workflow（Actions 分頁每 2 小時出現一期、易误判為「另有自動部署」），而該镜像不是正式管道、也不影響三個正式域名。
- 真的要重建镜像：先在 GitHub repo 重新啟用 Pages（branch 來源 `gh-pages`），再跑 `./build/deploy.sh --gh`（憑證优先序：`GH_PAT` → 本機 `github` remote 的 SSH）。

> 只有一邊要上線：`public/` 只推 Cloudflare Pages。

> ⚠️ `deploy.sh` 完成訊息與站內 canonical URL 都以 Cloudflare 域名為準；`llms.txt`／`llms-full.txt` 的 canonical base 也是 `https://weather.avpclub.eu.org`（`build/site.py` 的 `SITE_BASE`）。

---

## 6. 排程自動化（選用，非本文件範圍）

- **本地 cron（唯一自動通道）**：本機（部署機 `192.168.100.14`）每 2 小時跑 `build/deploy-cron.sh` → `deploy.sh` → Cloudflare Pages。需該機器常醒著；安裝/停用/自檢 → `LOCAL_CRON.md`。
- **GitHub Actions：不使用**（2026-11-07 刪除 `.github/workflows/build.yml`）。scheduler 不可靠（2026-10-23 實測 24 期只跑 10 期、間隔 185–424 分）。
- **災情更新**：由 LLM Agent 在有颱風／災害時觸發（查資料 → 更新 markdown → build → push），平常不自動跑。

---

## 附：快速指令速查

```bash
./build/build.sh                          # 完整 build（抓 CWA + 產出 public/）
./build/deploy.sh                         # build ＋ 部署到 Cloudflare Pages
./build/deploy.sh --build-only            # 只 build
cd public && python3 -m http.server 8080  # 本機預覽
grep -rl 'CWA_API_KEY\|CLOUDFLARE' public/ # 金鑰零外洩檢查（應無輸出）
```
