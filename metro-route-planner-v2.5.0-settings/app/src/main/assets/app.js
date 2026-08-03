'use strict';

const DATA_ROOT = 'https://raw.githubusercontent.com/danwo1415/metro-data-public/refs/heads/main/';
const STORAGE = {
  language: 'metro.language.v1',
  cityOrder: 'metro.cityOrder.v1',
  currentCity: 'metro.currentCity.v1',
  favorites: 'metro.favorites.v1'
};

const CITY_CONFIGS = [
  { id: 'shenzhen', dataUrl: DATA_ROOT + 'shenzhen-data.json', enabled: true },
  { id: 'hongkong', dataUrl: DATA_ROOT + 'hong-kong-data.json', enabled: true },
  { id: 'guangfo', dataUrl: null, enabled: false },
  { id: 'dongguan', dataUrl: null, enabled: false },
  { id: 'taipei', dataUrl: null, enabled: false },
  { id: 'kaohsiung', dataUrl: null, enabled: false }
];

const I18N = {
  'zh-Hant': {
    search: '查詢', favorites: '收藏', about: '關於', settings: '設定',
    from: '起點', to: '終點', placeholder: '中文／英文／拼音首字母', swap: '交換起點終點',
    searchRoute: '查詢路線', fastest: '時間最短', fewest: '換乘最少',
    initialHint: '請選擇起點和終點', loading: '正在載入城市線路資料…',
    loadFailed: '線路資料讀取失敗，請檢查網絡後重試。', unavailable: '此城市的完整線路資料尚未接入。',
    sameStation: '起點和終點不能相同。', stationNotFound: '請從搜尋結果中選擇有效車站。', noRoute: '找不到可用路線。',
    minutes: '分鐘', transfers: '次換乘', noTransfer: '直達', fare: '票價', firstTrain: '最早出發', lastTrain: '最晚出發',
    temperature: '溫度', humidity: '濕度', uv: '紫外線', pm25: 'PM2.5',
    direction: '往', transferAt: '在此換乘', distance: '距離', walking: '步行', meter: '米',
    addFavorite: '加入收藏', favorited: '已收藏', routeEstimate: '時間按站間約2分鐘及換乘步行0.5米／秒估算。首末班為全程可行時間的近似值。',
    favoriteEmpty: '尚未收藏任何路線。', open: '打開', remove: '刪除',
    aboutApp: '地鐵路線規劃', version: '版本 2.5.0-settings',
    aboutDescription: '本版新增統一設定頁、三語切換、城市長按拖動排序、首頁只顯示前四個城市，並移除長路線的一屏壓縮限制。',
    dataCoverage: '資料覆蓋', ready: '已接入', pending: '待接入',
    language: '語言', citySelection: '城市選擇', cityHelp: '長按城市名稱後上下拖動排序。首頁抬頭只顯示前四個城市。',
    topCity: '首頁第{n}位', hiddenCity: '不在首頁前四位',
    dataUpdated: '資料更新：{date}', dataReady: '線路、首末班資料已載入', fareReady: '深圳官方普通車廂票價已載入',
    fareMissing: '票價暫無資料', hoursMissing: '首末班暫無資料', environmentalBlank: '紫外線和PM2.5暫時留空。',
    city: { shenzhen:'深圳', hongkong:'香港', guangfo:'廣州／佛山', dongguan:'東莞', taipei:'台北', kaohsiung:'高雄' },
    languageNames: { 'zh-Hant':'繁體中文', 'zh-Hans':'简体中文', en:'English' }
  },
  'zh-Hans': {
    search: '查询', favorites: '收藏', about: '关于', settings: '设置',
    from: '起点', to: '终点', placeholder: '中文／英文／拼音首字母', swap: '交换起点终点',
    searchRoute: '查询路线', fastest: '时间最短', fewest: '换乘最少',
    initialHint: '请选择起点和终点', loading: '正在载入城市线路数据…',
    loadFailed: '线路数据读取失败，请检查网络后重试。', unavailable: '此城市的完整线路数据尚未接入。',
    sameStation: '起点和终点不能相同。', stationNotFound: '请从搜索结果中选择有效车站。', noRoute: '找不到可用路线。',
    minutes: '分钟', transfers: '次换乘', noTransfer: '直达', fare: '票价', firstTrain: '最早出发', lastTrain: '最晚出发',
    temperature: '温度', humidity: '湿度', uv: '紫外线', pm25: 'PM2.5',
    direction: '往', transferAt: '在此换乘', distance: '距离', walking: '步行', meter: '米',
    addFavorite: '加入收藏', favorited: '已收藏', routeEstimate: '时间按站间约2分钟及换乘步行0.5米／秒估算。首末班为全程可行时间的近似值。',
    favoriteEmpty: '尚未收藏任何路线。', open: '打开', remove: '删除',
    aboutApp: '地铁路线规划', version: '版本 2.5.0-settings',
    aboutDescription: '本版新增统一设置页、三语切换、城市长按拖动排序、首页只显示前四个城市，并移除长路线的一屏压缩限制。',
    dataCoverage: '数据覆盖', ready: '已接入', pending: '待接入',
    language: '语言', citySelection: '城市选择', cityHelp: '长按城市名称后上下拖动排序。首页抬头只显示前四个城市。',
    topCity: '首页第{n}位', hiddenCity: '不在首页前四位',
    dataUpdated: '数据更新：{date}', dataReady: '线路、首末班数据已载入', fareReady: '深圳官方普通车厢票价已载入',
    fareMissing: '票价暂无数据', hoursMissing: '首末班暂无数据', environmentalBlank: '紫外线和PM2.5暂时留空。',
    city: { shenzhen:'深圳', hongkong:'香港', guangfo:'广州／佛山', dongguan:'东莞', taipei:'台北', kaohsiung:'高雄' },
    languageNames: { 'zh-Hant':'繁體中文', 'zh-Hans':'简体中文', en:'English' }
  },
  en: {
    search: 'Routes', favorites: 'Saved', about: 'About', settings: 'Settings',
    from: 'From', to: 'To', placeholder: 'Name, English or pinyin initials', swap: 'Swap origin and destination',
    searchRoute: 'Find route', fastest: 'Fastest', fewest: 'Fewest transfers',
    initialHint: 'Select an origin and destination', loading: 'Loading city rail data…',
    loadFailed: 'Could not load rail data. Check the network and try again.', unavailable: 'Complete rail data for this city has not been connected yet.',
    sameStation: 'Origin and destination must be different.', stationNotFound: 'Choose a valid station from the search results.', noRoute: 'No route was found.',
    minutes: 'min', transfers: 'transfers', noTransfer: 'Direct', fare: 'Fare', firstTrain: 'Earliest departure', lastTrain: 'Latest departure',
    temperature: 'Temperature', humidity: 'Humidity', uv: 'UV', pm25: 'PM2.5',
    direction: 'towards', transferAt: 'Transfer here', distance: 'Distance', walking: 'Walk', meter: 'm',
    addFavorite: 'Save route', favorited: 'Saved', routeEstimate: 'Travel time uses about 2 minutes per station plus transfer walking at 0.5 m/s. First and last departures are whole-trip estimates.',
    favoriteEmpty: 'No saved routes yet.', open: 'Open', remove: 'Remove',
    aboutApp: 'Metro Route Planner', version: 'Version 2.5.0-settings',
    aboutDescription: 'This release adds a unified settings page, three languages, long-press city sorting, a four-city header, and natural scrolling for long route results.',
    dataCoverage: 'Data coverage', ready: 'Connected', pending: 'Pending',
    language: 'Language', citySelection: 'City selection', cityHelp: 'Long-press a city and drag it to reorder. Only the first four cities appear in the header.',
    topCity: 'Header position {n}', hiddenCity: 'Outside the first four',
    dataUpdated: 'Data updated: {date}', dataReady: 'Lines and service hours loaded', fareReady: 'Official Shenzhen standard-class fares loaded',
    fareMissing: 'Fare unavailable', hoursMissing: 'Service hours unavailable', environmentalBlank: 'UV and PM2.5 are intentionally blank for now.',
    city: { shenzhen:'Shenzhen', hongkong:'Hong Kong', guangfo:'Guangzhou/Foshan', dongguan:'Dongguan', taipei:'Taipei', kaohsiung:'Kaohsiung' },
    languageNames: { 'zh-Hant':'繁體中文', 'zh-Hans':'简体中文', en:'English' }
  }
};

