# CWA Open Data API — 逐 dataset 欄位查表

> **定位**：on-demand 查表檔，解析 CWA 資料前讀這裡。
> - **路由**（哪種事件查哪個 dataset、P0/P1/P2 優先級）→ `AGENTS.md`「中央氣象署（CWA）Open Data API」
> - **實測結構陷阱** → `WORKFLOW.md` §5（各 dataset 的「實測差異」註記同內容）
> - **完整資料集清單（80 個 Data ID）權威來源** → `https://opendata.cwa.gov.tw/apidoc/v1`（OpenAPI YAML；web 版資料清單頁是 SPA，直接爬 HTML 拿不到）
>
> Base URL：`https://opendata.cwa.gov.tw/api/v1/rest/datastore/{DataID}?Authorization=${CWA_API_KEY}&format=JSON`
> Key 設定見 `AGENTS.md`。⚠️ CWA API **不支援 CORS**（回應無 `Access-Control-Allow-Origin`），前端無法直接呼叫，必須 build 時本機抓取寫入靜態 HTML。

---

## P0：颱風追蹤核心

### W-C0034-005 熱帶氣旋完整資料 ⭐ 最優先

- **用途**：西北太平洋及南海所有活動中熱帶氣旋的**完整歷史軌跡 + 未來預報**，資料最完整，**每次更新都必須查詢**
- **主要欄位**（官方文件結構）：
  - `records.TropicalCyclones[].AnalysisData.Fix`：過去至現在觀測資料（每 6 小時）
  - `records.TropicalCyclones[].ForecastData.Fix`：未來預報（6h~120h）
  - 每個 Fix 包含：DateTime、位置（`CoordinateLatitude`/`CoordinateLongitude`）、最大風速、氣壓、移動速度/方向、暴風半徑
- **實測差異（2026/8/26–27）**：
  - 結構是 `records.TropicalCyclones.TropicalCyclone[]`（**多一層**，與官方文件不同）
  - 移動欄位是 `MovingSpeed` / `MovingDirection`
  - 風圈 `Circle15ms` / `Circle25ms` = `{Radius: str}`（字串）

### W-C0034-001 海上颱風警報

- **用途**：CAP 格式警報（標題、顏色、嚴重程度、報數、編號、警戒區域）＋完整警報內文，**每次更新都必須查詢**
- **主要欄位**：
  - `records.info[0].parameter`：警報標題（`alert_title`）、顏色（`alert_color`）、嚴重程度（`severity_level`）
  - `records.info[0].description.typhoon-info[].section[]`：颱風基本資料，但**僅元數據**（「警報報數」「警報類別」「颱風編號」「颱風資訊」），無實際內文
  - `records.info[0].description.section[]`：**實際警報全文**（「命名與位置」「強度與半徑」「移速與預測」「颱風動態」「警戒區域及事項」「大雨/強風特報」「注意事項」等 8 個 section），需由此處讀取
  - `records.info[0].area`：警戒區域多邊形座標
- **實測差異（2026/8/26–27）**：
  - CAP `parameter = [{valueName, value}]`（array of pairs，非扁平 dict）
  - 「解除」狀態看 `typhoon-info` sections 的「警報類別」值 `END`（`alert_title` 含「解除」亦可）
  - 全文**不在 `typhoon-info`**，在 `description.section[]`

---

## P1：災情記錄相關

### W-C0033-001 陸上強風特報

- **用途**：各縣市陸上強風特報
- **主要欄位**：
  - `records.location[].hazardConditions.hazards`：`phenomena`（陸上強風）、`significance`（特報）、`validTime`（有效時間）

### W-C0033-003 / W-C0033-002 災害性天氣特報 ⭐ 豪雨事件首選

- **用途**：豪大雨特報等（W-C0033-003 為 CAP 格式，W-C0033-002 為純文字＋影響區域，**較易解析**）
- **W-C0033-003 欄位**：
  - `records.info[].description`：災害說明（通常提及颱風編號與影響）
  - `records.info[].parameter`：警報顏色、嚴重程度
  - `records.info[].area`：警戒區域（區/鄉鎮級別）
  - `records.info[].effective` / `onset` / `expires`：生效／開始／失效時間
- **W-C0033-002 欄位**：
  - `records.record[].datasetInfo.datasetDescription`：特報品名（如「大雨特報」）
  - `records.record[].datasetInfo.validTime` / `issueTime` / `update`：有效與發布時間
  - `records.record[].contents.content.contentText`：特報全文（純文字）
  - `records.record[].hazardConditions.hazards.hazard[]`：`phenomena`（大雨/豪雨/強風…）、`significance`（特報/警報）、`affectingArea`
- **實測差異（2026/8/26–27，W-C0033-002）**：
  - `validTime = {startTime, endTime}`（無時區，視同 +08:00）
  - 影響區域在 `hazard[].info.affectedAreas.location[].locationName`
- **特點**：**豪雨/大雨事件每次更新必查**，用於記錄降雨災情與警報升降級

### O-A0002-001 雨量觀測站資料 ⭐ 豪雨事件雨量首選

- **用途**：全臺 1300+ 自動雨量站，**每 10 分鐘更新**，含多重時間尺度累計雨量
- **回傳**：JSON（約 1.2 MB；可用 `&StationName=高雄&StationName=屏東` 疊加篩選）
- **主要欄位**（`records.Station[]`）：
  - `StationName` / `StationId` / `ObsTime.DateTime` / `GeoInfo`（座標、鄉鎮、海拔）
  - `RainfallElement.Now.Precipitation`：**本日 0 時至目前的累積雨量** ⚠️ 不是 1 小時雨量
  - `RainfallElement.Past10Min / Past1hr / Past3hr / Past6Hr / Past12hr / Past24hr / Past2days / Past3days`：各時間尺度累計
