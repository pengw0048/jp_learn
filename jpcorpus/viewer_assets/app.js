const {
  STORAGE_LANG,
  STORAGE_EXAMPLE_COLUMNS,
  STORAGE_MODE,
  STORAGE_SPLIT_RATIOS,
  STORAGE_READER_WORD_LIST,
  STORAGE_READER_POSITIONS,
  DAILY_STUDY_LIMIT,
  STUDY_TARGET_COUNT,
  EXAMPLE_COLUMN_VALUES,
  MODE_VALUES,
  READER_WORD_LIST_VALUES,
  SPLIT_DEFAULT_RATIOS,
  readStatuses,
  readStudyCounts,
  todayKey,
  readStudySession,
  readStudySchedule,
  readExampleColumns,
  readSplitRatios,
  readMode,
  readReaderWordList,
  readReaderPositions,
} = window.JPCORPUS_STORAGE;
const api = window.JPCORPUS_API;
const {
  clearSearchIndexForWord,
  compareKana,
  searchScore,
  searchTerms,
} = window.JPCORPUS_SEARCH;
const {
  asArray,
  badge,
  clampNumber,
  contextPreview,
  el,
  emptyMessage,
  statChip,
  strong,
} = window.JPCORPUS_DOM;
const WORD_LIST_PAGE_SIZE = 600;
const SPLIT_LIMITS = {
  browse: { minLeft: 300, minRight: 420 },
  study: { minLeft: 300, minRight: 420 },
  read: { minLeft: 420, minRight: 340 },
};

const text = window.JPCORPUS_TEXT;


const stateLabels = {
  none: { zh: "未标记", en: "Unmarked", symbol: "·" },
  learning: { zh: "复习中", en: "Reviewing", symbol: "★" },
  uncertain: { zh: "模糊", en: "Unsure", symbol: "?" },
  known: { zh: "认识", en: "Known", symbol: "✓" },
  ignored: { zh: "忽略", en: "Ignored", symbol: "−" },
};

const app = {
  corpus: null,
  words: [],
  selectedWord: null,
  wordDetailRequests: new Map(),
  sourceDetails: new Map(),
  sourceDetailRequests: new Map(),
  sourceDetailFailures: new Set(),
  query: "",
  level: "all",
  sort: "count",
  status: "all",
  source: "all",
  sourcePanelType: null,
  sourcePanelGroupKey: null,
  sourceInventoryNotice: "",
  sourceInventoryBusy: false,
  sourceInventoryNoticeJobId: null,
  expandedSourceGroups: new Set(),
  reader: {
    sourceType: "all",
    groupKey: null,
    documentKey: null,
    wordList: readReaderWordList(),
    selection: null,
    explanation: null,
    question: null,
    controlsOpen: false,
    markedOpen: false,
    preserveScrollOnRender: false,
    positions: readReaderPositions(),
    positionKey: null,
    positionSaveTimer: null,
  },
  listLimit: WORD_LIST_PAGE_SIZE,
  exampleColumns: readExampleColumns(),
  splitRatios: readSplitRatios(),
  lang: localStorage.getItem(STORAGE_LANG) || "zh",
  mode: readMode(),
  statuses: readStatuses(),
  studyCounts: readStudyCounts(),
  studySchedule: readStudySchedule(),
  study: {
    showAnswer: false,
    session: readStudySession(),
  },
  exampleExplanations: {},
  maintenance: {
    enabled: false,
    job: null,
    config: null,
    llm: null,
    task: "sync_media",
    pollTimer: null,
    reloadedJobId: null,
  },
};
const {
  displayMeaningRaw,
  renderLexicalNotes,
  renderMeaningValue,
} = window.JPCORPUS_LEXICAL.createLexicalHelpers({
  el,
  t,
  getLanguage: () => app.lang,
});
const {
  exampleSourceClass,
  fileStem,
  formatNumber,
  formatReference,
  formatTimestamp,
  normalizedTextTitle,
} = window.JPCORPUS_FORMAT.createFormatHelpers({
  getLanguage: () => app.lang,
});
const {
  mergeRemoteStudyState,
  renderStudyCountBadge,
  sameStudySession,
  scheduleStudyReview,
  setStatus,
  setStudyCount,
  statusFor,
  studyCheckLabel,
  studyCountFor,
  studyDueDateFor,
  writeStudySession,
} = window.JPCORPUS_STUDY.createStudyHelpers({
  app,
  api,
  asArray,
  el,
  formatNumber,
  isActiveStudyStatus,
  storage: window.JPCORPUS_STORAGE,
  t,
});

const $ = (selector) => document.querySelector(selector);

const refs = {
  workspace: $(".workspace"),
  sidebar: $(".sidebar"),
  splitResizer: $("#split-resizer"),
  generatedAt: $("#generated-at"),
  summaryStrip: $("#summary-strip"),
  sourcePanel: $("#source-panel"),
  sourcePanelClose: $("#source-panel-close"),
  searchInput: $("#search-input"),
  levelFilter: $("#level-filter"),
  sortSelect: $("#sort-select"),
  statusFilter: $("#status-filter"),
  sourceFilter: $("#source-filter"),
  resultCount: $("#result-count"),
  wordList: $("#word-list"),
  detailPane: $(".detail-pane"),
  emptyState: $("#empty-state"),
  wordDetail: $("#word-detail"),
  studyModeButtons: document.querySelectorAll("[data-mode]"),
  maintenanceToggle: $("#maintenance-toggle"),
  maintenancePanel: $("#maintenance-panel"),
  maintenanceClose: $("#maintenance-close"),
  maintenanceActionButtons: document.querySelectorAll("[data-maintenance-task]"),
  sourceInventory: $("#source-inventory"),
  configSave: $("#config-save"),
  configPath: $("#config-path"),
  configStatusList: $("#config-status-list"),
  configForm: $("#config-form"),
  configSaveStatus: $("#config-save-status"),
  configBangumiClientId: $("#config-bangumi-client-id"),
  configBangumiClientSecret: $("#config-bangumi-client-secret"),
  configJimakuApiKey: $("#config-jimaku-api-key"),
  configLlmProvider: $("#config-llm-provider"),
  configLlmBaseUrl: $("#config-llm-base-url"),
  configLlmModel: $("#config-llm-model"),
  configLlmApiKey: $("#config-llm-api-key"),
  importTextTitle: $("#import-text-title"),
  importTextUrl: $("#import-text-url"),
  importTextContent: $("#import-text-content"),
  importTextSave: $("#import-text-save"),
  importTextStatus: $("#import-text-status"),
  maintenanceProgress: $("#maintenance-progress"),
  maintenanceProgressFill: $("#maintenance-progress-fill"),
  maintenanceProgressLabel: $("#maintenance-progress-label"),
  maintenanceStatus: $("#maintenance-status"),
  maintenanceLog: $("#maintenance-log"),
};
const {
  maintenanceJobSpec,
  maintenanceStatusLabel,
  maintenanceTask,
  renderMaintenanceProgress,
} = window.JPCORPUS_MAINTENANCE.createMaintenanceHelpers({
  app,
  formatNumber,
  refs,
  t,
});
const {
  buildSourceGroups,
  cleanSourceFileLabel,
  formatEpisodeLabel,
  renderSourceInventory,
  sourceDocumentKey,
  sourceDocumentLineCount,
  sourceDocumentWithDetail,
  sourceDocumentWords,
  sourceLabel,
} = window.JPCORPUS_SOURCES.createSourceHelpers({
  app,
  api,
  asArray,
  el,
  emptyMessage,
  fileStem,
  formatNumber,
  hasExampleAnnotations,
  hideSourcePanel,
  normalizedTextTitle,
  refs,
  render,
  startMaintenanceJob,
  storageMode: STORAGE_MODE,
  strong,
  t,
});
const {
  compareNullableNumbers,
  compareReaderDocuments,
  exampleExplanationKey,
  readerDocumentKey,
  readerDocumentLabel,
  readerDocumentsForSource,
  readerLineDomKey,
  readerSelectionForLine,
  renderSourceReader,
} = window.JPCORPUS_READER.createReaderHelpers({
  app,
  asArray,
  cleanSourceFileLabel,
  el,
  emptyMessage,
  formatEpisodeLabel,
  formatNumber,
  formatTimestamp,
  readerWordAllowed,
  selectReaderWord,
  sourceDocumentKey,
  sourceDocumentLineCount,
  sourceDocumentWords,
  strong,
  t,
});

init();

async function init() {
  bindControls();
  applyLanguage();
  loadMaintenanceStatus();
  try {
    app.corpus = await api.loadCorpusIndex();
    app.words = Array.isArray(app.corpus.words) ? app.corpus.words : [];
    await mergeRemoteStudyState();
    app.selectedWord = chooseInitialWord(currentWordSet());
    render();
  } catch (error) {
    renderLoadError(error);
  }
}

function bindControls() {
  refs.searchInput.addEventListener("input", (event) => {
    app.query = event.target.value.trim();
    resetWordListLimit();
    app.selectedWord = chooseInitialWord(currentWordSet());
    app.study.showAnswer = false;
    render();
  });
  refs.sortSelect.addEventListener("change", (event) => {
    app.sort = event.target.value;
    resetWordListLimit();
    render();
  });
  refs.statusFilter.addEventListener("change", (event) => {
    app.status = event.target.value;
    resetWordListLimit();
    app.selectedWord = chooseInitialWord(currentWordSet());
    app.study.showAnswer = false;
    render();
  });
  refs.sourceFilter.addEventListener("change", (event) => {
    app.source = event.target.value;
    resetWordListLimit();
    app.selectedWord = chooseInitialWord(currentWordSet());
    app.study.showAnswer = false;
    render();
  });
  refs.studyModeButtons.forEach((button) => {
    button.addEventListener("click", () => {
      setStudyMode(button.dataset.mode);
    });
  });
  document.querySelectorAll("[data-lang]").forEach((button) => {
    button.addEventListener("click", () => {
      app.lang = button.dataset.lang;
      localStorage.setItem(STORAGE_LANG, app.lang);
      applyLanguage();
      render();
    });
  });
  refs.maintenanceToggle.addEventListener("click", () => {
    refs.maintenancePanel.hidden = !refs.maintenancePanel.hidden;
    refs.maintenanceToggle.classList.toggle("active", !refs.maintenancePanel.hidden);
    if (!refs.maintenancePanel.hidden) {
      hideSourcePanel();
    }
    renderMaintenance();
  });
  refs.maintenanceClose.addEventListener("click", () => {
    refs.maintenancePanel.hidden = true;
    refs.maintenanceToggle.classList.remove("active");
  });
  refs.maintenanceActionButtons.forEach((button) => {
    button.addEventListener("click", () => startMaintenanceJob(button.dataset.maintenanceTask));
  });
  refs.sourcePanelClose.addEventListener("click", hideSourcePanel);
  refs.configSave.addEventListener("click", saveConfig);
  refs.importTextSave.addEventListener("click", importTextFromMaintenance);
  refs.importTextContent.addEventListener("input", renderMaintenance);
  refs.configForm.addEventListener("toggle", () => {
    refs.configForm.dataset.userToggled = "1";
  });
  [
    refs.configLlmProvider,
  ].forEach((control) => {
    control.addEventListener("input", renderMaintenance);
    control.addEventListener("change", renderMaintenance);
  });
  bindSplitResizer();
  window.addEventListener("resize", () => applyWorkspaceSplit());
}

