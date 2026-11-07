# 開發機 / 部署機 分工與環境細節（2026-10-23 實測定案）

> **為什麼有這檔**：本倉儲跑在**兩台不同的機器**上。過去多個 session（含 2026-10-23 這次）只站在「部署機」看 repo，就誤判「`DEV` 上沒有進行中的功能」——因為部署機的本地分支指標可能嚴重過時，而開發機未 push 的工作在這裡完全看不見。本檔記錄兩台的實測差異，避免重複踩。
> 規則本體在 `AGENTS.md`「兩台機器分工」（六條鐵則）、流程在 `WORKFLOW.md` §0.1；本檔放**環境細節與已知缺口**。

## 一、兩機對照（2026-10-23 實測）

| | **開發機** | **部署機**＝本機 |
|---|---|---|
| IP | `192.168.100.15` | `192.168.100.14`（另有 `192.168.1.14`、`172.17.0.1` docker bridge） |
| hostname | `Code-Agent-01` | `hermes` |
| OS / 架構 | Ubuntu 24.04.5 LTS, x86_64（LXC/VM） | Ubuntu 24.04.4 LTS, x86_64（LXC） |
| repo 路徑 | `/root/opencode-stuffs/Weather`（同路徑） | `/root/opencode-stuffs/Weather` |
| 目前分支 | **`DEV`**（`git status -sb` 首行 `## DEV`） | **`main`**（HEAD 常駐，勿切分支） |
| 角色 | 功能開發、`build/` 改動、測試站驗證 | 每 2 小時 cron build＋部署生產三站；災情/颱風 markdown；ops 修正 |
| cron | **應為空（不會部署）**。⚠️ 但**不是恒空、不得引用舊快照**：2026-11-07 復查發現該機存在生效的 `0 */2 * * * … build/deploy-cron.sh # weather-deploy-cron`（備份檔顯示至少 8/27、10/31 就裝過）。因其 `deploy-cron.sh` 是舊版、PATH 找不到 node，當日 00:00–18:00 十期全 `rc=127` → 從未真的部署、也未污染生產。已於當日 `bash build/cron-disable.sh` 關掉（現在 `crontab -l` 為空）。風險與規則 → `AGENTS.md` 鐵則 6 | `0 */2 * * * /bin/bash .../build/deploy-cron.sh`（`# weather-deploy-cron`，2026-10-24 起每 2 小時） |
| git | 2.43.0 | 2.43.0 |
| remotes | `origin`(Forgejo `ssh://fg/...`)／`github`(https)／`codeberg`(ssh) — 三邊同名 | 同三邊 |
| Python | 3.12.3（系統版）；repo 內 `build/.venv` **已建立**（⚙ 2026-10-28 更新，舊行寫「未建立」已過時：開發機已兩度跑通 `./build/build.sh`，venv 在 `build/.venv`） | 3.12.3；`build/build.sh` 自動建 repo 內 `.venv`（⚠ `WORKFLOW.md` §0 舊寫「Python ≥ 3.14」與實測不符，已更正為 3.12） |
| Node | **無系統 node**（bash login shell 找不到；`/usr/local/bin/node`、nvm、fnm、volta 皆無；有 `~/.bun` 1.3.14）。⚠️ **但 pi 自带 node 可用**：`/root/.local/share/pi-node/current/bin/{node,npm,npx}`（⚠️ 版號會隨 pi 升級變動，用 `current` 這個符號連結，勿寫死版本目錄名；2026-11-06 於部署機實測 `current` → v24.22.2／npm 11.19.1），`~/.zshrc` 已把它加進 PATH → **zsh／agent shell 內 `npx wrangler` 可用**（2026-10-26 實測：測試站部署成功，見 §五） | ⚠️ **無系統 node**（`/usr/bin/node` 不存在）。兩個可用 node：pi 自帶 `/root/.local/share/pi-node/current/bin/{node,npm,npx}` （2026-11-06 實測 `current` → `node-v24.22.2-linux-x64`、v24.22.2／npm 11.19.1）與 `/root/.hermes/node/bin`（v22.22.2／npx 10.9.7）。⚠️ **版號會隨 pi 升級變動、舊版目錄會被移除**（2026-11-05 10:48 由 v22.23.2 換成 v24.22.2）——cron 的 PATH 由 `deploy-cron.sh` 以 `current`＋現存的 `node-v*/bin` 現查組合，**不得寫死版本目錄名**（寫死的後果與事故 → `LOCAL_CRON.md` §六 7） |
| Playwright | `~/.cache/ms-playwright` 有 `chromium-1248`、`chromium_headless_shell-1248`、`ffmpeg-1013`；skills 有 `playwright`/`obscura`/`index-translate`；`obscura` 已裝於 `/usr/local/bin/obscura`。⚠️ 用哪個 `node_modules` 要對修訂：`translate-cloud/node_modules`＝playwright **1.64.0**（對應 1248，可用）；`steam-deck-utilities/web/node_modules`＝**1.62.1**（要 chromium_headless_shell-**1234**、本機沒有 → launch 失敗，2026-10-26 實測） | 同有 chromium 快取，真瀏覽器驗證於此執行（`design/map.md` 要求 Playwright 驗證 `/map/`） |
| 金鑰 | `build/deploy.env` **已刪**（2026-10-31；舊檔是 8/27 的失效 token，2026-10-26 實測 CF API **HTTP 403／9109**）。要兜底檔就 `cp build/deploy.env.example build/deploy.env && chmod 600`。⚠️ 實測可用的鍵在 **`~/.zshrc.secrets`**（憑證集中檔，2026-10-29 起；`~/.zshrc` 只 source 它；export `CWA_API_KEY`／`CLOUDFLARE_API_TOKEN`／`CLOUDFLARE_ACCOUNT_ID`；CF token 對 `/accounts` 與 `wea-testing` 皆 HTTP 200）。shell 預設仍 unset → 用前需 `eval "$(grep -E '^export (CLOUDFLARE_API_TOKEN\|CLOUDFLARE_ACCOUNT_ID\|CWA_API_KEY)=' ~/.zshrc.secrets)"` | `build/deploy.env`（`600`）由 `deploy-cron.sh` 從 `~/.zshrc.secrets`（其次 `~/.zshrc`／`~/.bashrc`）抽鍵 → `LOCAL_CRON.md`。⚠️ 2026-10-26 實測：該檔直接 source 時 `CWA_API_KEY` 報「請設定（環境變數或下方預設值）」→ **它是模板、不是金鑰本體**，鍵確實來自 `~/.zshrc.secrets` |

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
  git rev-list --count DEV..origin/main; \
  echo "cron 生效行數: $(crontab -l 2>/dev/null | grep -cE "^[0-9*/].*weather-deploy-cron")"'
