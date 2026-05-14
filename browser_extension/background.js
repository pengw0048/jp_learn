const DEFAULT_BASE_URL = "http://127.0.0.1:8767";
const MENU_IMPORT_SELECTION = "jpcorpus-import-selection";
const MENU_IMPORT_ARTICLE = "jpcorpus-import-article";
const MENU_TOGGLE_READER = "jpcorpus-toggle-reader";
const NOTIFICATION_ICON = "icon.svg";
const MESSAGES = {
  zh: {
    menuImportSelection: "导入选中文字到 jpcorpus",
    menuImportArticle: "导入正文到 jpcorpus",
    menuToggleReader: "切换 jpcorpus 网页阅读模式",
    noSelection: "没有选中文字可导入。",
    importingToJpcorpus: "正在导入 jpcorpus...",
    alreadyImported: "已经导入过 {title}，无需刷新。",
    corpusRefreshRunning: "语料刷新已经在运行。",
    corpusRefreshStarted: "语料刷新已开始。",
    imported: "已导入 {title}。{refresh}",
    importFailedTitle: "jpcorpus 导入失败",
    readerFailedTitle: "jpcorpus 网页阅读模式失败",
    readingMode: "网页阅读模式",
    studyUpdate: "学习状态更新",
    importAction: "导入",
    corpusRefreshAction: "语料刷新",
    noActiveAnnotateTab: "没有可标注的当前标签页。",
    cannotToggleReader: "无法切换网页阅读模式。",
    readerBusy: "网页阅读模式仍在标注中。",
    readerOn: "网页阅读模式已开启，标注了 {count} 个词。",
    readerOnEmpty: "网页阅读模式已开启，但没有应用标注。",
    readerOff: "网页阅读模式已关闭。",
    extractingArticle: "正在提取正文...",
    noActiveExtractTab: "没有可提取正文的当前标签页。",
    cannotExtractArticle: "无法提取正文。",
    requestNoReach: "{action} 无法连接本地阅读器。请启动或重启 uv run jpcorpus，然后 reload 扩展。",
    oldViewerHint: "本地阅读器可能还是旧进程，没有网页导入 API。",
    nonJsonHint: "本地阅读器返回了 HTML 或其他非 JSON 内容。",
    requestFailed: "{action} 失败：{hint} 请重启 uv run jpcorpus，并 reload 扩展。",
    httpFailed: "{action} 失败：HTTP {status}",
    webTextTitle: "网页文本",
  },
  en: {
    menuImportSelection: "Add selection to jpcorpus",
    menuImportArticle: "Add main article to jpcorpus",
    menuToggleReader: "Toggle jpcorpus reading mode",
    noSelection: "No selected text to import.",
    importingToJpcorpus: "Importing to jpcorpus...",
    alreadyImported: "Already imported {title}. No refresh needed.",
    corpusRefreshRunning: "Corpus refresh is already running.",
    corpusRefreshStarted: "Corpus refresh started.",
    imported: "Imported {title}. {refresh}",
    importFailedTitle: "jpcorpus import failed",
    readerFailedTitle: "jpcorpus reading mode failed",
    readingMode: "Reading mode",
    studyUpdate: "Study update",
    importAction: "Import",
    corpusRefreshAction: "Corpus refresh",
    noActiveAnnotateTab: "No active tab to annotate.",
    cannotToggleReader: "Could not toggle reading mode.",
    readerBusy: "Reading mode is still annotating.",
    readerOn: "Reading mode on. Annotated {count} words.",
    readerOnEmpty: "Reading mode on, but no annotations were applied.",
    readerOff: "Reading mode off.",
    extractingArticle: "Extracting article text...",
    noActiveExtractTab: "No active tab to extract article text from.",
    cannotExtractArticle: "Could not extract main article.",
    requestNoReach: "{action} could not reach the local viewer. Start or restart uv run jpcorpus, then reload this extension.",
    oldViewerHint: "The local viewer is probably an old running process without the web import API.",
    nonJsonHint: "The local viewer returned HTML or another non-JSON response.",
    requestFailed: "{action} failed: {hint} Restart uv run jpcorpus and reload the extension.",
    httpFailed: "{action} failed with HTTP {status}",
    webTextTitle: "web text",
  },
};

chrome.runtime.onInstalled.addListener(() => {
  refreshContextMenus();
});

chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName === "local" && changes.lang) {
    refreshContextMenus();
  }
});

