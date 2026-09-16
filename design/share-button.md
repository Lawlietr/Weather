# 事件分享按鈕設計

> 狀態：構想、待實作（🟢 最低優先級，2026/8/29 提出）｜最後更新：2026/9/16
> 對應 TODO：S1–S3（見 `TODO.md` 主表）
> TL;DR：事件頁一鍵分享（Web Share→複製連結→平台一鍵三層降級）＋OG 分享圖卡；純 build 期改動、不需新 API。

## 目的

讓使用者能從「事件頁」一鍵把該颱風/災情紀錄分享出去（Line、社群、複製連結等），提升災情傳播範圍。

## 分享內容

每筆事件分享出去的三樣資料（皆取自建站既有資料，不需新 API）：

- **正規 URL**：沿用 `build/site.py` 的 `link(e)`（`{SITE_BASE}/{'/'.join(e['url'])}`），例如 `https://weather.avpclub.eu.org/events/颱風/2026/08/0807_13_白海豚_DOLPHIN.html`。
- **標題**：`ev['name']`（例「颱風白海豚（DOLPHIN）— 2026 年第 13 號」）。
- **摘要**：`[狀態]・[severity]・[縣市]`（例「進行中・🔴重大・台南／高雄」），控制長度以便 Line 分享。

## 分享機制（三層降級）

| 層級 | 機制 | 適合情境 | 備註 |
|------|------|----------|------|
| 一 | **Web Share API** `navigator.share()` | 手機原生分享列 | 最優雅；需 https（本站符合）＋使用者觸發（按鈕點擊正合適）；不可用時退到二 |
| 二 | **複製連結到剪貼簿** | 桌面／API 不可用 | `navigator.clipboard` 失敗時退回到 `execCommand`，並顯示「已複製」提示 |
| 三 | **平台一鍵連結**（純 URL builder） | 想直達特定 App | 台灣首需 **Line**（`https://share-line.me/dialog/?text=&url`），其次 X/Twitter、Facebook；純 URL 拼裝、**無需 API key、無 CORS**，與 build 時抓取架構不打架 |

## OG / Twitter Card meta（體驗加分項，工作量最大）

目前事件頁沒有 OG 標籤，連結貼到 Line/Slack 僅顯示裸 URL。補上 `og:title / og:description / og:image / twitter:card` 後，分享預覽會變成有標題＋severity 徽章的卡片。需一張分享圖卡（可用事件 severity 色系生成簡單圖），可與此項一起或之後單獨立。

## 實作位置與方式

- 在 `build_event_page()` 的 hero section（放 `badge`＋`status`＋`chips` 的 `<section class="card hero">`）右側加分享按鈕。
- 加 i18n 字串：`share`、`copy_link`、`copied`（走現成 `t(lang, key)` 三級回退，ja 頁面也會有）。
- 內聯 JS + 現有 CSS 變數（`--accent` 等），自動適配深色／淺色主題。
- 純 build 期 Python 改動，不碰 CWA/API，符合「災情新聞人工把關」原則。

## 注意事項

- Line 分享文字有長度上限，摘要需控制長度。
- 分享按鈕只放「事件頁」；首頁「事件 Hero 入口卡」是中性入口（無 severity 色系），**不放**（符合 AGENTS.md 設計意圖）。
- 建議執行順序：**A（Web Share ＋ 複製連結）→ B（＋ Line 一鍵）→ C（＋ OG 分享圖卡）**，目前全列為最低優先、暫未實作。
