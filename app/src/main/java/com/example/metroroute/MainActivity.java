package com.example.metroroute;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import org.json.JSONArray;
import org.json.JSONObject;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;
import org.xml.sax.InputSource;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.StringReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.Iterator;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import javax.xml.parsers.DocumentBuilderFactory;

public class MainActivity extends Activity {
    private static final String OFFICIAL_NEWS_URL =
            "https://www.mtr.com.hk/ch/corporate/news/corporate.php";
    private static final String HKO_WEATHER_URL =
            "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=en";
    private static final String HKO_UV_15MIN_URL =
            "https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_15min_uvindex.csv";
    private static final String EPD_PM25_URL =
            "https://www.aqhi.gov.hk/epd/ddata/html/out/24pc_Eng.xml";
    private static final String PUBLISHED_ENV_URL =
            "https://raw.githubusercontent.com/danwo1415/metro-data-public/main/hk-environment.json";
    private static final String EPD_AQHI_PAGE_URL =
            "https://www.aqhi.gov.hk/en/";
    private static final String DATA_GOV_FILTER_URL =
            "https://api.data.gov.hk/v2/filter?q=";
    private static final String MTR_FARES_URL =
            "https://opendata.mtr.com.hk/data/mtr_lines_fares.csv";
    private static final String AIRPORT_EXPRESS_FARES_URL =
            "https://opendata.mtr.com.hk/data/airport_express_fares.csv";

    private static final Set<String> AIRPORT_EXPRESS_STATIONS = new HashSet<>();
    static {
        AIRPORT_EXPRESS_STATIONS.add(normalizeStationName("Hong Kong"));
        AIRPORT_EXPRESS_STATIONS.add(normalizeStationName("Kowloon"));
        AIRPORT_EXPRESS_STATIONS.add(normalizeStationName("Tsing Yi"));
        AIRPORT_EXPRESS_STATIONS.add(normalizeStationName("Airport"));
        AIRPORT_EXPRESS_STATIONS.add(normalizeStationName("AsiaWorld-Expo"));
    }

    private final ExecutorService networkExecutor = Executors.newFixedThreadPool(3);
    private final Object fareLock = new Object();
    private volatile Map<String, String> regularFareMap;
    private volatile Map<String, String> airportFareMap;
    private WebView webView;
    private SharedPreferences environmentCache;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        environmentCache = getSharedPreferences("environment_cache", MODE_PRIVATE);
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

