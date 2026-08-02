package com.example.metroroute;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;

public class MainActivity extends Activity {
    private static final String OFFICIAL_NEWS_URL =
            "https://www.mtr.com.hk/ch/corporate/news/corporate.php";

    private WebView webView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        webView = new WebView(this);
        setContentView(webView);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setJavaScriptCanOpenWindowsAutomatically(false);
        settings.setSupportMultipleWindows(false);

        // Browser opening is isolated behind this explicit bridge. Remote JSON
        // downloads never navigate the WebView and therefore cannot open a browser.
        webView.addJavascriptInterface(new Object() {
            @JavascriptInterface
            public void openOfficialNews() {
                runOnUiThread(() -> {
                    try {
                        startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(OFFICIAL_NEWS_URL)));
                    } catch (Exception ignored) {
                        // Keep the app usable even if no external browser is available.
                    }
                });
            }
        }, "AndroidApp");

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                // Never allow the bundled app page to navigate away. The official
                // news link uses AndroidApp.openOfficialNews() above instead.
                return request.isForMainFrame();
            }
        });
        webView.setWebChromeClient(new WebChromeClient());

        // Use an HTTPS base origin so the bundled page can request GitHub JSON.
        try {
            String html = readAsset("index.html");
            webView.loadDataWithBaseURL(
                    "https://appassets.androidplatform.net/",
                    html,
                    "text/html",
                    "UTF-8",
                    null
            );
        } catch (IOException exception) {
            webView.loadData(
                    "<h3>無法載入應用程式介面</h3><p>" + exception.getMessage() + "</p>",
                    "text/html",
                    "UTF-8"
            );
        }
    }

    private String readAsset(String fileName) throws IOException {
        StringBuilder result = new StringBuilder();
        try (InputStream input = getAssets().open(fileName);
             BufferedReader reader = new BufferedReader(
                     new InputStreamReader(input, StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                result.append(line).append('\n');
            }
        }
        return result.toString();
    }

    @Override
    protected void onDestroy() {
        if (webView != null) webView.destroy();
        super.onDestroy();
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }
}