async function refreshContextMenus() {
  const lang = await currentLang();
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: MENU_IMPORT_SELECTION,
      title: t(lang, "menuImportSelection"),
      contexts: ["selection"],
    });
    chrome.contextMenus.create({
      id: MENU_IMPORT_ARTICLE,
      title: t(lang, "menuImportArticle"),
      contexts: ["page"],
    });
    chrome.contextMenus.create({
      id: MENU_TOGGLE_READER,
      title: t(lang, "menuToggleReader"),
      contexts: ["page"],
    });
  });
}

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === MENU_IMPORT_SELECTION) {
    importSelectedText({
      text: info.selectionText || "",
      title: tab?.title || "",
      url: info.pageUrl || tab?.url || "",
      tabId: tab?.id,
    }).catch((error) => reportImportError(error, tab?.id));
    return;
  }
  if (info.menuItemId === MENU_IMPORT_ARTICLE) {
    importMainArticle(tab).catch((error) => reportImportError(error, tab?.id));
    return;
  }
  if (info.menuItemId === MENU_TOGGLE_READER) {
    toggleReadingMode(tab).catch(async (error) => reportImportError(error, tab?.id, t(await currentLang(), "readerFailedTitle")));
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "GET_EXTENSION_LANG") {
    currentLang()
      .then((lang) => sendResponse({ ok: true, lang }))
      .catch((error) => sendResponse({ ok: false, error: error.message || String(error) }));
    return true;
  }
  if (message?.type === "IMPORT_TEXT") {
    const tabId = sender.tab?.id || message.payload?.tabId;
    importSelectedText({ ...(message.payload || {}), tabId })
      .then((result) => sendResponse({ ok: true, result }))
      .catch(async (error) => {
        await reportImportError(error, tabId);
        sendResponse({ ok: false, error: error.message || String(error) });
      });
    return true;
  }
  if (message?.type === "ANNOTATE_TEXT_BLOCKS") {
    annotateTextBlocks(message.payload || {})
      .then((result) => sendResponse({ ok: true, result }))
      .catch((error) => sendResponse({ ok: false, error: error.message || String(error) }));
    return true;
  }
  if (message?.type === "SET_WORD_STATUS") {
    setWordStatus(message.payload || {})
      .then((result) => sendResponse({ ok: true, result }))
      .catch((error) => sendResponse({ ok: false, error: error.message || String(error) }));
    return true;
  }
  return false;
});

async function annotateTextBlocks(payload) {
  const baseUrl = await localBaseUrl();
  const lang = await currentLang();
  return requestJson(`${baseUrl}/api/annotate-text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  }, t(lang, "readingMode"), lang);
}

async function setWordStatus(payload) {
  const baseUrl = await localBaseUrl();
  const lang = await currentLang();
  return requestJson(`${baseUrl}/api/word-status`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  }, t(lang, "studyUpdate"), lang);
}

async function toggleReadingMode(tab) {
  const lang = await currentLang();
  if (!tab?.id) {
    throw new Error(t(lang, "noActiveAnnotateTab"));
  }
  await ensureContentScript(tab.id);
  const response = await chrome.tabs.sendMessage(tab.id, { type: "TOGGLE_READING_MODE" });
  if (!response?.ok) {
    throw new Error(response?.error || t(lang, "cannotToggleReader"));
  }
  const message = response.busy
    ? t(lang, "readerBusy")
    : response.enabled && response.tokenCount > 0
    ? t(lang, "readerOn", { count: response.tokenCount || 0 })
    : response.enabled
    ? t(lang, "readerOnEmpty")
    : t(lang, "readerOff");
  await clearStoredStatus();
  await showPageToast(tab.id, message);
  return response;
}

async function importSelectedText(payload) {
  const lang = await currentLang();
  const text = String(payload.text || "").trim();
  if (!text) {
    throw new Error(t(lang, "noSelection"));
  }
  await clearStoredStatus();
  await clearActionBadge();
  await showPageToast(payload.tabId, t(lang, "importingToJpcorpus"));
  const baseUrl = await localBaseUrl();
  const importPayload = await requestJson(`${baseUrl}/api/import-text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: payload.title || "",
      url: payload.url || "",
      text,
    }),
  }, t(lang, "importAction"), lang);
  const title = importPayload.imported?.title || t(lang, "webTextTitle");
  if (importPayload.imported?.duplicate) {
    const message = t(lang, "alreadyImported", { title });
    await clearStoredStatus();
    await clearActionBadge();
    await showPageToast(payload.tabId, message);
    return { imported: importPayload.imported, job: null, duplicate: true };
  }
  const refreshPayload = await startCorpusRefresh(baseUrl);
  const refreshMessage = refreshPayload.alreadyRunning
    ? t(lang, "corpusRefreshRunning")
    : t(lang, "corpusRefreshStarted");
  const message = t(lang, "imported", { title, refresh: refreshMessage });
  await clearStoredStatus();
  await clearActionBadge();
  await showPageToast(payload.tabId, message);
  return { imported: importPayload.imported, job: refreshPayload.job || null };
}