const state = {
  language: safeGet(STORAGE.language, 'zh-Hant'),
  cityOrder: normalizeCityOrder(readJson(STORAGE.cityOrder, CITY_CONFIGS.map(c => c.id))),
  currentCity: safeGet(STORAGE.currentCity, 'shenzhen'),
  screen: 'search',
  mode: 'fast',
  fromCode: null,
  toCode: null,
  currentData: null,
  currentGraph: null,
  dataCache: new Map(),
  graphCache: new Map(),
  fareData: null,
  routeResults: { fast: null, few: null },
  favorites: readJson(STORAGE.favorites, []),
  loadingToken: 0,
  sorting: { timer: null, id: null, active: false, startX: 0, startY: 0 }
};

if (!CITY_CONFIGS.some(c => c.id === state.currentCity)) state.currentCity = state.cityOrder[0];
if (!state.cityOrder.slice(0, 4).includes(state.currentCity)) state.currentCity = state.cityOrder[0];

const el = {};

document.addEventListener('DOMContentLoaded', init);

async function init() {
  cacheElements();
  bindEvents();
  await loadFareData();
  applyLanguage();
  renderCityTabs();
  renderSettings();
  renderFavorites();
  renderAbout();
  showInitialResult();
  await selectCity(state.currentCity, false);
}

function cacheElements() {
  [
    'cityTabs','fromLabel','toLabel','fromInput','toInput','fromSuggestions','toSuggestions','swapButton','searchButton','dataStatus',
    'fastMode','fewMode','result','favoritesTitle','favoritesList','aboutTitle','aboutAppTitle','aboutVersion','aboutDescription',
    'dataCoverageTitle','dataCoverage','settingsTitle','languageTitle','languageOptions','cityOrderTitle','cityOrderHelp','citySortList','bottomNav'
  ].forEach(id => { el[id] = document.getElementById(id); });
}

