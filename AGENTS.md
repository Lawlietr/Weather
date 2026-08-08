# Weather - Typhoon Tracking

紀錄颱風動態與災情的 markdown 倉儲。

## ⚠️ 時間意識（極度重要）

**撰寫或查詢災情前，必須先確認目前的現實時間（系統時間）。**

- 本項目核心目的是**記錄目前正在發生的天氣事件**與即時災情彙整
- 搜尋與引用新聞時，**只關注當前事件相關的最新報導**，不應檢索上個月或幾年前的事件
- 檔案中的時間戳必須與現實時間一致，不可混淆年份或日期
- 若搜尋結果出現非當前事件的歷史資料，應主動過濾，避免將過去的事件誤植到當前紀錄中
- 每次新增災情前，先確認該災情是否屬於「目前正在發生」的颱風事件

## 目錄與檔名

```
颱風/{YYYY}/{MM}/{MMDD}_{NN}_{中文名}_{國際命名}.md
```

範例：`颱風/2026/07/0702_09_巴威_BAVI.md`

**說明**：
- `{MMDD}`：生成日期（月 + 日，補零，如 0702 表示 7 月 2 日）
- `{NN}`：颱風編號（補零，如 09 表示第 9 號）
- 這樣命名可確保檔案按日期和編號自然排序

## 檔案撰寫規則

- 全部使用**繁體中文**
- 時間戳須含年與時間，如 `2026/7/10 05:30`
- 災害分級標籤：`🔴重大` `🟡警戒` `🟢一般`
- 新進展**附加**在檔尾，不覆寫；僅在結構錯誤時修改既有內容
- 颱風基本資料表（強度、風速、半徑等）置於檔首，使用表格
- **每次修改**必須在檔首（基本資料表上方）新增一筆 `最後修改：YYYY/M/D HH:mm`，例如 `最後修改：2026/7/11 18:30`

## 章節慣例

依序：基本資料 → 警報時程 → 停班停課 → 風力/雨量/浪高 → 災情紀錄（依 🔴🟡🟢 分節）→ 交通影響 → 防災作為 → 備註

## Git

- 預設分支：`main`（原 `master` 已更名）
- 無 CI、無 lint/test 指令

---

## 中央氣象署（CWA）Open Data API

### API Key 設定

請在專案根目錄建立 `.env` 文件，內容如下：

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

### 常用颱風相關 API

#### 1. 海上颱風警報（W-C0034-001）

- **用途**：CAP 格式的颱風警報資訊（警報報數、颱風編號、強度、位置、預測、警戒區域）
- **回傳格式**：JSON
- **呼叫方式**：
```bash
curl "${BASE_URL}/W-C0034-001?Authorization=${CWA_API_KEY}&format=JSON"
```
- **主要欄位**：
  - `records.info[0].description.typhoon-info`：颱風基本資料（分析數據、預測數據）
  - `records.info[0].parameter`：警報標題、顏色、嚴重程度
  - `records.info[0].area`：警戒區域多邊形座標

#### 2. 熱帶氣旋完整資料（W-C0034-005）⭐ 推薦使用

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
- **特點**：資料最完整，適合自動更新颱風軌跡和預報

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

### 其他可用 API（已測試）

| Data ID | 用途 | 格式 | 備註 |
|---------|------|------|------|
| `F-A0012-001` | 海面天氣預報 | XML/ZIP | 非 JSON |
| `F-C0032-001` | 今明 36 小時天氣預報 | JSON | 鄉鎮預報 |
| `O-A0002-001` | 全測站逐時氣象資料 | JSON | 自動氣象站觀測 |

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
