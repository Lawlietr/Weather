# LOCAL_CRON.md：本地自動部署（主力更新通道）

> **定位**：**本地 cron 是唯一自動 build＋部署通道**（本機＝**部署機 `192.168.100.14`**、Ubuntu LXC（hostname `hermes`）；2026-10-23 颱風期間改為**每小時**，2026-10-24 薔琵遠離後**降回每 2 小時**）。**本機 HEAD 常駐 `main`**：開發在另一台 `192.168.100.15` 的 `DEV` 分支，而 `build/deploy-cron.sh`/`deploy.sh` **不做 `git pull`**→ 開發機 merge 回 `main` 後，本機須 `git pull --ff-only origin main` 才會真正上線 → `WORKFLOW.md` §0.1。現行**只推 Cloudflare Pages**，且 **GitHub Actions 完全不使用**（2026-11-07 刪除 `.github/workflows/build.yml`）：scheduler 實測不可靠（近 2 天 24 期只跑 10 期、間隔 185–424 分），再也不會回來。GitHub Pages 鏡像（`gh-pages` 分支）也於 2026-11-07 停用 → §四。
> 排程頻率：2026-10-23 薔琵期間曾改為每小時，2026-10-24 起固定每 2 小時。
> cron 工作項目以 `build/cron-enable.sh` 安裝（主力通道應常開）。
> 最後更新：2026-11-07（只推 Cloudflare Pages；Actions 與 gh-pages 鏡像停用；`/tmp` 殘留與 npm 快取的自動清理 → §5.1、§6 第 9–10 條）

---

## 一、這是什麼

在機器本地排 `build/deploy.sh`（抓 CWA → build → 推 **Cloudflare Pages**），
**每 2 小時一次（一天 12 次）**。執行前檢查 CWA 可用性（3 次重試，失敗則中止部署，不推舊資料）。

為何不用 GitHub Actions（2026-10-23 實測數據，2026-11-07 正式移除 workflow）：

| | GitHub Actions | 本地 cron（現行唯一自動通道） |
|---|---|---|
| 排程準度 | 24 期只跑 10 期、間隔 185–424 分（應為 120 分） | **每 2 小時整點，10/10 準時** |
| 執行時間 | 約 3 分鐘 | 約 40 秒 |
| 金鑰 | GitHub Secrets（需與本機同步兩份） | `~/.zshrc.secrets`（600）；兜底範本＝`build/deploy.env.example` |
| 其他 | 無法推 git 鏡像（無 SSH key） | 本機需保持醒著 |

日后若要重新引入自動觸發，首選方案是用 Cloudflare Worker Cron 打一個手動觸發（**僅評估、未實作**）→ `design/cf-cron.md`。

---

## 二、檔案對照

| 檔案 | 用途 |
|---|---|
| `~/.zshrc.secrets` | **金鑰本體**（`CWA_API_KEY`、`CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID`，選用 `GH_PAT`）。不進 git、不同步、權限 600，由 `~/.zshrc` source 它（2026-10-29 定案：token 太多，不再塞 `~/.zshrc`）。 |
| `build/deploy.env.example` | 兜底檔**範本**（進 repo；內容全是註解佔位，不含金鑰）。要兜底時 `cp build/deploy.env.example build/deploy.env && chmod 600 build/deploy.env` 再填值——`deploy-cron.sh` 只在 `~/.zshrc.secrets`／`~/.zshrc`／`~/.bashrc` 都取不到金鑰時才 source 它。兩機目前已無 `build/deploy.env`（2026-10-31 刪除：開發機那份是失效 token、部署機那份是會以 `${VAR:?}` 中止腳本的模板）。缺鑰時 `deploy-cron.sh` 會先寫 `ERROR: 找不到金鑰 …` 進 `build/logs/` 再 exit 3。 |
| `build/deploy-cron.sh` | cron 進入點。依序 grep `~/.zshrc.secrets`→`~/.zshrc`→`~/.bashrc` 的 export 行取金鑰、`flock` 防重疊、跑 `deploy.sh`、寫 `build/logs/`。支援 `--selfcheck`。 |
| `build/cron.txt` | crontab 內容（排程行）。 |
| `build/cron-enable.sh` | **安裝** cron（主力自動通道）。冪等。 |
| `build/cron-disable.sh` | **停用** cron。冪等。 |
| `build/logs/` | 每次執行的日誌 `deploy-cron-YYYY-MM-DD.log` ＋ crontab 備份。gitignore。 |

---

## 三、使用流程

