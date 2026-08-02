Shenzhen environment updater v3

What changed
- Removes the obsolete/unavailable dataset ID 29200_00900269 from the workflow.
- Publishes official Shenzhen temperature and humidity even when no verified official real-time PM2.5 dataset is available.
- Continues attempting to read the Shenzhen Meteorological Bureau UV page.
- Writes pm25 as null, so the app displays -- rather than using stale or unofficial data.
- The workflow now succeeds when temperature and humidity are valid; UV may be null without blocking publication.

Required secret
- SZ_OPEN_DATA_APP_KEY, subscribed to dataset 29200_00903509.

PM2.5 policy
- Do not restore 29200_00900269 unless the current Shenzhen Open Data catalog exposes it again and its interface is verified.
- Do not substitute a third-party PM2.5 value while the app labels the data as official.