```

⚠ 從部署機對開發機**只做讀取**；要在開發機改東西（例如 `git merge origin/main` 同步 `DEV`、或關掉那台的 cron）需先取得使用者同意——那是她正在開發的工作環境。**2026-11-07 已獲同意**在開發機執行：`DEV`→`main` 的 fast-forward merge（推三邊）、`git pull --ff-only origin DEV` 對齊本地 `DEV`、`bash build/cron-disable.sh`。當時開發機狀態：在 `DEV`、dirty 0、stash 0、`origin/DEV..DEV` = 0（無未 push 的開發中工作）。

## 三、由環境差异產生的操作結論

1. **測試站 `wea-testing` 部署：開發機已可行（2026-10-26 實測推翻舊結論）**。舊記錄「開發機無 node → 跑不起來」已過時：pi 自带 node 在 zsh／agent shell 可用（見上方 Node 列）。
   - **實測可用指令（開發機）**：
     ```bash
     eval "$(grep -E '^export (CLOUDFLARE_API_TOKEN|CLOUDFLARE_ACCOUNT_ID)=' ~/.zshrc.secrets)"
     ./build/build.sh
     npx -y wrangler@latest pages deploy public --project-name wea-testing --branch main
     ```
     ⚠️ 務必 `--branch main`（自訂域名指向 production branch）；⚠️ 別用 `build/deploy.env` 的 CF 鍵（已失效 403）。實測：2,241 檔上傳、349 檔上傳／1,892 已存在、2.47s，部署成 `https://<hash>.wea-testing.pages.dev`＋`weatesting.avpclub.eu.org` 生效。
   - **備援做法（仍可用）**：開發機只寫碼與 push `DEV`，到部署機（.14）`git fetch && git checkout DEV && ./build/build.sh` ＋部署＋驗證，測完切回 `main`；切 `DEV` 前先 `bash build/cron-disable.sh`、測完 `cron-enable.sh`，否則每小時 cron 會把未合併內容推上生產。**優先把測試站留在開發機**——不需要動部署機的 HEAD／cron。
