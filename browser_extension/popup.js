const DEFAULT_BASE_URL = "http://127.0.0.1:8767";

const refs = {
  baseUrl: document.querySelector("#base-url"),
  saveUrl: document.querySelector("#save-url"),
  importSelection: document.querySelector("#import-selection"),
  pickArea: document.querySelector("#pick-area"),
  status: document.querySelector("#status"),
};

init();

async function init() {
  const settings = await chrome.storage.local.get({
    baseUrl: DEFAULT_BASE_URL,
    lastStatus: "",
    lastStatusAt: "",
  });
  refs.baseUrl.value = settings.baseUrl;
  refs.status.textContent = settings.lastStatus || "";
  refs.saveUrl.addEventListener("click", saveBaseUrl);
  refs.importSelection.addEventListener("click", importCurrentSelection);
  refs.pickArea.addEventListener("click", startAreaPicker);
}

async function saveBaseUrl() {
  const baseUrl = refs.baseUrl.value.trim().replace(/\/+$/, "") || DEFAULT_BASE_URL;
  await chrome.storage.local.set({ baseUrl });
  refs.baseUrl.value = baseUrl;
  refs.status.textContent = "Saved local viewer URL.";
}

async function importCurrentSelection() {
  refs.importSelection.disabled = true;
  refs.status.textContent = "Reading current selection...";
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) {
      throw new Error("No active tab.");
    }
    const [selection] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => window.getSelection()?.toString() || "",
    });
    const text = String(selection?.result || "").trim();
    if (!text) {
      throw new Error("No selected text to import.");
    }
    const response = await chrome.runtime.sendMessage({
      type: "IMPORT_TEXT",
      payload: {
        title: tab.title || "",
        url: tab.url || "",
        text,
      },
    });
    if (!response?.ok) {
      throw new Error(response?.error || "Import failed.");
    }
    refs.status.textContent = "Imported. Corpus refresh started.";
  } catch (error) {
    refs.status.textContent = error.message || String(error);
  } finally {
    refs.importSelection.disabled = false;
  }
}

async function startAreaPicker() {
  refs.pickArea.disabled = true;
  refs.status.textContent = "Starting area picker...";
  try {
    const tab = await activeTab();
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ["content.js"],
    });
    const response = await chrome.tabs.sendMessage(tab.id, { type: "START_AREA_PICKER" });
    if (!response?.ok) {
      throw new Error("Could not start area picker.");
    }
    refs.status.textContent = "Hover a text block, click to import, or press Esc.";
    window.close();
  } catch (error) {
    refs.status.textContent = error.message || String(error);
  } finally {
    refs.pickArea.disabled = false;
  }
}

async function activeTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) {
    throw new Error("No active tab.");
  }
  return tab;
}