function bindEvents() {
  el.bottomNav.addEventListener('click', event => {
    const button = event.target.closest('[data-screen]');
    if (button) showScreen(button.dataset.screen);
  });
  el.cityTabs.addEventListener('click', event => {
    const button = event.target.closest('[data-city]');
    if (button) selectCity(button.dataset.city, true);
  });
  el.fromInput.addEventListener('input', () => { state.fromCode = null; showSuggestions('from'); });
  el.toInput.addEventListener('input', () => { state.toCode = null; showSuggestions('to'); });
  el.fromInput.addEventListener('focus', () => showSuggestions('from'));
  el.toInput.addEventListener('focus', () => showSuggestions('to'));
  el.fromSuggestions.addEventListener('click', event => chooseSuggestion(event, 'from'));
  el.toSuggestions.addEventListener('click', event => chooseSuggestion(event, 'to'));
  document.addEventListener('click', event => {
    if (!event.target.closest('.field')) hideSuggestions();
  });
  el.swapButton.addEventListener('click', swapStations);
  el.searchButton.addEventListener('click', runSearch);
  el.fastMode.addEventListener('click', () => setMode('fast'));
  el.fewMode.addEventListener('click', () => setMode('few'));
  el.result.addEventListener('click', event => {
    const favoriteButton = event.target.closest('[data-action="favorite"]');
    if (favoriteButton) addCurrentFavorite();
  });
  el.languageOptions.addEventListener('change', event => {
    if (event.target.name === 'language') setLanguage(event.target.value);
  });
  el.citySortList.addEventListener('click', onCitySortClick);
  el.citySortList.addEventListener('pointerdown', onSortPointerDown);
  document.addEventListener('pointermove', onSortPointerMove, { passive: false });
  document.addEventListener('pointerup', finishSortGesture);
  document.addEventListener('pointercancel', finishSortGesture);
  el.favoritesList.addEventListener('click', onFavoriteAction);
}

function t(key, vars = {}) {
  let value = I18N[state.language]?.[key] ?? I18N['zh-Hant'][key] ?? key;
  if (typeof value !== 'string') return value;
  Object.entries(vars).forEach(([name, replacement]) => { value = value.replaceAll('{' + name + '}', replacement); });
  return value;
}

function cityName(id) { return I18N[state.language].city[id] || id; }

function applyLanguage() {
  document.documentElement.lang = state.language;
  el.fromLabel.textContent = t('from');
  el.toLabel.textContent = t('to');
  el.fromInput.placeholder = t('placeholder');
  el.toInput.placeholder = t('placeholder');
  el.swapButton.setAttribute('aria-label', t('swap'));
  el.searchButton.textContent = t('searchRoute');
  el.fastMode.textContent = t('fastest');
  el.fewMode.textContent = t('fewest');
  el.favoritesTitle.textContent = t('favorites');
  el.aboutTitle.textContent = t('about');
  el.settingsTitle.textContent = t('settings');
  el.languageTitle.textContent = t('language');
  el.cityOrderTitle.textContent = t('citySelection');
  el.cityOrderHelp.textContent = t('cityHelp');
  el.aboutAppTitle.textContent = t('aboutApp');
  el.aboutVersion.textContent = t('version');
  el.aboutDescription.textContent = t('aboutDescription');
  el.dataCoverageTitle.textContent = t('dataCoverage');
  document.querySelectorAll('[data-nav-label]').forEach(node => { node.textContent = t(node.dataset.navLabel); });
  renderCityTabs();
  renderSettings();
  renderFavorites();
  renderAbout();
  refreshInputNames();
  renderSelectedRoute();
}

function setLanguage(language) {
  if (!I18N[language]) return;
  state.language = language;
  localStorage.setItem(STORAGE.language, language);
  applyLanguage();
}

function renderCityTabs() {
  const topFour = state.cityOrder.slice(0, 4);
  el.cityTabs.innerHTML = topFour.map(id =>
    `<button type="button" class="city-tab ${id === state.currentCity ? 'active' : ''}" data-city="${escapeHtml(id)}">${escapeHtml(cityName(id))}</button>`
  ).join('');
}

async function selectCity(cityId, clearInputs = true) {
  state.currentCity = cityId;
  localStorage.setItem(STORAGE.currentCity, cityId);
  renderCityTabs();
  hideSuggestions();
  if (clearInputs) clearStationSelection();
  state.routeResults = { fast: null, few: null };
  const config = getCityConfig(cityId);
  const token = ++state.loadingToken;
  if (!config?.dataUrl) {
    state.currentData = null;
    state.currentGraph = null;
    setSearchEnabled(false);
    setStatus(t('unavailable'), 'error');
    renderUnavailableResult();
    return;
  }
  setSearchEnabled(false);
  setStatus(t('loading'));
  el.result.innerHTML = `<div class="empty-state">${escapeHtml(t('loading'))}</div>`;
  try {
    const data = await loadCityData(config);
    if (token !== state.loadingToken) return;
    state.currentData = data;
    state.currentGraph = getOrBuildGraph(cityId, data);
    setSearchEnabled(true);
    const messages = [t('dataReady')];
    if (cityId === 'shenzhen' && state.fareData) messages.push(t('fareReady'));
    if (data.updatedAt) messages.push(t('dataUpdated', { date: data.updatedAt }));
    setStatus(messages.join('｜'));
    showInitialResult();
  } catch (error) {
    console.error(error);
    if (token !== state.loadingToken) return;
    state.currentData = null;
    state.currentGraph = null;
    setSearchEnabled(false);
    setStatus(t('loadFailed'), 'error');
    el.result.innerHTML = `<div class="empty-state"><span>${escapeHtml(t('loadFailed'))}</span></div>`;
  }
}

async function loadCityData(config) {
  if (state.dataCache.has(config.id)) return state.dataCache.get(config.id);
  const response = await fetch(config.dataUrl, { cache: 'no-store' });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const data = await response.json();
  if (!data || !data.L) throw new Error('Invalid city data');
  state.dataCache.set(config.id, data);
  return data;
}

async function loadFareData() {
  try {
    const response = await fetch('shenzhen-fares-by-name.json');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.fareData = await response.json();
  } catch (error) {
    console.error('Fare data unavailable', error);
    state.fareData = null;
  }
}

function getOrBuildGraph(cityId, data) {
  if (state.graphCache.has(cityId)) return state.graphCache.get(cityId);
  const graph = buildGraph(data);
  state.graphCache.set(cityId, graph);
  return graph;
}

