const STORAGE_LANG = "jpcorpus.viewer.lang";
const STORAGE_STATUS = "jpcorpus.viewer.status.v1";
const STORAGE_STUDY_COUNTS = "jpcorpus.viewer.studyCounts.v1";
const STORAGE_EXAMPLE_COLUMNS = "jpcorpus.viewer.exampleColumns.v1";
const STORAGE_MODE = "jpcorpus.viewer.mode.v1";
const EXAMPLE_COLUMN_VALUES = new Set(["auto", "1", "2", "3"]);
const MODE_VALUES = new Set(["browse", "study"]);
const STUDY_TARGET_COUNT = 7;
const EXAMPLE_SELECTION_FIELDS = [
  "source_type",
  "source_title",
  "source_artist",
  "source_album",
  "subtitle_file",
  "episode",
  "start_ms",
  "end_ms",
  "matched_text",
  "sentence",
];

const text = {
  zh: {
    appTitle: "个人日语语料",
    generatedAt: "生成于 {date}",
    searchPlaceholder: "搜索词、假名、释义、作品",
    sortLabel: "排序",
    sortCount: "频次",
    sortLevel: "等级",
    sortWord: "五十音",
    statusLabel: "状态",
    statusAll: "全部",
    statusNone: "未标记",
    statusLearning: "复习中",
    statusKnown: "认识",
    statusIgnored: "忽略",
    statusUncertain: "模糊",
    sourceLabel: "来源",
    sourceAll: "全部",
    sourceSubtitles: "字幕",
    sourceLyrics: "歌词",
    loadingTitle: "正在读取 corpus.json",
    loadingBody: "如果这里停住了，请确认本地服务能访问 corpus.json。",
    loadErrorTitle: "没有读到 corpus.json",
    loadErrorBody: "先运行导出命令，再重新打开 viewer。",
    allLevels: "全部",
    wordsFound: "{count} 个词",
    studyWordsFound: "{count} 个可复习词",
    noWords: "没有匹配的词",
    noStudyWords: "当前筛选下没有带例句的可复习词",
    count: "频次",
    examples: "例句",
    exampleColumns: "列数",
    exampleColumnsAuto: "自动",
    chineseMeaning: "日中",
    missingMeaning: "暂无释义",
    noExamples: "这个词暂时没有例句",
    scene: "场景",
    translation: "翻译",
    usageNote: "用法",
    reannotateExample: "重标",
    reannotateExampleTitle: "重新生成这一条例句的翻译和用法",
    studyMode: "学习",
    browseMode: "浏览",
    studyProgress: "第 {current} / {total} 个",
    revealAnswer: "看答案",
    hideAnswer: "先不看答案",
    nextWord: "跳过",
    studyUnsure: "模糊",
    studyKnown: "已经会了",
    studyMastered: "已记住",
    studyChecks: "勾 {count}/{target}",
    studyCheckButton: "不熟，记一勾",
    studyHint: "先读例句，想一下意思；不会就打一个勾，满 7 勾算记住。",
    shows: "作品",
    subtitles: "字幕",
    lyrics: "歌词",
    studyWords: "单词",
    maintenance: "维护",
    maintenanceTitle: "维护",
    maintenanceTask: "任务",
    maintenanceScope: "范围",
    maintenanceProvider: "Provider",
    maintenanceLimit: "上限",
    maintenanceLimitOptional: "上限（空=全部）",
    maintenanceConcurrency: "并发",
    maintenanceRpm: "RPM",
    maintenanceOverwrite: "覆盖已有标注",
    maintenanceOverwriteLyrics: "覆盖已有歌词",
    maintenanceShowContext: "使用作品简介",
    maintenanceStart: "开始",
    maintenanceStartSyncMedia: "同步并刷新",
    maintenanceStartExportCorpus: "刷新语料",
    maintenanceStartRefreshAll: "刷新所有",
    maintenanceStartAnnotate: "开始标注",
    maintenanceReloaded: "，页面已刷新",
    taskAnnotate: "LLM 标注",
    taskSyncMedia: "同步",
    taskExportCorpus: "刷新语料",
    taskRefreshAll: "刷新所有",
    scopeCurrentWord: "当前词",
    scopeFilteredWords: "当前筛选结果",
    scopeFirstUnannotated: "前 N 条缺失例句",
    maintenanceEstimate: "将处理约 {count} 条例句；会先查本地 LLM 缓存，缺失时才调用 API；当前来源 {source}，等级 {level}",
    maintenanceEstimateRefresh: "将重新生成约 {count} 条例句，并更新本地 LLM 缓存；当前来源 {source}，等级 {level}",
    maintenanceTaskSyncMedia: "从 Bangumi 同步动画/字幕和音乐，再从 LRCLIB 拉歌词，最后刷新页面语料",
    maintenanceTaskExportCorpus: "不联网，只用现有本地数据重新生成网页语料",
    maintenanceTaskRefreshAll: "更新词表、词典和动画数据库，再同步媒体、拉歌词并刷新语料",
    maintenanceDisabled: "维护 API 未启用",
    maintenanceIdle: "还没有运行任务",
    maintenanceRunningTask: "正在运行：{task}，开始于 {time}",
    maintenanceSucceededTask: "已完成：{task}{reload}，完成于 {time}",
    maintenanceFailedTask: "失败：{task}，结束于 {time}",
    maintenanceProgressAnnotate: "已处理 {completed}/{total}；缓存 {cached}，新标注 {annotated}，失败 {failed}",
    maintenanceProgressSteps: "步骤 {completed}/{total}：{step}",
    maintenanceProgressGeneric: "已处理 {completed}/{total}",
  },
  en: {
    appTitle: "Personal Japanese Corpus",
    generatedAt: "Generated {date}",
    searchPlaceholder: "Search word, reading, meaning, title",
    sortLabel: "Sort",
    sortCount: "Count",
    sortLevel: "Level",
    sortWord: "Kana",
    statusLabel: "Status",
    statusAll: "All",
    statusNone: "Unmarked",
    statusLearning: "Reviewing",
    statusKnown: "Known",
    statusIgnored: "Ignored",
    statusUncertain: "Unsure",
    sourceLabel: "Source",
    sourceAll: "All",
    sourceSubtitles: "Subtitles",
    sourceLyrics: "Lyrics",
    loadingTitle: "Loading corpus.json",
    loadingBody: "If this does not change, make sure the local server can read corpus.json.",
    loadErrorTitle: "Could not read corpus.json",
    loadErrorBody: "Export the corpus first, then reload the viewer.",
    allLevels: "All",
    wordsFound: "{count} words",
    studyWordsFound: "{count} review words",
    noWords: "No matching words",
    noStudyWords: "No reviewable words with examples in the current filter",
    count: "Count",
    examples: "Examples",
    exampleColumns: "Columns",
    exampleColumnsAuto: "Auto",
    chineseMeaning: "ZH",
    missingMeaning: "No meaning yet",
    noExamples: "No examples for this word yet",
    scene: "Scene",
    translation: "Translation",
    usageNote: "Usage",
    reannotateExample: "Refresh",
    reannotateExampleTitle: "Regenerate this example translation and usage note",
    studyMode: "Study",
    browseMode: "Browse",
    studyProgress: "{current} / {total}",
    revealAnswer: "Reveal",
    hideAnswer: "Hide answer",
    nextWord: "Skip",
    studyUnsure: "Unsure",
    studyKnown: "Already know it",
    studyMastered: "Mastered",
    studyChecks: "{count}/{target} checks",
    studyCheckButton: "Not solid, add a check",
    studyHint: "Read first and guess; add a check when it is not solid. Seven checks means mastered.",
    shows: "Shows",
    subtitles: "Subtitles",
    lyrics: "Lyrics",
    studyWords: "Study words",
    maintenance: "Maintain",
    maintenanceTitle: "Maintenance",
    maintenanceTask: "Task",
    maintenanceScope: "Scope",
    maintenanceProvider: "Provider",
    maintenanceLimit: "Limit",
    maintenanceLimitOptional: "Limit (blank = all)",
    maintenanceConcurrency: "Concurrency",
    maintenanceRpm: "RPM",
    maintenanceOverwrite: "Overwrite annotations",
    maintenanceOverwriteLyrics: "Overwrite lyrics",
    maintenanceShowContext: "Use show context",
    maintenanceStart: "Start",
    maintenanceStartSyncMedia: "Sync and refresh",
    maintenanceStartExportCorpus: "Refresh corpus",
    maintenanceStartRefreshAll: "Refresh all",
    maintenanceStartAnnotate: "Start annotation",
    maintenanceReloaded: ", page refreshed",
    taskAnnotate: "LLM annotations",
    taskSyncMedia: "Sync",
    taskExportCorpus: "Export corpus",
    taskRefreshAll: "Refresh all",
    scopeCurrentWord: "Current word",
    scopeFilteredWords: "Current filtered words",
    scopeFirstUnannotated: "First N missing examples",
    maintenanceEstimate: "About {count} examples; local LLM cache is checked first, API is used only for misses; source {source}, level {level}",
    maintenanceEstimateRefresh: "Regenerate about {count} examples and update the local LLM cache; source {source}, level {level}",
    maintenanceTaskSyncMedia: "Syncs Bangumi anime/subtitles and music, fetches LRCLIB lyrics, then refreshes the corpus",
    maintenanceTaskExportCorpus: "Uses existing local data only and regenerates the viewer corpus",
    maintenanceTaskRefreshAll: "Updates word/dictionary/anime data, syncs media, fetches lyrics, then refreshes the corpus",
    maintenanceDisabled: "Maintenance API disabled",
    maintenanceIdle: "No task has run yet",
    maintenanceRunningTask: "Running: {task}, started {time}",
    maintenanceSucceededTask: "Done: {task}{reload}, finished {time}",
    maintenanceFailedTask: "Failed: {task}, ended {time}",
    maintenanceProgressAnnotate: "Processed {completed}/{total}; cache {cached}, new {annotated}, failed {failed}",
    maintenanceProgressSteps: "Step {completed}/{total}: {step}",
    maintenanceProgressGeneric: "Processed {completed}/{total}",
  },
};

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
  query: "",
  level: "all",
  sort: "count",
  status: "all",
  source: "all",
  exampleColumns: readExampleColumns(),
  lang: localStorage.getItem(STORAGE_LANG) || "zh",
  mode: readMode(),
  statuses: readStatuses(),
  studyCounts: readStudyCounts(),
  study: {
    showAnswer: false,
  },
  maintenance: {
    enabled: false,
    job: null,
    pollTimer: null,
    reloadedJobId: null,
  },
};