### 準備（接手時一次，或金鑰移動後）
金鑰放在 `~/.zshrc.secrets`（600、不進 git、由 `~/.zshrc` source）。`deploy-cron.sh` 依序找 `~/.zshrc.secrets` → `~/.zshrc` → `~/.bashrc` 的 export 行，都取不到才用 `build/deploy.env` 兜底。
每次換鍵後驗證：`bash build/deploy-cron.sh --selfcheck`（只驗金鑰與網路，不部署）。

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
不裝 cron，直接跑（金鑰取自環境，或先 `source ~/.zshrc.secrets`）：
```bash
source ~/.zshrc.secrets
./build/deploy.sh            # 完整（build ＋ 推 Cloudflare Pages）
./build/deploy.sh --build-only
./build/deploy.sh --gh       # 額外重建 GitHub Pages 鏡像（已停用 → §四）
```
> `--gh` 需要推 `gh-pages` 的憑證：優先 `GH_PAT`（token HTTPS），未設則用本機 `github` remote 的 SSH。cron 不取 `GH_PAT`、也不帶 `--gh`。

---

## 四、部署範圍與鏡像（2026-11-07 定案，已執行）

- **cron 只推 Cloudflare Pages**（`weather` 專案＋三個自訂域名），這是唯一上線通道。
- ⚠️ **GitHub Pages 鏡像已徹底移除**（不再推、分支已刪、站已關）。理由：
  1. 推 `gh-pages` 就會觸發 GitHub 為 branch 來源 Pages 內建的 `pages build and deployment` workflow——Actions 分頁每 2 小時出現一期，容易被誤判為「又在 Actions 上設了自動部署」（2026-11-07 就是這樣被發現的）。
  2. 鏡像不是正式管道，多一條 push 路就多一個失敗點（舊版這條路也正是 `/tmp` 垃圾的來源 → §5.1）。
  3. 停在最後一期的舊災情挂在网上有誤導風險——**舊資料比沒資料更危險**。
- **已做的事（2026-11-07）**：
  1. cron 不再推鏡像（`build/deploy.sh` 預設關閉，要推得明確給 `--gh`）。
  2. `.github/workflows/build.yml` 已從 repo 刪除（`DEV` commit `9c0a901`）。
  3. `gh-pages` 分支已從 **origin 與 github 刪除**（codeberg 本來就沒有這分支）；本地追蹤指標已 prune。
     三邊現在只剩 `main` 與 `DEV`。
  4. **Pages 站隨分支刪除而自動關闭**：`gh api repos/Lawlietr/Weather/pages` → 404。
     ⚠️ 反過來說無效：先跑 `gh api -X DELETE repos/Lawlietr/Weather/pages` 會被 GitHub 拒
     （422 `Deactivating GitHub pages for this repository is not allowed`）——**刪分支才是有效路徑**。
     舊內容之後仍由 GitHub CDN 發了一段（`cache-control: max-age=600`、`last-modified` 為舊值），
     數十分鐘後才全部轉 404。
- **兩個收尾提醒**：
  - `Build & Deploy` 這筆 workflow 記錄要等 `DEV` 合入 `main` 才會從 Actions 清單消失（GitHub 的清單看 default branch）；但不會有新 run。
  - `pages build and deployment` 是 GitHub 内建的（不在 repo），不再推 `gh-pages` 就不會再觸發。
- **若将来要重建鏡像**：`./build/deploy.sh --gh` 會重建 `gh-pages` 分支，但 **Pages 要在 GitHub 設定（或 API）重新啟用**才會真的上線；並保留 `public/.nojekyll`（Jekyll 會忽略 `_` 開頭資產 → `design/map.md` §2-7c）。

---

## 五、排程細節

- 排程（`build/cron.txt`）：`0 */2 * * *`（台灣時間，**每 2 小時**；2026-10-23 颱風薔琵期間曾升為 `0 * * * *` 每小時，2026-10-24 薔琵遠離後降回每 2 小時）。Actions 側 `schedule:` 已移除，不再錯開、也不重複 publish。
- ⚠️ **不再推 `gh-pages` 後，Actions 分頁就不會再出現新 run**。之前每 2 小時那期是 GitHub 內建的 `pages build and deployment`（來源 `dynamic/pages/pages-build-deployment`），由 cron 的 gh-pages push 觸發，不讀我們的 workflow、不抓 CWA、不碰 Cloudflare。已刪除的 `build.yml`（workflow id 343566300）最後一期自動 run 為 2026-10-23T01:01Z（#129）。
- 機器時區 `Asia/Taipei`（UTC+8），cron 直接用本地時間。
- `deploy-cron.sh` 用 `flock`（`/tmp/weather-deploy.lock`）防止兩次重疊；退出時（含失敗）由 EXIT trap 刪掉該檔。
- 日誌依天切檔：`build/logs/deploy-cron-YYYY-MM-DD.log`。

### 5.1 /tmp 的使用與清理（2026-11-07 定案）