function buildGraph(data) {
  const adjacency = new Map();
  const stationLines = new Map();
  const stationMap = new Map();
  const lineStations = new Map();

  const ensureNode = id => { if (!adjacency.has(id)) adjacency.set(id, []); };
  const addEdge = (from, to, edge) => { ensureNode(from); ensureNode(to); adjacency.get(from).push({ to, ...edge }); };

  Object.entries(data.L).forEach(([lineId, line]) => {
    const stations = Array.isArray(line.stations) ? line.stations : [];
    lineStations.set(lineId, stations.map(item => item[0]));
    stations.forEach(([code, trad]) => {
      stationMap.set(code, stationMap.get(code) || { code, trad });
      if (!stationLines.has(code)) stationLines.set(code, []);
      if (!stationLines.get(code).includes(lineId)) stationLines.get(code).push(lineId);
      ensureNode(nodeId(lineId, code));
    });
    for (let index = 0; index < stations.length - 1; index += 1) {
      const a = stations[index][0];
      const b = stations[index + 1][0];
      const edge = { type: 'train', lineId, minutes: 2.0, transfers: 0 };
      addEdge(nodeId(lineId, a), nodeId(lineId, b), edge);
      addEdge(nodeId(lineId, b), nodeId(lineId, a), edge);
    }
  });

  stationLines.forEach((lines, code) => {
    for (let i = 0; i < lines.length; i += 1) {
      for (let j = i + 1; j < lines.length; j += 1) {
        const meters = Number(data.transferMeters?.[code]) || 180;
        const minutes = meters / 0.5 / 60 + 0.5;
        const edgeAB = { type: 'transfer', stationCode: code, fromLine: lines[i], toLine: lines[j], meters, minutes, transfers: 1 };
        const edgeBA = { ...edgeAB, fromLine: lines[j], toLine: lines[i] };
        addEdge(nodeId(lines[i], code), nodeId(lines[j], code), edgeAB);
        addEdge(nodeId(lines[j], code), nodeId(lines[i], code), edgeBA);
      }
    }
  });

  const searchStations = [...stationMap.values()].map(station => {
    const code = station.code;
    const aliases = [
      station.trad,
      data.simplified?.[code],
      data.english?.[code],
      data.roman?.[code]
    ].filter(Boolean);
    const initials = aliases.map(initialsOf).filter(Boolean);
    return { ...station, aliases, searchKey: normalizeSearch([...aliases, ...initials].join(' ')) };
  });
  return { adjacency, stationLines, stationMap, lineStations, searchStations };
}

function nodeId(lineId, stationCode) { return `${lineId}|${stationCode}`; }
function parseNode(id) { const split = id.indexOf('|'); return { lineId: id.slice(0, split), stationCode: id.slice(split + 1) }; }

function showSuggestions(which) {
  const input = which === 'from' ? el.fromInput : el.toInput;
  const box = which === 'from' ? el.fromSuggestions : el.toSuggestions;
  if (!state.currentGraph) { box.classList.remove('visible'); return; }
  const query = normalizeSearch(input.value);
  const matches = state.currentGraph.searchStations
    .filter(station => !query || station.searchKey.includes(query))
    .slice(0, 40);
  box.innerHTML = matches.map(station => {
    const primary = stationName(station.code);
    const secondary = station.aliases.filter(name => name !== primary).slice(0, 2).join(' · ');
    return `<button class="suggestion" type="button" data-code="${escapeHtml(station.code)}"><strong>${escapeHtml(primary)}</strong>${secondary ? `<small>${escapeHtml(secondary)}</small>` : ''}</button>`;
  }).join('');
  box.classList.toggle('visible', matches.length > 0);
}

function chooseSuggestion(event, which) {
  const button = event.target.closest('[data-code]');
  if (!button) return;
  const code = button.dataset.code;
  if (which === 'from') {
    state.fromCode = code;
    el.fromInput.value = stationName(code);
    el.fromSuggestions.classList.remove('visible');
  } else {
    state.toCode = code;
    el.toInput.value = stationName(code);
    el.toSuggestions.classList.remove('visible');
  }
}

function hideSuggestions() {
  el.fromSuggestions.classList.remove('visible');
  el.toSuggestions.classList.remove('visible');
}

function swapStations() {
  [state.fromCode, state.toCode] = [state.toCode, state.fromCode];
  const fromValue = el.fromInput.value;
  el.fromInput.value = el.toInput.value;
  el.toInput.value = fromValue;
}

function clearStationSelection() {
  state.fromCode = null;
  state.toCode = null;
  el.fromInput.value = '';
  el.toInput.value = '';
}

function refreshInputNames() {
  if (state.fromCode) el.fromInput.value = stationName(state.fromCode);
  if (state.toCode) el.toInput.value = stationName(state.toCode);
}

function setSearchEnabled(enabled) {
  el.fromInput.disabled = !enabled;
  el.toInput.disabled = !enabled;
  el.searchButton.disabled = !enabled;
  el.swapButton.disabled = !enabled;
}

function setStatus(message, kind = '') {
  el.dataStatus.textContent = message || '';
  el.dataStatus.className = `data-status ${kind}`.trim();
}

function runSearch() {
  if (!state.currentGraph || !state.currentData) { renderUnavailableResult(); return; }
  resolveTypedStation('from');
  resolveTypedStation('to');
  if (!state.fromCode || !state.toCode) { renderError(t('stationNotFound')); return; }
  if (state.fromCode === state.toCode) { renderError(t('sameStation')); return; }
  state.routeResults.fast = findRoute(state.fromCode, state.toCode, 'fast');
  state.routeResults.few = findRoute(state.fromCode, state.toCode, 'few');
  renderSelectedRoute();
  hideSuggestions();
}

