# design/cf-cron.md — 排程／部署改到 Cloudflare 的評估（**未實作**）

> 狀態：**僅評估記錄，2026-10-23 定案「不做」**。触发缘由＝GitHub Actions 排程名存實亡。
> 對應動作（已執行）：Actions `schedule:` 停用 → 見 `.github/workflows/build.yml`；
> 本地 cron 改**每小時** → 見 `build/cron.txt`、`LOCAL_CRON.md`。
> 最後更新：2026-10-23 10:40

---

## 1. 動機：Actions 排程實測（2026-10-23 查，近 2 天 30 筆 run）

| 項目 | 實測 | 應有 |
|---|---|---|
| schedule 觸發次數（2 天） | **10 次** | 24 次 |
| 相鄰 schedule 間隔 | **185–424 分** | 120 分 |
| 每次 run 耗時 | 2.5–3.4 分鐘 | — |
| 對照：本地 cron | 每 2 小時 `:00:01` 起跑、**10/10 全部 END 成功**、历時 33–58 秒 | — |

GitHub 2026 年确有排程大面積延遲／靜默丢單的公開回報（orgs/community discussion #201472：延遲 5–7 小時、整期漏跑；Status page 曾示「平均延遲約 3 小時」）。
→ **結論：`schedule:` 是 GitHub 側排程器的可靠度問題，非本 repo 設定問題。**

---

## 2. 「直接在 CF Worker 裡跑 build」＝硬性不可行（四個阻擋點）

| 阻擋點 | 本專案現況 | CF 限制（2026-10 官方文件） |
|---|---|---|
| CPU 時間 | build＋部署 本地 ≈40 s、Actions ≈2.5–3.4 min | Workers **Free：Cron Trigger 每次 10 ms**；Paid：間隔 <1 h 給 30 s、≥1 h 給 15 min |
| 對外請求數 | CWA 多 dataset＋cbph＋DGPA CAP＋RSS＋**967 張離線瓦片** | Free **50 subrequest/次**（Paid 10,000）→ Free 連抓瓦片都不可能 |
| 檔案系統 | `site.py`/`cwa.py`/`tiles.py`/`map_page.py` 全程 `pathlib`、產出 1007 檔 | Worker 無 FS；**Python Workers 走 Pyodide（WASM）**，改寫＝全部 I/O 換成 R2/Assets（≈10 模組重寫） |
| GitHub Pages mirror | `deploy.sh` 以 `git push -f` 推 orphan `gh-pages` | Worker 無法跑 git，只能改 GitHub Contents API（每輪約 1000 檔 tree，脆弱） |

其他事實：
- Pages build image **預裝 Python 3.13.3**（可用 `.python-version`／`PYTHON_VERSION` 指定）→ Python 專案可在 Pages build 內跑，但**不在 Worker 內**。
- Pages build 限制：**timeout 20 分鐘**、Free **500 builds/月、1 併發**（Pro 5,000／5 併發）。
- Pages Direct Upload（現行 `weather` 專案用法）上限 **20,000 檔／單檔 25 MiB** → 本站 `public/` 1,007 檔、12 MB，遠低於上限。
- 現有 `weather`／`wea-testing` 專案 **`build_configs: None`＝Direct Upload**，**不能原地轉 git-backed build**，需新建專案並重掛 3 個自訂域名。
- Cloudflare **Containers 需 Workers Paid（$5/月）**，另依 10 ms 計費 vCPU／記憶體，且另計 Durable Objects；image storage 50 GB/帳號。
- 本帳號已有 4 支 Worker（Free：Worker 上限 100、**cron trigger 上限 5 個/帳號**）。API token 看不到帳號方案（`/accounts/../subscriptions` 權限不足）→ **Free／Paid 需在後台自行確認**。

---

## 3. 三個可行變體（若將來要搬）

| 變體 | 做法 | 改動量 | 成本 | 判定 |
|---|---|---|---|---|
| **A. CF Worker Cron → 打 GitHub dispatch** | 幾十行的 Worker，`scheduled()` 對 GitHub `workflow_dispatch`／`repository_dispatch` 發一次 POST（PAT 存 Worker secret）。排程交给 CF（UTC 執行），compute 留 Actions，且走一般 job 佇列而非排程佇列 | 極小：加 1 支 Worker；`build.yml` 保留 `workflow_dispatch` | $0（Free Workers 即可，一次 fetch 的 CPU 遠小於 10 ms） | 若要恢復 Actions Compute，這是**首選修法** |
| **B. git-backed Pages build ＋ Deploy Hook** | 新建 git-backed Pages 專案（build command `bash build/build.sh`、output `public`），CF Worker Cron POST Deploy Hook URL 觸發 build（不需每輪 commit） | 中：新建專案＋改域名；**967 張瓦片（11 MB）必須進 repo 或改放 R2**（現行 `public/`、`build/_tile_cache/` 皆 gitignore）；gh-pages 要在 build 內用 `GH_PAT` push | $0，但 Free 500 builds/月 → 每 2 h（360/月）很緊，需改每 3 h（240/月） | 只有「把 compute 也搬離 GitHub」才值得 |
| **C. Cloudflare Containers** | Docker 化現有 Python build，Worker Cron 啟動 container session（有真實 FS／CPython，程式碼 1:1） | 中（image 推送管線、DO 綁定、image storage） | **需 Workers Paid $5/月** ＋ 容器與 DO 計費 | 40 秒批次任務用容器＝殺雞用刀，**不建議** |

### 變體 B 的待驗證項（做之前必須先測）
1. **CF 出口 IP 能否連 CWA Open Data／cbph／DGPA**（未驗證；CWA 可能對 datacenter IP 限流）。
2. **OSM 瓦片**：`tile.openstreetmap.de` 對 CF build IP 可否抓；且**每輪重抓 967 張違反社群 tile server 用量政策** → 必須改為 repo 內建或 R2 託管。
3. Pages Free **500 builds/月**額度與手動 build 互相排擠。
4. 域名搬遷（3 個自訂域名重新掛新專案）與 `wea-testing` 測試站的對應做法。
5. **AGENTS 落差**：本條已記於 `WORKFLOW.md` §5-4「公開 GitHub repo 只應收到 `public/` 產物，不收 markdown 原文與 build 腳本」，但**實測 `build/` 已在公開 GitHub `main` 的 tree 裡**。走 B 時 CF 必須能讀原始碼 → 要嘛正式修改該規則、要嘛把 repo 轉私有再接 Pages（並處理 Forgejo→GitHub 同步）。

---

## 4. 現行定案（2026-10-23 起）

- **唯一自動通道＝本地 cron，每小時整點**（`0 * * * *`，Asia/Taipei）。颱風期間提高頻率；平日是否降回每 2 小時另行決定。
- **Actions `schedule:` 已移除**，只留 `workflow_dispatch` 手動按鈕（不會自己跑）。
- **未實作任何 CF 側東西**（無 Worker、無新 Pages 專案、無 Cron Trigger）。
- 日後若要重啟此案，先決定：(a) 只要「準時觸發」→ 變體 A；(b) 要「compute 也離開 GitHub」→ 變體 B 並先跑上面 5 項驗證。

### 顺帶記錄（本次評估發現、尚未處理）
- `build/deploy.env` 未設 `GH_PAT` → cron 每次都 `--no-gh`，**GitHub Pages mirror 只在手動部署時更新**（最近一次 cron 皆顯示「跳過 GitHub Pages」）。若要 mirror 同步，需補 `GH_PAT` 或改用 github remote 直推邏輯。