| 物件 | 位置 | 誰清 |
|---|---|---|
| 防重疊 lock | `/tmp/weather-deploy.lock` | `deploy-cron.sh` 取得 lock 後設 `trap ... EXIT`，跑完（含失敗）即刪。舊版不刪 → 每期留一個 0 位元組空檔 |
| gh-pages 暫存目錄（一份 `public/` 副本、2200+ 檔／數 MB）——**只在手動跑 `deploy.sh --gh` 時才建立**；cron 預設不推鏡像就不會建立它 | `${TMPDIR:-/tmp}/weather-gh-pages.XXXXXXXX` | `deploy.sh` 的 `trap 'rm -rf "$TMP"' EXIT`（正常與失敗退出都清）；被 SIGKILL／斷電時 trap 不會執行 → `deploy-cron.sh` 的 `cleanup_tmp()` 每期開工掃超過 3 小時的同前綴殘骸，並順帶清掉舊版無前綴的 `tmp.<10 個亂碼>` 目錄（超過 3 天） |
| agent 除錯暫存檔 | `/tmp/weather-scratch/`（單一目錄，規則 → `WORKFLOW.md` §8 第 3 條） | `cleanup_tmp()` 清超過 2 天未動的 |
| npm／npx 快取（不在 `/tmp`） | `~/.npm`（其中 `_npx`） | `cleanup_tmp()` 清 14 天未碰的 `_npx` entries；整個 `~/.npm` 超過 **300 MB** 時跑 `npm cache clean --force`（下趟重抓 wrangler，多十幾秒） |

⚠️ **2026-11-07 過渡期間**：這批改動已 commit 在 `DEV`（包括已刪除的 `.github/workflows/build.yml`），而本機（部署機）工作區刻意**保留同內容的未 commit 版本**（cron 每 2 小時就是跑這份，不能先還原）。開發機把 `DEV` merge 進 `main` 並 push 後，本機落地順序：

```bash
# 1) 還原本機未 commit 的修改（內容與 DEV 那份相同，不會倒退）。
#    只還原狀態為 M 的檔案：已刪除的 .github/workflows/build.yml 不得 checkout，否則會被復活。
git checkout -- $(git status --porcelain | awk '$1=="M"{print $2}')
# 2) 拉進已合入 main 的 DEV 內容（含該 workflow 檔的刪除）
git checkout main && git pull --ff-only origin main
# 3) 確認未被復活
ls .github/workflows/ 2>/dev/null || echo 'workflow 已移除（正確）'
```

舊版的三個缺陷（2026-11-07 修正前）：① `deploy.sh` 只有結尾一行 `rm -rf "$TMP"`，而腳本是 `set -euo pipefail` —— [3/4] 中途失敗（push 被拒、rsync／commit 錯）就提前 exit，**每次部署失敗都會在 `/tmp` 留一份完整 `public/` 副本**（無前綴的 `tmp.` ＋ 10 個亂碼字元，事後無法辨識是誰留的）；② `flock` 的 lock 檔永不刪除；③ 舊版 `WORKFLOW.md` §8 叫 agent 把查到的 JSON 存到 `/tmp` 頂層 → 實測堆了 70+ 個來源不明的 `cwa_*.json`／`*.html`／`*.py`（已清；現行規則改成只准寫 `/tmp/weather-scratch/`，見 §8 第 8 條）。
⚠️ 本機不是完全沒有清理：`systemd-tmpfiles-clean.timer` 每日跑，設定為 `D /tmp 1777 root root 30d`（2026-11-07 實測）——但 **30 天對本專案太慢也太粗**：一份 `public/` 副本數 MB，兩週就能積出十幾份，而且 30 天的窗口完全蓋不住「連續失敗的這段時間」。所以靠 `cleanup_tmp()` 自己掃（3 小時就清），不能等系統回收。

---

## 六、注意事項