function applyLanguage() {
  document.documentElement.lang = app.lang === "zh" ? "zh-CN" : "en";
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.placeholder = t(node.dataset.i18nPlaceholder);
  });
  document.querySelectorAll("[data-lang]").forEach((button) => {
    button.classList.toggle("active", button.dataset.lang === app.lang);
  });
  updateStudyModeButtons();
}

function render() {
  if (!app.corpus) {
    return;
  }
  updateWorkspaceMode();
  renderHeader();
  renderSourceInventory();
  if (app.mode === "read") {
    renderReadingPane();
  } else {
    renderLevelFilter();
    renderWordList();
  }
  renderDetail();
  renderMaintenance();
}

function updateWorkspaceMode() {
  const reading = app.mode === "read";
  refs.workspace.classList.toggle("reader-workspace", reading);
  refs.sidebar.classList.toggle("reader-sidebar", reading);
  applyWorkspaceSplit();
}

function bindSplitResizer() {
  if (!refs.splitResizer) {
    return;
  }
  refs.splitResizer.addEventListener("pointerdown", (event) => {
    if (window.matchMedia("(max-width: 860px)").matches) {
      return;
    }
    event.preventDefault();
    refs.splitResizer.setPointerCapture(event.pointerId);
    refs.workspace.classList.add("resizing");
    updateWorkspaceSplitFromPointer(event.clientX);
  });
  refs.splitResizer.addEventListener("pointermove", (event) => {
    if (!refs.workspace.classList.contains("resizing")) {
      return;
    }
    updateWorkspaceSplitFromPointer(event.clientX);
  });
  refs.splitResizer.addEventListener("pointerup", (event) => {
    finishSplitResize(event.pointerId);
  });
  refs.splitResizer.addEventListener("pointercancel", (event) => {
    finishSplitResize(event.pointerId);
  });
  refs.splitResizer.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
      return;
    }
    event.preventDefault();
    const ratio = splitRatioForMode();
    const step = event.shiftKey ? 0.08 : 0.03;
    let nextRatio = ratio;
    if (event.key === "ArrowLeft") {
      nextRatio -= step;
    } else if (event.key === "ArrowRight") {
      nextRatio += step;
    } else if (event.key === "Home") {
      nextRatio = 0.22;
    } else if (event.key === "End") {
      nextRatio = 0.78;
    }
    setSplitRatioForMode(nextRatio);
    applyWorkspaceSplit();
  });
}

function finishSplitResize(pointerId) {
  refs.workspace.classList.remove("resizing");
  if (refs.splitResizer?.hasPointerCapture(pointerId)) {
    refs.splitResizer.releasePointerCapture(pointerId);
  }
}

function updateWorkspaceSplitFromPointer(clientX) {
  const rect = refs.workspace.getBoundingClientRect();
  const availableWidth = splitAvailableWidth(rect.width);
  if (availableWidth <= 0) {
    return;
  }
  const leftWidth = clientX - rect.left;
  setSplitRatioForMode(leftWidth / availableWidth);
  applyWorkspaceSplit();
}

function applyWorkspaceSplit() {
  if (!refs.workspace || window.matchMedia("(max-width: 860px)").matches) {
    return;
  }
  const availableWidth = splitAvailableWidth(refs.workspace.getBoundingClientRect().width);
  if (availableWidth <= 0) {
    return;
  }
  const ratio = clampedSplitRatio(splitRatioForMode(), availableWidth);
  const leftWidth = Math.round(ratio * availableWidth);
  refs.workspace.style.setProperty("--split-left-width", `${leftWidth}px`);
  refs.splitResizer?.setAttribute("aria-valuenow", String(Math.round(ratio * 100)));
  setSplitRatioForMode(ratio, { persist: false });
}

function splitAvailableWidth(totalWidth) {
  const resizerWidth = refs.splitResizer?.offsetWidth || 9;
  return Math.max(totalWidth - resizerWidth, 1);
}

function splitRatioForMode() {
  return app.splitRatios[app.mode] ?? SPLIT_DEFAULT_RATIOS[app.mode] ?? 0.3;
}

function setSplitRatioForMode(ratio, options = {}) {
  const persist = options.persist ?? true;
  const availableWidth = splitAvailableWidth(refs.workspace.getBoundingClientRect().width);
  const nextRatio = clampedSplitRatio(ratio, availableWidth);
  app.splitRatios = {
    ...app.splitRatios,
    [app.mode]: nextRatio,
  };
  if (persist) {
    localStorage.setItem(STORAGE_SPLIT_RATIOS, JSON.stringify(app.splitRatios));
  }
}

function clampedSplitRatio(ratio, availableWidth) {
  const limits = SPLIT_LIMITS[app.mode] || SPLIT_LIMITS.browse;
  const minRatio = Math.min(limits.minLeft / availableWidth, 0.82);
  const maxRatio = Math.max(1 - limits.minRight / availableWidth, minRatio);
  return clampNumber(Number(ratio), minRatio, maxRatio);
}

function renderHeader() {
  updateStudyModeButtons();
  refs.generatedAt.textContent = app.corpus.generated_at
    ? t("generatedAt", { date: app.corpus.generated_at })
    : "";
  if (app.mode !== "read") {
    refs.summaryStrip.hidden = true;
    refs.summaryStrip.replaceChildren();
    if (!refs.sourcePanel.hidden) {
      hideSourcePanel();
    }
    return;
  }
  refs.summaryStrip.hidden = false;
  const summary = app.corpus.summary || {};
  const items = [
    { label: t("subtitles"), value: summary.subtitle_file_count, sourceType: "subtitle" },
    { label: t("lyrics"), value: summary.lyric_file_count, sourceType: "lyrics" },
    { label: t("texts"), value: summary.text_file_count, sourceType: "text" },
  ];
  refs.summaryStrip.replaceChildren(
    ...items.map(({ label, value, sourceType }) => {
      const pill = el(sourceType ? "button" : "div", "summary-pill");
      if (sourceType) {
        pill.type = "button";
        pill.dataset.sourcePanelType = sourceType;
        pill.addEventListener("click", () => toggleSourcePanel(sourceType));
      }
      pill.append(label, " ", strong(value ?? "0"));
      return pill;
    }),
  );
  updateSummaryPillStates();
}

function toggleSourcePanel(sourceType) {
  if (!refs.sourcePanel.hidden && app.sourcePanelType === sourceType) {
    hideSourcePanel();
    return;
  }
  if (app.sourcePanelType !== sourceType) {
    app.sourcePanelGroupKey = null;
  }
  app.sourcePanelType = sourceType;
  refs.sourcePanel.hidden = false;
  refs.maintenancePanel.hidden = true;
  refs.maintenanceToggle.classList.remove("active");
  renderSourceInventory();
  updateSummaryPillStates();
}

function hideSourcePanel() {
  refs.sourcePanel.hidden = true;
  app.sourcePanelType = null;
  app.sourcePanelGroupKey = null;
  updateSummaryPillStates();
}

function updateSummaryPillStates() {
  const sourceOpen = !refs.sourcePanel.hidden;
  refs.summaryStrip.querySelectorAll(".summary-pill").forEach((pill) => {
    const active = sourceOpen && pill.dataset.sourcePanelType === app.sourcePanelType;
    pill.classList.toggle("active", active);
    if (pill.dataset.sourcePanelType) {
      pill.setAttribute("aria-expanded", active ? "true" : "false");
    }
  });
}

async function loadMaintenanceStatus() {
  try {
    const payload = await api.loadMaintenanceStatus();
    app.maintenance.enabled = Boolean(payload.enabled);
    app.maintenance.job = payload.job || null;
    app.maintenance.config = payload.config || null;
    app.maintenance.llm = payload.llm || null;
    if (payload.llm?.provider) {
      refs.configLlmProvider.value = payload.llm.provider;
    }
    if (payload.llm?.base_url && refs.configLlmBaseUrl && !refs.configLlmBaseUrl.value) {
      refs.configLlmBaseUrl.value = payload.llm.base_url;
    }
    if (payload.llm?.model && refs.configLlmModel && !refs.configLlmModel.value) {
      refs.configLlmModel.value = payload.llm.model;
    }
    renderMaintenance();
    if (app.maintenance.job?.status === "running") {
      pollMaintenanceJob();
    }
  } catch {
    app.maintenance.enabled = false;
    renderMaintenance();
  }
}

function renderMaintenance() {
  if (!refs.maintenancePanel) {
    return;
  }
  renderConfigStatus();
  const task = maintenanceTask();
  const job = app.maintenance.job;
  refs.maintenanceToggle.disabled = !app.maintenance.enabled;
  refs.maintenanceActionButtons.forEach((button) => {
    button.disabled = !app.maintenance.enabled || job?.status === "running";
    button.classList.toggle("active", button.dataset.maintenanceTask === task && job?.status === "running");
  });
  refs.importTextSave.disabled =
    !app.maintenance.enabled
    || job?.status === "running"
    || !refs.importTextContent.value.trim();
  refs.maintenanceStatus.textContent = job ? maintenanceStatusLabel(job) : t("maintenanceIdle");
  renderMaintenanceProgress(job);
  refs.maintenanceLog.textContent = job?.log?.join("\n") || "";
}

