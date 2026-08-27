# Weather - 台灣天氣與災情總覽

紀錄颱風動態與災情的 Markdown 倉儲，並附靜態網站 build（產出 `public/`、`llms.txt`、`llms-full.txt`；主要 host 於 Cloudflare Pages 自訂域名，另同步 GitHub Pages；見下方「網站專案」）。

## ⚠️ 時間意識（極度重要）

**撰寫或查詢災情前，必須先確認目前的現實時間（系統時間）。**

- 本項目核心目的是**記錄目前正在發生的天氣事件**與即時災情彙整
- 搜尋與引用新聞時，**只關注當前事件相關的最新報導**，不應檢索上個月或幾年前的事件
- 檔案中的時間戳必須與現實時間一致，不可混淆年份或日期
- 若搜尋結果出現非當前事件的歷史資料，應主動過濾，避免將過去的事件誤植到當前紀錄中
- 每次新增災情前，先確認該災情是否屬於「目前正在發生」的颱風事件

## 目錄與檔名

### 颱風檔案

```
颱風/{YYYY}/{MM}/{MMDD}_{NN}_{中文名}_{國際命名}.md
```

範例：`颱風/2026/07/0702_09_巴威_BAVI.md`

**說明**：
- `{MMDD}`：生成日期（月 + 日，補零，如 0702 表示 7 月 2 日）
- `{NN}`：颱風編號（補零，如 09 表示第 9 號）
- 這樣命名可確保檔案按日期和編號自然排序

### 災情檔案（非颱風事件）

```
災情/{YYYY}/{MM}/{MMDD}_{事件類型}_{事件名稱}.md
```

範例：`災情/2026/08/0821_低壓帶_南台灣大雨.md`

**說明**：
- `{MMDD}`：事件起始日期（月 + 日，補零）
- `事件類型`：低壓帶、西南風、梅雨等
- `事件名稱`：簡明描述事件影響範圍
- 適用範圍：非颱風造成的災害（低壓帶、梅雨、西南風等）

## 檔案撰寫規則

- 全部使用**繁體中文**
- 時間戳須含年與時間，如 `2026/7/10 05:30`
- 災害分級標籤：`🔴重大` `🟡警戒` `🟢一般`
- 新進展**附加**在檔尾，不覆寫；僅在結構錯誤時修改既有內容
- 颱風基本資料表（強度、風速、半徑等）置於檔首，使用表格
- **每次修改**必須在檔首（基本資料表上方）新增一筆 `最後修改：YYYY/M/D HH:mm`，例如 `最後修改：2026/7/11 18:30`

## 章節慣例

### 颱風檔案

依序：基本資料 → 警報時程 → 停班停課 → 風力/雨量/浪高 → 災情紀錄（依 🔴🟡🟢 分節）→ 交通影響 → 防災作為 → 備註

### 災情檔案（非颱風事件）

依序：災害概述 → 各縣市災情 → 停班停課時程 → 氣象署警報與特報 → 中央災害應變中心 → 專家分析 → 災情分級 → 未來天氣預報 → 備註 → 資料來源

## 資料來源規範

- **颱風資料**（軌跡、強度、位置、預測）：以中央氣象署（CWA）API 為主
- **警報與特報**（海上颱風警報、大雨特報、強風特報）：以 CWA API 為主
- **雨量、風力、浪高**：以 CWA API 為主
- **災情紀錄**（淹水、樹倒、落石、停電等）：以各縣市新聞媒體為輔，引用時請註明出處
- **停班停課**：以教育部或各縣市政府公告為主
- **交通影響**：以交通部或各縣市政府公告為主，新聞媒體為輔

> ⚠️ 使用新聞資料時，請確認時效性，避免使用舊聞；引用時請註明新聞來源與日期。

## Git

- 預設分支：`main`（原 `master` 已更名）
- 功能開發在 `DEV` 分支，**經使用者確認後才合併回 `main`**
- 無 CI、無 lint/test 指令

---

## 中央氣象署（CWA）Open Data API

### API Key 設定

**方式一：環境變數（推薦，自動載入）**

API Key 已設定在 `~/.zshrc`，開啟新 terminal 即可使用：

```bash
export CWA_API_KEY="你的_API_KEY"
```

**方式二：專案 `.env` 文件**

在專案根目錄建立 `.env` 文件，內容如下：

```bash
CWA_API_KEY=你的_API_KEY
```

