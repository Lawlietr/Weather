# 開發機 / 部署機 分工與環境細節（2026-10-23 實測定案）

> **為什麼有這檔**：本倉儲跑在**兩台不同的機器**上。過去多個 session（含 2026-10-23 這次）只站在「部署機」看 repo，就誤判「`DEV` 上沒有進行中的功能」——因為部署機的本地分支指標可能嚴重過時，而開發機未 push 的工作在這裡完全看不見。本檔記錄兩台的實測差異，避免重複踩。
> 規則本體在 `AGENTS.md`「兩台機器分工」（五條鐵則）、流程在 `WORKFLOW.md` §0.1；本檔放**環境細節與已知缺口**。

## 一、兩機對照（2026-10-23 實測）

| | **開發機** | **部署機**＝本機 |
|---|---|---|
| IP | `192.168.100.15` | `192.168.100.14`（另有 `192.168.1.14`、`172.17.0.1` docker bridge） |
| hostname | `Code-Agent-01` | `hermes` |
| OS / 架構 | Ubuntu 24.04.5 LTS, x86_64（LXC/VM） | Ubuntu 24.04.4 LTS, x86_64（LXC） |
| repo 路徑 | `/root/opencode-stuffs/Weather`（同路徑） | `/root/opencode-stuffs/Weather` |
| 目前分支 | **`DEV`**（`git status -sb` 首行 `## DEV`） | **`main`**（HEAD 常駐，勿切分支） |
| 角色 | 功能開發、`build/` 改動、測試站驗證 | 每小時 cron build＋部署生產三站；災情/颱風 markdown；ops 修正 |
| cron | **空**（`crontab -l` 無任何項目）→ 不會部署 | `0 * * * * .../build/deploy-cron.sh`（`# weather-deploy-cron`） |
| git | 2.43.0 | 2.43.0 |
| remotes | `origin`(Forgejo `ssh://fg/...`)／`github`(https)／`codeberg`(ssh) — 三邊同名 | 同三邊 |
| Python | 3.12.3（系統版）；repo 內 `.venv` **未建立**（＝尚未在開發機跑過 `build.sh`） | 3.12.3；`build/build.sh` 自動建 repo 內 `.venv`（⚠ `WORKFLOW.md` §0 舊寫「Python ≥ 3.14」與實測不符，已更正為 3.12） |
| Node | **無 node/npm/npx**（`which -a` 與 zsh login 皆找不到；`/usr/local/bin/node`、nvm、fnm、volta 皆無；但有 `~/.bun`） | node `v22.22.2`、npx `10.9.7` → `npx wrangler` 可用 |
| Playwright | `~/.cache/ms-playwright` 有 `chromium-1248`、`chromium_headless_shell-1248`、`ffmpeg-1013`；skills 有 `playwright`/`obscura`/`index-translate`；`obscura` 已裝於 `/usr/local/bin/obscura` | 同有 chromium 快取，真瀏覽器驗證於此執行（`design/map.md` 要求 Playwright 驗證 `/map/`） |
| 金鑰 | `build/deploy.env` **存在**（210 bytes、`600`、日期 8/27）；無 `.env`；**shell 環境 `CWA_API_KEY`/`CLOUDFLARE_*`/`GH_PAT` 全 unset**（未 source deploy.env） | `build/deploy.env`（`600`）由 `deploy-cron.sh` 載入＋從 `~/.zshrc` 抽鍵驗證 → `LOCAL_CRON.md` |

### 兩機共用、不需要擔心的部分
同一 git 身分（`Lawlietr <yanzilme@gmail.com>`）、同三個 remote、同 repo 路徑、同 Python/git 版本——**所以「哪個 commit 是哪台機器做的」無法靠 git 身分分辨**，只能看分支與指標（見下節快照方法）。

## 二、2026-10-23 狀態快照（當時實測，之後會過時，勿當現值引用）