function renderConfigStatus() {
  const config = app.maintenance.config;
  refs.configSave.disabled = !app.maintenance.enabled;
  if (!config) {
    refs.configPath.textContent = app.maintenance.enabled ? "" : t("maintenanceDisabled");
    refs.configStatusList.replaceChildren();
    return;
  }
  refs.configPath.textContent = t("configPath", { path: config.env_path || ".env" });
  const services = Array.isArray(config.services) ? config.services : [];
  const hasMissing = services.some((service) => !service.configured);
  if (hasMissing && !refs.configForm.dataset.userToggled) {
    refs.configForm.open = true;
  }
  refs.configStatusList.replaceChildren(
    ...services.map((service) => {
      const item = el("div", service.configured ? "config-status ready" : "config-status missing");
      item.append(
        strong(service.label || service.id),
        el(
          "span",
          "",
          service.configured
            ? t("configReady")
            : t("configMissing", { keys: (service.missing || []).join(", ") }),
        ),
      );
      return item;
    }),
  );
}

function renderSourceSnippet(item) {
  const row = el("div", "source-snippet");
  const wordButton = el("button", "source-word-button", item.word.word || item.example.matched_text || "");
  wordButton.type = "button";
  wordButton.addEventListener("click", () => openWordFromSource(item.word.word));
  const textLine = el("div", "source-snippet-text");
  appendHighlighted(textLine, item.example.sentence || "", item.example.matched_text || item.word.word);
  const reference = el("small", `reference reference-${exampleSourceClass(item.example)}`, formatReference(item.example));
  row.append(wordButton, textLine, reference);
  return row;
}

function openWordFromSource(wordText) {
  const word = findWord(wordText);
  if (!word) {
    return;
  }
  app.mode = "browse";
  localStorage.setItem(STORAGE_MODE, app.mode);
  app.selectedWord = word;
  hideSourcePanel();
  render();
}

function selectReaderWord(wordText, selection = null) {
  const word = findWord(wordText);
  if (!word) {
    return;
  }
  if (app.mode !== "read") {
    openWordFromSource(wordText);
    return;
  }
  const changedWord = app.selectedWord?.word !== word.word;
  app.selectedWord = word;
  app.reader.selection = selection;
  if (!selection || app.reader.explanation?.key !== selection.key) {
    app.reader.explanation = null;
  }
  if (!selection || app.reader.question?.key !== selection.key) {
    app.reader.question = null;
  }
  app.study.showAnswer = false;
  renderDetail();
  if (changedWord) {
    resetDetailScroll();
  }
  renderMaintenance();
  updateReaderActiveTokens();
}

function updateReaderActiveTokens() {
  if (!refs.wordList) {
    return;
  }
  const selected = app.selectedWord?.word || "";
  refs.wordList.querySelectorAll(".reader-token").forEach((node) => {
    node.classList.toggle("active", Boolean(selected) && node.dataset.word === selected);
  });
}

function findWord(wordText) {
  return app.words.find((item) => item.word === wordText);
}

function ensureWordDetail(word) {
  if (!needsWordDetail(word)) {
    return;
  }
  const key = word.word || "";
  if (!key || app.wordDetailRequests.has(key)) {
    return;
  }
  word._detailLoading = true;
  const request = api.loadWordDetail(key)
    .then((payload) => {
      if (payload.word && typeof payload.word === "object") {
        Object.assign(word, payload.word, {
          _detailLoaded: true,
          _detailLoading: false,
        });
        clearSearchIndexForWord(word);
      }
    })
    .catch(() => {
      word._detailLoading = false;
      word._detailLoaded = true;
    })
    .finally(() => {
      app.wordDetailRequests.delete(key);
      if (app.selectedWord?.word === key) {
        render();
      }
    });
  app.wordDetailRequests.set(key, request);
}

function needsWordDetail(word) {
  return Boolean(word)
    && word.has_detail !== false
    && !word._detailLoaded
    && !Array.isArray(word.examples);
}

function ensureSourceDetails(documents) {
  const keys = asArray(documents)
    .map(sourceDocumentKey)
    .filter((key) => key && !app.sourceDetails.has(key) && !app.sourceDetailRequests.has(key) && !app.sourceDetailFailures.has(key));
  if (!keys.length) {
    return;
  }
  keys.forEach((key) => app.sourceDetailRequests.set(key, true));
  api.loadSourceDetails(keys)
    .then((payload) => {
      asArray(payload.sources).forEach((source) => {
        app.sourceDetails.set(sourceDocumentKey(source), source);
      });
      asArray(payload.missing).forEach((key) => app.sourceDetailFailures.add(key));
    })
    .catch(() => {
      keys.forEach((key) => app.sourceDetailFailures.add(key));
    })
    .finally(() => {
      keys.forEach((key) => app.sourceDetailRequests.delete(key));
      if (app.mode === "read") {
        app.reader.preserveScrollOnRender = true;
        render();
      }
    });
}

function sourceDetailsReady(documents) {
  return asArray(documents).every((document) => {
    if (asArray(document.lines).length > 0) {
      return true;
    }
    const key = sourceDocumentKey(document);
    return Boolean(key && (app.sourceDetails.has(key) || app.sourceDetailFailures.has(key)));
  });
}

function hasExampleAnnotations(example) {
  return Boolean(example.translation_zh && example.usage_note_zh);
}

async function saveConfig() {
  refs.configSave.disabled = true;
  refs.configSaveStatus.textContent = "";
  const payload = {
    bangumi_client_id: refs.configBangumiClientId.value.trim(),
    bangumi_client_secret: refs.configBangumiClientSecret.value.trim(),
    jimaku_api_key: refs.configJimakuApiKey.value.trim(),
    llm_provider: refs.configLlmProvider.value,
    llm_base_url: refs.configLlmBaseUrl.value.trim(),
    llm_model: refs.configLlmModel.value.trim(),
    llm_api_key: refs.configLlmApiKey.value.trim(),
  };
  try {
    const result = await api.saveConfig(payload);
    app.maintenance.config = result.config || null;
    app.maintenance.llm = result.config?.llm || app.maintenance.llm;
    if (app.maintenance.llm?.provider) {
      refs.configLlmProvider.value = app.maintenance.llm.provider;
    }
    [refs.configBangumiClientSecret, refs.configJimakuApiKey, refs.configLlmApiKey].forEach((input) => {
      input.value = "";
    });
    refs.configSaveStatus.textContent = t("configSaved");
    renderMaintenance();
  } catch (error) {
    refs.configSaveStatus.textContent = t("configSaveFailed", { error: error.message });
  } finally {
    refs.configSave.disabled = !app.maintenance.enabled;
  }
}

async function importTextFromMaintenance() {
  refs.importTextSave.disabled = true;
  refs.importTextStatus.textContent = t("importTextSaving");
  try {
    const result = await api.importText({
      title: refs.importTextTitle.value.trim(),
      url: refs.importTextUrl.value.trim(),
      text: refs.importTextContent.value,
    });
    const title = result.imported?.title || refs.importTextTitle.value.trim() || t("sourceInventoryUnknown");
    refs.importTextTitle.value = "";
    refs.importTextUrl.value = "";
    refs.importTextContent.value = "";
    if (result.imported?.duplicate) {
      refs.importTextStatus.textContent = t("importTextDuplicate", { title });
    } else {
      refs.importTextStatus.textContent = t("importTextSaved", { title });
      await startMaintenanceJob("refresh_imported_texts");
    }
  } catch (error) {
    refs.importTextStatus.textContent = t("importTextFailed", { error: error.message || String(error) });
  } finally {
    renderMaintenance();
  }
}

function renderLevelFilter() {
  const levels = ["all", "N5", "N4", "N3", "N2", "N1"];
  refs.levelFilter.replaceChildren(
    ...levels.map((level) => {
      const button = el("button", "chip");
      button.type = "button";
      button.textContent = level === "all" ? t("allLevels") : level;
      button.classList.toggle("active", app.level === level);
      button.addEventListener("click", () => {
        app.level = level;
        resetWordListLimit();
        app.selectedWord = chooseInitialWord(currentWordSet());
        app.study.showAnswer = false;
        render();
      });
      return button;
    }),
  );
}

function renderWordList() {
  const words = currentWordSet();
  if (app.mode === "study") {
    const breakdown = studyQueueBreakdown(words);
    refs.resultCount.textContent = t("studyWordsFound", {
      count: formatNumber(words.length),
      review: formatNumber(breakdown.review),
      new: formatNumber(breakdown.new),
    });
  } else {
    refs.resultCount.textContent = t("wordsFound", {
      count: formatNumber(words.length),
    });
  }
  if (words.length === 0) {
    app.selectedWord = null;
    refs.wordList.replaceChildren(emptyMessage(t(app.mode === "study" ? "noStudyWords" : "noWords")));
    return;
  }
  if (!app.selectedWord || !words.some((word) => word.word === app.selectedWord.word)) {
    app.selectedWord = words[0];
  }
  const selectedIndex = words.findIndex((word) => word.word === app.selectedWord?.word);
  if (selectedIndex >= app.listLimit) {
    app.listLimit = Math.ceil((selectedIndex + 1) / WORD_LIST_PAGE_SIZE) * WORD_LIST_PAGE_SIZE;
  }
  const scrollTop = refs.wordList.scrollTop;
  const visibleWords = words.slice(0, app.listLimit);
  const nodes = visibleWords.map(renderWordRow);
  if (visibleWords.length < words.length) {
    nodes.push(renderLoadMoreWords(words.length - visibleWords.length));
  }
  refs.wordList.replaceChildren(...nodes);
  refs.wordList.scrollTop = scrollTop;
}

