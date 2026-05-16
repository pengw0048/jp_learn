const {
  STORAGE_LANG,
  STORAGE_MODE,
  STORAGE_READER_FURIGANA,
  STORAGE_READER_POSITIONS,
  DAILY_STUDY_LIMIT,
  STUDY_TARGET_COUNT,
  MODE_VALUES,
  READER_WORD_LIST_VALUES,
  readStatuses,
  readStudyCounts,
  todayKey,
  readStudySession,
  readStudySchedule,
  readExampleColumns,
  readSplitRatios,
  readMode,
  readReaderWordList,
  readReaderFurigana,
  readReaderPositions,
  readTtsProvider,
  readTtsBrowserVoice,
  readTtsVoicevoxSpeaker,
  readTtsRate,
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

const text = window.JPCORPUS_TEXT;
const {
  configMissingLabels,
  configServiceLabel,
  llmInputState,
} = window.JPCORPUS_CONFIG;


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
    showFurigana: readReaderFurigana(),
    selection: null,
    explanation: null,
    question: null,
    speechStartKey: null,
    controlsOpen: false,
    markedOpen: false,
    preserveScrollOnRender: false,
    positions: readReaderPositions(),
    positionKey: null,
    positionSaveTimer: null,
    tts: {
      playing: false,
      preparing: false,
      stopRequested: false,
      lineKey: null,
      runId: 0,
    },
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
    pollIntervalMs: null,
    pollInFlight: false,
    reloadedJobId: null,
    pendingReloadJob: null,
    syncNotice: "",
    syncApplying: false,
    syncError: "",
  },
  tts: {
    provider: readTtsProvider(),
    browserVoice: readTtsBrowserVoice(),
    voicevoxSpeaker: readTtsVoicevoxSpeaker(),
    rate: readTtsRate(),
    browserVoices: [],
    voicevoxSpeakers: [],
    loading: false,
    error: "",
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
  ttsProviderButtons: document.querySelectorAll("[data-tts-provider]"),
  ttsBrowserVoiceField: $("#tts-browser-voice-field"),
  ttsBrowserVoice: $("#tts-browser-voice"),
  ttsVoicevoxSpeakerField: $("#tts-voicevox-speaker-field"),
  ttsVoicevoxSpeaker: $("#tts-voicevox-speaker"),
  ttsRate: $("#tts-rate"),
  ttsRateValue: $("#tts-rate-value"),
  ttsPreview: $("#tts-preview"),
  ttsStatus: $("#tts-status"),
  maintenanceProgress: $("#maintenance-progress"),
  maintenanceProgressFill: $("#maintenance-progress-fill"),
  maintenanceProgressLabel: $("#maintenance-progress-label"),
  maintenanceStatus: $("#maintenance-status"),
  maintenanceLog: $("#maintenance-log"),
  corpusSyncBanner: $("#corpus-sync-banner"),
  corpusSyncMessage: $("#corpus-sync-message"),
  corpusSyncApply: $("#corpus-sync-apply"),
};
const {
  maintenanceJobSpec,
  maintenanceStatusLabel,
  maintenanceTask,
  renderMaintenanceProgress,
  visibleMaintenanceJob,
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
  stopAllSpeech,
  storageMode: STORAGE_MODE,
  strong,
  t,
});
const {
  applyPendingCorpusReload,
  pollMaintenanceJob,
  refreshMaintenanceJob,
  renderCorpusSyncBanner,
  startMaintenanceStatusSync,
} = window.JPCORPUS_SYNC.createCorpusSyncHelpers({
  api,
  app,
  refs,
  reloadCorpus,
  renderMaintenance,
  renderSourceInventory,
  shouldDeferCorpusReload: () => app.mode === "read",
  t,
});
const {
  applyWorkspaceSplit,
  bindSplitResizer,
  updateWorkspaceMode,
} = window.JPCORPUS_LAYOUT.createLayoutHelpers({
  app,
  clampNumber,
  refs,
  storage: window.JPCORPUS_STORAGE,
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
  setReaderSpeechStartLine,
  startReaderSpeechFromLine,
  statusFor,
  strong,
  t,
});
const {
  currentReaderScrollTop,
  currentReaderSelectionSource,
  readerPositionKey,
  readerUnitsForSource,
  readerWordSet,
  renderReaderModeControls,
  renderReaderModeSummary,
  saveReaderPosition,
} = window.JPCORPUS_READER_MODE.createReaderModeHelpers({
  app,
  asArray,
  buildSourceGroups,
  cleanSourceFileLabel,
  compareNullableNumbers,
  compareReaderDocuments,
  el,
  findWord,
  formatEpisodeLabel,
  formatNumber,
  isActiveStudyStatus,
  readerDocumentKey,
  readerDocumentLabel,
  readerDocumentsForSource,
  readerMarkedWordsForCurrentUnit,
  refs,
  render,
  renderReaderQuickActions,
  sourceDocumentLineCount,
  sourceLabel,
  statusFor,
  storage: window.JPCORPUS_STORAGE,
  studyQueue,
  t,
  todayKey,
  clearReaderSelection,
  persistReaderPositions,
  stopAllSpeech,
});
const {
  bindTtsSettings,
  prepareSpeech,
  renderSpeakButton,
  renderTtsSettings,
  speakPreparedText,
  speechTextForWord,
  stopSpeech,
} = window.JPCORPUS_TTS.createTtsHelpers({
  api,
  app,
  el,
  refs,
  storage: window.JPCORPUS_STORAGE,
  t,
});
const {
  canUseReaderAi,
  explanationWordPayload,
  renderExplanationResult,
  renderReaderExplanation,
  renderReaderQuestionAnswer,
  renderReaderQuestionForm,
  startReaderExplanation,
} = window.JPCORPUS_AI.createAiHelpers({
  api,
  app,
  displayMeaningRaw,
  el,
  renderDetail,
  t,
});
const {
  appendHighlighted,
  renderExamples,
} = window.JPCORPUS_EXAMPLES.createExampleHelpers({
  api,
  app,
  canUseReaderAi,
  clampNumber,
  contextPreview,
  el,
  emptyMessage,
  exampleExplanationKey,
  exampleSourceClass,
  examplesForWord,
  explanationWordPayload,
  formatReference,
  refs,
  renderDetail,
  renderExplanationResult,
  renderSpeakButton,
  scheduleStudyReview,
  setStatus,
  statusFor,
  storage: window.JPCORPUS_STORAGE,
  t,
});
const {
  renderDetailHeader,
  renderStudyCard,
} = window.JPCORPUS_DETAIL.createDetailHelpers({
  app,
  displayCount,
  displayMeaningRaw,
  el,
  examplesForWord,
  formatNumber,
  render,
  renderExamples,
  renderLexicalNotes,
  renderMeaningValue,
  renderSpeakButton,
  scheduleStudyReview,
  setStatus,
  speechTextForWord,
  statChip,
  stateLabels,
  statusFor,
  studyActions: {
    addStudyCheck,
    markStudyWord,
    nextStudyWord,
  },
  studyCheckLabel,
  studyCountFor,
  studyKindLabel,
  studyTargetCount: STUDY_TARGET_COUNT,
  t,
});