const $ = (selector) => document.querySelector(selector);

const refs = {
  generatedAt: $("#generated-at"),
  summaryStrip: $("#summary-strip"),
  searchInput: $("#search-input"),
  levelFilter: $("#level-filter"),
  sortSelect: $("#sort-select"),
  statusFilter: $("#status-filter"),
  sourceFilter: $("#source-filter"),
  resultCount: $("#result-count"),
  wordList: $("#word-list"),
  emptyState: $("#empty-state"),
  wordDetail: $("#word-detail"),
  studyToggle: $("#study-toggle"),
  maintenanceToggle: $("#maintenance-toggle"),
  maintenancePanel: $("#maintenance-panel"),
  maintenanceClose: $("#maintenance-close"),
  maintenanceTask: $("#maintenance-task"),
  maintenanceScope: $("#maintenance-scope"),
  maintenanceProvider: $("#maintenance-provider"),
  maintenanceLimitLabel: $("#maintenance-limit-label"),
  maintenanceLimit: $("#maintenance-limit"),
  maintenanceConcurrency: $("#maintenance-concurrency"),
  maintenanceRpm: $("#maintenance-rpm"),
  maintenanceOverwriteLabel: $("#maintenance-overwrite-label"),
  maintenanceOverwrite: $("#maintenance-overwrite"),
  maintenanceShowContext: $("#maintenance-show-context"),
  maintenanceStart: $("#maintenance-start"),
  maintenanceEstimate: $("#maintenance-estimate"),
  maintenanceProgress: $("#maintenance-progress"),
  maintenanceProgressFill: $("#maintenance-progress-fill"),
  maintenanceProgressLabel: $("#maintenance-progress-label"),
  maintenanceStatus: $("#maintenance-status"),
  maintenanceLog: $("#maintenance-log"),
};

