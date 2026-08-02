Shenzhen environment updater v2 fix

Fixes:
- Uses the official service.xhtml endpoint rather than the invalid service.json path.
- Reads official weather fields T (temperature) and RHSFC (relative humidity).
- Keeps PM2.5 key matching compatible with PM2.5 / PM25 / PM2_5 variants.
- Gives a clear error if the appKey is valid but either API has not been subscribed.
- Uploads a short-lived diagnostic report from GitHub Actions on failure.

Required API subscriptions for the appKey:
- 29200_00903509 Shenzhen automatic-station grid observations
- 29200_00900269 Shenzhen PM2.5 real-time query