let remoteStudyRefreshInFlight = false;
init();

async function init() {
  bindControls();
  bindExternalStateRefresh();
  applyLanguage();
  await loadMaintenanceStatus();
  try {
    app.corpus = await api.loadCorpusIndex();
    app.words = Array.isArray(app.corpus.words) ? app.corpus.words : [];
    await mergeRemoteStudyState({ preferRemote: true });
    app.selectedWord = chooseInitialWord(currentWordSet());
    render();
    if (app.maintenance.enabled) {
      startMaintenanceStatusSync(app.maintenance.job?.status === "running" ? 1500 : 6000);
    }
  } catch (error) {
    renderLoadError(error);
  }
}

function bindExternalStateRefresh() {
  window.addEventListener("focus", refreshExternalState);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      stopAllSpeech();
      return;
    }
    refreshExternalState();
  });
  window.addEventListener("pagehide", stopAllSpeech);
}

function refreshExternalState() {
  refreshRemoteStudyState();
  refreshMaintenanceJob({ quiet: true });
}

async function refreshRemoteStudyState() {
  if (!app.corpus || remoteStudyRefreshInFlight) {
    return;
  }
  remoteStudyRefreshInFlight = true;
  try {
    const changed = await mergeRemoteStudyState({ preferRemote: true });
    if (changed) {
      if (app.mode === "read") {
        app.reader.preserveScrollOnRender = true;
      }
      render();
    }
  } finally {
    remoteStudyRefreshInFlight = false;
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
    setMaintenanceOpen(refs.maintenancePanel.hidden);
    renderMaintenance();
  });
  refs.maintenanceClose.addEventListener("click", () => {
    setMaintenanceOpen(false);
  });
  refs.maintenanceActionButtons.forEach((button) => {
    button.addEventListener("click", () => startMaintenanceJob(button.dataset.maintenanceTask));
  });
  refs.sourcePanelClose.addEventListener("click", hideSourcePanel);
  refs.configSave.addEventListener("click", saveConfig);
  refs.corpusSyncApply.addEventListener("click", applyPendingCorpusReload);
  bindTtsSettings();
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
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && app.maintenance.enabled) {
      refreshMaintenanceJob({ quiet: true });
    }
  });
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