function renderReadingPane() {
  renderLevelFilter();
  const previousScrollTop = app.reader.preserveScrollOnRender ? currentReaderScrollTop() : null;
  const readerWords = readerWordSet();
  const sourceType = app.reader.sourceType === "all" ? null : app.reader.sourceType;
  const groups = buildSourceGroups(sourceType);
  if (groups.length === 0) {
    app.reader.groupKey = null;
    app.reader.documentKey = null;
    refs.resultCount.textContent = t("readerSourcesFound", { count: formatNumber(0) });
    refs.wordList.replaceChildren(emptyMessage(t("sourceReaderEmpty")));
    app.reader.preserveScrollOnRender = false;
    return;
  }
  if (!groups.some((group) => group.key === app.reader.groupKey)) {
    app.reader.groupKey = groups[0].key;
    app.reader.documentKey = null;
  }
  const selected = groups.find((group) => group.key === app.reader.groupKey) || groups[0];
  const units = readerUnitsForSource(selected);
  if (!units.some((unit) => unit.key === app.reader.documentKey)) {
    app.reader.documentKey = units[0]?.key || null;
  }
  const selectedUnit = units.find((unit) => unit.key === app.reader.documentKey) || units[0] || null;
  syncSelectedWordToReaderSource(selectedUnit || selected, readerWords);
  refs.resultCount.replaceChildren(renderReaderModeControls(groups, selected, units, selectedUnit));
  const detailDocuments = selectedUnit?.documents || selected.sourceDocuments || [];
  const detailsReady = sourceDetailsReady(detailDocuments);
  if (!detailsReady) {
    ensureSourceDetails(detailDocuments);
  }

  const pane = el("div", "reader-mode-pane");
  const scroller = el("div", "reader-mode-scroll");
  const positionKey = readerPositionKey(selected, selectedUnit);
  app.reader.positionKey = positionKey;
  scroller.addEventListener("click", clearReaderWordSelectionFromBlank);
  scroller.addEventListener("scroll", () => saveReaderPosition(positionKey, scroller), { passive: true });
  scroller.append(
    renderReaderModeSummary(selected, selectedUnit),
    renderReaderMarkedWordsPanel(),
    detailsReady
      ? renderSourceReader(selected, {
        full: true,
        wordSet: readerWords,
        documents: selectedUnit?.documents || [],
      })
      : emptyMessage(t("sourceDetailLoading")),
  );
  pane.append(scroller);
  refs.wordList.replaceChildren(pane);
  const restoredScrollTop = previousScrollTop ?? (app.reader.positions[positionKey]?.scrollTop || 0);
  const nextScroller = refs.wordList.querySelector(".reader-mode-scroll");
  if (nextScroller && restoredScrollTop > 0) {
    nextScroller.scrollTop = restoredScrollTop;
  }
  app.reader.preserveScrollOnRender = false;
  updateReaderActiveTokens();
}

function currentReaderScrollTop() {
  return refs.wordList.querySelector(".reader-mode-scroll")?.scrollTop || 0;
}

function readerPositionKey(source, unit) {
  return [
    source?.type || "",
    source?.key || "",
    unit?.key || "",
  ].join("\u0000");
}

function saveReaderPosition(key, scroller) {
  if (!key || !scroller) {
    return;
  }
  const nextTop = Math.max(0, Math.round(scroller.scrollTop || 0));
  const maxScroll = Math.max(0, (scroller.scrollHeight || 0) - (scroller.clientHeight || 0));
  const progress = maxScroll > 0 ? Math.round((nextTop / maxScroll) * 100) : 0;
  const current = app.reader.positions[key];
  if (current?.scrollTop === nextTop && current?.progress === progress) {
    return;
  }
  app.reader.positions[key] = { scrollTop: nextTop, progress, updatedAt: Date.now() };
  if (app.reader.positionSaveTimer) {
    window.clearTimeout(app.reader.positionSaveTimer);
  }
  app.reader.positionSaveTimer = window.setTimeout(() => {
    app.reader.positionSaveTimer = null;
    persistReaderPositions();
  }, 150);
}

function syncSelectedWordToReaderSource(readingTarget, wordSet) {
  const words = readingTarget?.words || new Set();
  if (
    app.reader.selection
    && words.has(app.selectedWord?.word)
    && readerWordAllowed(app.selectedWord.word, wordSet)
  ) {
    return;
  }
  app.selectedWord = null;
  clearReaderSelection();
}

function clearReaderSelection() {
  app.reader.selection = null;
  app.reader.explanation = null;
  app.reader.question = null;
}

function clearReaderWordSelectionFromBlank(event) {
  if (event.target instanceof Element && event.target.closest(".reader-token, summary, button, select, input, textarea, label, a")) {
    return;
  }
  clearReaderWordSelection();
}

function clearReaderWordSelection() {
  if (!app.selectedWord && !app.reader.selection && !app.reader.explanation) {
    return;
  }
  app.selectedWord = null;
  clearReaderSelection();
  app.study.showAnswer = false;
  renderDetail();
  renderMaintenance();
  updateReaderActiveTokens();
}

function renderReaderModeControls(groups, selected, units, selectedUnit) {
  const details = el("details", "reader-mode-controls");
  details.open = app.reader.controlsOpen;
  details.addEventListener("toggle", () => {
    app.reader.controlsOpen = details.open;
  });
  details.append(
    el("summary", "reader-mode-controls-summary", readerModeSummaryLabel(groups, selected, selectedUnit)),
    renderReaderModeToolbar(groups, selected, units, selectedUnit),
  );
  return details;
}

function readerModeSummaryLabel(groups, selected, selectedUnit) {
  const parts = [
    t("readerSourcesFound", { count: formatNumber(groups.length) }),
    selected.title,
  ];
  if (selectedUnit?.label && selectedUnit.label !== selected.title) {
    parts.push(selectedUnit.label);
  }
  return parts.filter(Boolean).join(" · ");
}

function renderReaderModeToolbar(groups, selected, units, selectedUnit) {
  const toolbar = el("div", "reader-mode-toolbar");
  const tabs = el("div", "reader-source-tabs");
  [
    ["all", t("sourceAll")],
    ["subtitle", t("sourceSubtitles")],
    ["lyrics", t("sourceLyrics")],
    ["text", t("sourceTexts")],
  ].forEach(([value, label]) => {
    const button = el("button", "", label);
    button.type = "button";
    button.classList.toggle("active", app.reader.sourceType === value);
    button.addEventListener("click", () => {
      app.reader.sourceType = value;
      app.reader.groupKey = null;
      app.reader.documentKey = null;
      clearReaderSelection();
      render();
    });
    tabs.append(button);
  });

  const sourcePicker = el("label", "reader-source-picker");
  sourcePicker.append(el("span", "reader-source-picker-label", t("readerSourceChoice")));
  const select = el("select", "reader-source-select");
  groups.forEach((group) => {
    const option = el("option", "", group.title || t("sourceInventoryUnknown"));
    option.value = group.key;
    option.selected = group.key === selected.key;
    const meta = [
      sourceLabel(group.type),
      group.meta,
      `${formatNumber(group.readerLineCount || group.exampleCount)} ${group.readerLineCount ? t("sourceInventoryLines") : t("sourceInventoryExamples")}`,
      readerSourceProgressLabel(group),
    ].filter(Boolean).join(" · ");
    option.textContent = [group.title || t("sourceInventoryUnknown"), meta].filter(Boolean).join(" · ");
    select.append(option);
  });
  select.addEventListener("change", () => {
    app.reader.groupKey = select.value;
    app.reader.documentKey = null;
    clearReaderSelection();
    render();
  });
  sourcePicker.append(select);
  toolbar.append(tabs, sourcePicker, renderReaderUnitPicker(units, selectedUnit), renderReaderWordListPicker());
  return toolbar;
}

function renderReaderUnitPicker(units, selectedUnit) {
  const { source } = currentReaderSelectionSource();
  const picker = el("label", "reader-source-picker");
  picker.append(el("span", "reader-source-picker-label", t("readerItemChoice")));
  const select = el("select", "reader-source-select");
  if (!units.length) {
    select.disabled = true;
    select.append(el("option", "", t("sourceReaderEmpty")));
  }
  units.forEach((unit) => {
    const label = [readerUnitOptionLabel(unit), readerUnitProgressLabel(source, unit)].filter(Boolean).join(" · ");
    const option = el("option", "", label);
    option.value = unit.key;
    option.selected = unit.key === selectedUnit?.key;
    select.append(option);
  });
  select.addEventListener("change", () => {
    app.reader.documentKey = select.value;
    clearReaderSelection();
    render();
  });
  picker.append(select);
  return picker;
}

function renderReaderWordListPicker() {
  const picker = el("div", "reader-word-list-picker");
  picker.append(el("span", "reader-source-picker-label", t("readerWordListChoice")));
  const options = el("div", "reader-word-list-tabs");
  [
    ["all", t("readerWordListAll")],
    ["study", t("readerWordListStudy")],
    ["piece", t("readerWordListPiece")],
    ["N5", "N5"],
    ["N4", "N4"],
    ["N3", "N3"],
    ["N2", "N2"],
    ["N1", "N1"],
  ].forEach(([value, label]) => {
    const button = el("button", "", label);
    button.type = "button";
    button.classList.toggle("active", app.reader.wordList === value);
    button.addEventListener("click", () => {
      app.reader.wordList = value;
      localStorage.setItem(STORAGE_READER_WORD_LIST, value);
      app.reader.preserveScrollOnRender = true;
      clearReaderSelection();
      render();
    });
    options.append(button);
  });
  picker.append(options);
  return picker;
}

function readerWordSet() {
  if (app.reader.wordList === "all") {
    return null;
  }
  if (app.reader.wordList === "study") {
    return new Set(readerStudyWords().map((word) => word.word));
  }
  if (app.reader.wordList === "piece") {
    return new Set(readerMarkedWordsForCurrentUnit().map((entry) => entry.word.word));
  }
  return new Set(
    app.words
      .filter((word) => word.level === app.reader.wordList)
      .map((word) => word.word),
  );
}

function readerStudyWords() {
  const sessionWords = app.study.session?.date === todayKey()
    ? asArray(app.study.session.words).map(findWord).filter(Boolean)
    : [];
  return sessionWords.length ? sessionWords : studyQueue();
}

function readerWordAllowed(wordText, wordSet) {
  return !wordSet || wordSet.has(wordText);
}

function readerUnitsForSource(source) {
  const documents = readerDocumentsForSource(source);
  if (source.type === "subtitle") {
    return subtitleReaderUnits(documents);
  }
  return documents
    .map((document) => {
      const label = readerDocumentLabel(document);
      const meta = readerDocumentMeta(document);
      return createReaderUnit({
        key: readerDocumentKey(document),
        label,
        meta,
        documents: [document],
      });
    })
    .sort(compareReaderUnits);
}

function subtitleReaderUnits(documents) {
  const units = new Map();
  documents.forEach((document) => {
    const episode = Number.isInteger(document.episode) ? document.episode : null;
    const key = episode === null ? readerDocumentKey(document) : `episode:${episode}`;
    if (!units.has(key)) {
      units.set(key, {
        key,
        episode,
        label: episode === null ? readerDocumentLabel(document) : formatEpisodeLabel(episode),
        metaParts: new Set(),
        documents: [],
      });
    }
    const unit = units.get(key);
    const fileLabel = cleanSourceFileLabel(document.source_file || document.source_title || "");
    if (fileLabel && episode === null) {
      unit.metaParts.add(fileLabel);
    }
    unit.documents.push(document);
  });
  return [...units.values()]
    .map((unit) => {
      const documentsForUnit = unit.documents.sort(compareReaderDocuments);
      const selectedDocuments = unit.episode === null
        ? documentsForUnit
        : [preferredSubtitleDocument(documentsForUnit)];
      return createReaderUnit({
        key: unit.key,
        episode: unit.episode,
        label: unit.label,
        meta: unit.episode === null ? [...unit.metaParts][0] || "" : "",
        documents: selectedDocuments.filter(Boolean),
      });
    })
    .sort(compareReaderUnits);
}