1. **本機需保持醒著**；休眠/關機期間的排程不會補跑（cron 非 systemd timer 的 missed-run 補執）。
2. **金鑰安全**：`~/.zshrc.secrets` 與 `build/deploy.env` 皆權限 600、不在 git（後者另 gitignore），絕不 commit。若懷疑洩漏，請到 Cloudflare/CWA 後台重設並更新 `~/.zshrc.secrets`。
3. GitHub Actions **完全不使用**（2026-11-07 已刪除 `.github/workflows/build.yml`）：repo 內沒有 workflow 檔案就不會有 run，不與 cron 撞車、不重複 publish。
4. 部署前的前置檢查用 `--selfcheck`（驗三把金鑰、驗 CWA 與 Cloudflare token、驗 node/npx）。舊版 Actions 失敗最常見的原因是 Cloudflare token 限區域或失效，同樣的檢查現在都在本機做。
5. cron 環境極簡（不載入 shell rc），故 `deploy-cron.sh` 直接 grep `~/.zshrc.secrets`（其次 `~/.zshrc`、`~/.bashrc`）的 export 行；**三把金鑰齊全時不再 source `build/deploy.env`**，避免該檔的過時 token 覆寫（開發機那份 2026-10-26 實測 CF API 403／9109）。
6. ⚠️ **金鑰只從固定檔名取**：把金鑰搬家（如 2026-10-29 從 `~/.zshrc` 移到 `~/.zshrc.secrets`）之後，一定要 `bash build/deploy-cron.sh --selfcheck` 驗一次。舊版腳本只 grep `~/.zshrc`，鑰搬走後 `build/deploy.env` 的 `${VAR:?}` 會把腳本在寫日誌前就終止——連續 18 期（2026-10-29 22:00～10-31 08:00）只在 cron 郵件留字、`build/logs` 一片空白。現版已改為先 log 再 exit 3。
7. ⚠️ **cron PATH 不得寫死 node 的版本目錄名**（2026-11-06 修正）。舊版 `deploy-cron.sh` 寫死 `/root/.local/share/pi-node/node-v22.23.2-linux-x64/bin`。pi 升級 node 時會換掉目錄名並移除舊版（本機 2026-11-05 10:48 換成 `node-v24.22.2-linux-x64`），當天 12:00 起連續 10 期在 `npx -y wrangler` 得到 `rc=127`（`npx: command not found`）。⚠️ **CF 部署失敗整個站台就不會更新**：`deploy.sh` 是 `set -euo pipefail`，[2/4] Cloudflare 掛了就不有上線（本機自 11-05 08:00 起約 25 小時沒上線）。現版改以 `current` 符號連結優先、再補上現存的 `node-v*/bin`（依版本由新到舊），並在 build 前先 log「node 就緒」、找不到就 exit 4；`--selfcheck` 也驗 node/npx。
8. **gh-pages 鏡像已移除**（2026-11-07，見 §四）：cron 不再推它，分支已從 origin/github 刪除、Pages 站已關。舊版的 push 重試（3 次、間隔 5 秒）只在手動 `--gh` 時才會用到——它存在的原因是 GitHub 偶發拒整個 ref：`cannot lock ref 'refs/heads/gh-pages': is at <sha> but expected <sha>`（2026-11-04 20:00、11-05 02:00／06:00／10:00 實測各一次）。
9. **部署不得在 `/tmp` 留殘骸**（2026-11-07 定案）：`deploy.sh` 的 mktemp 目錄帶 `weather-gh-pages.` 前綴且有 EXIT trap；`deploy-cron.sh` 退出時刪 lock 檔、開工時掃舊殘留（→ §5.1）。檢查有無殘留（兩種都應為空）：

   ```bash
   ls -d /tmp/weather-gh-pages.* 2>/dev/null
   find /tmp -maxdepth 1 -type d -regextype posix-extended -regex '.*/tmp\.[A-Za-z0-9_-]{8,12}'
   ```

   ⚠️ **現行 cron 已不再建立任何 mktemp 目錄**（不推鏡像就跳過那段），正常運行的 `/tmp` 應該完全沒變化。
10. **npm 快取自動清理**（2026-11-07）：`npx -y wrangler@latest` 會為每個新版 wrangler 留一份快取（實測 `~/.npm` 366 MB、`_npx` 104 MB）。`cleanup_tmp()` 先清 14 天未碰的 `_npx` entries；整個 `~/.npm` 超過 **300 MB** 就跑 `npm cache clean --force`（下趟重抓 wrangler，多十幾秒）。本機目前 366 MB → 下一期 cron 就會清一次，之後穩定在阈值以下。

---

## 七、除錯

```bash
# 看最近一次執行結果
tail -n 40 build/logs/deploy-cron-$(date +%F).log

# 手動跑一次（會實際部署，慎用）
bash build/deploy-cron.sh --selfcheck   # 先驗金鑰與網路
bash build/deploy-cron.sh

# 排程有跑但 build/logs 是空白 → 看 cron 的郵件（stdout/stderr 進 postfix，不在日誌）
grep -c "Subject: Cron" /var/mail/root && tail -60 /var/mail/root

# 確認 cron 是否已安裝
crontab -l | grep weather

# 手動 build 驗證（不部署）
./build/deploy.sh --build-only

# 停在 [2/4]、rc=127 → cron 找不到 node/npx（pi-node 升級改了目錄名，見 §六 7）
ls -l /root/.local/share/pi-node/                 # 看現存版本目錄與 current 指向

# 用近似 cron 的極簡環境自檢（驗證 PATH 與金鑰都能取到）
env -i HOME=/root PATH=/usr/bin:/bin bash build/deploy-cron.sh --selfcheck
```