function setMaintenanceOpen(open) {
  refs.maintenancePanel.hidden = !open;
  refs.maintenanceToggle.classList.toggle("active", open);
  if (open) {
    hideSourcePanel();
  }
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
    if (app.maintenance.job?.status === "succeeded" && app.maintenance.job.result?.reload_corpus) {
      app.maintenance.reloadedJobId = app.maintenance.job.id;
    }
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
    renderCorpusSyncBanner();
  } catch {
    app.maintenance.enabled = false;
    renderMaintenance();
    renderCorpusSyncBanner();
  }
}

function renderMaintenance() {
  if (!refs.maintenancePanel) {
    return;
  }
  renderConfigStatus();
  renderLlmConfigFields();
  renderTtsSettings();
  const task = maintenanceTask();
  const job = app.maintenance.job;
  const visibleJob = visibleMaintenanceJob(job);
  refs.maintenanceToggle.disabled = !app.maintenance.enabled;
  refs.maintenanceActionButtons.forEach((button) => {
    button.disabled = !app.maintenance.enabled || job?.status === "running";
    button.classList.toggle("active", button.dataset.maintenanceTask === task && job?.status === "running");
  });
  refs.maintenanceStatus.textContent = job ? maintenanceStatusLabel(job) : t("maintenanceIdle");
  renderMaintenanceProgress(visibleJob);
  refs.maintenanceLog.textContent = visibleJob?.log?.join("\n") || "";
  renderCorpusSyncBanner();
}

function renderLlmConfigFields() {
  const state = llmInputState(refs.configLlmProvider.value, t);
  [refs.configLlmBaseUrl, refs.configLlmModel, refs.configLlmApiKey].forEach((input) => {
    input.disabled = state.disabled;
    input.placeholder = state.placeholder;
  });
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
      const missing = configMissingLabels(service, t).join(", ");
      item.append(
        strong(configServiceLabel(service, t)),
        el(
          "span",
          "",
          service.configured
            ? t("configReady")
            : t("configMissing", { keys: missing }),
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
  stopAllSpeech();
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
    const messageKey = app.words.length === 0
      ? "emptyCorpusList"
      : app.mode === "study"
        ? "noStudyWords"
        : "noWords";
    refs.wordList.replaceChildren(emptyMessage(t(messageKey)));
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
  const detailDocuments = selectedUnit?.documents || selected.sourceDocuments || [];
  const detailsReady = sourceDetailsReady(detailDocuments);
  refs.resultCount.replaceChildren(renderReaderModeControls(groups, selected, units, selectedUnit, detailsReady));
  if (!detailsReady) {
    ensureSourceDetails(detailDocuments);
  }

  const pane = el("div", "reader-mode-pane");
  const scroller = el("div", "reader-mode-scroll");
  const positionKey = readerPositionKey(selected, selectedUnit);
  app.reader.positionKey = positionKey;
  scroller.addEventListener("click", clearReaderWordSelectionFromBlank);
  scroller.addEventListener("scroll", () => saveReaderPosition(positionKey, scroller), { passive: true });
  const summaryNode = renderReaderModeSummary(selected, selectedUnit);
  scroller.append(...[
    summaryNode,
    renderReaderMarkedWordsPanel(),
    detailsReady
      ? renderSourceReader(selected, {
        full: true,
        wordSet: readerWords,
        documents: selectedUnit?.documents || [],
      })
      : emptyMessage(t("sourceDetailLoading")),
  ].filter(Boolean));
  pane.append(scroller);
  refs.wordList.replaceChildren(pane);
  const restoredScrollTop = previousScrollTop ?? (app.reader.positions[positionKey]?.scrollTop || 0);
  const nextScroller = refs.wordList.querySelector(".reader-mode-scroll");
  if (nextScroller && restoredScrollTop > 0) {
    nextScroller.scrollTop = restoredScrollTop;
  }
  app.reader.preserveScrollOnRender = false;
  updateReaderActiveTokens();
  updateReaderSpeechUi();
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

function renderReaderQuickActions(detailsReady) {
  const actions = el("div", "reader-quick-actions");
  actions.append(renderReaderFuriganaButton(), renderReaderSpeechButton(detailsReady));
  return actions;
}

function renderReaderFuriganaButton() {
  const button = el(
    "button",
    `reader-furigana-button${app.reader.showFurigana ? " active" : ""}`,
    t("readerFuriganaOn"),
  );
  button.type = "button";
  button.setAttribute("aria-pressed", app.reader.showFurigana ? "true" : "false");
  button.title = t(app.reader.showFurigana ? "readerFuriganaDisableHint" : "readerFuriganaEnableHint");
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    app.reader.showFurigana = !app.reader.showFurigana;
    try {
      localStorage.setItem(STORAGE_READER_FURIGANA, app.reader.showFurigana ? "on" : "off");
    } catch {
      // Keep the in-memory toggle working even if storage is unavailable.
    }
    app.reader.preserveScrollOnRender = true;
    render();
  });
  return button;
}

function renderReaderSpeechButton(enabled) {
  const button = el(
    "button",
    `reader-speech-button${app.reader.tts.playing ? " active" : ""}`,
    readerSpeechButtonLabel(),
  );
  button.type = "button";
  button.disabled = !enabled && !app.reader.tts.playing;
  button.setAttribute("aria-pressed", app.reader.tts.playing ? "true" : "false");
  button.title = t(app.reader.speechStartKey ? "readerReadFromSelectedHint" : "readerReadAloudHint");
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    if (app.reader.tts.playing) {
      stopReaderSpeech();
    } else {
      startReaderSpeech();
    }
  });
  return button;
}

