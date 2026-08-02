Hong Kong PM2.5 automatic updater

Install these files once in the root of danwo1415/metro-data-public.

What it does:
- Runs automatically every hour at minute 37.
- Also runs immediately when these updater files are first pushed.
- Reads the official Hong Kong EPD past-24-hour pollutant XML.
- Validates at least 10 stations and 80 valid PM2.5 records before publishing.
- Publishes hk-environment.json for the Android app.
- Keeps the previous public file untouched when downloading or validation fails.

Files:
- update_hk_environment.py
- .github/workflows/update-hk-environment.yml

The Android app v2.4.13 reads:
https://raw.githubusercontent.com/danwo1415/metro-data-public/main/hk-environment.json