        webView.addJavascriptInterface(new Object() {
            @JavascriptInterface
            public void fetchWeather(String callbackId) {
                networkExecutor.execute(() -> {
                    try {
                        JSONObject payload = readWeatherPayload();
                        invokeJavascript("__nativeWeatherResolve", callbackId, true, payload.toString());
                    } catch (Exception exception) {
                        invokeJavascript("__nativeWeatherResolve", callbackId, false,
                                exception.getMessage() == null ? "Weather request failed" : exception.getMessage());
                    }
                });
            }

            @JavascriptInterface
            public void fetchFare(String originEnglish, String destinationEnglish, String callbackId) {
                networkExecutor.execute(() -> {
                    try {
                        String fare = lookupFare(originEnglish, destinationEnglish);
                        invokeJavascript("__nativeFareResolve", callbackId, fare != null, fare == null ? "" : fare);
                    } catch (Exception exception) {
                        invokeJavascript("__nativeFareResolve", callbackId, false,
                                exception.getMessage() == null ? "Fare request failed" : exception.getMessage());
                    }
                });
            }
        }, "AndroidData");

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return request.isForMainFrame();
            }
        });
        webView.setWebChromeClient(new WebChromeClient());

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

    private JSONObject readWeatherPayload() throws Exception {
        JSONObject root = new JSONObject(httpGet(HKO_WEATHER_URL));
        JSONObject result = new JSONObject();
        result.put("temperature", findWeatherValue(root.optJSONObject("temperature"), "Hong Kong Observatory"));
        result.put("humidity", findWeatherValue(root.optJSONObject("humidity"), "Hong Kong Observatory"));

        String uv;
        try {
            uv = readLatest15MinuteUv();
            if (!"--".equals(uv) && environmentCache != null) {
                environmentCache.edit().putString("uv15", uv).apply();
            }
        } catch (Exception ignored) {
            uv = environmentCache == null ? "--"
                    : cleanNumber(environmentCache.getString("uv15", "--"));
        }
        result.put("uv", uv);

        String pm25 = readPublishedPm25();
        if ("--".equals(pm25)) pm25 = readPm25WithFallbacks();
        if ("--".equals(pm25) && environmentCache != null) {
            pm25 = cleanNumber(environmentCache.getString("pm25", "--"));
        }
        if (!"--".equals(pm25) && environmentCache != null) {
            environmentCache.edit().putString("pm25", pm25).apply();
        }
        result.put("pm25", pm25);
        return result;
    }

    private String readPublishedPm25() {
        try {
            JSONObject payload = new JSONObject(httpGet(PUBLISHED_ENV_URL, true));
            String value = cleanNumber(payload.opt("pm25"));
            if (!"--".equals(value)) return value;
        } catch (Exception ignored) {
            // The public repository may not have produced its first hourly file yet.
        }
        return "--";
    }

    private String findWeatherValue(JSONObject group, String preferredPlace) {
        if (group == null) return "--";
        JSONArray data = group.optJSONArray("data");
        if (data == null || data.length() == 0) return "--";
        String fallback = "--";
        for (int i = 0; i < data.length(); i++) {
            JSONObject item = data.optJSONObject(i);
            if (item == null) continue;
            String value = cleanNumber(item.opt("value"));
            if (!"--".equals(value) && "--".equals(fallback)) fallback = value;
            if (preferredPlace.equalsIgnoreCase(item.optString("place"))) return value;
        }
        return fallback;
    }

    private String readLatest15MinuteUv() throws IOException {
        String csv = httpGet(HKO_UV_15MIN_URL, true).replace("\uFEFF", "").trim();
        if (csv.isEmpty()) return "--";

        String[] lines = csv.split("\r?\n");
        for (int i = lines.length - 1; i >= 1; i--) {
            String line = lines[i].trim();
            if (line.isEmpty()) continue;
            List<String> fields = parseCsvLine(line);
            if (fields.size() < 2) continue;
            String timestamp = fields.get(0).replaceAll("[^0-9]", "");
            if (timestamp.length() != 12) continue;
            return cleanNumber(fields.get(1));
        }
        return "--";
    }

    private String readPm25WithFallbacks() {
        // 1) Direct EPD XML feed. This is the authoritative source.
        try {
            String xml = httpGet(EPD_PM25_URL, true);
            String value = readPm25Value(xml);
            if (!"--".equals(value)) return value;
            value = readPm25ValueRegex(xml);
            if (!"--".equals(value)) return value;
        } catch (Exception ignored) {
            // Continue to an official DATA.GOV.HK proxy when the AQHI host rejects
            // a native Android request or changes its XML response headers.
        }

        // 2) DATA.GOV.HK Filter API. It reads the same EPD resource and returns JSON,
        // avoiding device-specific TLS, redirect and XML content-type problems.
        try {
            JSONObject query = new JSONObject();
            query.put("resource", EPD_PM25_URL);
            query.put("format", "json");
            String url = DATA_GOV_FILTER_URL
                    + URLEncoder.encode(query.toString(), StandardCharsets.UTF_8.name());
            String text = httpGet(url, true).trim();
            Object json = text.startsWith("[") ? new JSONArray(text) : new JSONObject(text);
            String value = readPm25FromJson(json);
            if (!"--".equals(value)) return value;
        } catch (Exception ignored) {
            // Continue to the official EPD public summary page.
        }

        // 3) Official EPD public summary page. This is a final fallback for cases
        // where the XML download endpoint is temporarily unavailable.
        try {
            String value = readPm25FromHtml(httpGet(EPD_AQHI_PAGE_URL, true));
            if (!"--".equals(value)) return value;
        } catch (Exception ignored) {
            // Returning -- keeps the rest of the weather row usable.
        }
        return "--";
    }

    private String readPm25FromJson(Object root) {
        List<Pm25Candidate> candidates = new ArrayList<>();
        collectPm25Candidates(root, candidates);
        return selectPm25Candidate(candidates);
    }

    private void collectPm25Candidates(Object node, List<Pm25Candidate> output) {
        if (node instanceof JSONObject) {
            JSONObject object = (JSONObject) node;
            String station = "";
            String dateTime = "";
            String value = "--";
            Iterator<String> keys = object.keys();
            while (keys.hasNext()) {
                String key = keys.next();
                Object child = object.opt(key);
                String normalized = key.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]", "");
                if (normalized.equals("stationname") || normalized.equals("station")) {
                    station = child == null ? "" : String.valueOf(child).trim();
                } else if (normalized.equals("datetime") || normalized.equals("date")
                        || normalized.equals("lastbuilddate")) {
                    dateTime = child == null ? "" : String.valueOf(child).trim();
                } else if (normalized.equals("pm25") || normalized.equals("fineparticulates")
                        || normalized.equals("finesuspendedparticulates")) {
                    value = cleanNumber(child);
                }
            }
            if (!"--".equals(value)) output.add(new Pm25Candidate(station, dateTime, value));

            keys = object.keys();
            while (keys.hasNext()) collectPm25Candidates(object.opt(keys.next()), output);
        } else if (node instanceof JSONArray) {
            JSONArray array = (JSONArray) node;
            for (int i = 0; i < array.length(); i++) collectPm25Candidates(array.opt(i), output);
        }
    }

    private String readPm25ValueRegex(String xml) {
        List<Pm25Candidate> candidates = new ArrayList<>();
        Pattern rowPattern = Pattern.compile(
                "<PollutantConcentration\\b[^>]*>(.*?)</PollutantConcentration>",
                Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
        Matcher rows = rowPattern.matcher(xml);
        while (rows.find()) {
            String row = rows.group(1);
            String station = findXmlTag(row, "StationName");
            String dateTime = findXmlTag(row, "DateTime");
            String value = cleanNumber(findXmlTag(row, "PM2\\.5"));
            if (!"--".equals(value)) candidates.add(new Pm25Candidate(station, dateTime, value));
        }
        return selectPm25Candidate(candidates);
    }

    private String findXmlTag(String text, String tagRegex) {
        Pattern pattern = Pattern.compile("<" + tagRegex + "\\b[^>]*>(.*?)</" + tagRegex + ">",
                Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
        Matcher matcher = pattern.matcher(text);
        if (!matcher.find()) return "";
        return decodeBasicHtml(stripTags(matcher.group(1))).trim();
    }

    private String readPm25FromHtml(String html) {
        List<Pm25Candidate> candidates = new ArrayList<>();
        Pattern rowPattern = Pattern.compile("<tr\\b[^>]*>(.*?)</tr>",
                Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
        Pattern cellPattern = Pattern.compile("<t[dh]\\b[^>]*>(.*?)</t[dh]>",
                Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
        Matcher rows = rowPattern.matcher(html);
        while (rows.find()) {
            List<String> cells = new ArrayList<>();
            Matcher cellMatcher = cellPattern.matcher(rows.group(1));
            while (cellMatcher.find()) {
                cells.add(decodeBasicHtml(stripTags(cellMatcher.group(1))).trim());
            }
            // Station, NO2, O3, SO2, CO, PM10, PM2.5, AQHI.
            if (cells.size() >= 8) {
                String station = cells.get(0);
                String value = cleanNumber(cells.get(6));
                if (!"--".equals(value) && looksLikeStation(station)) {
                    candidates.add(new Pm25Candidate(station, "", value));
                }
            }
        }
        return selectPm25Candidate(candidates);
    }

    private boolean looksLikeStation(String value) {
        String normalized = value.toLowerCase(Locale.ROOT).replace(" ", "");
        return normalized.contains("central/western")
                || normalized.contains("centralandwestern")
                || normalized.equals("mongkok")
                || normalized.equals("eastern")
                || normalized.contains("中西")
                || normalized.contains("旺角")
                || normalized.contains("東區")
                || normalized.contains("东区");
    }

    private String stripTags(String value) {
        return value == null ? "" : value.replaceAll("(?s)<[^>]+>", " ");
    }

    private String decodeBasicHtml(String value) {
        if (value == null) return "";
        return value.replace("&nbsp;", " ")
                .replace("&#160;", " ")
                .replace("&amp;", "&")
                .replace("&lt;", "<")
                .replace("&gt;", ">");
    }

    private String selectPm25Candidate(List<Pm25Candidate> candidates) {
        if (candidates.isEmpty()) return "--";
        String[] preferredStations = {
                "central/western", "centralandwestern", "中西區", "中西区",
                "mongkok", "旺角", "eastern", "東區", "东区"
        };
        Pm25Candidate best = null;
        int bestPriority = Integer.MAX_VALUE;
        for (Pm25Candidate candidate : candidates) {
            String station = candidate.station.toLowerCase(Locale.ROOT)
                    .replace(" ", "").replace("-", "");
            int priority = preferredStations.length;
            for (int i = 0; i < preferredStations.length; i++) {
                if (station.equals(preferredStations[i]) || station.contains(preferredStations[i])) {
                    priority = i;
                    break;
                }
            }
            if (best == null || priority < bestPriority
                    || (priority == bestPriority && candidate.dateTime.compareTo(best.dateTime) > 0)) {
                best = candidate;
                bestPriority = priority;
            }
        }
        return best == null ? "--" : best.value;
    }

    private static final class Pm25Candidate {
        final String station;
        final String dateTime;
        final String value;

        Pm25Candidate(String station, String dateTime, String value) {
            this.station = station == null ? "" : station;
            this.dateTime = dateTime == null ? "" : dateTime;
            this.value = value == null ? "--" : value;
        }
    }

    private String readPm25Value(String xml) throws Exception {
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
        factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
        factory.setExpandEntityReferences(false);
        Document document = factory.newDocumentBuilder().parse(new InputSource(new StringReader(xml)));
        NodeList rows = document.getElementsByTagName("PollutantConcentration");
        List<Pm25Candidate> candidates = new ArrayList<>();
        for (int i = 0; i < rows.getLength(); i++) {
            Node node = rows.item(i);
            if (!(node instanceof Element)) continue;
            Element row = (Element) node;
            String station = childText(row, "StationName");
            String dateTime = childText(row, "DateTime");
            String value = cleanNumber(childText(row, "PM2.5"));
            if (!"--".equals(value)) candidates.add(new Pm25Candidate(station, dateTime, value));
        }
        return selectPm25Candidate(candidates);
    }

    private String childText(Element parent, String tagName) {
        NodeList nodes = parent.getElementsByTagName(tagName);
        if (nodes.getLength() == 0) return "";
        String text = nodes.item(0).getTextContent();
        return text == null ? "" : text.trim();
    }

    private String lookupFare(String originEnglish, String destinationEnglish) throws Exception {
        String origin = normalizeStationName(originEnglish);
        String destination = normalizeStationName(destinationEnglish);
        if (origin.isEmpty() || destination.isEmpty()) return null;

        boolean airportPair = AIRPORT_EXPRESS_STATIONS.contains(origin)
                && AIRPORT_EXPRESS_STATIONS.contains(destination);
        Map<String, String> primary = airportPair ? getAirportFareMap() : getRegularFareMap();
        String fare = primary.get(fareKey(origin, destination));
        if (fare != null) return fare;

        Map<String, String> secondary = airportPair ? getRegularFareMap() : getAirportFareMap();
        return secondary.get(fareKey(origin, destination));
    }

    private Map<String, String> getRegularFareMap() throws Exception {
        Map<String, String> cached = regularFareMap;
        if (cached != null) return cached;
        synchronized (fareLock) {
            if (regularFareMap == null) regularFareMap = loadFareMap(MTR_FARES_URL);
            return regularFareMap;
        }
    }

    private Map<String, String> getAirportFareMap() throws Exception {
        Map<String, String> cached = airportFareMap;
        if (cached != null) return cached;
        synchronized (fareLock) {
            if (airportFareMap == null) airportFareMap = loadFareMap(AIRPORT_EXPRESS_FARES_URL);
            return airportFareMap;
        }
    }

    private Map<String, String> loadFareMap(String url) throws Exception {
        String csv = httpGet(url);
        BufferedReader reader = new BufferedReader(new StringReader(csv));
        String headerLine = reader.readLine();
        if (headerLine == null) throw new IOException("Empty fare file");
        List<String> header = parseCsvLine(headerLine);
        if (!header.isEmpty()) header.set(0, header.get(0).replace("\uFEFF", ""));

        int sourceIndex = findHeader(header, "SRC_STATION_NAME");
        int destinationIndex = findHeader(header, "DEST_STATION_NAME");
        int fareIndex = findFareHeader(header);
        if (sourceIndex < 0 || destinationIndex < 0 || fareIndex < 0) {
            throw new IOException("Unknown fare file format");
        }

        Map<String, String> fares = new HashMap<>();
        String line;
        while ((line = reader.readLine()) != null) {
            if (line.trim().isEmpty()) continue;
            List<String> row = parseCsvLine(line);
            int required = Math.max(sourceIndex, Math.max(destinationIndex, fareIndex));
            if (row.size() <= required) continue;
            String source = normalizeStationName(row.get(sourceIndex));
            String destination = normalizeStationName(row.get(destinationIndex));
            String fare = normalizeFare(row.get(fareIndex));
            if (!source.isEmpty() && !destination.isEmpty() && fare != null) {
                fares.put(fareKey(source, destination), fare);
                fares.put(fareKey(destination, source), fare);
            }
        }
        if (fares.isEmpty()) throw new IOException("No fare records found");
        return fares;
    }

    private int findHeader(List<String> header, String expected) {
        for (int i = 0; i < header.size(); i++) {
            if (expected.equalsIgnoreCase(header.get(i).trim())) return i;
        }
        return -1;
    }

    private int findFareHeader(List<String> header) {
        int exact = findHeader(header, "OCT_ADT_FARE");
        if (exact >= 0) return exact;
        for (int i = 0; i < header.size(); i++) {
            String value = header.get(i).toUpperCase(Locale.ROOT);
            if (value.contains("OCT") && value.contains("FARE")
                    && (value.contains("ADT") || value.contains("ADULT"))) return i;
        }
        return -1;
    }

    private List<String> parseCsvLine(String line) {
        List<String> fields = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        boolean quoted = false;
        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);
            if (c == '"') {
                if (quoted && i + 1 < line.length() && line.charAt(i + 1) == '"') {
                    current.append('"');
                    i++;
                } else {
                    quoted = !quoted;
                }
            } else if (c == ',' && !quoted) {
                fields.add(current.toString().trim());
                current.setLength(0);
            } else {
                current.append(c);
            }
        }
        fields.add(current.toString().trim());
        return fields;
    }

    private String normalizeFare(String value) {
        try {
            double number = Double.parseDouble(value.trim());
            if (number < 0) return null;
            if (Math.rint(number) == number) return String.format(Locale.US, "%.0f", number);
            return String.format(Locale.US, "%.1f", number);
        } catch (Exception ignored) {
            return null;
        }
    }

    private static String normalizeStationName(String value) {
        if (value == null) return "";
        return value.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]", "");
    }

    private String fareKey(String source, String destination) {
        return source + "|" + destination;
    }

    private String cleanNumber(Object value) {
        if (value == null || value == JSONObject.NULL) return "--";
        String text = String.valueOf(value).trim();
        if (text.isEmpty() || text.equalsIgnoreCase("N.A.") || text.equalsIgnoreCase("N/A")
                || text.equals("-") || text.equals("--")) return "--";
        String numeric = text.replaceAll("[^0-9.+-]", "");
        if (numeric.isEmpty() || numeric.equals("+") || numeric.equals("-")) return "--";
        try {
            double number = Double.parseDouble(numeric);
            if (Math.rint(number) == number) return String.format(Locale.US, "%.0f", number);
            return String.format(Locale.US, "%.1f", number);
        } catch (Exception ignored) {
            return "--";
        }
    }

    private String httpGet(String urlString) throws IOException {
        return httpGet(urlString, false);
    }

    private String httpGet(String urlString, boolean browserHeaders) throws IOException {
        HttpURLConnection connection = (HttpURLConnection) new URL(urlString).openConnection();
        connection.setRequestMethod("GET");
        connection.setConnectTimeout(15000);
        connection.setReadTimeout(20000);
        connection.setInstanceFollowRedirects(true);
        connection.setUseCaches(false);
        connection.setRequestProperty("User-Agent", browserHeaders
                ? "Mozilla/5.0 (Linux; Android 14; Mobile) AppleWebKit/537.36 "
                + "(KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36"
                : "MetroRoutePlanner/2.4.14");
        connection.setRequestProperty("Accept",
                "application/json,application/xml,text/xml,text/html,text/csv,text/plain,*/*");
        connection.setRequestProperty("Accept-Language", "en-HK,en;q=0.9,zh-HK;q=0.8");
        connection.setRequestProperty("Cache-Control", "no-cache");
        int status = connection.getResponseCode();
        InputStream stream = status >= 200 && status < 300
                ? connection.getInputStream() : connection.getErrorStream();
        if (stream == null) throw new IOException("HTTP " + status);
        StringBuilder result = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(stream, StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) result.append(line).append('\n');
        } finally {
            connection.disconnect();
        }
        if (status < 200 || status >= 300) throw new IOException("HTTP " + status);
        return result.toString();
    }

    private void invokeJavascript(String functionName, String callbackId, boolean ok, String payload) {
        if (webView == null) return;
        String script = "window." + functionName + "(" + JSONObject.quote(callbackId)
                + "," + (ok ? "true" : "false") + "," + JSONObject.quote(payload) + ");";
        runOnUiThread(() -> {
            if (webView != null) webView.evaluateJavascript(script, null);
        });
    }

    private String readAsset(String fileName) throws IOException {
        StringBuilder result = new StringBuilder();
        try (InputStream input = getAssets().open(fileName);
             BufferedReader reader = new BufferedReader(
                     new InputStreamReader(input, StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) result.append(line).append('\n');
        }
        return result.toString();
    }

    @Override
    protected void onDestroy() {
        networkExecutor.shutdownNow();
        if (webView != null) webView.destroy();
        super.onDestroy();
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }
}