- 三邊 `origin/DEV`＝`github/DEV`＝`codeberg/DEV`＝`bca1b0d`（2026-09-26 11:08）
- **開發機上 `DEV` 沒有未 push 的 commit**（`origin/main..DEV` 內容與 remote 完全一致：4 個排程 commit）、工作區乾淨（0 個未 commit 檔案）、無 stash
- `DEV` 落後 `main` **23** commits；`DEV` 上沒有任何 `main` 沒有的檔案（`--diff-filter=A` 為空）
- 部署機本機 `DEV` 指標原停在 `dcf10d7`（2026-08-30，落後 77）→ 已 `git branch -f DEV origin/DEV` 對齊並設定 track `origin/DEV`

**查「DEV 現在到底在做什麼」的正確方法（在開發機上跑，或從部署機 SSH 過去唯讀探測）：**

```bash
# 從部署機（.14）到開發機（.15）——免密金鑰已可用，唯讀探測即可
ssh -o BatchMode=yes 192.168.100.15 'cd /root/opencode-stuffs/Weather && \
  git fetch --all --prune -q; git status -sb | head -5; git status --porcelain | wc -l; \
  git stash list; git log --oneline origin/main..DEV | head -20; \
  git rev-list --count DEV..origin/main'
```

⚠ 從部署機對開發機**只做讀取**；要在開發機改東西（例如 `git merge origin/main` 同步 `DEV`）需先取得使用者同意——那是她正在開發的工作環境。

## 三、由環境差异產生的操作結論

1. **測試站 `wea-testing` 部署在開發機跑不起來**：`npx wrangler pages deploy public --project-name wea-testing` 需要 node，開發機無 node。兩條解法（未實作，擇一）：
   - 在開發機裝 node（或用已有 bun：`bun x wrangler ...`，未驗證 wrangler 與 bun 相容性）；
   - **慣用做法**：開發機只寫碼與 commit/push `DEV`，**build＋部署測試站＋Playwright 驗證在部署機**（用 `git fetch && git checkout DEV && ./build/build.sh`，測完切回 `main`；切 `DEV` 前先 `bash build/cron-disable.sh`，測完 `cron-enable.sh`，否則每小時 cron 会把未合併內容推上生產）。
2. **開發機要跑 build 前先載入金鑰**：`CWA_API_KEY` 等在 shell 未設定，只有 `build/deploy.env`（8/27 舊档，內容未驗證是否仍有效）。`./build/build.sh` 需 `CWA_API_KEY`；`deploy-cron.sh` 的「從 `~/.zshrc` 抽鍵」邏輯只存在于部署機。
3. **部署機的 HEAD 是生產內容的唯一來源**：`build/deploy-cron.sh` 與 `build/deploy.sh` 不做 `git pull`/`fetch`/`checkout` → 「已 push 到 remote」≠「已上線」。開發機 merge 回 `main` 後，**務必**在部署機 `git checkout main && git pull --ff-only origin main`（`WORKFLOW.md` §0.1）。
4. **Python 版本**：兩機實測皆 3.12.3，cron build 每小時正常 → `WORKFLOW.md` §0 的「Python ≥ 3.14」已更正為 3.12（實測可用），不要照舊文去裝新 Python。

## 四、待辦（本檔相關，尚未做）

- [ ] 決定測試站部署落點：開發機裝 node／`bun x wrangler`／固定在部署機（建議固定部署機，理由見上節 1）
- [ ] 開發機 `build/deploy.env` 內容與時效待使用者確認（8/27 建立，可能已過期；**不要**把值貼進任何輸出或 commit）
- [ ] `DEV` 落後 `main` 23 commits：開發新功能**前**先在開發機 `git merge origin/main`（五條鐵則第 5 條），重疊檔是 `build/dgpa.py`、`site.py`、`i18n.py`、`deploy-cron.sh`
- [ ] 若日後要完全捨棄長期 `DEV`：改從 `main` 切 `feat/<名稱>` 短支，本檔改寫為「分支模型」記錄