function resolveTypedStation(which) {
  const current = which === 'from' ? state.fromCode : state.toCode;
  if (current) return;
  const input = which === 'from' ? el.fromInput : el.toInput;
  const query = normalizeSearch(input.value);
  if (!query || !state.currentGraph) return;
  const exact = state.currentGraph.searchStations.find(station => station.aliases.some(alias => normalizeSearch(alias) === query));
  if (exact) {
    if (which === 'from') state.fromCode = exact.code;
    else state.toCode = exact.code;
    input.value = stationName(exact.code);
  }
}

function findRoute(fromCode, toCode, mode) {
  const graph = state.currentGraph;
  const starts = graph.stationLines.get(fromCode) || [];
  const targets = new Set((graph.stationLines.get(toCode) || []).map(line => nodeId(line, toCode)));
  if (!starts.length || !targets.size) return null;

  const heap = new MinHeap();
  const best = new Map();
  const previous = new Map();
  starts.forEach(lineId => {
    const id = nodeId(lineId, fromCode);
    const record = { minutes: 0, transfers: 0, score: scoreFor(mode, 0, 0) };
    best.set(id, record);
    heap.push({ id, ...record }, record.score);
  });

  let endId = null;
  while (heap.size) {
    const current = heap.pop();
    const currentBest = best.get(current.id);
    if (!currentBest || current.score !== currentBest.score) continue;
    if (targets.has(current.id)) { endId = current.id; break; }
    for (const edge of graph.adjacency.get(current.id) || []) {
      const minutes = current.minutes + edge.minutes;
      const transfers = current.transfers + edge.transfers;
      const score = scoreFor(mode, minutes, transfers);
      const existing = best.get(edge.to);
      if (!existing || score < existing.score - 1e-7) {
        const record = { minutes, transfers, score };
        best.set(edge.to, record);
        previous.set(edge.to, { from: current.id, edge });
        heap.push({ id: edge.to, ...record }, score);
      }
    }
  }
  if (!endId) return null;
  const nodes = [endId];
  const edges = [];
  let cursor = endId;
  while (previous.has(cursor)) {
    const step = previous.get(cursor);
    edges.push(step.edge);
    cursor = step.from;
    nodes.push(cursor);
  }
  nodes.reverse();
  edges.reverse();
  return buildPlan(nodes, edges, best.get(endId));
}

function scoreFor(mode, minutes, transfers) {
  return mode === 'few' ? transfers * 100000 + minutes : minutes * 100 + transfers;
}

function buildPlan(nodes, edges, metrics) {
  const legs = [];
  const transfers = [];
  let currentLeg = null;
  let elapsed = 0;

  for (let i = 0; i < edges.length; i += 1) {
    const edge = edges[i];
    const from = parseNode(nodes[i]);
    const to = parseNode(nodes[i + 1]);
    if (edge.type === 'train') {
      if (!currentLeg || currentLeg.lineId !== edge.lineId) {
        currentLeg = { lineId: edge.lineId, stations: [from.stationCode], startElapsed: elapsed };
        legs.push(currentLeg);
      }
      if (currentLeg.stations[currentLeg.stations.length - 1] !== to.stationCode) currentLeg.stations.push(to.stationCode);
      elapsed += edge.minutes;
    } else {
      transfers.push({
        stationCode: edge.stationCode,
        fromLine: edge.fromLine,
        toLine: edge.toLine,
        meters: edge.meters,
        minutes: edge.minutes,
        elapsedBefore: elapsed
      });
      elapsed += edge.minutes;
      currentLeg = null;
    }
  }

  legs.forEach(leg => {
    const lineCodes = state.currentGraph.lineStations.get(leg.lineId) || [];
    const startIndex = lineCodes.indexOf(leg.stations[0]);
    const endIndex = lineCodes.indexOf(leg.stations[leg.stations.length - 1]);
    leg.terminalCode = endIndex >= startIndex ? lineCodes[lineCodes.length - 1] : lineCodes[0];
  });

  return {
    nodes, edges, legs, transfers,
    minutes: metrics.minutes,
    transferCount: metrics.transfers,
    fare: lookupFare(nodes[0], nodes[nodes.length - 1]),
    serviceWindow: calculateServiceWindow(legs)
  };
}

function lookupFare(firstNode, lastNode) {
  const fromCode = parseNode(firstNode).stationCode;
  const toCode = parseNode(lastNode).stationCode;
  const dataFares = state.currentData?.fares;
  if (dataFares) {
    const [a, b] = [fromCode, toCode].sort();
    const value = dataFares?.[a]?.[b] ?? dataFares?.[fromCode]?.[toCode] ?? dataFares?.[toCode]?.[fromCode];
    if (value !== undefined && value !== null) return { value, currency: state.currentData.fareMetadata?.currency || 'CNY' };
  }
  if (state.currentCity !== 'shenzhen' || !state.fareData) return null;
  const aName = simpleStationName(fromCode);
  const bName = simpleStationName(toCode);
  const ai = state.fareData.index?.[aName];
  const bi = state.fareData.index?.[bName];
  if (!Number.isInteger(ai) || !Number.isInteger(bi)) return null;
  const value = state.fareData.matrix?.[ai]?.[bi];
  if (value === undefined || value === null) return null;
  return { value, currency: state.fareData.currency || 'CNY' };
}

