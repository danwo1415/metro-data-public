# Changelog

## 2.5.0-settings — 2026-08-03

### Added
- Unified Settings tab.
- Traditional Chinese, Simplified Chinese and English UI.
- Long-press city ordering with persisted order.
- Four-city header derived from saved city order.
- Saved-route page and local favorites.
- Shenzhen official 2026 standard-class fare matrix.
- Whole-trip estimated first/last departure constraints.

### Fixed
- Long route results now use natural vertical scrolling.
- Removed viewport-fit classes that compressed long results into one screen.
- Added bottom safe-area padding so fixed navigation does not cover the final route section.

### Deferred
- UV and PM2.5 are intentionally blank.
- Guangzhou/Foshan and Dongguan require current complete city JSON before fares and service hours can be shown safely.