function preferredSubtitleDocument(documents) {
  return [...documents].sort(comparePreferredSubtitleDocuments)[0] || null;
}

function comparePreferredSubtitleDocuments(left, right) {
  return subtitleDocumentPreferenceScore(right) - subtitleDocumentPreferenceScore(left)
    || compareReaderDocuments(left, right);
}

function subtitleDocumentPreferenceScore(document) {
  const file = String(document.source_file || document.source_title || "").toLowerCase();
  let score = sourceDocumentLineCount(document);
  if (/(^|[._\s-])ja($|[._\s-]|\[)/u.test(file) || /jpn|japanese/u.test(file)) {
    score += 80;
  }
  if (/ja[-_]?en|en[-_]?ja|dual|bilingual/u.test(file)) {
    score -= 120;
  }
  if (/netflix|web-?rip/u.test(file)) {
    score += 20;
  }
  return score;
}

function createReaderUnit({ key, episode = null, label, meta = "", documents }) {
  const words = new Set();
  const lineCount = documents.reduce((total, document) => {
    asArray(document.words).forEach((word) => {
      if (word) {
        words.add(word);
      }
    });
    asArray(document.lines).forEach((line) => {
      asArray(line.matches).forEach((match) => {
        if (match.word) {
          words.add(match.word);
        }
      });
    });
    return total + sourceDocumentLineCount(document);
  }, 0);
  return {
    key,
    episode,
    label,
    meta,
    documents,
    words,
    lineCount,
  };
}

function readerDocumentMeta(document) {
  if (document.source_type === "lyrics") {
    return [
      document.source_artist,
      document.source_album && document.source_album !== document.source_title ? document.source_album : "",
    ].filter(Boolean).join(" · ");
  }
  if (document.source_type === "text") {
    return [document.source_artist, cleanSourceFileLabel(document.source_file || "")]
      .filter(Boolean)
      .join(" · ");
  }
  return cleanSourceFileLabel(document.source_file || "");
}

function readerUnitOptionLabel(unit) {
  const meta = [
    unit.meta,
    `${formatNumber(unit.lineCount)} ${t("sourceInventoryLines")}`,
  ].filter(Boolean).join(" · ");
  return [unit.label, meta].filter(Boolean).join(" · ");
}

function readerUnitProgressLabel(source, unit) {
  if (!source || !unit) {
    return "";
  }
  const progress = app.reader.positions[readerPositionKey(source, unit)]?.progress;
  if (!Number.isFinite(progress) || progress <= 0) {
    return "";
  }
  return t("readerProgress", { percent: formatNumber(Math.min(100, Math.max(0, Math.round(progress)))) });
}

function readerSourceProgressLabel(source) {
  const units = readerUnitsForSource(source);
  const progressValues = units
    .map((unit) => app.reader.positions[readerPositionKey(source, unit)]?.progress)
    .filter((value) => Number.isFinite(value) && value > 0);
  if (progressValues.length === 0) {
    return "";
  }
  const progress = Math.max(...progressValues);
  return t("readerProgress", { percent: formatNumber(Math.min(100, Math.max(0, Math.round(progress)))) });
}

function compareReaderUnits(left, right) {
  const episodeDiff = compareNullableNumbers(left.episode, right.episode);
  if (episodeDiff !== 0) {
    return episodeDiff;
  }
  const labelDiff = String(left.label || "").localeCompare(String(right.label || ""), app.lang === "zh" ? "zh-CN" : "ja-JP");
  if (labelDiff !== 0) {
    return labelDiff;
  }
  return String(left.meta || "").localeCompare(String(right.meta || ""), app.lang === "zh" ? "zh-CN" : "ja-JP");
}

function renderReaderModeSummary(source, unit) {
  const summary = el("div", `reader-mode-summary source-card-${source.type || "unknown"}`);
  const title = el("div", "reader-mode-title");
  title.append(el("span", "source-kind", sourceLabel(source.type)), el("strong", "", source.title));
  if (source.meta) {
    title.append(el("span", "source-meta", source.meta));
  }
  if (unit) {
    title.append(el("span", "source-meta", unit.label));
  }
  const hint = !source.sourceDocuments?.length && source.exampleItems.length > 0
    ? t("sourceReaderFallback")
    : t("readerCurrentHint");
  if (unit) {
    const metrics = el("div", "source-metrics reader-mode-metrics");
    [
      [t("sourceInventoryLines"), unit.lineCount],
      [t("sourceInventoryWords"), unit.words.size],
      [t("sourceInventoryFiles"), unit.documents.length],
    ].forEach(([label, value], index) => {
      if (index === 2 && value <= 1) {
        return;
      }
      const metric = el("span", "source-metric");
      metric.append(el("span", "", label), strong(value));
      metrics.append(metric);
    });
    summary.append(title, metrics, el("p", "", hint));
  } else {
    summary.append(title, el("p", "", hint));
  }
  return summary;
}

function resetWordListLimit() {
  app.listLimit = WORD_LIST_PAGE_SIZE;
  refs.wordList.scrollTop = 0;
}

function renderLoadMoreWords(remaining) {
  const button = el("button", "load-more-words");
  button.type = "button";
  button.textContent = t("showMoreWords", {
    count: formatNumber(Math.min(WORD_LIST_PAGE_SIZE, remaining)),
  });
  button.addEventListener("click", () => {
    app.listLimit += WORD_LIST_PAGE_SIZE;
    renderWordList();
  });
  return button;
}

function renderWordRow(word) {
  const button = el("button", "word-row");
  button.type = "button";
  button.classList.toggle("active", app.selectedWord?.word === word.word);
  button.addEventListener("click", () => {
    selectWord(word, button);
  });

  const main = el("div", "word-main");
  const wordText = el("div", "word-text", word.word || "");
  const badges = el("div", "word-badges");
  if (word.level) {
    badges.append(badge(word.level));
  }
  const checks = renderStudyCountBadge(word);
  if (checks) {
    badges.append(checks);
  }
  badges.append(statusDot(statusFor(word)));
  main.append(wordText, badges);

  const meta = el(
    "div",
    "word-meta",
    `${word.reading || ""} · ${t("count")} ${formatNumber(displayCount(word))}`,
  );
  button.append(main, meta);
  if (app.mode !== "study") {
    button.append(renderMeaningValue(word, "word-meaning"));
  }
  return button;
}

function renderDetail() {
  if (app.mode === "study") {
    renderStudyDetail();
    return;
  }
  const word = app.selectedWord;
  if (!word) {
    refs.wordDetail.hidden = true;
    refs.emptyState.hidden = false;
    refs.emptyState.querySelector("h2").textContent = t(app.mode === "read" ? "readerNoSelection" : "noWords");
    refs.emptyState.querySelector("p").textContent = "";
    return;
  }
  refs.emptyState.hidden = true;
  refs.wordDetail.hidden = false;
  ensureWordDetail(word);
  const nodes = [renderDetailHeader(word), renderLexicalNotes(word)];
  const readerContext = renderReaderContextPanel(word);
  if (readerContext) {
    nodes.push(readerContext);
  }
  nodes.push(renderExamples(word));
  refs.wordDetail.replaceChildren(...nodes);
}

function resetDetailScroll() {
  if (refs.detailPane) {
    refs.detailPane.scrollTop = 0;
  }
}

function renderStudyDetail() {
  const words = studyQueue();
  if (words.length === 0) {
    refs.wordDetail.hidden = true;
    refs.emptyState.hidden = false;
    refs.emptyState.querySelector("h2").textContent = t("noStudyWords");
    refs.emptyState.querySelector("p").textContent = "";
    return;
  }
  const selectedIndex = Math.max(0, words.findIndex((word) => word.word === app.selectedWord?.word));
  const word = words[selectedIndex] || words[0];
  app.selectedWord = word;
  ensureWordDetail(word);
  refs.emptyState.hidden = true;
  refs.wordDetail.hidden = false;
  refs.wordDetail.replaceChildren(renderStudyCard(word, selectedIndex, words.length));
}

function renderDetailHeader(word) {
  const header = el("header", "detail-header");
  const titleRow = el("div", "detail-title-row");
  const title = el("div", "detail-title");
  title.append(el("h2", "", word.word || ""), el("span", "reading", word.reading || ""));
  const stats = el("div", "detail-stats");
  const examples = examplesForWord(word);
  const exampleCount = examples.length || Number(word.example_count || 0);
  stats.append(
    ...(word.level ? [statChip(word.level)] : []),
    statChip(`${t("count")} ${formatNumber(displayCount(word))}`),
    statChip(`${t("examples")} ${formatNumber(exampleCount)}`),
    statChip(studyCheckLabel(word)),
  );
  titleRow.append(title, stats);

  const meanings = el("div", "meaning-block");
  const mainMeaning = displayMeaningRaw(word);
  meanings.append(mainMeaning ? renderMeaningValue(word, "meaning-main") : el("div", "meaning-main", "—"));
  if (!mainMeaning) {
    meanings.append(el("div", "meaning-alt", t("missingMeaning")));
  }

  header.append(titleRow, meanings, renderStatusActions(word));
  return header;
}

function renderReaderContextPanel(word) {
  const selection = app.reader.selection;
  if (app.mode !== "read" || !selection || selection.word !== word.word) {
    return null;
  }
  const example = selection.example || {};
  const sourceClass = exampleSourceClass(example);
  const section = el("section", "reader-context-card");
  const top = el("div", "reader-context-top");
  top.append(el("h3", "section-title", t("readerContextTitle")));
  const actions = el("div", "reader-context-actions");
  const explain = el("button", "reader-explain-button", t("readerExplain"));
  explain.type = "button";
  const canExplain = canUseReaderAi();
  explain.disabled = !canExplain || app.reader.explanation?.status === "loading";
  if (!canExplain) {
    explain.title = t("readerExplainUnavailable");
  }
  explain.addEventListener("click", () => startReaderExplanation(word, selection));
  actions.append(explain);
  top.append(actions);
  section.append(top);
  section.append(el("small", `reader-context-reference reference reference-${sourceClass}`, formatReference(example)));
  section.append(renderReaderQuestionForm(word, selection));

  const explanation = renderReaderExplanation(selection);
  if (explanation) {
    section.append(explanation);
  }
  const answer = renderReaderQuestionAnswer(selection);
  if (answer) {
    section.append(answer);
  }
  return section;
}

function renderReaderMarkedWordsPanel() {
  const entries = readerMarkedWordsForCurrentUnit();
  const section = el("details", "reader-marked-card");
  section.open = app.reader.markedOpen;
  section.addEventListener("toggle", () => {
    app.reader.markedOpen = section.open;
  });
  const top = el("summary", "reader-marked-top");
  top.append(el("h3", "section-title", t("readerMarkedTitle")));
  top.append(el("span", "reader-marked-count", t("readerMarkedCount", { count: formatNumber(entries.length) })));
  section.append(top);
  const body = el("div", "reader-marked-body");
  if (entries.length === 0) {
    body.append(emptyMessage(t("readerMarkedEmpty")));
    section.append(body);
    return section;
  }
  const list = el("div", "reader-marked-list");
  entries.forEach(({ word, status, count, selection, lineKey }) => {
    const button = el("button", `reader-marked-chip ${status}`.trim());
    button.type = "button";
    button.title = [
      word.reading || "",
      stateLabels[status]?.[app.lang] || "",
      count > 1 ? `${formatNumber(count)}x` : "",
    ].filter(Boolean).join(" · ");
    button.append(
      el("span", "reader-marked-word", word.word || ""),
      el("span", "reader-marked-state", stateLabels[status]?.[app.lang] || ""),
    );
    button.addEventListener("click", () => {
      selectReaderWord(word.word, selection);
      scrollReaderLineIntoView(lineKey);
    });
    list.append(button);
  });
  body.append(list);
  section.append(body);
  return section;
}

function readerMarkedWordsForCurrentUnit() {
  const { unit } = currentReaderSelectionSource();
  if (!unit?.documents?.length) {
    return [];
  }
  const entries = new Map();
  unit.documents.forEach((document) => {
    asArray(document.lines).forEach((line, lineIndex) => {
      asArray(line.matches).forEach((match) => {
        const word = findWord(match.word);
        if (!word) {
          return;
        }
        const status = statusFor(word);
        if (!isActiveStudyStatus(status)) {
          return;
        }
        const current = entries.get(word.word) || {
          word,
          status,
          count: 0,
          selection: readerSelectionForLine(line, match, { document, lineIndex }),
          lineKey: readerLineDomKey(document, line, lineIndex),
        };
        current.status = status;
        current.count += 1;
        entries.set(word.word, current);
      });
    });
  });
  return [...entries.values()].sort(compareReaderMarkedWords);
}

function currentReaderSelectionSource() {
  const sourceType = app.reader.sourceType === "all" ? null : app.reader.sourceType;
  const groups = buildSourceGroups(sourceType);
  const source = groups.find((group) => group.key === app.reader.groupKey) || groups[0] || null;
  if (!source) {
    return { source: null, unit: null };
  }
  const units = readerUnitsForSource(source);
  const unit = units.find((item) => item.key === app.reader.documentKey) || units[0] || null;
  return { source, unit };
}

function scrollReaderLineIntoView(lineKey) {
  if (!lineKey) {
    return;
  }
  const line = refs.wordList.querySelector(`.reader-line[data-reader-line-key="${lineKey}"]`);
  if (!line) {
    return;
  }
  const documentDetails = line.closest(".reader-document");
  if (documentDetails) {
    documentDetails.open = true;
  }
  refs.wordList.querySelectorAll(".reader-line-target").forEach((node) => {
    node.classList.remove("reader-line-target");
  });
  line.classList.add("reader-line-target");
  line.scrollIntoView({ block: "center", behavior: "smooth" });
  window.setTimeout(() => {
    line.classList.remove("reader-line-target");
  }, 1600);
}

function compareReaderMarkedWords(left, right) {
  return readerMarkedStatusRank(left.status) - readerMarkedStatusRank(right.status)
    || compareKana(left.word, right.word);
}

function readerMarkedStatusRank(status) {
  return {
    learning: 0,
    uncertain: 1,
  }[status] ?? 4;
}

function isActiveStudyStatus(status) {
  return status === "learning" || status === "uncertain";
}

function canUseReaderAi() {
  const llm = app.maintenance.llm || {};
  return Boolean(
    app.maintenance.enabled
    && llm.api_key_configured
    && (llm.provider === "apple" || llm.model),
  );
}

function renderExplanationResult(explanation, loadingClass = "reader-explanation") {
  if (!explanation) {
    return null;
  }
  const block = el("div", `${loadingClass} ${explanation.status || ""}`.trim());
  if (explanation.status === "loading") {
    block.append(el("div", "annotation-line", t("readerExplainLoading")));
    return block;
  }
  if (explanation.status === "failed") {
    block.append(el("div", "annotation-line", t("readerExplainFailed", { error: explanation.error || "" })));
    return block;
  }
  const result = explanation.result || {};
  if (result.translation_zh) {
    block.append(el("div", "annotation-line translation-line", `${t("readerTranslation")}: ${result.translation_zh}`));
  }
  if (result.usage_note_zh) {
    block.append(el("div", "annotation-line", `${t("readerUsage")}: ${result.usage_note_zh}`));
  }
  return block.childNodes.length ? block : null;
}

function renderReaderExplanation(selection) {
  const explanation = app.reader.explanation;
  if (!explanation || explanation.key !== selection.key) {
    return null;
  }
  return renderExplanationResult(explanation);
}

function renderReaderQuestionForm(word, selection) {
  const form = el("form", "reader-question-form");
  const input = el("input", "reader-question-input");
  input.type = "text";
  input.placeholder = t("readerQuestionPlaceholder");
  input.disabled = !canUseReaderAi() || app.reader.question?.status === "loading";
  const button = el("button", "reader-question-submit", t("readerQuestionSubmit"));
  button.type = "submit";
  button.disabled = input.disabled;
  if (!canUseReaderAi()) {
    input.title = t("readerExplainUnavailable");
    button.title = t("readerExplainUnavailable");
  }
  form.append(input, button);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const question = input.value.trim();
    if (!question) {
      return;
    }
    startReaderQuestion(word, selection, question);
  });
  return form;
}