function calculateServiceWindow(legs) {
  let earliest = null;
  let latest = null;
  let constraints = 0;
  for (const leg of legs) {
    const hours = state.currentData?.serviceHours?.[leg.stations[0]]?.[leg.lineId]?.[leg.terminalCode];
    if (!hours) continue;
    const first = parseClock(hours.first, false);
    const last = parseClock(hours.last, true);
    if (first !== null) {
      const candidate = first - leg.startElapsed;
      earliest = earliest === null ? candidate : Math.max(earliest, candidate);
      constraints += 1;
    }
    if (last !== null) {
      const candidate = last - leg.startElapsed;
      latest = latest === null ? candidate : Math.min(latest, candidate);
    }
  }
  return { earliest, latest, constraints };
}

function parseClock(value, lastTrain) {
  if (!/^\d{1,2}:\d{2}$/.test(String(value || ''))) return null;
  const [hour, minute] = String(value).split(':').map(Number);
  let total = hour * 60 + minute;
  if (lastTrain && hour < 4) total += 1440;
  return total;
}

function setMode(mode) {
  state.mode = mode;
  el.fastMode.classList.toggle('active', mode === 'fast');
  el.fewMode.classList.toggle('active', mode === 'few');
  renderSelectedRoute();
}

function renderSelectedRoute() {
  if (!el.result) return;
  const plan = state.routeResults[state.mode];
  if (!plan) {
    if (!state.currentData) renderUnavailableResult();
    else showInitialResult();
    return;
  }
  renderPlan(plan);
}

function renderPlan(plan) {
  const transferText = plan.transferCount ? `${plan.transferCount} ${t('transfers')}` : t('noTransfer');
  const fareText = plan.fare ? formatFare(plan.fare) : '—';
  const firstText = plan.serviceWindow.earliest === null ? '—' : formatClock(plan.serviceWindow.earliest);
  const lastText = plan.serviceWindow.latest === null ? '—' : formatClock(plan.serviceWindow.latest);
  let transferIndex = 0;
  const routeHtml = plan.legs.map((leg, index) => {
    const line = state.currentData.L[leg.lineId] || {};
    const lineColor = sanitizeColor(line.color) || '#315efb';
    const stationHtml = leg.stations.map(code => `<span>${escapeHtml(stationName(code))}</span>`).join('');
    const directionName = stationName(leg.terminalCode);
    let html = `<article class="leg" style="--line-color:${lineColor}">
      <div class="leg-head"><span class="line-badge">${escapeHtml(lineName(leg.lineId))}</span><span class="leg-title">${escapeHtml(stationName(leg.stations[0]))} → ${escapeHtml(stationName(leg.stations[leg.stations.length - 1]))}</span><span class="leg-direction">${escapeHtml(t('direction'))} ${escapeHtml(directionName)}</span></div>
      <div class="station-sequence">${stationHtml}</div>
    </article>`;
    if (index < plan.legs.length - 1) {
      const transfer = plan.transfers[transferIndex++];
      if (transfer) {
        html += `<article class="transfer-card">
          <div><span class="label">${escapeHtml(t('transferAt'))}</span><strong>${escapeHtml(stationName(transfer.stationCode))}</strong></div>
          <div><span class="label">${escapeHtml(t('distance'))}</span><strong>${Math.round(transfer.meters)} ${escapeHtml(t('meter'))}</strong></div>
          <div><span class="label">${escapeHtml(t('walking'))}</span><strong>${Math.ceil(transfer.minutes)} ${escapeHtml(t('minutes'))}</strong></div>
        </article>`;
      }
    }
    return html;
  }).join('');

  el.result.innerHTML = `
    <div class="result-head">
      <h2>${escapeHtml(stationName(state.fromCode))} → ${escapeHtml(stationName(state.toCode))}</h2>
      <div class="result-meta">${Math.ceil(plan.minutes)} ${escapeHtml(t('minutes'))}<br>${escapeHtml(transferText)}</div>
    </div>
    <div class="metric-grid">
      <div class="metric"><span class="metric-label">${escapeHtml(t('fare'))}</span><strong>${escapeHtml(fareText)}</strong></div>
      <div class="metric"><span class="metric-label">${escapeHtml(t('firstTrain'))}</span><strong>${escapeHtml(firstText)}</strong></div>
      <div class="metric"><span class="metric-label">${escapeHtml(t('lastTrain'))}</span><strong>${escapeHtml(lastText)}</strong></div>
    </div>
    <div class="environment">
      <div class="metric"><span class="metric-label">${escapeHtml(t('temperature'))}</span><strong>—</strong></div>
      <div class="metric"><span class="metric-label">${escapeHtml(t('humidity'))}</span><strong>—</strong></div>
      <div class="metric"><span class="metric-label">${escapeHtml(t('uv'))}</span><strong>—</strong></div>
      <div class="metric"><span class="metric-label">${escapeHtml(t('pm25'))}</span><strong>—</strong></div>
    </div>
    <div class="route-stack">${routeHtml}</div>
    <div class="notice" style="margin-top:10px">${escapeHtml(t('routeEstimate'))}<br>${escapeHtml(t('environmentalBlank'))}</div>
    <div class="result-actions"><button class="secondary-button" type="button" data-action="favorite">${escapeHtml(isCurrentFavorite() ? t('favorited') : t('addFavorite'))}</button></div>`;
}

function showInitialResult() {
  if (!el.result) return;
  el.result.innerHTML = `<div class="empty-state"><span>${escapeHtml(t('initialHint'))}</span></div>`;
}

function renderUnavailableResult() {
  el.result.innerHTML = `<div class="empty-state"><span>${escapeHtml(t('unavailable'))}</span></div>`;
}

function renderError(message) {
  el.result.innerHTML = `<div class="empty-state"><span class="error">${escapeHtml(message)}</span></div>`;
}