- **實測（2026/8/25）**：值全為字串。
- **取數原則**：短延時強降雨（時雨量 40/80mm 等）看 `Past1hr` / `Past3hr`；災情累計雨量看 `Past24hr` / `Past3days`；`Now` 絕不可標註成「1 小時雨量」。

### O-A0001-001 / O-A0003-001 自動氣象站

- **用途**：O-A0001-001 全測站**逐時**氣象；O-A0003-001 為 10 分鐘綜觀氣象
- **主要欄位**（`records.Station[].WeatherElement.Now`）：
  - `Precipitation`：雨量（⚠️ 與 O-A0002-001 的 `Now` 同源，為**本日 0 時至目前累計**，非 1 小時雨量）
  - `WindSpeed` / 陣風（部分站點回傳 None）
  - `AirTemperature` / `RelativeHumidity` / `AirPressure`
- **特點**：風速、氣壓、氣溫紀錄用；雨量請改用 O-A0002-001

### C-B0025-001 每日雨量

- **用途**：地面測站每日雨量（當年 1/1 起逐日；「T」=雨跡〈0.5mm、「X」=無紀錄/儀器故障）
- **欄位**：`records.location[].station`（StationID/StationName）＋ `stationObsTimes.stationObsTime[].{Date, weatherElements.Precipitation}`
- **特點**：事件結束後補寫每日雨量總表時使用

### C-B0024-001 30 天觀測資料

- **用途**：近 30 天逐日氣象要素（氣壓、氣溫、濕度、風速、雨量、日照）
- **特點**：事件前後背景氣候資料（如「近 30 日第 N 大雨」比較）

---

## P2：輔助（可選查詢）

### F-D0047-xxx 鄉鎮天氣預報 ⭐ 豪雨事件預報首選

- **用途**：各縣鄉鎮級「未來 3 天／未來 1 週」預報（溫度、降水、降雨機率、風、天氣現象）
- **Data ID 對照**：屏東 033/035、臺東 037/039、花蓮 041/043、高雄 065/067、臺南 077/079、連江 081/083、**全臺各鄉鎮 093**（同一縣有「未來 3 天」與「未來 1 週」兩個 ID，依官方清單對照；例如 F-D0047-033 為屏東未來 3 天）
- **欄位**：`records.Locations[].Location[]` → `WeatherElement[].{ElementName, Time[].{DataTime, ElementValue[]}}`（結構清晰，比 F-C0032-001 易解析）

### F-C0032-001 今明 36 小時天氣預報

- **用途**：鄉鎮級 36 小時預報（天氣現象、降雨機率）
- **欄位**：`records.location[].weatherElement[]`（⚠️ 子欄位結構與 F-D0047 不同，解析前**先 dump 一筆確認**；解析失敗就改用 F-D0047-093）

### F-A0021-001 潮汐預報

- **用途**：未來 1 個月潮汐（大潮小潮、滿潮乾潮、時間、潮高）；**當颱風可能引發沿海風暴潮時查詢**
- **欄位**：`LocationName`（鄉鎮）、`Tide`（滿潮/乾潮）、`TideHeights`（潮高）

### C-B0074-001 / C-B0074-002 測站基本資料

- **用途**：有人（001）／無人（002）氣象測站清單（站號、站名、經緯度、海拔、狀態、起止日期）
- **欄位**：`records.data.stationStatus.station[]` → `StationID` / `StationName` / `StationLatitude`/`StationLongitude` / `StationAltitude` / `CountyName`
- **特點**：無人氣象站（山區雨量站）的座標對照

### O-B0075-001 48 小時海況 ⚠️ 勿用

- **2026/8/25 實測：JSON 回傳 `records` 為空。** 海況改看 CWA 官網頁面（obscura）或新聞。

---

## 資料解析範例（Python）

```python
import os
import requests

API_KEY = os.getenv("CWA_API_KEY")
BASE_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"

def get_typhoon_data():
    """取得 W-C0034-005 熱帶氣旋資料"""
    r = requests.get(f"{BASE_URL}/W-C0034-005",
                     params={"Authorization": API_KEY, "format": "JSON"})
    data = r.json()

    # ⚠️ 實測結構多一層 TropicalCyclone[]（見上方「實測差異」）
    for cyclone in data["records"]["TropicalCyclones"]["TropicalCyclone"]:
        name = cyclone.get("CwaTyphoonName")
        latest = cyclone["AnalysisData"]["Fix"][-1]
        print(f"{name} 最新觀測 {latest['DateTime']}"
              f" {latest['CoordinateLatitude']}, {latest['CoordinateLongitude']}"
              f" 風速 {latest['MaxWindSpeed']} m/s 氣壓 {latest['Pressure']} hPa")
        for fc in cyclone["ForecastData"]["Fix"]:
            print(f"  +{fc['ForecastHour']}h：{fc['CoordinateLatitude']}, {fc['CoordinateLongitude']}")
    return data
```

---

## 其他注意事項

1. **快取**：API 有快取機制，建議每 30 分鐘～1 小時查詢一次。
2. **更新頻率**：颱風警報每 3~6 小時，熱帶氣旋資料每 6 小時。
3. **錯誤處理**：`success` 欄位為 `"false"` 時檢查 API Key 或 Data ID。
4. **格式**：各 dataset 可下載格式不同（JSON/XML/ZIP/CAP），使用前確認。
5. **開發指南**：https://opendata.cwa.gov.tw/devManual/insrtuction
6. **資料清單（web 版）**：https://opendata.cwa.gov.tw/devManual/datalist（SPA，爬不到；以 apidoc/v1 YAML 為準）
7. **Swagger**：https://opendata.cwa.gov.tw/dist/opendata-swagger.html