function renderReaderQuestionAnswer(selection) {
  const question = app.reader.question;
  if (!question || question.key !== selection.key) {
    return null;
  }
  const block = el("div", `reader-question-answer ${question.status || ""}`.trim());
  if (question.status === "loading") {
    block.append(el("div", "annotation-line", t("readerQuestionLoading")));
    return block;
  }
  if (question.status === "failed") {
    block.append(el("div", "annotation-line", t("readerQuestionFailed", { error: question.error || "" })));
    return block;
  }
  if (question.answer) {
    block.append(
      el("div", "annotation-line translation-line", `${t("readerQuestionAnswer")}: ${question.answer}`),
    );
  }
  return block.childNodes.length ? block : null;
}

async function startReaderExplanation(word, selection) {
  if (!selection) {
    return;
  }
  app.reader.explanation = {
    key: selection.key,
    status: "loading",
  };
  renderDetail();
  try {
    const payload = await api.explain({
      word: explanationWordPayload(word),
      example: selection.example,
    });
    app.reader.explanation = {
      key: selection.key,
      status: "succeeded",
      result: payload.explanation || {},
    };
  } catch (error) {
    app.reader.explanation = {
      key: selection.key,
      status: "failed",
      error: error.message || String(error),
    };
  }
  renderDetail();
}

async function startReaderQuestion(word, selection, question) {
  if (!selection) {
    return;
  }
  app.reader.question = {
    key: selection.key,
    status: "loading",
    prompt: question,
  };
  renderDetail();
  try {
    const payload = await api.explain({
      word: explanationWordPayload(word),
      example: selection.example,
      question,
    });
    app.reader.question = {
      key: selection.key,
      status: "succeeded",
      prompt: question,
      answer: payload.answer || "",
    };
  } catch (error) {
    app.reader.question = {
      key: selection.key,
      status: "failed",
      prompt: question,
      error: error.message || String(error),
    };
  }
  renderDetail();
}

function explanationWordPayload(word) {
  return {
    word: word.word || "",
    reading: word.reading || "",
    level: word.level || "",
    meaning_zh: word.meaning_zh || displayMeaningRaw(word) || "",
    meaning: word.meaning || "",
  };
}

function renderStudyCard(word, index, total) {
  const card = el("section", "study-card");
  const topLine = el("div", "study-topline");
  topLine.append(
    el("span", "study-progress", t("studyProgress", {
      current: formatNumber(index + 1),
      total: formatNumber(total),
    })),
    el("span", "study-hint", t("studyHint")),
  );

  const titleRow = el("div", "study-title-row");
  const title = el("div", "detail-title");
  title.append(el("h2", "", word.word || ""), el("span", "reading", word.reading || ""));
  const stats = el("div", "detail-stats");
  stats.append(
    ...(word.level ? [statChip(word.level)] : []),
    statChip(`${t("count")} ${formatNumber(displayCount(word))}`),
    statChip(`${t("examples")} ${formatNumber(examplesForWord(word).length)}`),
    statChip(studyKindLabel(word)),
    statChip(studyCheckLabel(word)),
  );
  titleRow.append(title, stats);
  card.append(topLine, titleRow);

  if (app.study.showAnswer) {
    const mainMeaning = displayMeaningRaw(word);
    const meanings = el("div", "study-answer-block");
    meanings.append(mainMeaning ? renderMeaningValue(word, "meaning-main") : el("div", "meaning-main", "—"));
    card.append(meanings);
    card.append(renderLexicalNotes(word));
  }

  card.append(renderStudyActions(word));
  card.append(renderExamples(word, {
    revealAnnotations: app.study.showAnswer,
  }));
  return card;
}

function renderStudyActions(word) {
  const actions = el("div", "study-actions");
  const check = el("button", "study-primary-action", t("studyCheckButton"));
  check.type = "button";
  check.addEventListener("click", () => {
    addStudyCheck(word);
  });

  const shaky = el("button", "study-secondary-action", t("studyAgain"));
  shaky.type = "button";
  shaky.addEventListener("click", () => {
    markStudyWord("learning");
  });

  const reveal = el("button", "study-answer-action", t(app.study.showAnswer ? "hideAnswer" : "revealAnswer"));
  reveal.type = "button";
  reveal.addEventListener("click", () => {
    app.study.showAnswer = !app.study.showAnswer;
    renderDetail();
  });

  const next = el("button", "study-next-action", t("nextWord"));
  next.type = "button";
  next.addEventListener("click", nextStudyWord);

  actions.append(check, shaky, reveal, next);
  return actions;
}