function showScreen(screen) {
  state.screen = screen;
  document.querySelectorAll('.screen').forEach(node => node.classList.toggle('active', node.id === `screen-${screen}`));
  document.querySelectorAll('.nav-item').forEach(node => node.classList.toggle('active', node.dataset.screen === screen));
  if (screen === 'settings') renderSettings();
  if (screen === 'favorites') renderFavorites();
  window.scrollTo({ top: 0, behavior: 'auto' });
}

function renderSettings() {
  if (!el.languageOptions || !el.citySortList) return;
  el.languageOptions.innerHTML = Object.keys(I18N).map(language => `
    <label class="option-row"><input type="radio" name="language" value="${language}" ${language === state.language ? 'checked' : ''}><span>${escapeHtml(I18N[state.language].languageNames[language])}</span></label>`).join('');
  renderCitySortList();
}

function renderCitySortList() {
  if (!el.citySortList) return;
  el.citySortList.innerHTML = state.cityOrder.map((id, index) => {
    const rank = index < 4 ? t('topCity', { n: String(index + 1) }) : t('hiddenCity');
    return `<div class="city-sort-item ${state.sorting.active && state.sorting.id === id ? 'dragging' : ''}" data-sort-city="${escapeHtml(id)}">
      <div class="drag-handle" aria-hidden="true">≡</div>
      <div><span class="city-sort-name">${escapeHtml(cityName(id))}</span><span class="city-sort-rank">${escapeHtml(rank)}</span></div>
      <button class="sort-button" type="button" data-sort-action="up" aria-label="up">↑</button>
      <button class="sort-button" type="button" data-sort-action="down" aria-label="down">↓</button>
    </div>`;
  }).join('');
}

function onCitySortClick(event) {
  const button = event.target.closest('[data-sort-action]');
  const item = event.target.closest('[data-sort-city]');
  if (!button || !item) return;
  const id = item.dataset.sortCity;
  const index = state.cityOrder.indexOf(id);
  const next = button.dataset.sortAction === 'up' ? index - 1 : index + 1;
  if (next < 0 || next >= state.cityOrder.length) return;
  moveCity(index, next);
  finishCityOrderChange();
}

function onSortPointerDown(event) {
  if (event.target.closest('button')) return;
  const item = event.target.closest('[data-sort-city]');
  if (!item) return;
  clearTimeout(state.sorting.timer);
  state.sorting.id = item.dataset.sortCity;
  state.sorting.startX = event.clientX;
  state.sorting.startY = event.clientY;
  state.sorting.active = false;
  state.sorting.timer = setTimeout(() => {
    state.sorting.active = true;
    document.body.classList.add('sorting');
    if (navigator.vibrate) navigator.vibrate(20);
    renderCitySortList();
  }, 430);
}

function onSortPointerMove(event) {
  if (!state.sorting.id) return;
  const distance = Math.hypot(event.clientX - state.sorting.startX, event.clientY - state.sorting.startY);
  if (!state.sorting.active) {
    if (distance > 9) cancelSortGesture();
    return;
  }
  event.preventDefault();
  const target = document.elementFromPoint(event.clientX, event.clientY)?.closest?.('[data-sort-city]');
  if (!target) return;
  const fromIndex = state.cityOrder.indexOf(state.sorting.id);
  const toIndex = state.cityOrder.indexOf(target.dataset.sortCity);
  if (fromIndex >= 0 && toIndex >= 0 && fromIndex !== toIndex) {
    moveCity(fromIndex, toIndex);
    renderCitySortList();
  }
}

function finishSortGesture() {
  clearTimeout(state.sorting.timer);
  if (state.sorting.active) finishCityOrderChange();
  state.sorting.timer = null;
  state.sorting.id = null;
  state.sorting.active = false;
  document.body.classList.remove('sorting');
  renderCitySortList();
}

function cancelSortGesture() {
  clearTimeout(state.sorting.timer);
  state.sorting.timer = null;
  state.sorting.id = null;
  state.sorting.active = false;
  document.body.classList.remove('sorting');
}

function moveCity(fromIndex, toIndex) {
  const [item] = state.cityOrder.splice(fromIndex, 1);
  state.cityOrder.splice(toIndex, 0, item);
}

function finishCityOrderChange() {
  localStorage.setItem(STORAGE.cityOrder, JSON.stringify(state.cityOrder));
  if (!state.cityOrder.slice(0, 4).includes(state.currentCity)) {
    selectCity(state.cityOrder[0], true);
  } else {
    renderCityTabs();
  }
  renderCitySortList();
}

function addCurrentFavorite() {
  if (!state.fromCode || !state.toCode || !state.currentData) return;
  const key = favoriteKey(state.currentCity, state.fromCode, state.toCode, state.mode);
  if (state.favorites.some(item => item.key === key)) return;
  state.favorites.unshift({
    key, cityId: state.currentCity, fromCode: state.fromCode, toCode: state.toCode, mode: state.mode,
    fromLabel: stationName(state.fromCode), toLabel: stationName(state.toCode), createdAt: new Date().toISOString()
  });
  localStorage.setItem(STORAGE.favorites, JSON.stringify(state.favorites));
  renderFavorites();
  renderSelectedRoute();
}

function isCurrentFavorite() {
  if (!state.fromCode || !state.toCode) return false;
  const key = favoriteKey(state.currentCity, state.fromCode, state.toCode, state.mode);
  return state.favorites.some(item => item.key === key);
}

function favoriteKey(cityId, fromCode, toCode, mode) { return [cityId, fromCode, toCode, mode].join('|'); }