function readerSpeechButtonLabel() {
  if (app.reader.tts.preparing) {
    return t("readerPreparingSpeech");
  }
  return app.reader.tts.playing ? t("readerStopReading") : t("readerReadAloud");
}

function startReaderSpeechFromLine(lineKey, options = {}) {
  startReaderSpeech(lineKey, { singleLine: options.singleLine === true });
}

async function startReaderSpeech(startKey = null, options = {}) {
  if (app.reader.tts.playing) {
    stopReaderSpeech();
  }
  const runId = app.reader.tts.runId + 1;
  app.reader.tts.runId = runId;
  let lines = currentReaderSpeechLines(startKey || app.reader.speechStartKey || firstVisibleReaderLineKey());
  if (options.singleLine) {
    lines = lines.slice(0, 1);
  }
  if (lines.length === 0) {
    return;
  }
  app.reader.tts.playing = true;
  app.reader.tts.preparing = true;
  app.reader.tts.stopRequested = false;
  app.reader.tts.lineKey = lines[0].key;
  markReaderSpeechStart(lines[0].key);
  updateReaderSpeechUi();
  let pendingPrefetch = null;
  let pendingPrefetchKey = "";
  const beginPrefetch = (line) => {
    if (!line || app.tts.provider !== "voicevox") {
      pendingPrefetch = null;
      pendingPrefetchKey = "";
      return;
    }
    if (pendingPrefetchKey === line.key) {
      return;
    }
    pendingPrefetchKey = line.key;
    pendingPrefetch = prefetchReaderSpeechLine(line, runId);
  };
  try {
    for (let index = 0; index < lines.length; index += 1) {
      const line = lines[index];
      if (!isReaderSpeechRunActive(runId)) {
        break;
      }
      let prepared = null;
      app.reader.tts.preparing = true;
      setReaderSpeakingLine(line.key);
      if (pendingPrefetch && pendingPrefetchKey === line.key) {
        const result = await pendingPrefetch;
        if (!isReaderSpeechRunActive(runId)) {
          break;
        }
        prepared = result?.prepared || null;
        pendingPrefetch = null;
        pendingPrefetchKey = "";
      }
      const ok = await speakPreparedText(prepared, line.text, {
        awaitEnd: true,
        isCancelled: () => !isReaderSpeechRunActive(runId),
        onStart: () => {
          if (!isReaderSpeechRunActive(runId)) {
            return;
          }
          app.reader.tts.preparing = false;
          setReaderSpeakingLine(line.key);
          if (!options.singleLine) {
            beginPrefetch(lines[index + 1]);
          }
        },
        onEnd: () => {
          if (isReaderSpeechRunCurrent(runId) && app.reader.tts.lineKey === line.key) {
            setReaderSpeakingLine(null);
          }
        },
      });
      if (!ok || !isReaderSpeechRunActive(runId)) {
        break;
      }
    }
  } finally {
    if (!isReaderSpeechRunCurrent(runId)) {
      return;
    }
    app.reader.tts.playing = false;
    app.reader.tts.preparing = false;
    app.reader.tts.stopRequested = false;
    setReaderSpeakingLine(null);
  }
}