init();

async function init() {
  bindControls();
  applyLanguage();
  loadMaintenanceStatus();
  try {
    const response = await fetch("/corpus.json", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    app.corpus = await response.json();
    app.words = Array.isArray(app.corpus.words) ? app.corpus.words : [];
    app.selectedWord = chooseInitialWord(currentWordSet());
    render();
  } catch (error) {
    renderLoadError(error);
  }
}

function bindControls() {
  refs.searchInput.addEventListener("input", (event) => {
    app.query = event.target.value.trim().toLowerCase();
    app.selectedWord = chooseInitialWord(currentWordSet());
    app.study.showAnswer = false;
    render();
  });
  refs.sortSelect.addEventListener("change", (event) => {
    app.sort = event.target.value;
    render();
  });
  refs.statusFilter.addEventListener("change", (event) => {
    app.status = event.target.value;
    app.selectedWord = chooseInitialWord(currentWordSet());
    app.study.showAnswer = false;
    render();
  });
  refs.sourceFilter.addEventListener("change", (event) => {
    app.source = event.target.value;
    app.selectedWord = chooseInitialWord(currentWordSet());
    app.study.showAnswer = false;
    render();
  });
  refs.studyToggle.addEventListener("click", toggleStudyMode);
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
    renderMaintenance();
  });
  refs.maintenanceClose.addEventListener("click", () => {
    refs.maintenancePanel.hidden = true;
    refs.maintenanceToggle.classList.remove("active");
  });
  [
    refs.maintenanceTask,
    refs.maintenanceScope,
    refs.maintenanceProvider,
    refs.maintenanceLimit,
    refs.maintenanceConcurrency,
    refs.maintenanceRpm,
    refs.maintenanceOverwrite,
    refs.maintenanceShowContext,
  ].forEach((control) => {
    control.addEventListener("input", renderMaintenance);
    control.addEventListener("change", renderMaintenance);
  });
  refs.maintenanceStart.addEventListener("click", startMaintenanceJob);
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
}

function render() {
  if (!app.corpus) {
    return;
  }
  renderHeader();
  renderLevelFilter();
  renderWordList();
  renderDetail();
  renderMaintenance();
}

function renderHeader() {
  refs.studyToggle.textContent = t(app.mode === "study" ? "browseMode" : "studyMode");
  refs.studyToggle.classList.toggle("active", app.mode === "study");
  refs.generatedAt.textContent = app.corpus.generated_at
    ? t("generatedAt", { date: app.corpus.generated_at })
    : "";
  const summary = app.corpus.summary || {};
  const items = [
    [t("shows"), summary.watched_show_count],
    [t("subtitles"), summary.subtitle_file_count],
    [t("lyrics"), summary.lyric_file_count],
    [t("studyWords"), app.words.length],
    [t("examples"), totalExampleCount()],
  ];
  refs.summaryStrip.replaceChildren(
    ...items.map(([label, value]) => {
      const pill = el("div", "summary-pill");
      pill.append(label, " ", strong(value ?? "0"));
      return pill;
    }),
  );
}