⚠️ **安全規範**：
- API Key **不得**硬編碼在腳本或 commit 到 Git
- `.env` 已加入 `.gitignore`，不會被提交
- 使用時請透過 `os.getenv("CWA_API_KEY")` 或 shell 讀取

### API 基礎 URL

```bash
BASE_URL="https://opendata.cwa.gov.tw/api/v1/rest/datastore"
```

### API 優先級說明（依事件類型）

| 優先級 | 颱風事件 | 豪雨/大雨事件（非颱風） |
|--------|----------|--------------------------|
| **P0（必須）** | W-C0034-005（軌跡）、W-C0034-001（海警） | W-C0033-002/003（豪大雨特報）、O-A0002-001（雨量站） |
| **P1（重要）** | W-C0033-001（強風特報）、W-C0033-003、O-A0001-001（逐時氣象） | W-C0033-001（強風特報）、O-A0001-001（逐時氣象）、C-B0025-001（每日雨量）、F-D0047-xxx（鄉鎮預報） |
| **P2（輔助）** | F-C0032-001、F-D0047-xxx、F-A0021-001（潮汐） | C-B0024-001（30天觀測）、C-B0074-001/002（測站基本資料）、F-C0032-001、F-A0021-001（潮汐） |

> 完整官方清單（80 筆，2026/8/25 核對）見 `https://opendata.cwa.gov.tw/apidoc/v1`（OpenAPI YAML）。舊資料中常見但**已不存在**（404）的 Data ID：O-A0013~19（逐時/3h/24h 雨量）、F-C0033-001（48h 雨量預報）、F-C0034-001、F-A0045-001（降雨雷達）、W-C0024-001、F-C0040-001（土石流）、O-C0010-001（河川水位）——開放資料平台無這些產品，需改抓 CWA 官網頁面（obscura）或新聞。

---

### P0 必須查詢（颱風追蹤核心）

#### 1. 熱帶氣旋完整資料（W-C0034-005）⭐ 最優先

- **用途**：西北太平洋及南海所有活動中熱帶氣旋的**完整歷史軌跡 + 未來預報**
- **回傳格式**：JSON
- **呼叫方式**：
```bash
curl "${BASE_URL}/W-C0034-005?Authorization=${CWA_API_KEY}&format=JSON"
```
- **主要欄位**：
  - `records.TropicalCyclones[].AnalysisData.Fix`：過去至現在的觀測資料（每 6 小時）
  - `records.TropicalCyclones[].ForecastData.Fix`：未來預報（6h~120h）
  - 每個 Fix 包含：DateTime、位置（CoordinateLatitude/Longitude）、最大風速、氣壓、移動速度/方向、暴風半徑
- **特點**：資料最完整，**每次更新都必須查詢**，適合自動更新颱風軌跡和預報

#### 2. 海上颱風警報（W-C0034-001）

- **用途**：CAP 格式的颱風警報資訊（警報標題、顏色、嚴重程度、警報報數、颱風編號、警戒區域）＋完整警報內文
- **回傳格式**：JSON
- **呼叫方式**：
```bash
curl "${BASE_URL}/W-C0034-001?Authorization=${CWA_API_KEY}&format=JSON"
```
- **主要欄位**：
  - `records.info[0].parameter`：警報標題（`alert_title`）、顏色（`alert_color`）、嚴重程度（`severity_level`）
  - `records.info[0].description.typhoon-info[].section[]`：颱風基本資料，但**僅元數據**（「警報報數」「警報類別」「颱風編號」「颱風資訊」），無實際內文
  - `records.info[0].description.section[]`：**實際警報全文**（「命名與位置」「強度與半徑」「移速與預測」「颱風動態」「警戒區域及事項」「大雨/強風特報」「注意事項」等），需由此處讀取
  - `records.info[0].area`：警戒區域多邊形座標
- **特點**：提供警報顏色、警戒區域與完整內文，**每次更新都必須查詢**（全文在 `description.section`，不在 `typhoon-info`）

---

### P1 重要（災情記錄相關）

#### 3. 陸上強風特報（W-C0033-001）

- **用途**：各縣市陸上強風特報資訊
- **回傳格式**：JSON
- **呼叫方式**：
```bash
curl "${BASE_URL}/W-C0033-001?Authorization=${CWA_API_KEY}&format=JSON"
```
- **主要欄位**：
  - `records.location[].hazardConditions.hazards`：各縣市強風特報
  - 包含：phenomena（陸上強風）、significance（特報）、validTime（有效時間）
