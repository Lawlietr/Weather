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
| Node | **無系統 node**（bash login shell 找不到；`/usr/local/bin/node`、nvm、fnm、volta 皆無；有 `~/.bun` 1.3.14）。⚠️ **但 pi 自带 node 可用**：`/root/.local/share/pi-node/current/bin/{node,npm,npx}` v22.23.2／npm 10.9.8，`~/.zshrc` 已把它加進 PATH → **zsh／agent shell 內 `npx wrangler` 可用**（2026-10-26 實測：測試站部署成功，見 §五） | node `v22.22.2`、npx `10.9.7` → `npx wrangler` 可用 |
| Playwright | `~/.cache/ms-playwright` 有 `chromium-1248`、`chromium_headless_shell-1248`、`ffmpeg-1013`；skills 有 `playwright`/`obscura`/`index-translate`；`obscura` 已裝於 `/usr/local/bin/obscura`。⚠️ 用哪個 `node_modules` 要對修訂：`translate-cloud/node_modules`＝playwright **1.64.0**（對應 1248，可用）；`steam-deck-utilities/web/node_modules`＝**1.62.1**（要 chromium_headless_shell-**1234**、本機沒有 → launch 失敗，2026-10-26 實測） | 同有 chromium 快取，真瀏覽器驗證於此執行（`design/map.md` 要求 Playwright 驗證 `/map/`） |
| 金鑰 | `build/deploy.env` **存在但已失效**（210 bytes、`600`、8/27；2026-10-26 實測 CF API **HTTP 403／9109**）。⚠️ 實測可用的鍵在 **`~/.zshrc`**（export `CWA_API_KEY`／`CLOUDFLARE_API_TOKEN`／`CLOUDFLARE_ACCOUNT_ID`；CF token 對 `/accounts` 與 `wea-testing` 皆 HTTP 200）。shell 預設仍 unset → 用前需 `eval "$(grep -E '^export (CLOUDFLARE_API_TOKEN\|CLOUDFLARE_ACCOUNT_ID\|CWA_API_KEY)=' ~/.zshrc)"` | `build/deploy.env`（`600`）由 `deploy-cron.sh` 載入＋從 `~/.zshrc` 抽鍵驗證 → `LOCAL_CRON.md`。⚠️ 2026-10-26 實測：該檔直接 source 時 `CWA_API_KEY` 報「請設定（環境變數或下方預設值）」→ **它是模板、不是金鑰本體**，鍵確實來自 `~/.zshrc` |

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

1. **測試站 `wea-testing` 部署：開發機已可行（2026-10-26 實測推翻舊結論）**。舊記錄「開發機無 node → 跑不起來」已過時：pi 自带 node 在 zsh／agent shell 可用（見上方 Node 列）。
   - **實測可用指令（開發機）**：
     ```bash
     eval "$(grep -E '^export (CLOUDFLARE_API_TOKEN|CLOUDFLARE_ACCOUNT_ID)=' ~/.zshrc)"
     ./build/build.sh
     npx -y wrangler@latest pages deploy public --project-name wea-testing --branch main
     ```
     ⚠️ 務必 `--branch main`（自訂域名指向 production branch）；⚠️ 別用 `build/deploy.env` 的 CF 鍵（已失效 403）。實測：2,241 檔上傳、349 檔上傳／1,892 已存在、2.47s，部署成 `https://<hash>.wea-testing.pages.dev`＋`weatesting.avpclub.eu.org` 生效。
   - **備援做法（仍可用）**：開發機只寫碼與 push `DEV`，到部署機（.14）`git fetch && git checkout DEV && ./build/build.sh` ＋部署＋驗證，測完切回 `main`；切 `DEV` 前先 `bash build/cron-disable.sh`、測完 `cron-enable.sh`，否則每小時 cron 會把未合併內容推上生產。**優先把測試站留在開發機**——不需要動部署機的 HEAD／cron。
2. **開發機跑 build 的鍵來源＝`~/.zshrc`，不是 `build/deploy.env`**：2026-10-26 實測 `eval` 抽 `~/.zshrc` 的 export 後 `./build/build.sh` 正常（「✓ CWA API 連線正常」、輸出 `CWA live`），並已存在 repo 內 `build/.venv`（Python 3.12.3）。**勿用 `build/deploy.env`**（本機那份 8/27、CF API 回 403／9109）。
3. **部署機的 HEAD 是生產內容的唯一來源**：`build/deploy-cron.sh` 與 `build/deploy.sh` 不做 `git pull`/`fetch`/`checkout` → 「已 push 到 remote」≠「已上線」。開發機 merge 回 `main` 後，**務必**在部署機 `git checkout main && git pull --ff-only origin main`（`WORKFLOW.md` §0.1）。
4. **Python 版本**：兩機實測皆 3.12.3，cron build 每小時正常 → `WORKFLOW.md` §0 的「Python ≥ 3.14」已更正為 3.12（實測可用），不要照舊文去裝新 Python。

## 四、待辦（本檔相關，尚未做）

- [x] 決定測試站部署落點 → **2026-10-26 定案：留開發機**（pi 自带 node ＋ `~/.zshrc` 的有效 CF 鍵，實測部署成功；不用再碰部署機的 HEAD／cron，見 §三.1）
- [x] 開發機 `build/deploy.env` 時效 → **已查：失效**（2026-10-26 CF API 403／9109）。可用的鍵在 `~/.zshrc`。⚠️ 待辦：要嘛重發 token 後同步更新兩機的 `deploy.env`，要嘛把本機那份改掉／標成模板，避免下一個 session 又拿來用
- [x] `DEV` 落後 `main` 23 commits → 2026-10-26 已處理（本地 `DEV` 曾落後 `origin/DEV` 20＋ commit、造成 push 非快進；已 `git rebase origin/DEV` 對齊後推送）。重疊檔以往是 `build/dgpa.py`、`site.py`、`i18n.py`、`deploy-cron.sh` → 開發前先 fetch 的鐵則繼續成立
- [ ] **兩機 `build/deploy.env` 一致性**：開發機那份＝失效 token；部署機那份＝模板（source 時 `CWA_API_KEY: 請設定...`）。實戰都靠 `~/.zshrc` → 建議統一（重發 token、或明確改名為 `deploy.env.example`），並確認 `deploy-cron.sh` 的抽鍵邏輯仍只靠 `~/.zshrc`
- [ ] 開發機 `crontab -l` 仍空 ✓（2026-10-26 未變）、`git remote` 三邊都在 ✓；但**開發機的 `main` 常態落後 `origin/main` 數十個 commit** → 開發前先 `git fetch --all --prune`＋`git merge origin/main`（五條鐵則第 5 條），本輪 2026-10-26 又踩到一次（本地 DEV 落後 20＋ commit，造成 push 非快進）
- [ ] 若日後要完全捨棄長期 `DEV`：改從 `main` 切 `feat/<名稱>` 短支，本檔改寫為「分支模型」記錄
