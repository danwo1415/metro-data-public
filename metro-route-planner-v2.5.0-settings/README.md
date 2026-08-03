# 地铁路线规划器 v2.5.0-settings

本版本在现有 Android WebView 架构上实现以下变更：

- 底部导航新增“设置”，并将语言选择统一放入设置。
- 支持繁体中文、简体中文、English，选择写入 LocalStorage。
- 设置中的城市列表支持长按约 0.43 秒后拖动排序，同时保留上下移动按钮作为无障碍备用操作。
- 首页抬头只展示城市排序前四位。
- 删除一屏压缩逻辑；页面使用自然高度、纵向滚动和固定底部导航安全间距。
- 深圳线路数据继续读取 `metro-data-public/shenzhen-data.json`。
- 深圳首末班读取现有 `serviceHours`；换乘路线按各段首末班和到达换乘站的估算时间计算全程可行窗口。
- 深圳普通车厢票价采用深圳市发展和改革委员会 2026 年官方 432 站线网票价矩阵，已转换为本地轻量 JSON。
- 紫外线和 PM2.5 暂时显示 `—`，不发起无可靠来源的请求。
- 广州／佛山、东莞、台北、高雄保留城市入口和数据接入位；在完整城市 JSON 接入前明确显示“待接入”，不会伪造票价或首末班。

## 在现有 GitHub 仓库中使用

1. 将整个 `metro-route-planner-v2.5.0-settings` 文件夹放到 `metro-data-public` 仓库根目录。
2. 将本包的 `.github/workflows/build-apk-v2.5.0.yml` 放到仓库根目录的同名路径。
3. 提交并推送到 `main`。
4. 在 GitHub Actions 中运行 **Build Metro APK v2.5.0**。
5. 在该工作流运行结果的 Artifacts 下载 `metro-route-planner-v2.5.0-settings-debug`。

## 数据文件约定

城市 JSON 至少需要：

```json
{
  "updatedAt": "YYYY-MM-DD",
  "L": {
    "LINE_ID": {
      "name": "繁体线路名",
      "simp": "简体线路名",
      "en": "English line name",
      "color": "#RRGGBB",
      "stations": [["STATION_CODE", "繁体站名"]]
    }
  },
  "simplified": {"STATION_CODE": "简体站名"},
  "english": {"STATION_CODE": "English station name"},
  "roman": {"STATION_CODE": "Pinyin"},
  "transferMeters": {"STATION_CODE": 200},
  "serviceHours": {
    "STATION_CODE": {
      "LINE_ID": {
        "TERMINAL_STATION_CODE": {"first": "06:00", "last": "23:30"}
      }
    }
  }
}
```

票价可以直接放在城市 JSON 的 `fares` 字段，也可以像深圳一样单独提供矩阵文件。

## 本地验证

本包已完成：

- JavaScript 语法检查；
- 路径算法、换乘计数、首末班约束、票价查询的 mock 单元测试；
- 深圳票价矩阵维度与常用站点抽样检查。

当前执行环境没有 Android SDK，因此未在本地生成 APK；仓库内的 GitHub Actions 工作流会使用 Android Gradle Plugin 8.5.2、Gradle 8.7 和 Java 17 构建。