- **特點**：當有陸上強風特報時查詢，用於記錄陸上風災影響

#### 4. 災害性天氣特報（W-C0033-003 / W-C0033-002）⭐ 豪雨事件首選

- **用途**：豪大雨特報等災害性天氣資訊（W-C0033-003 為 CAP 格式，W-C0033-002 為純文字＋影響區域）
- **回傳格式**：JSON
- **呼叫方式**：
```bash
curl "${BASE_URL}/W-C0033-003?Authorization=${CWA_API_KEY}&format=JSON"   # CAP 格式
curl "${BASE_URL}/W-C0033-002?Authorization=${CWA_API_KEY}&format=JSON"   # 純文字內容＋影響區域，較易解析
```
- **W-C0033-003 主要欄位**：
  - `records.info[].description`：災害說明（通常會提及颱風編號與影響）
  - `records.info[].parameter`：警報顏色、嚴重程度（如：severity_level、alert_color）
  - `records.info[].area`：警戒區域（區/鄉鎮級別）
  - `records.info[].effective` / `onset` / `expires`：生效／開始／失效時間
- **W-C0033-002 主要欄位**：
  - `records.record[].datasetInfo.datasetDescription`：特報品名（如「大雨特報」）
  - `records.record[].datasetInfo.validTime` / `issueTime` / `update`：有效與發布時間
  - `records.record[].contents.content.contentText`：特報全文（純文字）
  - `records.record[].hazardConditions.hazards.hazard[]`：phenomena（大雨/豪雨/強風…）、significance（特報/警報）、affectingArea
- **特點**：**豪雨/大雨事件每次更新必查**，用於記錄降雨災情與警報升降級

#### 5. 雨量觀測站資料（O-A0002-001）⭐ 豪雨事件雨量首選

- **用途**：全臺 1300+ 自動雨量站，**每 10 分鐘更新**，含多重時間尺度累計雨量
- **回傳格式**：JSON（約 1.2 MB；可用 `&StationName=高雄&StationName=屏東` 篩選）
- **呼叫方式**：
```bash
curl "${BASE_URL}/O-A0002-001?Authorization=${CWA_API_KEY}&format=JSON"
```
- **主要欄位**（`records.Station[]`）：
  - `StationName` / `StationId` / `ObsTime.DateTime` / `GeoInfo`（座標、鄉鎮、海拔）
  - `RainfallElement.Now.Precipitation`：**本日 0 時至目前的累積雨量** ⚠️ 不是 1 小時雨量！
  - `RainfallElement.Past10Min / Past1hr / Past3hr / Past6Hr / Past12hr / Past24hr / Past2days / Past3days`：各時間尺度累計（短延時強降雨看 Past1hr/Past3hr）
- **特點**：**豪雨事件 P0**。短延時強降雨（時雨量 40/80mm 等）以 `Past1hr` 為準；災情累計雨量以 `Past24hr` / `Past3days` 為準；`Now` 不可標註成「1 小時雨量」

#### 6. 自動氣象站資料（O-A0001-001 / O-A0003-001）

- **用途**：O-A0001-001 為全測站**逐時**氣象資料；O-A0003-001 為 10 分鐘綜觀氣象
- **回傳格式**：JSON
- **呼叫方式**：
```bash
curl "${BASE_URL}/O-A0001-001?Authorization=${CWA_API_KEY}&format=JSON"
curl "${BASE_URL}/O-A0003-001?Authorization=${CWA_API_KEY}&format=JSON"
```
- **主要欄位**（`records.Station[].WeatherElement.Now`）：
  - `Precipitation`：雨量（⚠️ 與 O-A0002-001 的 `Now` 同源，為**本日 0 時至目前累計**，非 1 小時雨量）
  - `WindSpeed` / 陣風：風速（注意：部分站點回傳 None，結構為 `WeatherElement.Now.*`）
  - `AirTemperature` / `RelativeHumidity` / `AirPressure`：氣溫／濕度／氣壓
- **特點**：用於風速、氣壓、氣溫等災情紀錄；雨量請改用 O-A0002-001

#### 7. 每日雨量（C-B0025-001）

- **用途**：地面測站每日雨量（當年 1/1 起逐日，「T」=雨跡〈0.5mm、「X」=無紀錄/儀器故障）
- **回傳格式**：JSON
- **呼叫方式**：
```bash
curl "${BASE_URL}/C-B0025-001?Authorization=${CWA_API_KEY}&format=JSON"
```
- **主要欄位**：`records.location[].station`（StationID/StationName）＋ `stationObsTimes.stationObsTime[].{Date, weatherElements.Precipitation}`
- **特點**：事件結束後補寫每日雨量總表時使用