function prefetchReaderSpeechLine(line, runId) {
  return prepareSpeech(line.text, {
    isCancelled: () => !isReaderSpeechRunActive(runId),
  })
    .then((prepared) => ({
      key: line.key,
      prepared,
    }))
    .catch(() => ({
      key: line.key,
      prepared: null,
    }));
}

function stopReaderSpeech() {
  if (!app.reader.tts.playing && !app.reader.tts.preparing && !app.reader.tts.lineKey) {
    return;
  }
  app.reader.tts.runId += 1;
  app.reader.tts.stopRequested = true;
  stopSpeech();
  app.reader.tts.playing = false;
  app.reader.tts.preparing = false;
  setReaderSpeakingLine(null);
}

function stopAllSpeech() {
  if (readerSpeechActive()) {
    stopReaderSpeech();
    return;
  }
  stopSpeech();
}

function readerSpeechActive() {
  return app.reader.tts.playing || app.reader.tts.preparing || Boolean(app.reader.tts.lineKey);
}

function isReaderSpeechRunCurrent(runId) {
  return app.reader.tts.runId === runId;
}

function isReaderSpeechRunActive(runId) {
  return isReaderSpeechRunCurrent(runId) && !app.reader.tts.stopRequested;
}

function currentReaderSpeechLines(startKey = null) {
  const lines = [...refs.wordList.querySelectorAll(".reader-mode-scroll .reader-line")]
    .map((row) => ({
      key: row.dataset.readerLineKey || "",
      text: row.dataset.readerLineText || row.querySelector(".reader-line-text")?.textContent || "",
    }))
    .map((line) => ({
      ...line,
      text: line.text.replace(/\s+/g, " ").trim(),
    }))
    .filter((line) => line.key && line.text);
  if (!startKey) {
    return lines;
  }
  const index = lines.findIndex((line) => line.key === startKey);
  return index >= 0 ? lines.slice(index) : lines;
}

function firstVisibleReaderLineKey() {
  const scroller = refs.wordList.querySelector(".reader-mode-scroll");
  if (!scroller) {
    return null;
  }
  const scrollerRect = scroller.getBoundingClientRect();
  const top = scrollerRect.top + 8;
  const bottom = scrollerRect.bottom - 8;
  const rows = [...scroller.querySelectorAll(".reader-line")];
  const row = rows.find((line) => {
    const rect = line.getBoundingClientRect();
    const visibleHeight = Math.min(rect.bottom, bottom) - Math.max(rect.top, top);
    return visibleHeight >= Math.min(rect.height * 0.45, 28);
  }) || rows.find((line) => {
    const rect = line.getBoundingClientRect();
    return rect.bottom > top && rect.top < bottom;
  });
  return row?.dataset.readerLineKey || null;
}

function markReaderSpeechStart(lineKey) {
  const row = lineKey
    ? refs.wordList.querySelector(`.reader-line[data-reader-line-key="${lineKey}"]`)
    : null;
  if (!row) {
    return;
  }
  row.classList.add("reader-line-speech-start");
  window.setTimeout(() => {
    row.classList.remove("reader-line-speech-start");
  }, 1400);
}

function setReaderSpeechStartLine(lineKey) {
  app.reader.speechStartKey = lineKey || null;
  updateReaderSpeechUi();
}

function setReaderSpeakingLine(lineKey) {
  app.reader.tts.lineKey = lineKey || null;
  updateReaderSpeechUi();
  if (lineKey) {
    const row = refs.wordList.querySelector(`.reader-line[data-reader-line-key="${lineKey}"]`);
    row?.scrollIntoView({ block: "nearest" });
  }
}