function renderStatusActions(word) {
  if (app.mode === "read") {
    return renderReaderStudyActions(word);
  }
  const wrap = el("div", "status-actions");
  ["learning", "uncertain", "known", "ignored", "none"].forEach((status) => {
    const button = el("button", "");
    button.type = "button";
    button.textContent = stateLabels[status][app.lang];
    button.classList.toggle("active", statusFor(word) === status);
    button.addEventListener("click", () => {
      setStatus(word, status);
      render();
    });
    wrap.append(button);
  });
  return wrap;
}

function renderReaderStudyActions(word) {
  const wrap = el("div", "status-actions reader-study-actions");
  const status = statusFor(word);
  [
    {
      label: t("readerAddStudy"),
      active: status === "learning" || status === "uncertain",
      className: "reader-study-primary",
      action: () => addWordToStudyFromReader(word),
    },
    {
      label: t("readerKnown"),
      active: status === "known",
      action: () => setStatus(word, "known"),
    },
    {
      label: t("readerIgnore"),
      active: status === "ignored",
      action: () => setStatus(word, "ignored"),
    },
  ].forEach((item) => {
    const button = el("button", item.className || "", item.label);
    button.type = "button";
    button.classList.toggle("active", item.active);
    button.addEventListener("click", () => {
      item.action();
      app.reader.preserveScrollOnRender = true;
      render();
    });
    wrap.append(button);
  });
  if (status !== "none") {
    const clear = el("button", "", t("readerClearMark"));
    clear.type = "button";
    clear.addEventListener("click", () => {
      setStatus(word, "none");
      app.reader.preserveScrollOnRender = true;
      render();
    });
    wrap.append(clear);
  }
  return wrap;
}

function addWordToStudyFromReader(word) {
  setStatus(word, "learning");
  scheduleStudyReview(word);
}

function selectWord(word, button) {
  const changedWord = app.selectedWord?.word !== word.word;
  app.selectedWord = word;
  app.study.showAnswer = false;
  refs.wordList.querySelectorAll(".word-row.active").forEach((row) => {
    row.classList.remove("active");
  });
  button.classList.add("active");
  renderDetail();
  if (changedWord) {
    resetDetailScroll();
  }
  renderMaintenance();
}

function setStudyMode(mode) {
  if (!MODE_VALUES.has(mode) || app.mode === mode) {
    return;
  }
  app.mode = mode;
  localStorage.setItem(STORAGE_MODE, app.mode);
  app.study.showAnswer = false;
  if (app.mode === "read") {
    hideSourcePanel();
    refs.maintenancePanel.hidden = true;
    refs.maintenanceToggle.classList.remove("active");
    app.selectedWord = null;
    clearReaderSelection();
  } else {
    clearReaderSelection();
    app.selectedWord = chooseInitialWord(currentWordSet());
  }
  render();
}

function updateStudyModeButtons() {
  refs.studyModeButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === app.mode);
  });
}

function nextStudyWord() {
  const words = studyQueue();
  if (words.length === 0) {
    app.selectedWord = null;
    render();
    return;
  }
  const currentIndex = words.findIndex((word) => word.word === app.selectedWord?.word);
  const nextIndex = currentIndex >= 0 ? (currentIndex + 1) % words.length : 0;
  app.selectedWord = words[nextIndex];
  app.study.showAnswer = false;
  render();
}

function markStudyWord(status) {
  const word = app.selectedWord;
  if (!word) {
    return;
  }
  const previousQueue = studyQueue();
  if (status === "known") {
    setStudyCount(word, STUDY_TARGET_COUNT);
  }
  setStatus(word, status);
  if (status === "learning" || status === "uncertain") {
    scheduleStudyReview(word);
  }
  advanceStudyQueue(previousQueue, word);
}

function addStudyCheck(word) {
  const previousQueue = studyQueue();
  const nextCount = Math.min(studyCountFor(word) + 1, STUDY_TARGET_COUNT);
  setStudyCount(word, nextCount);
  setStatus(word, nextCount >= STUDY_TARGET_COUNT ? "known" : "learning");
  if (nextCount < STUDY_TARGET_COUNT) {
    scheduleStudyReview(word);
  }
  advanceStudyQueue(previousQueue, word);
}

function advanceStudyQueue(previousQueue, word) {
  const currentIndex = previousQueue.findIndex((item) => item.word === word.word);
  const preferredNext = currentIndex >= 0 ? previousQueue[currentIndex + 1] : null;
  const nextQueue = studyQueue();
  app.selectedWord =
    (preferredNext && nextQueue.find((item) => item.word === preferredNext.word))
    || nextQueue.find((item) => item.word !== word.word)
    || nextQueue[0]
    || null;
  app.study.showAnswer = false;
  render();
}

async function startMaintenanceJob(taskOverride = null) {
  const task = taskOverride || maintenanceTask();
  app.maintenance.task = task;
  const spec = maintenanceJobSpec();
  try {
    const payload = await api.startMaintenanceJob(spec);
    app.maintenance.job = payload.job;
    app.maintenance.reloadedJobId = null;
    renderMaintenance();
    pollMaintenanceJob();
    return payload.job;
  } catch (error) {
    app.maintenance.job = {
      status: "failed",
      log: [String(error.message || error)],
    };
    renderMaintenance();
    return null;
  }
}

function pollMaintenanceJob() {
  if (app.maintenance.pollTimer) {
    clearInterval(app.maintenance.pollTimer);
  }
  refreshMaintenanceJob();
  app.maintenance.pollTimer = setInterval(refreshMaintenanceJob, 1500);
}

async function refreshMaintenanceJob() {
  try {
    const payload = await api.currentJob();
    app.maintenance.job = payload.job || null;
    renderMaintenance();
    const job = app.maintenance.job;
    if (!job || job.status === "running") {
      return;
    }
    if (app.maintenance.pollTimer) {
      clearInterval(app.maintenance.pollTimer);
      app.maintenance.pollTimer = null;
    }
    const clearsSourceNotice = app.sourceInventoryNoticeJobId === job.id;
    if (job.status === "succeeded" && job.result?.reload_corpus && app.maintenance.reloadedJobId !== job.id) {
      app.maintenance.reloadedJobId = job.id;
      await reloadCorpus();
    }
    if (clearsSourceNotice) {
      app.sourceInventoryBusy = false;
      app.sourceInventoryNoticeJobId = null;
      app.sourceInventoryNotice = job.status === "succeeded"
        ? ""
        : t("sourceInventoryDeleteFailed", { error: job.error || job.log?.at(-1) || "rebuild failed" });
      renderSourceInventory();
    }
  } catch (error) {
    app.maintenance.job = {
      status: "failed",
      log: [String(error.message || error)],
    };
    if (app.sourceInventoryBusy) {
      app.sourceInventoryBusy = false;
      app.sourceInventoryNoticeJobId = null;
      app.sourceInventoryNotice = t("sourceInventoryDeleteFailed", { error: error.message || String(error) });
    }
    renderMaintenance();
    renderSourceInventory();
  }
}

async function reloadCorpus() {
  const selectedWord = app.selectedWord?.word || "";
  app.wordDetailRequests.clear();
  app.sourceDetails.clear();
  app.sourceDetailRequests.clear();
  app.sourceDetailFailures.clear();
  app.corpus = await api.loadCorpusIndex();
  app.words = Array.isArray(app.corpus.words) ? app.corpus.words : [];
  await mergeRemoteStudyState();
  app.selectedWord = app.words.find((word) => word.word === selectedWord) || chooseInitialWord();
  render();
}

function renderExamples(word, options = {}) {
  const revealAnnotations = options.revealAnnotations ?? true;
  const section = el("section", "examples");
  const header = el("div", "examples-header");
  header.append(el("h3", "section-title", t("examples")));
  if (app.mode !== "read") {
    header.append(renderExampleColumnControl());
  }
  section.append(header);
  const examples = examplesForWord(word);
  if (examples.length === 0) {
    const message = word._detailLoading && !word._detailLoaded
      ? t("wordDetailLoading")
      : t("noExamples");
    section.append(emptyMessage(message));
    return section;
  }
  const columnCount = app.mode === "read" ? 1 : resolvedExampleColumnCount(app.exampleColumns);
  const grid = el("div", `examples-masonry columns-${columnCount}`);
  const columnNodes = Array.from({ length: columnCount }, () => el("div", "examples-column"));
  const columnWeights = Array.from({ length: columnCount }, () => 0);
  columnNodes.forEach((column) => grid.append(column));
  examples.forEach((example) => {
    const { item, weight } = renderExampleCard(word, example, {
      revealAnnotations,
    });
    const targetColumn = shortestColumnIndex(columnWeights);
    columnNodes[targetColumn].append(item);
    columnWeights[targetColumn] += weight;
  });
  section.append(grid);
  return section;
}

function renderExampleCard(word, example, options = {}) {
  const revealAnnotations = options.revealAnnotations ?? true;
  const allowAiExplain = app.mode !== "read" && (app.mode !== "study" || revealAnnotations);
  const sourceClass = exampleSourceClass(example);
  const item = el("div", `example example-${sourceClass}`);
  const lines = el("div", "example-lines");
  const beforeLines = contextPreview(example.context_before, "before");
  const afterLines = contextPreview(example.context_after, "after");
  appendContextBlock(lines, beforeLines, "before");
  const current = el("div", "example-current");
  appendHighlighted(current, example.sentence || "", example.matched_text || word.word);
  lines.append(current);
  appendContextBlock(lines, afterLines, "after");
  lines.append(renderExampleFooter(word, example, sourceClass, { allowAiExplain }));
  item.append(lines);
  const annotationBlock = renderExampleAnnotationBlock(word, example, {
    allowAiExplain,
    revealAnnotations,
  });
  if (annotationBlock) {
    item.append(annotationBlock);
  }
  return {
    item,
    weight: exampleCardWeight(example, beforeLines, afterLines),
  };
}

function renderExampleFooter(word, example, sourceClass, options = {}) {
  const footer = el("div", "example-footer");
  footer.append(el("small", `reference reference-${sourceClass}`, formatReference(example)));
  const actions = el("div", "example-footer-actions");
  if (options.allowAiExplain) {
    actions.append(renderExampleExplainButton(word, example, exampleExplanationKey(word, example)));
  }
  if (actions.childNodes.length > 0) {
    footer.append(actions);
  }
  return footer;
}