async function loadMaintenanceStatus() {
  try {
    const response = await fetch("/api/maintenance", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    app.maintenance.enabled = Boolean(payload.enabled);
    app.maintenance.job = payload.job || null;
    if (payload.llm?.provider && refs.maintenanceProvider) {
      refs.maintenanceProvider.value = payload.llm.provider;
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
  const task = maintenanceTask();
  const isAnnotation = task === "annotate";
  const spec = isAnnotation ? annotationJobSpec() : maintenanceJobSpec();
  const estimate = isAnnotation ? estimateAnnotationJob(spec) : { planned: 1 };
  const job = app.maintenance.job;
  document.querySelectorAll(".annotation-control").forEach((node) => {
    node.hidden = !isAnnotation;
  });
  refs.maintenanceLimitLabel.textContent =
    task === "fetch_lyrics" ? t("maintenanceLimitOptional") : t("maintenanceLimit");
  refs.maintenanceOverwriteLabel.textContent =
    task === "fetch_lyrics" ? t("maintenanceOverwriteLyrics") : t("maintenanceOverwrite");
  refs.maintenanceToggle.disabled = !app.maintenance.enabled;
  if (!app.maintenance.enabled) {
    refs.maintenanceEstimate.textContent = t("maintenanceDisabled");
  } else if (isAnnotation) {
    refs.maintenanceEstimate.textContent = t(
      spec.bypass_cache ? "maintenanceEstimateRefresh" : "maintenanceEstimate",
      {
        count: formatNumber(estimate.planned),
        source: sourceLabel(spec.source),
        level: spec.level,
      },
    );
  } else {
    refs.maintenanceEstimate.textContent = maintenanceTaskDescription(task);
  }
  refs.maintenanceStart.disabled =
    !app.maintenance.enabled || job?.status === "running" || (isAnnotation && estimate.planned <= 0);
  refs.maintenanceStart.textContent = maintenanceStartLabel(task);
  refs.maintenanceStatus.textContent = job ? maintenanceStatusLabel(job) : t("maintenanceIdle");
  renderMaintenanceProgress(job);
  refs.maintenanceLog.textContent = job?.log?.join("\n") || "";
  updateExampleActionButtons();
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
  refs.resultCount.textContent = t(app.mode === "study" ? "studyWordsFound" : "wordsFound", {
    count: formatNumber(words.length),
  });
  if (words.length === 0) {
    app.selectedWord = null;
    refs.wordList.replaceChildren(emptyMessage(t(app.mode === "study" ? "noStudyWords" : "noWords")));
    return;
  }
  if (!app.selectedWord || !words.some((word) => word.word === app.selectedWord.word)) {
    app.selectedWord = words[0];
  }
  refs.wordList.replaceChildren(...words.map(renderWordRow));
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
  badges.append(badge(word.level || ""));
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
    refs.emptyState.querySelector("h2").textContent = t("noWords");
    refs.emptyState.querySelector("p").textContent = "";
    return;
  }
  refs.emptyState.hidden = true;
  refs.wordDetail.hidden = false;
  refs.wordDetail.replaceChildren(renderDetailHeader(word), renderExamples(word));
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
  stats.append(
    statChip(word.level || ""),
    statChip(`${t("count")} ${formatNumber(displayCount(word))}`),
    statChip(`${t("examples")} ${formatNumber(examples.length)}`),
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
    statChip(word.level || ""),
    statChip(`${t("count")} ${formatNumber(displayCount(word))}`),
    statChip(`${t("examples")} ${formatNumber(examplesForWord(word).length)}`),
    statChip(studyCheckLabel(word)),
  );
  titleRow.append(title, stats);
  card.append(topLine, titleRow);

  if (app.study.showAnswer) {
    const mainMeaning = displayMeaningRaw(word);
    const meanings = el("div", "study-answer-block");
    meanings.append(mainMeaning ? renderMeaningValue(word, "meaning-main") : el("div", "meaning-main", "—"));
    card.append(meanings);
  }

  card.append(renderExamples(word, {
    revealAnnotations: app.study.showAnswer,
    allowActions: app.study.showAnswer,
  }));
  card.append(renderStudyActions(word));
  return card;
}

function renderStudyActions(word) {
  const actions = el("div", "study-actions");
  const reveal = el(
    "button",
    "study-primary-action",
    t(app.study.showAnswer ? "hideAnswer" : "revealAnswer"),
  );
  reveal.type = "button";
  reveal.addEventListener("click", () => {
    app.study.showAnswer = !app.study.showAnswer;
    renderDetail();
  });

  const statusActions = el("div", "study-status-actions");
  if (app.study.showAnswer) {
    [
      ["check", t("studyCheckButton")],
      ["known", t("studyKnown")],
    ].forEach(([action, label]) => {
      const button = el("button", "", label);
      button.type = "button";
      button.classList.toggle("active", action !== "check" && statusFor(word) === action);
      button.addEventListener("click", () => {
        if (action === "check") {
          addStudyCheck(word);
        } else {
          markStudyWord(action);
        }
      });
      statusActions.append(button);
    });
  }

  const next = el("button", "study-next-action", t("nextWord"));
  next.type = "button";
  next.addEventListener("click", nextStudyWord);

  actions.append(reveal);
  if (app.study.showAnswer) {
    actions.append(statusActions);
  }
  actions.append(next);
  return actions;
}

function renderStatusActions(word) {
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

function selectWord(word, button) {
  app.selectedWord = word;
  app.study.showAnswer = false;
  refs.wordList.querySelectorAll(".word-row.active").forEach((row) => {
    row.classList.remove("active");
  });
  button.classList.add("active");
  renderDetail();
  renderMaintenance();
}

function toggleStudyMode() {
  app.mode = app.mode === "study" ? "browse" : "study";
  localStorage.setItem(STORAGE_MODE, app.mode);
  app.study.showAnswer = false;
  app.selectedWord = chooseInitialWord(currentWordSet());
  render();
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
  advanceStudyQueue(previousQueue, word);
}

function addStudyCheck(word) {
  const previousQueue = studyQueue();
  const nextCount = Math.min(studyCountFor(word) + 1, STUDY_TARGET_COUNT);
  setStudyCount(word, nextCount);
  setStatus(word, nextCount >= STUDY_TARGET_COUNT ? "known" : "learning");
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

async function startMaintenanceJob() {
  const task = maintenanceTask();
  const spec = task === "annotate" ? annotationJobSpec() : maintenanceJobSpec();
  const endpoint = task === "annotate" ? "/api/jobs/annotate" : "/api/jobs/maintenance";
  refs.maintenanceStart.disabled = true;
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(spec),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    app.maintenance.job = payload.job;
    app.maintenance.reloadedJobId = null;
    renderMaintenance();
    pollMaintenanceJob();
  } catch (error) {
    app.maintenance.job = {
      status: "failed",
      log: [String(error.message || error)],
    };
    renderMaintenance();
  }
}

async function startExampleAnnotationJob(word, example, button) {
  if (!app.maintenance.enabled || app.maintenance.job?.status === "running") {
    return;
  }
  if (button) {
    button.disabled = true;
  }
  refs.maintenancePanel.hidden = false;
  refs.maintenanceToggle.classList.add("active");
  const spec = {
    scope: "selected_examples",
    provider: refs.maintenanceProvider.value,
    words: [word.word].filter(Boolean),
    examples: [exampleAnnotationSelector(example)],
    source: "all",
    level: "all",
    limit: 1,
    concurrency: 1,
    rpm: numberValue(refs.maintenanceRpm, 0) || null,
    cache_only: false,
    bypass_cache: true,
    overwrite: true,
    use_show_context: refs.maintenanceShowContext.checked,
  };
  try {
    const response = await fetch("/api/jobs/annotate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(spec),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    app.maintenance.job = payload.job;
    app.maintenance.reloadedJobId = null;
    renderMaintenance();
    pollMaintenanceJob();
  } catch (error) {
    app.maintenance.job = {
      status: "failed",
      log: [String(error.message || error)],
    };
    renderMaintenance();
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
    const response = await fetch("/api/jobs/current", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
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
    if (job.status === "succeeded" && job.result?.reload_corpus && app.maintenance.reloadedJobId !== job.id) {
      app.maintenance.reloadedJobId = job.id;
      await reloadCorpus();
    }
  } catch (error) {
    app.maintenance.job = {
      status: "failed",
      log: [String(error.message || error)],
    };
    renderMaintenance();
  }
}

async function reloadCorpus() {
  const selectedWord = app.selectedWord?.word || "";
  const response = await fetch("/corpus.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  app.corpus = await response.json();
  app.words = Array.isArray(app.corpus.words) ? app.corpus.words : [];
  app.selectedWord = app.words.find((word) => word.word === selectedWord) || chooseInitialWord();
  render();
}

function renderExamples(word, options = {}) {
  const revealAnnotations = options.revealAnnotations ?? true;
  const allowActions = options.allowActions ?? true;
  const section = el("section", "examples");
  const header = el("div", "examples-header");
  header.append(el("h3", "section-title", t("examples")), renderExampleColumnControl());
  section.append(header);
  const examples = examplesForWord(word);
  if (examples.length === 0) {
    section.append(emptyMessage(t("noExamples")));
    return section;
  }
  const grid = el("div", `examples-grid columns-${app.exampleColumns}`);
  examples.forEach((example) => {
    const sourceClass = example.source_type === "lyrics" ? "lyrics" : "subtitle";
    const item = el("div", `example example-${sourceClass}`);
    const lines = el("div", "example-lines");
    appendContextBlock(lines, contextPreview(example.context_before, "before"), "before");
    const current = el("div", "example-current");
    appendHighlighted(current, example.sentence || "", example.matched_text || word.word);
    lines.append(current);
    appendContextBlock(lines, contextPreview(example.context_after, "after"), "after");
    lines.append(el("small", `reference reference-${sourceClass}`, formatReference(example)));
    item.append(lines);
    if (allowActions) {
      item.append(renderExampleActions(word, example));
    }
    if (revealAnnotations && example.translation_zh) {
      item.append(el("div", "annotation-line translation-line", `${t("translation")}: ${example.translation_zh}`));
    }
    if (revealAnnotations && example.usage_note_zh) {
      item.append(el("div", "annotation-line", `${t("usageNote")}: ${example.usage_note_zh}`));
    }
    grid.append(item);
  });
  section.append(grid);
  return section;
}

function renderExampleActions(word, example) {
  const wrap = el("div", "example-actions");
  const button = el("button", "example-action-button", t("reannotateExample"));
  button.type = "button";
  button.title = t("reannotateExampleTitle");
  button.disabled = !app.maintenance.enabled || app.maintenance.job?.status === "running";
  button.addEventListener("click", () => startExampleAnnotationJob(word, example, button));
  wrap.append(button);
  return wrap;
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
  const query = app.query;
  const words = app.words.filter((word) => {
    if (app.level !== "all" && word.level !== app.level) {
      return false;
    }
    const status = statusFor(word);
    if (app.status !== "all" && status !== app.status) {
      return false;
    }
    if (app.source !== "all" && sourceCount(word, app.source) === 0) {
      return false;
    }
    if (!query) {
      return true;
    }
    const haystack = [
      word.word,
      word.reading,
      word.meaning,
      word.meaning_zh,
      ...(word.sources || []).map((source) => source.title),
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  });
  words.sort(compareWords);
  return words;
}

function currentWordSet() {
  return app.mode === "study" ? studyQueue() : filteredWords();
}

function studyQueue() {
  const words = filteredWords().filter((word) => {
    const status = statusFor(word);
    if (app.status === "all" && (status === "ignored" || status === "known")) {
      return false;
    }
    return examplesForWord(word).length > 0;
  });
  words.sort(compareStudyWords);
  return words;
}

function compareStudyWords(left, right) {
  return studyPriority(left) - studyPriority(right)
    || (right.count || 0) - (left.count || 0)
    || compareKana(left, right);
}

function studyPriority(word) {
  const status = statusFor(word);
  const count = studyCountFor(word);
  if (status === "ignored") {
    return 9;
  }
  if (count > 0 && count < STUDY_TARGET_COUNT) {
    return 0;
  }
  if (status === "learning") {
    return 1;
  }
  if (status === "uncertain" || status === "none") {
    return 2;
  }
  if (status === "known") {
    return 3;
  }
  return 4;
}

function compareWords(left, right) {
  if (app.sort === "word") {
    return compareKana(left, right);
  }
  if (app.sort === "level") {
    return (left.level_number || 0) - (right.level_number || 0) || (right.count || 0) - (left.count || 0);
  }
  return (right.count || 0) - (left.count || 0) || compareKana(left, right);
}

function compareKana(left, right) {
  const readingCompare = kanaSortKey(left).localeCompare(
    kanaSortKey(right),
    "ja",
  );
  if (readingCompare !== 0) {
    return readingCompare;
  }
  return String(left.word || "").localeCompare(String(right.word || ""), "ja");
}

function kanaSortKey(word) {
  let value = String(word.reading || word.word || "").normalize("NFKC").trim();
  value = value.replace(/^[（(][^）)]*[）)]\s*/u, "");
  value = value.replace(/^[^ぁ-ゖァ-ヺ一-龯々]+/u, "");
  return value || String(word.word || "");
}

function chooseInitialWord(words = app.words) {
  if (app.selectedWord && words.some((word) => word.word === app.selectedWord.word)) {
    return app.selectedWord;
  }
  return words[0] || null;
}

function displayMeaningRaw(word) {
  if (app.lang === "zh") {
    return word.meaning_zh || word.meaning || "";
  }
  return word.meaning || word.meaning_zh || "";
}

function renderMeaningValue(word, className) {
  return renderParsedMeaning(parseMeaning(displayMeaningRaw(word)), className);
}

function renderParsedMeaning(meaning, className) {
  const wrap = el("div", className);
  if (!meaning.raw) {
    return wrap;
  }
  if (meaning.accent) {
    wrap.append(el("span", "meaning-chip meaning-accent", meaning.accent));
  }
  if (meaning.pos) {
    wrap.append(el("span", "meaning-chip meaning-pos", meaning.pos));
  }
  wrap.append(el("span", "meaning-text", meaning.text || meaning.raw));
  return wrap;
}

function parseMeaning(value) {
  let textValue = String(value || "").trim();
  const raw = textValue;
  let accent = "";
  let pos = "";
  const accentMatch = textValue.match(/^([⓪①②③④⑤⑥⑦⑧⑨]+)\s*/u);
  if (accentMatch) {
    accent = accentMatch[1];
    textValue = textValue.slice(accentMatch[0].length).trim();
  }
  const bracketPosMatch = textValue.match(/^【([^】]+)】\s*/u);
  if (bracketPosMatch) {
    pos = bracketPosMatch[1];
    textValue = textValue.slice(bracketPosMatch[0].length).trim();
  } else {
    const prefix = meaningPosPrefix(textValue);
    if (prefix) {
      pos = normalizeMeaningPos(prefix);
      textValue = textValue.slice(prefix.length).trim();
    }
  }
  return { raw, accent, pos, text: textValue };
}

function meaningPosPrefix(value) {
  const prefixes = [
    "助动词",
    "连体词",
    "接续词",
    "感叹词",
    "形容词",
    "自动1",
    "自动2",
    "自动3",
    "他动1",
    "他动2",
    "他动3",
    "名词",
    "代词",
    "副词",
    "数词",
    "助词",
    "动1",
    "动2",
    "动3",
    "イ形",
    "ナ形",
    "连体",
    "名",
    "代",
    "副",
    "数",
  ];
  return prefixes.find((prefix) => value.startsWith(`${prefix} `) || value.startsWith(`${prefix}　`)) || "";
}

function normalizeMeaningPos(value) {
  const mapping = {
    名词: "名",
    代词: "代",
    副词: "副",
    数词: "数",
  };
  return mapping[value] || value;
}

function totalExampleCount() {
  return app.words.reduce(
    (total, word) => total + (Array.isArray(word.examples) ? word.examples.length : 0),
    0,
  );
}

function examplesForWord(word) {
  const examples = Array.isArray(word.examples) ? word.examples : [];
  if (app.source === "all") {
    return examples;
  }
  return examples.filter((example) => example.source_type === app.source);
}

function maintenanceTask() {
  return refs.maintenanceTask?.value || "annotate";
}

function maintenanceJobSpec() {
  const task = maintenanceTask();
  return {
    type: task,
    limit: optionalNumberValue(refs.maintenanceLimit),
    concurrency: numberValue(refs.maintenanceConcurrency, 4),
    overwrite: refs.maintenanceOverwrite.checked,
  };
}

function annotationJobSpec() {
  const scope = refs.maintenanceScope.value;
  let words = [];
  if (scope === "current_word" && app.selectedWord?.word) {
    words = [app.selectedWord.word];
  } else if (scope === "filtered_words") {
    words = filteredWords().map((word) => word.word).filter(Boolean);
  }
  return {
    scope,
    provider: refs.maintenanceProvider.value,
    words,
    source: app.source,
    level: app.level,
    limit: optionalNumberValue(refs.maintenanceLimit) || 20,
    concurrency: numberValue(refs.maintenanceConcurrency, 1),
    rpm: numberValue(refs.maintenanceRpm, 0) || null,
    cache_only: false,
    bypass_cache: refs.maintenanceOverwrite.checked,
    overwrite: refs.maintenanceOverwrite.checked,
    use_show_context: refs.maintenanceShowContext.checked,
  };
}

function estimateAnnotationJob(spec) {
  const wordSet = spec.scope === "first_unannotated" ? null : new Set(spec.words);
  const exampleSet = spec.scope === "selected_examples"
    ? new Set((spec.examples || []).map(exampleAnnotationSignature))
    : null;
  let selected = 0;
  app.words.forEach((word) => {
    if (wordSet && !wordSet.has(word.word)) {
      return;
    }
    if (spec.level !== "all" && word.level !== spec.level) {
      return;
    }
    (word.examples || []).forEach((example) => {
      if (exampleSet && !exampleSet.has(exampleAnnotationSignature(example))) {
        return;
      }
      if (spec.source !== "all" && example.source_type !== spec.source) {
        return;
      }
      if (!spec.overwrite && example.translation_zh && example.usage_note_zh) {
        return;
      }
      selected += 1;
    });
  });
  return {
    selected,
    planned: Math.min(selected, spec.limit),
  };
}

function updateExampleActionButtons() {
  const disabled = !app.maintenance.enabled || app.maintenance.job?.status === "running";
  document.querySelectorAll(".example-action-button").forEach((button) => {
    button.disabled = disabled;
  });
}

function exampleAnnotationSelector(example) {
  const selector = {};
  EXAMPLE_SELECTION_FIELDS.forEach((field) => {
    selector[field] = example[field] ?? null;
  });
  return selector;
}

function exampleAnnotationSignature(example) {
  return JSON.stringify(exampleAnnotationSelector(example));
}

function displayCount(word) {
  if (app.source === "all") {
    return word.count || 0;
  }
  return sourceCount(word, app.source);
}

function sourceLabel(source) {
  if (source === "subtitle") {
    return t("sourceSubtitles");
  }
  if (source === "lyrics") {
    return t("sourceLyrics");
  }
  return t("sourceAll");
}

function maintenanceTaskDescription(task) {
  const key = {
    sync_media: "maintenanceTaskSyncMedia",
    export_corpus: "maintenanceTaskExportCorpus",
    refresh_all: "maintenanceTaskRefreshAll",
  }[task];
  return key ? t(key) : "";
}

function maintenanceStartLabel(task) {
  const key = {
    sync_media: "maintenanceStartSyncMedia",
    export_corpus: "maintenanceStartExportCorpus",
    refresh_all: "maintenanceStartRefreshAll",
    annotate: "maintenanceStartAnnotate",
  }[task];
  return key ? t(key) : t("maintenanceStart");
}

function maintenanceTaskLabel(task) {
  const key = {
    sync_media: "taskSyncMedia",
    export_corpus: "taskExportCorpus",
    refresh_all: "taskRefreshAll",
    annotate: "taskAnnotate",
  }[task];
  return key ? t(key) : task || t("maintenance");
}

function maintenanceStatusLabel(job) {
  const task = maintenanceTaskLabel(job.kind || job.spec?.type || maintenanceTask());
  const time = formatJobTime(job.finished_at || job.started_at);
  if (job.status === "running") {
    return t("maintenanceRunningTask", { task, time });
  }
  if (job.status === "succeeded") {
    return t("maintenanceSucceededTask", {
      task,
      reload: job.result?.reload_corpus ? t("maintenanceReloaded") : "",
      time,
    });
  }
  if (job.status === "failed") {
    return t("maintenanceFailedTask", { task, time });
  }
  return t("maintenanceIdle");
}

function renderMaintenanceProgress(job) {
  const progress = job?.progress || null;
  if (!progress || !refs.maintenanceProgress) {
    refs.maintenanceProgress.hidden = true;
    return;
  }
  const total = Number(progress.total || 0);
  const completed = Number(progress.completed || 0);
  const percent = Number.isFinite(Number(progress.percent))
    ? Number(progress.percent)
    : total > 0
      ? (completed / total) * 100
      : 0;
  const boundedPercent = Math.max(0, Math.min(100, percent));
  refs.maintenanceProgress.hidden = false;
  refs.maintenanceProgressFill.style.width = `${boundedPercent}%`;
  refs.maintenanceProgress.querySelector("[role='progressbar']").setAttribute(
    "aria-valuenow",
    String(Math.round(boundedPercent)),
  );
  refs.maintenanceProgressLabel.textContent = maintenanceProgressLabel(progress);
}

function maintenanceProgressLabel(progress) {
  const phase = progress.phase || "";
  const completed = formatNumber(progress.completed || 0);
  const total = formatNumber(progress.total || 0);
  if (phase === "annotate" || phase === "cache") {
    return t("maintenanceProgressAnnotate", {
      completed,
      total,
      cached: formatNumber(progress.cached || 0),
      annotated: formatNumber(progress.annotated || 0),
      failed: formatNumber(progress.failed || 0),
    });
  }
  if (phase === "steps" || phase === "export") {
    return t("maintenanceProgressSteps", {
      completed,
      total,
      step: progress.current_step || maintenanceTaskLabel(maintenanceTask()),
    });
  }
  return t("maintenanceProgressGeneric", { completed, total });
}

function formatJobTime(value) {
  if (!value) {
    return "--";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "--";
  }
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function numberValue(input, fallback) {
  const value = Number.parseInt(input.value, 10);
  return Number.isFinite(value) ? value : fallback;
}

function optionalNumberValue(input) {
  const value = input.value.trim();
  if (!value) {
    return null;
  }
  const number = Number.parseInt(value, 10);
  return Number.isFinite(number) ? number : null;
}

function sourceCount(word, sourceType) {
  const counts = word.source_type_counts || {};
  return counts[sourceType] || 0;
}

function formatReference(example) {
  if (example.source_type === "lyrics") {
    return formatLyricReference(example);
  }

  const parts = [];
  if (example.source_title) {
    parts.push(example.source_title);
  }
  if (Number.isInteger(example.episode)) {
    parts.push(`EP${String(example.episode).padStart(2, "0")}`);
  } else if (example.subtitle_file) {
    parts.push(example.subtitle_file);
  }
  if (Number.isInteger(example.start_ms)) {
    parts.push(formatTimestamp(example.start_ms));
  }
  return parts.join(" ");
}

function formatLyricReference(example) {
  const parts = [];
  if (example.source_title) {
    parts.push(`♪ ${example.source_title}`);
  }
  if (example.source_artist) {
    parts.push(example.source_artist);
  }
  if (example.source_album && example.source_album !== example.source_title) {
    parts.push(`《${example.source_album}》`);
  }
  if (Number.isInteger(example.start_ms)) {
    parts.push(formatTimestamp(example.start_ms));
  }
  return parts.join(" · ");
}

function formatTimestamp(milliseconds) {
  let seconds = Math.floor(milliseconds / 1000);
  const hours = Math.floor(seconds / 3600);
  seconds -= hours * 3600;
  const minutes = Math.floor(seconds / 60);
  seconds -= minutes * 60;
  if (hours > 0) {
    return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
  }
  return `${pad(minutes)}:${pad(seconds)}`;
}

function statusFor(word) {
  const stored = app.statuses[word.word] || "none";
  if (stored === "ignored") {
    return stored;
  }
  const count = studyCountFor(word);
  if (count >= STUDY_TARGET_COUNT) {
    return "known";
  }
  if (stored === "none" && count > 0) {
    return "learning";
  }
  return stored;
}

function setStatus(word, status) {
  if (status === "none") {
    delete app.statuses[word.word];
    setStudyCount(word, 0);
  } else {
    app.statuses[word.word] = status;
    if (status === "known") {
      setStudyCount(word, STUDY_TARGET_COUNT);
    }
  }
  localStorage.setItem(STORAGE_STATUS, JSON.stringify(app.statuses));
}

function studyCountFor(word) {
  return clampStudyCount(app.studyCounts[word.word] || 0);
}

function setStudyCount(word, count) {
  const normalized = clampStudyCount(count);
  if (normalized <= 0) {
    delete app.studyCounts[word.word];
  } else {
    app.studyCounts[word.word] = normalized;
  }
  localStorage.setItem(STORAGE_STUDY_COUNTS, JSON.stringify(app.studyCounts));
}

function clampStudyCount(value) {
  const count = Number.parseInt(value, 10);
  if (!Number.isFinite(count) || count <= 0) {
    return 0;
  }
  return Math.min(count, STUDY_TARGET_COUNT);
}

function studyCheckLabel(word) {
  return t("studyChecks", {
    count: formatNumber(studyCountFor(word)),
    target: formatNumber(STUDY_TARGET_COUNT),
  });
}

function renderStudyCountBadge(word) {
  const count = studyCountFor(word);
  if (count <= 0 && app.mode !== "study") {
    return null;
  }
  const node = el("span", `study-count-badge ${count >= STUDY_TARGET_COUNT ? "mastered" : ""}`.trim());
  node.textContent = count >= STUDY_TARGET_COUNT ? t("studyMastered") : `${count}/${STUDY_TARGET_COUNT}`;
  node.title = studyCheckLabel(word);
  return node;
}

function readStatuses() {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_STATUS) || "{}");
    return value && typeof value === "object" ? value : {};
  } catch {
    return {};
  }
}

function readStudyCounts() {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_STUDY_COUNTS) || "{}");
    if (!value || typeof value !== "object") {
      return {};
    }
    return Object.fromEntries(
      Object.entries(value)
        .map(([word, count]) => [word, clampStudyCount(count)])
        .filter(([, count]) => count > 0),
    );
  } catch {
    return {};
  }
}

function readExampleColumns() {
  const value = localStorage.getItem(STORAGE_EXAMPLE_COLUMNS) || "auto";
  return EXAMPLE_COLUMN_VALUES.has(value) ? value : "auto";
}

function readMode() {
  const value = localStorage.getItem(STORAGE_MODE) || "browse";
  return MODE_VALUES.has(value) ? value : "browse";
}

function statusDot(status) {
  const dot = el("span", `status-dot ${status === "none" ? "" : status}`.trim());
  dot.textContent = stateLabels[status]?.symbol || "·";
  dot.title = stateLabels[status]?.[app.lang] || "";
  return dot;
}

function badge(value) {
  return el("span", "level-badge", value);
}

function statChip(value) {
  return el("span", "stat-chip", value);
}

function emptyMessage(value) {
  return el("div", "empty-list", value);
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

function el(tag, className = "", value = "") {
  const node = document.createElement(tag);
  if (className) {
    node.className = className;
  }
  if (value !== "") {
    node.textContent = value;
  }
  return node;
}

function strong(value) {
  return el("strong", "", String(value));
}

function formatNumber(value) {
  return new Intl.NumberFormat(app.lang === "zh" ? "zh-CN" : "en-US").format(value || 0);
}

function pad(value) {
  return String(value).padStart(2, "0");
}

function contextPreview(value, position, minChars = 40, maxLines = 3) {
  const lines = Array.isArray(value) ? value.filter(Boolean) : [];
  const selected = [];
  let charCount = 0;
  if (position === "before") {
    for (let index = lines.length - 1; index >= 0 && selected.length < maxLines; index -= 1) {
      selected.unshift(lines[index]);
      charCount += lines[index].length;
      if (charCount >= minChars) {
        break;
      }
    }
    return selected;
  }
  for (let index = 0; index < lines.length && selected.length < maxLines; index += 1) {
    selected.push(lines[index]);
    charCount += lines[index].length;
    if (charCount >= minChars) {
      break;
    }
  }
  return selected;
}