#### 8. 30 天觀測資料（C-B0024-001）

- **用途**：地面測站近 30 天逐日氣象要素（氣壓、氣溫、濕度、風速、雨量、日照）
- **回傳格式**：JSON
- **呼叫方式**：
```bash
curl "${BASE_URL}/C-B0024-001?Authorization=${CWA_API_KEY}&format=JSON"
```
- **特點**：事件前後背景氣候資料（如「近 30 日第 N 大雨」比較），P2

---

### P2 輔助（可選查詢）

#### 9. 鄉鎮天氣預報（F-D0047-xxx）⭐ 豪雨事件預報首選

- **用途**：各縣鄉鎮級「未來 3 天／未來 1 週」預報（溫度、降水、降雨機率、風、天氣現象）
- **回傳格式**：JSON
- **Data ID 對照**：屏東 033/035、臺東 037/039、花蓮 041/043、高雄 065/067、臺南 077/079、連江 081/083、**全臺各鄉鎮 093**
- **呼叫方式**：
```bash
curl "${BASE_URL}/F-D0047-033?Authorization=${CWA_API_KEY}&format=JSON"   # 屏東縣未來 3 天
curl "${BASE_URL}/F-D0047-093?Authorization=${CWA_API_KEY}&format=JSON"   # 全臺各鄉鎮
```
- **主要欄位**：`records.Locations[].Location[]` → `WeatherElement[].{ElementName, Time[].{DataTime, ElementValue[]}}`（結構清晰，比 F-C0032-001 易解析）
- **特點**：豪雨事件「未來天氣預報」章節首選

#### 10. 今明 36 小時天氣預報（F-C0032-001）

- **用途**：鄉鎮級 36 小時預報（天氣現象、降雨機率）
- **回傳格式**：JSON
- **呼叫方式**：
```bash
curl "${BASE_URL}/F-C0032-001?Authorization=${CWA_API_KEY}&format=JSON"
```
- **主要欄位**：`records.location[].weatherElement[]`（⚠️ 子欄位結構與 F-D0047 不同，解析前請先 dump 一筆確認；若遇到解析失敗，改用 F-D0047-093）
- **特點**：可選

#### 11. 潮汐預報（F-A0021-001）

- **用途**：未來 1 個月潮汐預報（鄉鎮、大潮小潮、滿潮乾潮、時間、潮高）
- **回傳格式**：JSON
- **呼叫方式**：
```bash
curl "${BASE_URL}/F-A0021-001?Authorization=${CWA_API_KEY}&format=JSON"
```
- **主要欄位**：
  - `LocationName`：鄉鎮名稱
  - `Tide`：滿潮/乾潮
  - `TideHeights`：潮高

#### 12. 測站基本資料（C-B0074-001 / C-B0074-002）

- **用途**：有人／無人氣象測站清單（站號、站名、經緯度、海拔、狀態、起止日期）
- **呼叫方式**：
```bash
curl "${BASE_URL}/C-B0074-002?Authorization=${CWA_API_KEY}&format=JSON"
```
- **主要欄位**：`records.data.stationStatus.station[]` → `StationID` / `StationName` / `StationLatitude/Longitude` / `StationAltitude` / `CountyName`
- **特點**：無人氣象站（山區雨量站）的坐標對照，P2
- **特點**：當颱風可能引發沿海風暴潮時查詢，**可選**

### 資料解析範例（Python）

```python
import requests
import os

API_KEY = os.getenv("CWA_API_KEY")
BASE_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"

def get_typhoon_data():
    """取得 W-C0034-005 熱帶氣旋資料"""
    url = f"{BASE_URL}/W-C0034-005"
    params = {
        "Authorization": API_KEY,
        "format": "JSON"
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    # 解析白海豚颱風資料
    for cyclone in data["records"]["TropicalCyclones"]:
        if cyclone["CwaTyphoonName"] == "白海豚":
            # 最新觀測數據
            latest = cyclone["AnalysisData"]["Fix"][-1]
            print(f"位置：{latest['CoordinateLatitude']}, {latest['CoordinateLongitude']}")
            print(f"風速：{latest['MaxWindSpeed']} m/s")
            print(f"氣壓：{latest['Pressure']} hPa")
            
            # 預報數據
            for forecast in cyclone["ForecastData"]["Fix"]:
                print(f"{forecast['ForecastHour']}h：{forecast['CoordinateLatitude']}°, {forecast['CoordinateLongitude']}°")
    
    return data
```

