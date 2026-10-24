# LOCAL_CRON.md：本地自動部署（主力更新通道）

> **定位**：**本地 cron 是唯一自動 build＋部署通道**（本機＝**部署機 `192.168.100.14`**、Ubuntu LXC（hostname `hermes`）；2026-10-23 颱風期間改為**每小時**，2026-10-24 薔琵遠離後**降回每 2 小時**）。**本機 HEAD 常駐 `main`**：開發在另一台 `192.168.100.15` 的 `DEV` 分支，而 `build/deploy-cron.sh`/`deploy.sh` **不做 `git pull`**→ 開發機 merge 回 `main` 後，本機須 `git pull --ff-only origin main` 才會真正上線 → `WORKFLOW.md` §0.1。同日起 GitHub Actions 的 `schedule:` 已**完全移除**，僅留 `workflow_dispatch` 手動按鈕——因為 GitHub scheduler 實測不可靠（近 2 天 24 期只跑 10 期、間隔 185–424 分），詳 `.github/workflows/build.yml` 頭註與 `design/cf-cron.md`。
> 歷史：2026/8/29 Actions 曾因 CWA 回傳 `MaxWindSpeed=None` 崩潰而暫停（已修復）、2026/9/26 恢復；2026-10-23 因排程可靠度問题彻底停用。
> cron 工作項目以 `build/cron-enable.sh` 安裝（主力通道應常開）。
> 最後更新：2026-10-24（cron 降回每 2 小時）

---

## 一、這是什麼

在機器本地排 `build/deploy.sh`（抓 CWA → build → 推 Cloudflare Pages ＋ GitHub Pages），
**每小時一次（一天 24 次）**。執行前檢查 CWA 可用性（3 次重試，失敗則中止部署，不推舊資料）。

與 Actions 的對比（2026-10-23 實測數據）：

| | GitHub Actions（已停用排程，僅手動 dispatch） | 本地 cron（唯一自動通道） |
|---|---|---|
| 金鑰 | GitHub Secrets | `build/deploy.env`（本機，gitignore，600） |
| git 憑證 | Actions env | 本機已設定（Forgejo SSH / GitHub 直推） |
| 依賴 | GitHub 伺服器 | **本機需保持醒著** |
| 執行時間 | 約 3 分鐘 | 約 40 秒 |
| 排程 | ~~每 2 小時 `schedule:`~~ → 2026-10-23 移除（延遲 185–424 分、24 期只跑 10 期） | **每 2 小時整點（`0 */2 * * *`）**（2026-10-24 由每小時降回；薔琵期間曾升為每小時） |
| 啟用 | 僅手動（workflow_dispatch） | 常開（`cron-enable.sh` 安裝） |
| 備註 | 若要重新利用 Actions compute：用 CF Worker Cron 打 dispatch（首選修法，未實作）→ `design/cf-cron.md` | 10/10 次準時、历時 33–58 秒 |

---

## 二、檔案對照

| 檔案 | 用途 |
|---|---|
| `build/deploy.env` | 本地金鑰（`CWA_API_KEY`、`CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID`，選用 `GH_PAT`）。**gitignore，不進 repo**，權限 600。 |
| `build/deploy-cron.sh` | cron 進入點。載入 `deploy.env`、`flock` 防重疊、跑 `deploy.sh`、寫 `build/logs/`。支援 `--selfcheck`。 |
| `build/cron.txt` | crontab 內容（排程行）。 |
| `build/cron-enable.sh` | **安裝** cron（主力自動通道）。冪等。 |
| `build/cron-disable.sh` | **停用** cron。冪等。 |
| `build/logs/` | 每次執行的日誌 `deploy-cron-YYYY-MM-DD.log` ＋ crontab 備份。gitignore。 |

---

## 三、使用流程

### 準備（接手時一次，或金鑰移動後）
金鑰已從 `~/.zshrc` 複製到 `build/deploy.env`（若遺失，手動寫入後 `chmod 600`）。

