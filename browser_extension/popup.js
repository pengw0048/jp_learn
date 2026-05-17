const DEFAULT_BASE_URL = "http://127.0.0.1:8767";

const MESSAGES = {
  zh: {
    appName: "日语阅读助手",
    baseUrl: "本地阅读器地址",
    saveUrl: "保存地址",
    settings: "设置",
    settingsTitle: "设置",
    back: "返回",
    toggleReader: "切换网页阅读模式",
    importSelection: "导入当前选中内容",
    pickArea: "点选页面文本块",
    savedUrl: "已保存本地阅读器地址。",
    togglingReader: "正在切换网页阅读模式...",
    readerBusy: "网页阅读模式仍在标注中。",
    readerOn: "网页阅读模式已开启，标注了 {count} 个词。",
    readerOnEmpty: "网页阅读模式已开启，但没有应用标注。",
    readerOff: "网页阅读模式已关闭。",
    noActiveTab: "没有可用的当前标签页。",
    cannotToggleReader: "无法切换网页阅读模式。",
    readingSelection: "正在读取当前选中内容...",
    noSelection: "没有选中文字可导入。",
    alreadyImported: "已经导入过 {title}。",
    imported: "已导入 {title}。",
    importFailed: "导入失败。",
    startingPicker: "正在启动点选模式...",
    cannotStartPicker: "无法启动点选模式。",
    pickerStarted: "移动鼠标高亮文本块，点击导入，或按 Esc 取消。",
    importSelectionUnavailable: "请先在网页上选中文字。",
    webTextTitle: "网页文本",
  },
  en: {
    appName: "Japanese Reading Companion",
    baseUrl: "Local viewer URL",
    saveUrl: "Save URL",
    settings: "Settings",
    settingsTitle: "Settings",
    back: "Back",
    toggleReader: "Toggle page reading mode",
    importSelection: "Import current selection",
    pickArea: "Pick page area",
    savedUrl: "Saved local viewer URL.",
    togglingReader: "Toggling reading mode...",
    readerBusy: "Reading mode is still annotating.",
    readerOn: "Reading mode on. Annotated {count} words.",
    readerOnEmpty: "Reading mode on, but no annotations were applied.",
    readerOff: "Reading mode off.",
    noActiveTab: "No active tab.",
    cannotToggleReader: "Could not toggle reading mode.",
    readingSelection: "Reading current selection...",
    noSelection: "No selected text to import.",
    alreadyImported: "Already imported {title}.",
    imported: "Imported {title}.",
    importFailed: "Import failed.",
    startingPicker: "Starting area picker...",
    cannotStartPicker: "Could not start area picker.",
    pickerStarted: "Hover a text block, click to import, or press Esc.",
    importSelectionUnavailable: "Select text on the page first.",
    webTextTitle: "web text",
  },
};

let lang = "zh";
let hasImportableSelection = false;

const refs = {
  baseUrl: document.querySelector("#base-url"),
  saveUrl: document.querySelector("#save-url"),
  openSettings: document.querySelector("#open-settings"),
  backMain: document.querySelector("#back-main"),
  mainView: document.querySelector("#main-view"),
  settingsView: document.querySelector("#settings-view"),
  toggleReader: document.querySelector("#toggle-reader"),
  importSelection: document.querySelector("#import-selection"),
  pickArea: document.querySelector("#pick-area"),
  status: document.querySelector("#status"),
  langButtons: document.querySelectorAll("[data-lang]"),
  i18nNodes: document.querySelectorAll("[data-i18n]"),
};

init();

async function init() {
  const settings = await chrome.storage.local.get({
    baseUrl: DEFAULT_BASE_URL,
    lastStatus: "",
    lastStatusAt: "",
    lang: defaultLang(),
  });
  lang = normalizeLang(settings.lang);
  refs.baseUrl.value = settings.baseUrl;
  const visibleStatus = visibleStoredStatus(settings.lastStatus);
  refs.status.textContent = visibleStatus;
  if (!visibleStatus && settings.lastStatus) {
    await chrome.storage.local.remove(["lastStatus", "lastStatusAt"]);
  }
  applyLanguage();
  refs.importSelection.disabled = true;
  refs.openSettings.addEventListener("click", () => showSettings(true));
  refs.backMain.addEventListener("click", () => showSettings(false));
  refs.saveUrl.addEventListener("click", saveBaseUrl);
  refs.toggleReader.addEventListener("click", toggleReadingMode);
  refs.importSelection.addEventListener("click", importCurrentSelection);
  refs.pickArea.addEventListener("click", startAreaPicker);
  refs.langButtons.forEach((button) => {
    button.addEventListener("click", () => setLanguage(button.dataset.lang));
  });
  refreshSelectionButton();
}