function updateReaderSpeechUi() {
  refs.wordList.querySelectorAll(".reader-line-speaking").forEach((row) => {
    row.classList.remove("reader-line-speaking");
  });
  refs.wordList.querySelectorAll(".reader-line-speech-anchor").forEach((row) => {
    row.classList.remove("reader-line-speech-anchor");
  });
  if (app.reader.speechStartKey) {
    const row = refs.wordList.querySelector(`.reader-line[data-reader-line-key="${app.reader.speechStartKey}"]`);
    if (row) {
      row.classList.add("reader-line-speech-anchor");
    } else {
      app.reader.speechStartKey = null;
    }
  }
  if (app.reader.tts.lineKey) {
    const row = refs.wordList.querySelector(`.reader-line[data-reader-line-key="${app.reader.tts.lineKey}"]`);
    row?.classList.add("reader-line-speaking");
  }
  document.querySelectorAll(".reader-speech-button").forEach((button) => {
    button.classList.toggle("active", app.reader.tts.playing);
    button.setAttribute("aria-pressed", app.reader.tts.playing ? "true" : "false");
    button.title = t(app.reader.speechStartKey ? "readerReadFromSelectedHint" : "readerReadAloudHint");
    button.textContent = readerSpeechButtonLabel();
  });
  document.querySelectorAll(".reader-line-speech-button").forEach((button) => {
    const active = Boolean(app.reader.tts.lineKey) && button.dataset.readerSpeechLineKey === app.reader.tts.lineKey;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
  });
}

function clearReaderWordSelectionFromBlank(event) {
  if (event.target instanceof Element && event.target.closest(".reader-token, summary, button, select, input, textarea, label, a")) {
    return;
  }
  if (event.target instanceof Element && !event.target.closest(".reader-line")) {
    setReaderSpeechStartLine(null);
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

function readerWordAllowed(wordText, wordSet) {
  return !wordSet || wordSet.has(wordText);
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
    if (app.words.length === 0) {
      renderEmptyState("emptyCorpusTitle", "emptyCorpusBody", "emptyCorpusAction");
    } else {
      renderEmptyState(app.mode === "read" ? "readerNoSelection" : "noWords");
    }
    return;
  }
  refs.emptyState.hidden = true;
  refs.wordDetail.hidden = false;
  ensureWordDetail(word);
  const nodes = [renderDetailHeader(word)];
  const readerContext = renderReaderContextPanel(word);
  if (readerContext) {
    nodes.push(readerContext);
  }
  nodes.push(renderLexicalNotes(word));
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
    if (app.words.length === 0) {
      renderEmptyState("emptyCorpusTitle", "emptyCorpusBody", "emptyCorpusAction");
    } else {
      renderEmptyState("noStudyWords");
    }
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
  actions.append(renderSpeakButton(example.sentence || word.word, "tts-button reader-context-tts-button"));
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
  if (entries.length === 0) {
    return null;
  }
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
  stopAllSpeech();
  const leavingReadMode = app.mode === "read" && mode !== "read";
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
  if (leavingReadMode && app.maintenance.pendingReloadJob) {
    applyPendingCorpusReload();
  }
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
    app.maintenance.pendingReloadJob = null;
    app.maintenance.syncError = "";
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

async function reloadCorpus() {
  const selectedWord = app.selectedWord?.word || "";
  const readMode = app.mode === "read";
  if (readMode) {
    app.reader.preserveScrollOnRender = true;
  }
  app.wordDetailRequests.clear();
  app.sourceDetails.clear();
  app.sourceDetailRequests.clear();
  app.sourceDetailFailures.clear();
  app.corpus = await api.loadCorpusIndex();
  app.words = Array.isArray(app.corpus.words) ? app.corpus.words : [];
  await mergeRemoteStudyState({ preferRemote: true });
  app.selectedWord = readMode
    ? app.words.find((word) => word.word === selectedWord) || null
    : app.words.find((word) => word.word === selectedWord) || chooseInitialWord();
  render();
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
  renderEmptyState("loadErrorTitle", `${t("loadErrorBody")} (${error.message})`, null, { bodyIsLiteral: true });
}

function renderEmptyState(titleKey, bodyKey = "", actionKey = null, options = {}) {
  refs.emptyState.hidden = false;
  refs.emptyState.querySelector("h2").textContent = t(titleKey);
  refs.emptyState.querySelector("p").textContent = options.bodyIsLiteral ? bodyKey : (bodyKey ? t(bodyKey) : "");
  refs.emptyState.querySelectorAll(".empty-state-action").forEach((node) => node.remove());
  if (!actionKey || !app.maintenance.enabled) {
    return;
  }
  const button = el("button", "secondary-button empty-state-action", t(actionKey));
  button.type = "button";
  button.addEventListener("click", () => {
    setMaintenanceOpen(true);
    renderMaintenance();
  });
  refs.emptyState.append(button);
}

function t(key, values = {}) {
  let value = text[app.lang]?.[key] || text.zh[key] || key;
  Object.entries(values).forEach(([name, replacement]) => {
    value = value.replace(`{${name}}`, replacement);
  });
  return value;
}