### 注意事項

1. **快取建議**：API 有快取機制，建議每 30 分鐘至 1 小時查詢一次
2. **資料更新頻率**：颱風警報每 3~6 小時更新，熱帶氣旋資料每 6 小時更新
3. **錯誤處理**：若 `success` 欄位為 `"false"`，檢查 API Key 或 Data ID
4. **格式確認**：各資料集可下載格式不同（JSON/XML/ZIP/CAP），使用前請確認
5. **開發指南**：https://opendata.cwa.gov.tw/devManual/insrtuction
6. **資料清單**：https://opendata.cwa.gov.tw/devManual/datalist
7. **Swagger 線上文件**：https://opendata.cwa.gov.tw/dist/opendata-swagger.html
8. **資料集清單權威來源**：`https://opendata.cwa.gov.tw/apidoc/v1`（OpenAPI YAML，含全部 80 個 Data ID、參數與枚舉值）；web 版資料清單頁為 SPA，直接爬 HTML 拿不到清單
9. **雨量欄位語意**：O-A0001-001 / O-A0002-001 的 `Now.Precipitation` = **本日 0 時至目前累計**（非 1 小時雨量）；1 小時雨量請用 O-A0002-001 的 `Past1hr`（2026/8/25 根據官方資料集說明核實）
10. **O-B0075-001（48 小時海況）JSON 回傳空**：2026/8/25 實測 `records` 為空，海況改看 CWA 官網頁面或新聞

---

## Obscura 無頭瀏覽器工具

用於爬取中央氣象署網站的 JavaScript 渲染內容（當 API 無法取得時）。

### 基本資訊
- **Binary 位置**：`/usr/local/bin/obscura`（v0.2.0）
- **Docker 容器**：`obscura`（MCP HTTP port 3000, CDP port 9222）
- **技能文件**：`/root/.pi/agent/skills/obscura/SKILL.md`

### 常用指令

```bash
# 提取頁面文字（JS 執行後）
obscura fetch https://www.cwa.gov.tw --dump text --timeout 20

# 提取完整 HTML
obscura fetch https://www.cwa.gov.tw --dump html --timeout 20

# 提取連結
obscura fetch https://www.cwa.gov.tw --dump links --timeout 20

# 等待特定元素
obscura fetch https://example.com --selector ".content" --timeout 15

# Stealth 模式（防封鎖）
obscura --stealth fetch https://example.com --dump text
```

### 中央氣象署常用頁面

| 頁面 | URL | 說明 |
|------|-----|------|
| 首頁 | `https://www.cwa.gov.tw/V8/C/` | 天氣預報、氣象觀測 |
| 颱風警報 | `TY_WARN.html` | 颱風警報狀態 |
| 颱風消息 | `TY_NEWS.html` | 颱風路徑潛勢預報 |
| 颱風強風告警 | `TY_WIND.html` | 強風告警狀態 |

### 注意事項
- 首頁有 SVG JS 錯誤（`getTotalLength is not a function`），不影響主要內容
- 舊路徑 `Typhoon.html` 已移除，正確路徑為 `P/Typhoon/TY_*.html`
- 多語句 JS 需包 IIFE：`(function(){ ... })()`
- SSRF 保護會阻擋 private network，需加 `--allow-private-network`
- Docker 容器未運行時：`docker run -d --name obscura -p 3000:3000 h4ckf0r0day/obscura mcp --http --port 3000 --host 0.0.0.0`

---

## 網站專案（已上線：Cloudflare Pages `weather.*` 自訂域名 ×3 ＋ GitHub Pages https://lawlietr.github.io/Weather/）

- **更新/部署工作流（runbook）**：`WORKFLOW.md`——接手者（agent 或人工）先看這個。
- **構想與待辦**：`TODO.md`。
- **build 入口**：`./build/build.sh`（產出 `public/`（繁中）與 `public/ja/`（日文）、`llms.txt`（LLM 索引）與 `llms-full.txt`（事件全文）；CWA 資料 build 時本機抓取）。
  公開網站主要 host 於 Cloudflare Pages（自訂域名），另同步 GitHub Pages；彙整氣象署天氣資訊與災情紀錄。

