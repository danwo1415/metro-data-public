# 六城地鐵路線規劃器 v2.4.3-HK


## v2.4.3 修正
- 修正已下載的 `serviceHours` 沒有載入：舊版在 `roman` 變數初始化之前讀取它，觸發 JavaScript 暫時性死區錯誤；錯誤被 `try/catch` 吞掉後，`serviceHours` 一直保持空物件。
- 安裝覆蓋後會直接讀取先前已成功刷新的本機資料，不需要重新抓取官方資料。

## v2.4.2 修正
- 修正 Android WebView 以 `file:///android_asset/` 載入頁面，導致 `fetch()` 無法可靠存取 GitHub 更新服務的問題。
- 改用 HTTPS base URL 載入 APK 內嵌 HTML，不開啟不安全的 file URL 跨網域權限。
- 更新檢查與刷新失敗時顯示具體錯誤，不再靜默失敗。
- 即使資料版本相同，只要本機沒有有效 `serviceHours`，仍會重新顯示刷新提示。

## 本次更新
- 取消「最新安排」按鈕與即時列車查詢介面。
- 新增港鐵官方新聞稿入口：「更多資訊可參考如下公告」。
- 起點／終點支援中文、官方英文名稱、拼音、拼音首字母及車站代碼搜尋。
- 新增資料版本檢查：偵測到本地路網資料有新版時，顯示「資訊有更新，請按刷新鍵刷新」。
- 按「刷新」下載新版 JSON，驗證後保存至本機；失敗時繼續使用舊資料。

## 更新服務設定
目前版本檢查地址：
`https://raw.githubusercontent.com/danwo1415/metro-data-public/main/version.json`

由於私人 GitHub 倉庫的 Raw 檔案不能匿名讀取，該倉庫需公開，或把 `UPDATE_MANIFEST_URL` 改為可公開訪問的 VPS/網站地址。manifest 格式：
```json
{
  "version": "2026.08.01.1",
  "dataUrl": "https://example.com/hk-data.json"
}
```
資料檔至少需包含 `L`，亦可包含 `transferMeters`、`roman`、`english`。

## 目前限制
- 行車時間是站間估算。
- 香港逐站、逐線、逐方向首末班資料已接入。
- 深圳、廣州、東莞、台北及高雄尚未接入真實資料。

## v2.2 public data endpoint

The app checks:
`https://raw.githubusercontent.com/danwo1415/metro-data-public/main/version.json`

The manifest points to the public `hong-kong-data.json` file.


## v2.3 首末班顯示規則
- 始發站顯示表定時間，不加「約」
- 中途站首末班加「約」
- 末班固定顯示建議提前 5 分鐘到達月台
- 僅在公開資料提供 `journeyTimes` 完整行程時間後顯示，缺失時不虛構時間


## v2.4 逐站首末班資料
- 改用 `serviceHours`，資料鍵為：車站代碼 → 路線代碼 → 方向終點代碼。
- 直達行程讀取起點站相應方向的表定首末班。
- 換乘行程按各段首末班、估算行車時間及換乘步行時間推算可完成行程的時間窗口。
- 中途站或換乘結果顯示「約」；末班固定提示提前 5 分鐘到達月台。

資料格式示例：
```json
{
  "serviceHours": {
    "CEN": {
      "TWL": {
        "TSW": {"first": "06:06", "last": "00:54"}
      }
    }
  }
}
```
