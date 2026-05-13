const DEFAULT_BASE_URL = "http://127.0.0.1:8767";
const MENU_IMPORT_SELECTION = "jpcorpus-import-selection";
const MENU_IMPORT_ARTICLE = "jpcorpus-import-article";

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
    }).catch(reportImportError);
    return;
  }
  if (info.menuItemId === MENU_IMPORT_ARTICLE) {
    importMainArticle(tab).catch(reportImportError);
  }
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "IMPORT_TEXT") {
    return false;
  }
  importSelectedText(message.payload || {})
    .then((result) => sendResponse({ ok: true, result }))
    .catch(async (error) => {
      await reportImportError(error);
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
  const baseUrl = await localBaseUrl();
  const importResponse = await fetch(`${baseUrl}/api/import-text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: payload.title || "",
      url: payload.url || "",
      text,
    }),
  });
  const importPayload = await importResponse.json();
  if (!importResponse.ok) {
    throw new Error(importPayload.error || `Import failed with HTTP ${importResponse.status}`);
  }
  const refreshResponse = await fetch(`${baseUrl}/api/jobs/maintenance`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ type: "export_corpus" }),
  });
  const refreshPayload = await refreshResponse.json();
  if (!refreshResponse.ok) {
    throw new Error(refreshPayload.error || `Refresh failed with HTTP ${refreshResponse.status}`);
  }
  const title = importPayload.imported?.title || "web text";
  await setStatus(`Imported ${title}. Corpus refresh started.`);
  await chrome.action.setBadgeText({ text: "OK" });
  await chrome.action.setBadgeBackgroundColor({ color: "#147d73" });
  return { imported: importPayload.imported, job: refreshPayload.job };
}

async function importMainArticle(tab) {
  if (!tab?.id) {
    throw new Error("No active tab to extract article text from.");
  }
  await setStatus("Extracting main article...");
  await ensureContentScript(tab.id);
  const response = await chrome.tabs.sendMessage(tab.id, { type: "EXTRACT_MAIN_ARTICLE" });
  if (!response?.ok) {
    throw new Error(response?.error || "Could not extract main article.");
  }
  return importSelectedText(response.payload || {});
}

async function ensureContentScript(tabId) {
  await chrome.scripting.executeScript({
    target: { tabId },
    files: ["content.js"],
  });
}

async function localBaseUrl() {
  const settings = await chrome.storage.local.get({ baseUrl: DEFAULT_BASE_URL });
  return String(settings.baseUrl || DEFAULT_BASE_URL).replace(/\/+$/, "");
}

async function setStatus(message) {
  await chrome.storage.local.set({
    lastStatus: message,
    lastStatusAt: new Date().toISOString(),
  });
}

async function reportImportError(error) {
  await setStatus(error.message || String(error));
  await chrome.action.setBadgeText({ text: "ERR" });
  await chrome.action.setBadgeBackgroundColor({ color: "#b75a35" });
}
