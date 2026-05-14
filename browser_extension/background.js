const DEFAULT_BASE_URL = "http://127.0.0.1:8767";
const MENU_IMPORT_SELECTION = "jpcorpus-import-selection";
const MENU_IMPORT_ARTICLE = "jpcorpus-import-article";
const NOTIFICATION_ICON = "icon.svg";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: MENU_IMPORT_SELECTION,
      title: "Add selection to jpcorpus",
      contexts: ["selection"],
    });
    chrome.contextMenus.create({
      id: MENU_IMPORT_ARTICLE,
      title: "Add main article to jpcorpus",
      contexts: ["page"],
    });
  });
});

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
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type !== "IMPORT_TEXT") {
    return false;
  }
  const tabId = sender.tab?.id || message.payload?.tabId;
  importSelectedText({ ...(message.payload || {}), tabId })
    .then((result) => sendResponse({ ok: true, result }))
    .catch(async (error) => {
      await reportImportError(error, tabId);
      sendResponse({ ok: false, error: error.message || String(error) });
    });
  return true;
});

async function importSelectedText(payload) {
  const text = String(payload.text || "").trim();
  if (!text) {
    throw new Error("No selected text to import.");
  }
  await setStatus("Importing selected text...");
  await showPageToast(payload.tabId, "Importing to jpcorpus...");
  const baseUrl = await localBaseUrl();
  const importPayload = await requestJson(`${baseUrl}/api/import-text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: payload.title || "",
      url: payload.url || "",
      text,
    }),
  }, "Import");
  const title = importPayload.imported?.title || "web text";
  if (importPayload.imported?.duplicate) {
    const message = `Already imported ${title}. No refresh needed.`;
    await setStatus(message);
    await chrome.action.setBadgeText({ text: "OK" });
    await chrome.action.setBadgeBackgroundColor({ color: "#147d73" });
    await showPageToast(payload.tabId, message);
    await notify("jpcorpus already has this text", message);
    return { imported: importPayload.imported, job: null, duplicate: true };
  }
  const refreshPayload = await startCorpusRefresh(baseUrl);
  const refreshMessage = refreshPayload.alreadyRunning
    ? "Corpus refresh is already running."
    : "Corpus refresh started.";
  const message = `Imported ${title}. ${refreshMessage}`;
  await setStatus(message);
  await chrome.action.setBadgeText({ text: "OK" });
  await chrome.action.setBadgeBackgroundColor({ color: "#147d73" });
  await showPageToast(payload.tabId, message);
  await notify("jpcorpus import started", message);
  return { imported: importPayload.imported, job: refreshPayload.job || null };
}

async function startCorpusRefresh(baseUrl) {
  try {
    return await requestJson(`${baseUrl}/api/jobs/maintenance`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type: "export_corpus" }),
    }, "Corpus refresh");
  } catch (error) {
    if (String(error.message || error).includes("Another maintenance job is already running")) {
      return { alreadyRunning: true };
    }
    throw error;
  }
}

async function importMainArticle(tab) {
  if (!tab?.id) {
    throw new Error("No active tab to extract article text from.");
  }
  await setStatus("Extracting main article...");
  await showPageToast(tab.id, "Extracting article text...");
  await ensureContentScript(tab.id);
  const response = await chrome.tabs.sendMessage(tab.id, { type: "EXTRACT_MAIN_ARTICLE" });
  if (!response?.ok) {
    throw new Error(response?.error || "Could not extract main article.");
  }
  return importSelectedText({ ...(response.payload || {}), tabId: tab.id });
}

async function ensureContentScript(tabId) {
  await chrome.scripting.executeScript({
    target: { tabId },
    files: ["content.js"],
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
    // Some pages cannot receive injected content scripts; the badge and notification still show status.
  }
}

async function localBaseUrl() {
  const settings = await chrome.storage.local.get({ baseUrl: DEFAULT_BASE_URL });
  return String(settings.baseUrl || DEFAULT_BASE_URL).replace(/\/+$/, "");
}

async function requestJson(url, options, action) {
  let response;
  try {
    response = await fetch(url, options);
  } catch (error) {
    throw new Error(`${action} could not reach the local viewer. Start or restart uv run jpcorpus, then reload this extension.`);
  }
  const contentType = response.headers.get("content-type") || "";
  const text = await response.text();
  let payload = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      const hint = response.status === 404
        ? "The local viewer is probably an old running process without the web import API."
        : "The local viewer returned HTML or another non-JSON response.";
      throw new Error(`${action} failed: ${hint} Restart uv run jpcorpus and reload the extension.`);
    }
  }
  if (!response.ok) {
    throw new Error(payload?.error || `${action} failed with HTTP ${response.status}`);
  }
  return payload || {};
}

async function setStatus(message) {
  await chrome.storage.local.set({
    lastStatus: message,
    lastStatusAt: new Date().toISOString(),
  });
}

async function reportImportError(error, tabId = null) {
  const message = error.message || String(error);
  await setStatus(message);
  await chrome.action.setBadgeText({ text: "ERR" });
  await chrome.action.setBadgeBackgroundColor({ color: "#b75a35" });
  await showPageToast(tabId, message, "error");
  await notify("jpcorpus import failed", message);
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
    // Notifications are only a convenience; the popup status and badge still show the result.
  }
}

function truncateMessage(message) {
  const text = String(message || "");
  return text.length > 220 ? `${text.slice(0, 217)}...` : text;
}