### 開啟 cron（一次）
```bash
# 1. 先自檢（驗證金鑰與網路，不部署）
bash build/deploy-cron.sh --selfcheck

# 2. 開啟 cron（首次會跑 selfcheck，通過後直接安裝；未通過會問你是否繼續）
bash build/cron-enable.sh

# 確認
crontab -l
```
之後每小時（台灣時間整點）自動 build＋部署，日誌見 `build/logs/deploy-cron-*.log`。

### 暫時停用 cron
```bash
bash build/cron-disable.sh
crontab -l   # 確認 Weather 排程已移除
```

### 不想用 cron、只想手動
不裝 cron，直接跑（金鑰取自環境，或先 `source build/deploy.env`）：
```bash
source build/deploy.env
./build/deploy.sh            # 完整（CF + GitHub Pages）
./build/deploy.sh --no-gh    # 僅 Cloudflare
./build/deploy.sh --build-only
```
> 若需推私有 GitHub Pages mirror，需在環境設 `GH_PAT`（個人AccessToken），`deploy.sh` 會自動走 `x-access-token` 驗證。

---

## 四、部署範圍預設（2026-10-23 起）

- **cron 一律完整部署**：Cloudflare Pages ＋ GitHub Pages（orphan `gh-pages`）。
  以往 `GH_PAT` 未設就自動加 `--no-gh`，gh-pages 是靠 Actions 順手推的；**Actions 排程已停用，所以 gh-pages 必須由本地 cron 自己推**（否則 mirror 會開始變舊）。
- **推送憑證優先序**（`build/deploy.sh`）：`GH_PAT`（token HTTPS）→ 本機 `git remote github`（**SSH，現行 cron 就是靠這個，已實測 push 成功**）→ https 預設（credential helper）。repo 公開，不需要 `GH_PAT`。
- 只要 Cloudflare 時：手動跑 `./build/deploy.sh --no-gh`（cron 不再自動加此參數）。

---

## 五、排程細節

- 排程（`build/cron.txt`）：`0 */2 * * *`（台灣時間，**每 2 小時**；2026-10-23 颱風薔琵期間曾升為 `0 * * * *` 每小時，2026-10-24 薔琵遠離後降回每 2 小時）。Actions 側 `schedule:` 已移除，不再錯開、也不重複 publish。
- 機器時區 `Asia/Taipei`（UTC+8），cron 直接用本地時間。
- `deploy-cron.sh` 用 `flock`（`/tmp/weather-deploy.lock`）防止兩次重疊。
- 日誌依天切檔：`build/logs/deploy-cron-YYYY-MM-DD.log`。

---

## 六、注意事項

1. **本機需保持醒著**；休眠/關機期間的排程不會補跑（cron 非 systemd timer 的 missed-run 補執）。
2. **金鑰安全**：`build/deploy.env` 權限 600、gitignore，絕不 commit。若懷疑洩漏，請到 Cloudflare/CWA 後台重設並更新此檔。
3. Actions 已無自動排程（2026-10-23 起），不會再與 cron 撞車或重複 publish；只有手動 dispatch 時才會多一次。
4. Actions 偶發失敗 99% 是 Cloudflare token 限區域或失效；用 `--selfcheck` 可先確認是 token 問題還是本機問題（手動 dispatch 時同樣適用）。
5. cron 環境極簡（不載入 `.zshrc`），故金鑰必須在 `build/deploy.env`（由 `deploy-cron.sh` 載入），不要依賴 shell 環境變數。

---

## 七、除錯

```bash
# 看最近一次執行結果
tail -n 40 build/logs/deploy-cron-$(date +%F).log

# 手動跑一次（會實際部署，慎用）
source build/deploy.env
./build/deploy-cron.sh

# 確認 cron 是否已安裝
crontab -l | grep weather

# 手動 build 驗證（不部署）
./build/deploy.sh --build-only
```
