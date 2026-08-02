深圳官方資料更新套件 v2

包含：
1. update_shenzhen_fares.py
   - 從深圳市發展和改革委員會官方 2026 普通車廂票價 XLSX 讀取全線網票價。
   - 安全門檻：至少映射 150 個 App 車站及 10,000 個站間票價才更新正式 JSON。
   - 寫入 shenzhen-data.json 的 fares 與 fareMetadata，並更新 shenzhen-version.json。

2. update_shenzhen_service_hours.py
   - 低頻讀取深圳地鐵／港鐵深圳官方公開時刻表網頁。
   - 保存工作日、休息日、節假日三套資料，並將當天適用資料寫入 serviceHours。
   - 覆蓋不足時不替換正式資料。

3. update_shenzhen_environment.py
   - 溫度／濕度：深圳政府開放資料 29200_00903509（需要 SZ_OPEN_DATA_APP_KEY）。
   - 紫外線：深圳市氣象局健康氣象服務公開頁面；只接受明確的實況值，不會把 0-2／3-5 等說明區間誤當成數值。
   - PM2.5：中國環境監測總站全國城市空氣質量實時發布平台。
   - PM2.5 暫時抓取失敗時不阻止溫濕度發布；有舊的有效官方數值時保留舊值。

工作流：
- Update Shenzhen fares：每週一檢查，也可手動運行。
- Update Shenzhen service hours：每日四次檢查，也可手動運行。
- Update Shenzhen environment data：每 15 分鐘檢查，也可手動運行。

注意：
- 本套件只放進公開的 metro-data-public。
- App 源碼請使用 metro-route-planner-v2.5.1-sz.zip，放進私有 Metro 倉庫。
- 票價工作流首次實際解析結果需以 GitHub Actions 報告為準；安全門檻不通過時不會覆蓋資料。
