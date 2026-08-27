# LOCAL_CRON.md：本地自動部署（GitHub Actions 備用）

> **定位**：當 GitHub Actions 排程異常時，本機（Ubuntu LXC）的 cron 作為**替代自動部署**。
> **預設「不啟用」**：cron 工作項目默认未安裝，只有 Actions 異常時才手動開啟。
> 最後更新：2026/8/27

---

## 一、這是什麼

在機器本地排 `build/deploy.sh`（抓 CWA → build → 推 Cloudflare Pages ＋ GitHub Pages），
對齊 Actions 的排程：**每 2 小時一次（一天 12 次）**。

與 Actions 的不同：

| | GitHub Actions | 本地 cron（本備用） |
|---|---|---|
| 金鑰 | GitHub Secrets | `build/deploy.env`（本機，gitignore，600） |
| git 憑證 | Actions env | 本機已設定（Forgejo SSH / GitHub 視 GH_PAT） |
| 依賴 | GitHub 伺服器 | **本機需保持醒著** |
| 啟用 | 一直跑 | **預設關閉，手動開啟** |

---

## 二、檔案對照

| 檔案 | 用途 |
|---|---|
| `build/deploy.env` | 本地金鑰（`CWA_API_KEY`、`CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID`，選用 `GH_PAT`）。**gitignore，不進 repo**，權限 600。 |
| `build/deploy-cron.sh` | cron 進入點。載入 `deploy.env`、`flock` 防重疊、跑 `deploy.sh`、寫 `build/logs/`。支援 `--selfcheck`。 |
| `build/cron.txt` | crontab 內容（排程行）。 |
| `build/cron-enable.sh` | **安裝** cron（對 Actions 備用）。冪等。 |
| `build/cron-disable.sh` | **停用** cron。冪等。 |
| `build/logs/` | 每次執行的日誌 `deploy-cron-YYYY-MM-DD.log` ＋ crontab 備份。gitignore。 |

---

## 三、使用流程

### 準備（接手時一次，或金鑰移動後）
金鑰已從 `~/.zshrc` 複製到 `build/deploy.env`（若遺失，手動寫入後 `chmod 600`）。

### Actions 異常時 → 開啟備用
```bash
# 1. 先自檢（驗證金鑰與網路，不部署）
bash build/deploy-cron.sh --selfcheck

# 2. 開啟 cron（首次會跑 selfcheck，通過後直接安裝；未通過會問你是否繼續）
bash build/cron-enable.sh

# 確認
crontab -l
```
之後每 2 小時（台灣時間）自動 build＋部署，日誌見 `build/logs/deploy-cron-*.log`。

### Actions 復原 → 停用備用
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

## 四、部署範圍預設

- **未設 `GH_PAT`** → cron 只推 **Cloudflare Pages**（`--no-gh`）。
  Cloudflare 是主要公開通道；GitHub Pages 已轉私有 mirror 且目前 404，非必需。
- **設了 `GH_PAT`** → cron 完整部署（Cloudflare ＋ GitHub Pages）。

---

## 五、排程細節

- 排程（`build/cron.txt`）：`0 */2 * * *`（台灣時間，每 2 小時；Actions 側等價 `0 */2 * * *` UTC）。
- 機器時區 `Asia/Taipei`（UTC+8），cron 直接用本地時間。
- `deploy-cron.sh` 用 `flock`（`/tmp/weather-deploy.lock`）防止兩次重疊。
- 日誌依天切檔：`build/logs/deploy-cron-YYYY-MM-DD.log`。

---

## 六、注意事項

1. **本機需保持醒著**；休眠/關機期間的排程不會補跑（cron 非 systemd timer 的 missed-run 補執）。
2. **金鑰安全**：`build/deploy.env` 權限 600、gitignore，絕不 commit。若懷疑洩漏，請到 Cloudflare/CWA 後台重設並更新此檔。
3. **Actions 與 cron 不要同時開**，否則一天會部署多次（Cloudflare 會重複 publish，無害但浪費）。
4. Actions 偶發失敗 99% 是 Cloudflare token 限區域或失效；用 `--selfcheck` 可先確認是 token 問題還是本機問題。
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