2. **開發機跑 build 的鍵來源＝`~/.zshrc.secrets`，不是 `build/deploy.env`**：2026-10-26 實測 `eval` 抽 `~/.zshrc.secrets` 的 export 後 `./build/build.sh` 正常（「✓ CWA API 連線正常」、輸出 `CWA live`），並已存在 repo 內 `build/.venv`（Python 3.12.3）。**`build/deploy.env` 已於 2026-10-31 刪除**（舊那份是失效 token）；要兜底檔請用 repo 內的 `build/deploy.env.example` 複製。
3. **部署機的 HEAD 是生產內容的唯一來源**：`build/deploy-cron.sh` 與 `build/deploy.sh` 不做 `git pull`/`fetch`/`checkout` → 「已 push 到 remote」≠「已上線」。開發機 merge 回 `main` 後，**務必**在部署機 `git checkout main && git pull --ff-only origin main`（`WORKFLOW.md` §0.1）。
4. **Python 版本**：兩機實測皆 3.12.3，cron build 每小時正常 → `WORKFLOW.md` §0 的「Python ≥ 3.14」已更正為 3.12（實測可用），不要照舊文去裝新 Python。

## 四、待辦（本檔相關，尚未做）

- [x] 決定測試站部署落點 → **2026-10-26 定案：留開發機**（pi 自带 node ＋ `~/.zshrc.secrets` 的有效 CF 鍵，實測部署成功；不用再碰部署機的 HEAD／cron，見 §三.1）
- [x] 開發機 `build/deploy.env` 時效 → **已查：失效**（2026-10-26 CF API 403／9109）。可用的鍵在 `~/.zshrc.secrets`。⚠️ 待辦：要嘛重發 token 後同步更新兩機的 `deploy.env`，要嘛把本機那份改掉／標成模板，避免下一個 session 又拿來用
- [x] `DEV` 落後 `main` 23 commits → 2026-10-26 已處理（本地 `DEV` 曾落後 `origin/DEV` 20＋ commit、造成 push 非快進；已 `git rebase origin/DEV` 對齊後推送）。重疊檔以往是 `build/dgpa.py`、`site.py`、`i18n.py`、`deploy-cron.sh` → 開發前先 fetch 的鐵則繼續成立
- [x] **兩機 `build/deploy.env` 一致性** → **2026-10-31 定案**：`build/deploy.env` 不再是金鑰本體（開發機那份是失效 token、部署機那份是無值模板）。金鑰一律放 `~/.zshrc.secrets`，`deploy-cron.sh` 依序 grep `~/.zshrc.secrets`→`~/.zshrc`→`~/.bashrc`，三鑰齊全就**不 source** `deploy.env`（不再被過時值覆寫）。⚠️ 反面教材：舊版只 grep `~/.zshrc`，10/29 鑰移到 `.zshrc.secrets` 後 cron 連續 18 期靜默失敗 → `LOCAL_CRON.md` §六.6
- [x] 開發機 `crontab -l` 是否仍空 → **2026-11-07 復查：不空、有生效的 weather 排程**（十期 rc=127、從未部署），已 `bash build/cron-disable.sh` 關掉。教訓寫進 `AGENTS.md` 鐵則 6：接手時一律現查、不得引用舊快照。另：舊版 `cron-disable.sh` 把備份寫在移除**之後** → 三份 `crontab.backup.*` 全是 0 位元組（無法恢復），已改為 `crontab.before.<時間>.txt`（移除前）＋`crontab.after.<時間>.txt`（移除後）
- [ ] **開發機的 `main` 常態落後 `origin/main` 數十個 commit** → 開發前先 `git fetch --all --prune`＋`git merge origin/main`（六條鐵則第 5 條），2026-10-26 曾踩到（本地 `DEV` 落後 20＋ commit，造成 push 非快進）
- [ ] 若日後要完全捨棄長期 `DEV`：改從 `main` 切 `feat/<名稱>` 短支，本檔改寫為「分支模型」記錄
