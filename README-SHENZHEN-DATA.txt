深圳地鐵公開資料 v1
====================

本套件只放到公開資料倉庫 danwo1415/metro-data-public：
- shenzhen-data.json：深圳現行線網、車站、換乘關係及搜尋字典
- shenzhen-version.json：供 App 檢查資料版本
- shenzhen-environment.json：深圳環境資料輸出；首次執行前為空值
- update_shenzhen_environment.py：從深圳官方資料源取溫度、濕度、PM2.5，並嘗試讀取深圳市氣象局紫外線實況
- .github/workflows/update-shenzhen-environment.yml：每 15 分鐘檢查一次

必要設定：SZ_OPEN_DATA_APP_KEY
--------------------------------
深圳市政府資料開放平台接口需要 appKey。請先在官方平台申請／生成 appKey，然後：
1. 進入 GitHub：metro-data-public → Settings
2. Secrets and variables → Actions
3. New repository secret
4. Name 填 SZ_OPEN_DATA_APP_KEY
5. Secret 填官方 appKey

不要把 appKey 寫入 JSON、Python、README 或任何公開 commit。

首次部署命令
------------
unzip -o shenzhen-data-public-v1.zip
rm -f shenzhen-data-public-v1.zip

git add shenzhen-data.json shenzhen-version.json shenzhen-environment.json \
  update_shenzhen_environment.py README-SHENZHEN-DATA.txt \
  .github/workflows/update-shenzhen-environment.yml
git commit -m "Add Shenzhen metro and environment data"
git pull --rebase
git push origin main

設定 Secret 後，可在 GitHub 網頁 Actions 頁手動 Run workflow；若 Codespaces token 無 workflow_dispatch 權限，等待下一個每 15 分鐘排程即可。

重要限制
--------
- 線網 JSON 可立即使用，不需要 appKey。
- 環境 JSON 要等 workflow 成功後才有數值。
- 紫外線頁若沒有提供可可靠解析的實況數字，uv 會保持 null，不會以預報等級冒充實況。
- App 內部 SZxxx 車站代碼只為穩定識別，不是深圳地鐵官方站碼。
- 西麗高鐵站尚未投入地鐵營運，本資料不列為可選站。
