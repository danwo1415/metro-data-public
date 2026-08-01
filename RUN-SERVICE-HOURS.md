# 港鐵首末班資料更新

把本包三個檔案上傳到公開 `metro-data-public` 倉庫，在 Codespaces 終端執行：

```bash
python -m pip install -r requirements-service-hours.txt
python update_hk_service_hours.py
python -m json.tool hong-kong-data.json >/dev/null
git add hong-kong-data.json version.json service-hours-report.json update_hk_service_hours.py requirements-service-hours.txt
git commit -m "Update Hong Kong first and last train data"
git push origin main
```

程式會讀取港鐵官方逐站服務時間頁，只有成功解析至少 70 個車站才會覆寫資料，並同步提高 `version.json` 的版本。App 下次啟動後會顯示資料更新提醒。