### 多語言（i18n）

- 預設語言 **zh-Hant**（`public/` 根目錄）、第二語言 **ja**（`public/ja/`）；頁首有語言切換。
- 所有 UI 字串收斂在 `build/i18n.py`（`STRINGS` 表＋`t()` 三級回退）；**加新語言＝在 `STRINGS` 加一組 dict**，不改模板。
- **內容不翻譯**：事件 Markdown 正文、CWA 資料（颱風名、雨量站名、特報全文）全語言保留中文原文；非預設語言頁面以 `content_note` / `cwa_data_note` 提示。

### 核心原則

- **手動更新（人工 / LLM 驅動）**：不自動排程，使用者手動 build 並推送。
- **金鑰不外洩**：CWA API Key 全程只存在本機執行環境，不寫進任何輸出檔案，不進 repo、不進公開網站。
  - ⚠️ CWA API **不支援 CORS**（實測 `W-C0034-005` 回應無 `Access-Control-Allow-Origin` 標頭），故**前端無法直接呼叫**，氣象資料必須由本機 build 時抓取後寫入靜態 HTML。
- **災情來源優先級**：repo 現有 `災情/` markdown → RSS → Obscura 抓取。每筆附**新聞來源**，僅給**少量摘要＋原連結**。
- **非即時**：Pages 為靜態託管，採手動 build。首頁必須顯示「**產生時間**」（build 時寫入當下系統時間，i18n key `updated`）。
  - ⚠️ 用「產生時間」而非「最後更新」：build 每次都會改這個時間戳，但它只代表「網頁何時生成」，**不等於氣象／災情資料已更新**（資料新鮮度改看各 CWA section 與事件的時間戳）。用「最後更新」會誤導一般使用者。
- **雙授權**：程式碼（`build/` 等）以 **GNU AGPLv3**（`LICENSE`）；內容（`災情/`、`颱風/` 紀錄及其網頁、`llms.txt`、`llms-full.txt` 產出）以 **CC BY-NC-SA 4.0**（`LICENSE-CONTENT`，不得商用）；CWA 資料以官方條款為準。
- **LLM 友善產出**：build 必產 `llms.txt`（站點＋事件索引）與 `llms-full.txt`（全部事件繁中全文），canonical base URL 為 `https://weather.avpclub.eu.org`（`build/site.py` 之 `SITE_BASE`）。

### 技術架構

```
本機（手動執行）
  ├── 讀 repo 災情 markdown → 災情資料（縣市/時間/分級/摘要）
  ├── 讀 RSS / Obscura       → 補即時新聞災情（附來源）〔待實作〕
  ├── 呼叫 CWA API（金鑰在本地）→ 氣象彙整
  └── build 出靜態 HTML（含「產生時間」）
        ├── wrangler pages deploy public → Cloudflare Pages（主要）
        └── orphan gh-pages 分支 force push → GitHub Pages
Cloudflare / GitHub 靜態託管提供公開網站
```

### 網站結構

- **首頁**：氣象彙整（颱風軌跡/警報特報/雨量/風力）＋ 各縣市災情總覽（依縣市分組，每組內按時間倒序，最新在最上）。
- **各縣市子頁（選用）**：該縣市災情按時間倒序。

### 部署與分支

- **內部仓库**：`ssh://fg/lawliet/Weather.git`（Forgejo，內網 `192.168.1.124:222`，SSH Host `fg`，Identity `~/.ssh/id_rsa_gitea`）。
- 目前開發與 commit **只推到內部 forgejo**。
- **GitHub Pages**（公開，2026/8/26 已上線）：<https://lawlietr.github.io/Weather/>（繁中）＋ `/ja/`（日文）。只推 `public/` 靜態產物（orphan `gh-pages` 分支、不共享 history），Markdown 原文、build 腳本、內部倉庫資訊一律不公開。部署步驟見 `WORKFLOW.md` §6。
- **Cloudflare Pages**（公開，2026/8/26 已上線，**主要更新通道**）：專案 `weather`，自訂域名 `weather.avpclub.eu.org`、`weather.avpclub.uk`、`weather.larch.dpdns.org`（CNAME 已建、proxied、自動 HTTPS）。更新只需 `npx wrangler pages deploy public --project-name weather`（憑證在 `~/.zshrc` 的 `CLOUDFLARE_API_TOKEN`/`CLOUDFLARE_ACCOUNT_ID`，不進 repo）。細節見 `WORKFLOW.md` §6。