function renderFavorites() {
  if (!el.favoritesList) return;
  if (!state.favorites.length) {
    el.favoritesList.innerHTML = `<div class="card empty-state">${escapeHtml(t('favoriteEmpty'))}</div>`;
    return;
  }
  el.favoritesList.innerHTML = state.favorites.map(item => `
    <article class="card favorite-card">
      <h3>${escapeHtml(item.fromLabel)} → ${escapeHtml(item.toLabel)}</h3>
      <p>${escapeHtml(cityName(item.cityId))} · ${escapeHtml(item.mode === 'few' ? t('fewest') : t('fastest'))}</p>
      <div class="favorite-actions">
        <button class="secondary-button" type="button" data-favorite-action="open" data-key="${escapeHtml(item.key)}">${escapeHtml(t('open'))}</button>
        <button class="secondary-button" type="button" data-favorite-action="remove" data-key="${escapeHtml(item.key)}">${escapeHtml(t('remove'))}</button>
      </div>
    </article>`).join('');
}

async function onFavoriteAction(event) {
  const button = event.target.closest('[data-favorite-action]');
  if (!button) return;
  const index = state.favorites.findIndex(item => item.key === button.dataset.key);
  if (index < 0) return;
  if (button.dataset.favoriteAction === 'remove') {
    state.favorites.splice(index, 1);
    localStorage.setItem(STORAGE.favorites, JSON.stringify(state.favorites));
    renderFavorites();
    return;
  }
  const item = state.favorites[index];
  showScreen('search');
  if (state.currentCity !== item.cityId || !state.currentData) await selectCity(item.cityId, true);
  if (!state.currentData) return;
  state.fromCode = item.fromCode;
  state.toCode = item.toCode;
  state.mode = item.mode;
  refreshInputNames();
  el.fastMode.classList.toggle('active', state.mode === 'fast');
  el.fewMode.classList.toggle('active', state.mode === 'few');
  runSearch();
}

function renderAbout() {
  if (!el.dataCoverage) return;
  el.dataCoverage.innerHTML = CITY_CONFIGS.map(config => `<div class="coverage-row"><span>${escapeHtml(cityName(config.id))}</span><span>${escapeHtml(config.enabled ? t('ready') : t('pending'))}</span></div>`).join('');
}

function stationName(code) {
  const data = state.currentData;
  const trad = state.currentGraph?.stationMap.get(code)?.trad || code;
  if (state.language === 'zh-Hans') return data?.simplified?.[code] || trad;
  if (state.language === 'en') return data?.english?.[code] || data?.roman?.[code] || trad;
  return trad;
}

function simpleStationName(code) {
  return String(state.currentData?.simplified?.[code] || state.currentGraph?.stationMap.get(code)?.trad || '').trim();
}

function lineName(lineId) {
  const line = state.currentData?.L?.[lineId] || {};
  if (state.language === 'zh-Hans') return line.simp || line.name || lineId;
  if (state.language === 'en') return line.en || line.name || lineId;
  return line.name || lineId;
}

function formatFare(fare) {
  const symbol = fare.currency === 'HKD' ? 'HK$' : fare.currency === 'TWD' ? 'NT$' : fare.currency === 'CNY' ? '¥' : `${fare.currency} `;
  return `${symbol}${fare.value}`;
}

function formatClock(minutes) {
  const normalized = ((Math.round(minutes) % 1440) + 1440) % 1440;
  const hour = Math.floor(normalized / 60);
  const minute = normalized % 60;
  return `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
}

function getCityConfig(id) { return CITY_CONFIGS.find(config => config.id === id); }

function normalizeCityOrder(value) {
  const all = CITY_CONFIGS.map(config => config.id);
  const valid = Array.isArray(value) ? value.filter((id, index) => all.includes(id) && value.indexOf(id) === index) : [];
  all.forEach(id => { if (!valid.includes(id)) valid.push(id); });
  return valid;
}

function safeGet(key, fallback) {
  try { return localStorage.getItem(key) || fallback; } catch { return fallback; }
}

function readJson(key, fallback) {
  try {
    const value = JSON.parse(localStorage.getItem(key));
    return value ?? fallback;
  } catch { return fallback; }
}

function normalizeSearch(value) {
  return String(value || '').normalize('NFKC').toLowerCase().replace(/[\s·・\-_/()（）.]/g, '');
}

function initialsOf(value) {
  return String(value || '').split(/[\s\-_/]+/).map(part => part[0] || '').join('').toLowerCase();
}

function sanitizeColor(value) { return /^#[0-9a-f]{3,8}$/i.test(String(value || '')) ? value : null; }

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, character => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#39;', '"':'&quot;' }[character]));
}

class MinHeap {
  constructor() { this.items = []; }
  get size() { return this.items.length; }
  push(value, priority) {
    const node = { value, priority };
    this.items.push(node);
    let index = this.items.length - 1;
    while (index > 0) {
      const parent = Math.floor((index - 1) / 2);
      if (this.items[parent].priority <= priority) break;
      this.items[index] = this.items[parent];
      index = parent;
    }
    this.items[index] = node;
  }
  pop() {
    if (!this.items.length) return null;
    const root = this.items[0].value;
    const last = this.items.pop();
    if (this.items.length && last) {
      let index = 0;
      while (true) {
        let child = index * 2 + 1;
        if (child >= this.items.length) break;
        if (child + 1 < this.items.length && this.items[child + 1].priority < this.items[child].priority) child += 1;
        if (this.items[child].priority >= last.priority) break;
        this.items[index] = this.items[child];
        index = child;
      }
      this.items[index] = last;
    }
    return root;
  }
}
