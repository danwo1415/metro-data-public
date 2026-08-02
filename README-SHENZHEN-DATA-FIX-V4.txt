深圳官方環境與首末班更新器 v4
================================

本包更新兩個 GitHub Actions 資料流程：

1. update_shenzhen_environment.py
   - 溫度、濕度：深圳政府資料開放平台資料集 29200_00903509（必需）。
   - PM2.5：依序嘗試 29200_01000344、29200_00900269（可選）。
   - 紫外線：嘗試 29200_03001143（可選）。
   - PM2.5 或紫外線無權限、無資料、欄位格式改變時，不會阻止溫度／濕度發布。
   - 有舊的有效 PM2.5／紫外線值時保留；沒有有效值則發布 null，App 顯示「--」。
   - 每次生成 shenzhen-environment-report.json，記錄各資料集的請求及解析狀態。

2. update_shenzhen_service_hours.py
   - 繼續只讀取深圳地鐵／港鐵深圳公開官方網頁。
   - 先讀取各線官方時刻表目錄；目錄未暴露文章連結時，使用少量已驗證的官方直達頁建立首批資料。
   - 對仍缺資料的線路，才有限並行讀取官方逐站頁，避免一個失效網址拖垮整個工作流。
   - 先使用當天對應的工作日／休息日／節假日時刻；當官方頁面某些站或方向缺失時，
     才以其他官方日型的同站同方向資料補齊，並標記 fallbackDayType。
   - 不會自行估算或偽造首末班時間。
   - 每次生成 shenzhen-service-hours-report.json，並由工作流上傳為診斷 Artifact。

部署
----
把本 ZIP 解壓到 metro-data-public 根目錄，提交並推送。確認 Repository Secret
SZ_OPEN_DATA_APP_KEY 已存在。

在深圳政府資料開放平台，請檢查 App 對以下資料集的訂閱／授權：
- 29200_00903509：溫度、濕度
- 29200_01000344：PM2.5（首選；若平台當前仍提供）
- 29200_03001143：紫外線指數預報

然後手動運行：
- Actions → Update Shenzhen environment data → Run workflow
- Actions → Update Shenzhen service hours → Run workflow

首次真實運行仍以 GitHub Actions 日誌與兩份 report Artifact 為準。即使可選資料集未獲授權，
環境工作流也應發布溫度／濕度；PM2.5、紫外線在取得有效官方值前顯示「--」。