async function startCorpusRefresh(baseUrl) {
  const lang = await currentLang();
  try {
    return await requestJson(`${baseUrl}/api/jobs/maintenance`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type: "export_corpus" }),
    }, t(lang, "corpusRefreshAction"), lang);
  } catch (error) {
    if (String(error.message || error).includes("Another maintenance job is already running")) {
      return { alreadyRunning: true };
    }
    throw error;
  }
}

async function importMainArticle(tab) {
  const lang = await currentLang();
  if (!tab?.id) {
    throw new Error(t(lang, "noActiveExtractTab"));
  }
  await clearStoredStatus();
  await showPageToast(tab.id, t(lang, "extractingArticle"));
  await ensureContentScript(tab.id);
  const response = await chrome.tabs.sendMessage(tab.id, { type: "EXTRACT_MAIN_ARTICLE" });
  if (!response?.ok) {
    throw new Error(response?.error || t(lang, "cannotExtractArticle"));
  }
  return importSelectedText({ ...(response.payload || {}), tabId: tab.id });
}

async function ensureContentScript(tabId) {
  await chrome.scripting.executeScript({
    target: { tabId },
    files: ["vendor/Readability.js", "content.js"],
  });
}

async function showPageToast(tabId, message, tone = "info") {
  if (!tabId) {
    return;
  }
  try {
    await ensureContentScript(tabId);
    await chrome.tabs.sendMessage(tabId, {
      type: "SHOW_TOAST",
      message,
      tone,
    });
  } catch {
    // Some pages cannot receive injected content scripts; popup status and notifications still show status.
  }
}

async function localBaseUrl() {
  const settings = await chrome.storage.local.get({ baseUrl: DEFAULT_BASE_URL });
  return String(settings.baseUrl || DEFAULT_BASE_URL).replace(/\/+$/, "");
}

async function requestJson(url, options, action, lang = "en") {
  let response;
  try {
    response = await fetch(url, options);
  } catch (error) {
    throw new Error(t(lang, "requestNoReach", { action }));
  }
  const contentType = response.headers.get("content-type") || "";
  const text = await response.text();
  let payload = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      const hint = response.status === 404
        ? t(lang, "oldViewerHint")
        : t(lang, "nonJsonHint");
      throw new Error(t(lang, "requestFailed", { action, hint }));
    }
  }
  if (!response.ok) {
    throw new Error(payload?.error || t(lang, "httpFailed", { action, status: response.status }));
  }
  return payload || {};
}

async function setStatus(message) {
  await chrome.storage.local.set({
    lastStatus: message,
    lastStatusAt: new Date().toISOString(),
  });
}

async function clearStoredStatus() {
  await chrome.storage.local.remove(["lastStatus", "lastStatusAt"]);
}

async function clearActionBadge() {
  await chrome.action.setBadgeText({ text: "" });
}

async function reportImportError(error, tabId = null, title = null) {
  const lang = await currentLang();
  const message = error.message || String(error);
  await setStatus(message);
  await chrome.action.setBadgeText({ text: "!" });
  await chrome.action.setBadgeBackgroundColor({ color: "#b75a35" });
  await showPageToast(tabId, message, "error");
  await notify(title || t(lang, "importFailedTitle"), message);
}

async function notify(title, message) {
  if (!chrome.notifications) {
    return;
  }
  try {
    await chrome.notifications.create({
      type: "basic",
      iconUrl: chrome.runtime.getURL(NOTIFICATION_ICON),
      title,
      message: truncateMessage(message),
    });
  } catch {
    // Notifications are only a convenience; the popup status still shows the result.
  }
}

function truncateMessage(message) {
  const text = String(message || "");
  return text.length > 220 ? `${text.slice(0, 217)}...` : text;
}

async function currentLang() {
  const settings = await chrome.storage.local.get({ lang: "zh" });
  return normalizeLang(settings.lang);
}

function normalizeLang(value) {
  return value === "en" ? "en" : "zh";
}

function t(lang, key, values = {}) {
  const template = MESSAGES[normalizeLang(lang)]?.[key] || MESSAGES.en[key] || key;
  return template.replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? ""));
}