function resolvedExampleColumnCount(value) {
  if (value !== "auto") {
    return Math.trunc(clampNumber(Number(value), 1, 3));
  }
  const width = refs.wordDetail?.clientWidth || document.documentElement.clientWidth || 0;
  return Math.trunc(clampNumber(Math.floor((width + 12) / 402), 1, 3));
}

function shortestColumnIndex(weights) {
  let index = 0;
  for (let candidate = 1; candidate < weights.length; candidate += 1) {
    if (weights[candidate] < weights[index]) {
      index = candidate;
    }
  }
  return index;
}

function exampleCardWeight(example, beforeLines, afterLines) {
  const text = [
    ...beforeLines,
    example.sentence || "",
    ...afterLines,
    formatReference(example),
    example.translation_zh || "",
    example.usage_note_zh || "",
  ].join("\n");
  return 1 + beforeLines.length + afterLines.length + Math.ceil(text.length / 34);
}

function renderExampleAnnotationBlock(word, example, options = {}) {
  const allowAiExplain = options.allowAiExplain ?? true;
  const revealAnnotations = options.revealAnnotations ?? true;
  const hasTranslation = revealAnnotations && example.translation_zh;
  const hasUsageNote = revealAnnotations && example.usage_note_zh;
  const key = exampleExplanationKey(word, example);
  const explanation = app.exampleExplanations[key];
  const explanationBlock = allowAiExplain ? renderExplanationResult(explanation, "example-explanation") : null;
  if (!hasTranslation && !hasUsageNote && !explanationBlock) {
    return null;
  }
  const block = el("div", "annotation-block");
  if (hasTranslation || hasUsageNote) {
    const lines = el("div", "annotation-lines");
    if (hasTranslation) {
      lines.append(el("div", "annotation-line translation-line", `${t("translation")}: ${example.translation_zh}`));
    }
    if (hasUsageNote) {
      lines.append(el("div", "annotation-line", `${t("usageNote")}: ${example.usage_note_zh}`));
    }
    block.append(lines);
  }
  if (explanationBlock) {
    block.append(explanationBlock);
  }
  return block;
}

function renderExampleExplainButton(word, example, key) {
  const button = el("button", "example-explain-button", "✨");
  const canExplain = canUseReaderAi();
  button.type = "button";
  button.title = t(canExplain ? "exampleExplainTitle" : "readerExplainUnavailable");
  button.setAttribute("aria-label", button.title);
  button.disabled = !canExplain || app.exampleExplanations[key]?.status === "loading";
  button.addEventListener("click", () => startExampleExplanation(word, example, key));
  return button;
}

async function startExampleExplanation(word, example, key) {
  app.exampleExplanations[key] = {
    status: "loading",
  };
  renderDetail();
  try {
    const payload = await api.explain({
      word: explanationWordPayload(word),
      example,
    });
    app.exampleExplanations[key] = {
      status: "succeeded",
      result: payload.explanation || {},
    };
  } catch (error) {
    app.exampleExplanations[key] = {
      status: "failed",
      error: error.message || String(error),
    };
  }
  renderDetail();
}

function renderExampleColumnControl() {
  const label = el("label", "columns-control");
  label.append(el("span", "", t("exampleColumns")));
  const select = el("select", "");
  [
    ["auto", t("exampleColumnsAuto")],
    ["1", "1"],
    ["2", "2"],
    ["3", "3"],
  ].forEach(([value, textValue]) => {
    const option = el("option", "", textValue);
    option.value = value;
    option.selected = app.exampleColumns === value;
    select.append(option);
  });
  select.addEventListener("change", (event) => {
    app.exampleColumns = event.target.value;
    localStorage.setItem(STORAGE_EXAMPLE_COLUMNS, app.exampleColumns);
    renderDetail();
  });
  label.append(select);
  return label;
}

function appendContextBlock(parent, lines, position) {
  const visibleLines = lines.filter(Boolean);
  if (visibleLines.length === 0) {
    return;
  }
  const block = el("div", `example-context ${position}`);
  visibleLines.forEach((line, index) => {
    const prefix = position === "before" && index === 0 ? "…" : "";
    const suffix = position === "after" && index === visibleLines.length - 1 ? "…" : "";
    block.append(el("div", "subtitle-cue", `${prefix}${line}${suffix}`));
  });
  parent.append(block);
}

function appendHighlighted(parent, value, match) {
  if (!value) {
    return;
  }
  if (!match || !value.includes(match)) {
    parent.append(value);
    return;
  }
  const index = value.indexOf(match);
  parent.append(value.slice(0, index));
  parent.append(el("mark", "", match));
  parent.append(value.slice(index + match.length));
}

function filteredWords() {
  const terms = searchTerms(app.query);
  const scored = [];
  app.words.forEach((word) => {
    if (app.level !== "all" && word.level !== app.level) {
      return;
    }
    const status = statusFor(word);
    if (app.status !== "all" && status !== app.status) {
      return;
    }
    if (app.source !== "all" && sourceCount(word, app.source) === 0) {
      return;
    }
    if (!terms.length) {
      scored.push({ word, score: 0 });
      return;
    }
    const score = searchScore(word, terms);
    if (score > 0) {
      scored.push({ word, score });
    }
  });
  scored.sort((left, right) => {
    if (terms.length && left.score !== right.score) {
      return right.score - left.score;
    }
    return compareWords(left.word, right.word);
  });
  return scored.map((item) => item.word);
}

function currentWordSet() {
  return app.mode === "study" ? studyQueue() : filteredWords();
}

function studyQueue() {
  const eligible = filteredWords()
    .filter(isStudyEligibleWord)
    .filter((word) => isStudyReviewDueWord(word) || isStudyNewWord(word));
  const today = todayKey();
  const session = app.study.session?.date === today
    ? app.study.session
    : { date: today, words: [] };
  const byWord = new Map(eligible.map((word) => [word.word, word]));
  const queued = [];
  const seen = new Set();
  session.words.forEach((wordText) => {
    const word = byWord.get(wordText);
    if (!word || seen.has(word.word)) {
      return;
    }
    queued.push(word);
    seen.add(word.word);
  });

  const reviewCandidates = eligible.filter(isStudyReviewDueWord).sort(compareReviewStudyWords);
  const newCandidates = eligible.filter(isStudyNewWord).sort(compareNewStudyWords);
  const candidates = [...reviewCandidates, ...newCandidates];
  candidates.forEach((word) => {
    if (queued.length >= DAILY_STUDY_LIMIT || seen.has(word.word)) {
      return;
    }
    queued.push(word);
    seen.add(word.word);
  });

  const nextSession = { date: today, words: queued.map((word) => word.word) };
  if (!sameStudySession(app.study.session, nextSession)) {
    app.study.session = nextSession;
    writeStudySession(nextSession);
  }
  return queued;
}

function isStudyEligibleWord(word) {
  const status = statusFor(word);
  return status !== "ignored"
    && status !== "known"
    && (examplesForWord(word).length > 0 || Number(word.example_count || 0) > 0);
}

function isStudyReviewWord(word) {
  const status = statusFor(word);
  const count = studyCountFor(word);
  return count > 0 && count < STUDY_TARGET_COUNT
    || status === "learning"
    || status === "uncertain";
}

function isStudyReviewDueWord(word) {
  return isStudyReviewWord(word) && studyDueDateFor(word) <= todayKey();
}

function isStudyNewWord(word) {
  return statusFor(word) === "none" && studyCountFor(word) === 0;
}

function compareReviewStudyWords(left, right) {
  return studyDueDateFor(left).localeCompare(studyDueDateFor(right))
    || studyCountFor(left) - studyCountFor(right)
    || (right.count || 0) - (left.count || 0)
    || compareKana(left, right);
}

function compareNewStudyWords(left, right) {
  return (right.count || 0) - (left.count || 0)
    || compareKana(left, right);
}

function studyQueueBreakdown(words) {
  return words.reduce((counts, word) => {
    if (isStudyReviewWord(word)) {
      counts.review += 1;
    } else {
      counts.new += 1;
    }
    return counts;
  }, { review: 0, new: 0 });
}

function studyKindLabel(word) {
  return isStudyReviewWord(word) ? t("studyReview") : t("studyNew");
}

function compareWords(left, right) {
  if (app.sort === "word") {
    return compareKana(left, right);
  }
  if (app.sort === "level") {
    return (left.level_number || 999) - (right.level_number || 999) || (right.count || 0) - (left.count || 0);
  }
  return (right.count || 0) - (left.count || 0) || compareKana(left, right);
}

function chooseInitialWord(words = app.words) {
  if (app.selectedWord && words.some((word) => word.word === app.selectedWord.word)) {
    return app.selectedWord;
  }
  return words[0] || null;
}

function examplesForWord(word) {
  const examples = Array.isArray(word.examples) ? word.examples : [];
  if (app.source === "all") {
    return examples;
  }
  return examples.filter((example) => example.source_type === app.source);
}

function displayCount(word) {
  if (app.source === "all") {
    return word.count || 0;
  }
  return sourceCount(word, app.source);
}

function sourceCount(word, sourceType) {
  const counts = word.source_type_counts || {};
  return counts[sourceType] || 0;
}

function persistReaderPositions() {
  const entries = Object.entries(app.reader.positions)
    .sort((left, right) => (right[1].updatedAt || 0) - (left[1].updatedAt || 0))
    .slice(0, 200);
  app.reader.positions = Object.fromEntries(entries);
  localStorage.setItem(STORAGE_READER_POSITIONS, JSON.stringify(app.reader.positions));
}

function statusDot(status) {
  const dot = el("span", `status-dot ${status === "none" ? "" : status}`.trim());
  dot.textContent = stateLabels[status]?.symbol || "·";
  dot.title = stateLabels[status]?.[app.lang] || "";
  return dot;
}

function renderLoadError(error) {
  refs.wordDetail.hidden = true;
  refs.emptyState.hidden = false;
  refs.emptyState.querySelector("h2").textContent = t("loadErrorTitle");
  refs.emptyState.querySelector("p").textContent = `${t("loadErrorBody")} (${error.message})`;
}

function t(key, values = {}) {
  let value = text[app.lang]?.[key] || text.zh[key] || key;
  Object.entries(values).forEach(([name, replacement]) => {
    value = value.replace(`{${name}}`, replacement);
  });
  return value;
}