async function saveBaseUrl() {
  const baseUrl = refs.baseUrl.value.trim().replace(/\/+$/, "") || DEFAULT_BASE_URL;
  await chrome.storage.local.set({ baseUrl });
  refs.baseUrl.value = baseUrl;
  refs.status.textContent = t("savedUrl");
}

async function toggleReadingMode() {
  refs.toggleReader.disabled = true;
  refs.status.textContent = t("togglingReader");
  try {
    const tab = await activeTab();
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ["vendor/Readability.js", "content.js"],
    });
    const response = await chrome.tabs.sendMessage(tab.id, { type: "TOGGLE_READING_MODE" });
    if (!response?.ok) {
      throw new Error(response?.error || t("cannotToggleReader"));
    }
    refs.status.textContent = response.busy
      ? t("readerBusy")
      : response.enabled && response.tokenCount > 0
      ? t("readerOn", { count: response.tokenCount || 0 })
      : response.enabled
      ? t("readerOnEmpty")
      : t("readerOff");
  } catch (error) {
    refs.status.textContent = error.message || String(error);
  } finally {
    refs.toggleReader.disabled = false;
  }
}

async function importCurrentSelection() {
  if (!hasImportableSelection) {
    refs.status.textContent = t("noSelection");
    return;
  }
  refs.importSelection.disabled = true;
  refs.status.textContent = t("readingSelection");
  try {
    const tab = await activeTab();
    const text = await readPageSelection(tab);
    if (!text) {
      hasImportableSelection = false;
      throw new Error(t("noSelection"));
    }
    const response = await chrome.runtime.sendMessage({
      type: "IMPORT_TEXT",
      payload: {
        title: tab.title || "",
        url: tab.url || "",
        text,
        tabId: tab.id,
      },
    });
    if (!response?.ok) {
      throw new Error(response?.error || t("importFailed"));
    }
    refs.status.textContent = importResultMessage(response.result);
  } catch (error) {
    refs.status.textContent = error.message || String(error);
  } finally {
    refreshSelectionButton();
  }
}

function importResultMessage(result) {
  const imported = result?.imported || {};
  const title = imported.title || t("webTextTitle");
  return result?.duplicate || imported.duplicate
    ? t("alreadyImported", { title })
    : t("imported", { title });
}

async function startAreaPicker() {
  refs.pickArea.disabled = true;
  refs.status.textContent = t("startingPicker");
  try {
    const tab = await activeTab();
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ["content.js"],
    });
    const response = await chrome.tabs.sendMessage(tab.id, { type: "START_AREA_PICKER" });
    if (!response?.ok) {
      throw new Error(t("cannotStartPicker"));
    }
    refs.status.textContent = t("pickerStarted");
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
    throw new Error(t("noActiveTab"));
  }
  return tab;
}

function showSettings(isOpen) {
  refs.mainView.classList.toggle("hidden", isOpen);
  refs.settingsView.classList.toggle("hidden", !isOpen);
  refs.openSettings.classList.toggle("hidden", isOpen);
}

async function refreshSelectionButton() {
  refs.importSelection.disabled = true;
  try {
    const tab = await activeTab();
    hasImportableSelection = Boolean(await readPageSelection(tab));
  } catch {
    hasImportableSelection = false;
  }
  refs.importSelection.disabled = !hasImportableSelection;
  refs.importSelection.title = hasImportableSelection ? "" : t("importSelectionUnavailable");
}

async function readPageSelection(tab) {
  const [selection] = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => window.getSelection()?.toString() || "",
  });
  return String(selection?.result || "").trim();
}

async function setLanguage(nextLang) {
  lang = normalizeLang(nextLang);
  await chrome.storage.local.set({ lang });
  applyLanguage();
}

function applyLanguage() {
  document.documentElement.lang = lang === "zh" ? "zh-Hans" : "en";
  refs.i18nNodes.forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  refs.langButtons.forEach((button) => {
    button.classList.toggle("active", normalizeLang(button.dataset.lang) === lang);
  });
  refs.importSelection.title = hasImportableSelection ? "" : t("importSelectionUnavailable");
}

function t(key, values = {}) {
  const template = MESSAGES[lang]?.[key] || MESSAGES.en[key] || key;
  return template.replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? ""));
}

function defaultLang() {
  return "zh";
}

function normalizeLang(value) {
  return value === "en" ? "en" : "zh";
}

function visibleStoredStatus(status) {
  const text = String(status || "");
  if (!text || isStaleTransientStatus(text)) {
    return "";
  }
  return text;
}

function isStaleTransientStatus(text) {
  return [
    "Imported ",
    "Already imported",
    "Importing ",
    "Corpus refresh",
    "Reading mode ",
    "Toggling reading mode",
    "Extracting ",
    "已导入",
    "已经导入",
    "正在导入",
    "语料刷新",
    "网页阅读模式",
    "正在切换网页阅读模式",
    "正在提取",
  ].some((prefix) => text.startsWith(prefix));
}
