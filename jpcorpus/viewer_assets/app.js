const STORAGE_LANG = "jpcorpus.viewer.lang";
const STORAGE_STATUS = "jpcorpus.viewer.status.v1";
const STORAGE_STUDY_COUNTS = "jpcorpus.viewer.studyCounts.v1";
const STORAGE_EXAMPLE_COLUMNS = "jpcorpus.viewer.exampleColumns.v1";
const STORAGE_MODE = "jpcorpus.viewer.mode.v1";
const WORD_LIST_PAGE_SIZE = 600;
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
const SEARCH_PUNCTUATION_RE = /[\s!"#$%&'()*+,\-./:;<=>?@[\\\]^_`{|}~、。，．・･；;：:！？!?「」『』【】（）()［］\[\]〈〉《》…〜～·]+/gu;
const GODAN_ENDINGS = {
  "う": { a: "わ", i: "い", e: "え", o: "お", te: "って", ta: "った" },
  "く": { a: "か", i: "き", e: "け", o: "こ", te: "いて", ta: "いた" },
  "ぐ": { a: "が", i: "ぎ", e: "げ", o: "ご", te: "いで", ta: "いだ" },
  "す": { a: "さ", i: "し", e: "せ", o: "そ", te: "して", ta: "した" },
  "つ": { a: "た", i: "ち", e: "て", o: "と", te: "って", ta: "った" },
  "ぬ": { a: "な", i: "に", e: "ね", o: "の", te: "んで", ta: "んだ" },
  "ぶ": { a: "ば", i: "び", e: "べ", o: "ぼ", te: "んで", ta: "んだ" },
  "む": { a: "ま", i: "み", e: "め", o: "も", te: "んで", ta: "んだ" },
  "る": { a: "ら", i: "り", e: "れ", o: "ろ", te: "って", ta: "った" },
};
const ROMAJI_DIGRAPHS = {
  きゃ: "kya", きゅ: "kyu", きょ: "kyo",
  ぎゃ: "gya", ぎゅ: "gyu", ぎょ: "gyo",
  しゃ: "sha", しゅ: "shu", しょ: "sho",
  じゃ: "ja", じゅ: "ju", じょ: "jo",
  ちゃ: "cha", ちゅ: "chu", ちょ: "cho",
  にゃ: "nya", にゅ: "nyu", にょ: "nyo",
  ひゃ: "hya", ひゅ: "hyu", ひょ: "hyo",
  びゃ: "bya", びゅ: "byu", びょ: "byo",
  ぴゃ: "pya", ぴゅ: "pyu", ぴょ: "pyo",
  みゃ: "mya", みゅ: "myu", みょ: "myo",
  りゃ: "rya", りゅ: "ryu", りょ: "ryo",
};
const ROMAJI_KANA = {
  あ: "a", い: "i", う: "u", え: "e", お: "o",
  か: "ka", き: "ki", く: "ku", け: "ke", こ: "ko",
  が: "ga", ぎ: "gi", ぐ: "gu", げ: "ge", ご: "go",
  さ: "sa", し: "shi", す: "su", せ: "se", そ: "so",
  ざ: "za", じ: "ji", ず: "zu", ぜ: "ze", ぞ: "zo",
  た: "ta", ち: "chi", つ: "tsu", て: "te", と: "to",
  だ: "da", ぢ: "ji", づ: "zu", で: "de", ど: "do",
  な: "na", に: "ni", ぬ: "nu", ね: "ne", の: "no",
  は: "ha", ひ: "hi", ふ: "fu", へ: "he", ほ: "ho",
  ば: "ba", び: "bi", ぶ: "bu", べ: "be", ぼ: "bo",
  ぱ: "pa", ぴ: "pi", ぷ: "pu", ぺ: "pe", ぽ: "po",
  ま: "ma", み: "mi", む: "mu", め: "me", も: "mo",
  や: "ya", ゆ: "yu", よ: "yo",
  ら: "ra", り: "ri", る: "ru", れ: "re", ろ: "ro",
  わ: "wa", を: "o", ん: "n",
  ゔ: "vu",
  ぁ: "a", ぃ: "i", ぅ: "u", ぇ: "e", ぉ: "o",
  ゃ: "ya", ゅ: "yu", ょ: "yo",
};

const text = {
  zh: {
    appTitle: "个人日语语料",
    generatedAt: "生成于 {date}",
    searchPlaceholder: "搜索词、假名、中文、变形/词根、作品",
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
    showMoreWords: "再显示 {count} 个",
    noWords: "没有匹配的词",
    noStudyWords: "当前筛选下没有带例句的可复习词",
    count: "频次",
    examples: "例句",
    exampleColumns: "列数",
    exampleColumnsAuto: "自动",
    chineseMeaning: "日中",
    missingMeaning: "暂无释义",
    noExamples: "这个词暂时没有例句",
    lexicalNotes: "词语知识",
    lexicalSpellings: "写法",
    lexicalReadings: "异读",
    lexicalPos: "语法",
    lexicalSenses: "义项",
    lexicalKanji: "字音",
    lexicalExamples: "词典例句",
    scene: "场景",
    translation: "翻译",
    usageNote: "用法",
    reannotateExample: "刷新标注",
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
    maintenanceStartFetchLexicalResources: "更新资源",
    maintenanceStartRefreshAll: "刷新所有",
    maintenanceStartAnnotate: "开始标注",
    maintenanceReloaded: "，页面已刷新",
    taskAnnotate: "LLM 标注",
    taskSyncMedia: "同步",
    taskExportCorpus: "刷新语料",
    taskFetchLexicalResources: "更新词语资源",
    taskRefreshAll: "刷新所有",
    scopeCurrentWord: "当前词",
    scopeFilteredWords: "当前筛选结果",
    scopeFirstUnannotated: "前 N 条缺失例句",
    maintenanceEstimate: "将处理约 {count} 条例句；会先查本地 LLM 缓存，缺失时才调用 API；当前来源 {source}，等级 {level}",
    maintenanceEstimateRefresh: "将重新生成约 {count} 条例句，并更新本地 LLM 缓存；当前来源 {source}，等级 {level}",
    maintenanceTaskSyncMedia: "从 Bangumi 同步动画/字幕和音乐，再从 LRCLIB 拉歌词，最后刷新页面语料",
    maintenanceTaskExportCorpus: "不联网，只用现有本地数据重新生成网页语料",
    maintenanceTaskFetchLexicalResources: "下载 JMdict 和 KANJIDIC2；之后点“刷新语料”才会出现在页面里",
    maintenanceTaskRefreshAll: "更新词表、中文词典、词语资源和动画数据库，再同步媒体、拉歌词并刷新语料",
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
    searchPlaceholder: "Search word, kana, meaning, form/root, title",
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
    showMoreWords: "Show {count} more",
    noWords: "No matching words",
    noStudyWords: "No reviewable words with examples in the current filter",
    count: "Count",
    examples: "Examples",
    exampleColumns: "Columns",
    exampleColumnsAuto: "Auto",
    chineseMeaning: "ZH",
    missingMeaning: "No meaning yet",
    noExamples: "No examples for this word yet",
    lexicalNotes: "Word knowledge",
    lexicalSpellings: "Spellings",
    lexicalReadings: "Alt. reading",
    lexicalPos: "Grammar",
    lexicalSenses: "Senses",
    lexicalKanji: "Kanji readings",
    lexicalExamples: "Dictionary examples",
    scene: "Scene",
    translation: "Translation",
    usageNote: "Usage",
    reannotateExample: "Refresh annotation",
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
    maintenanceStartFetchLexicalResources: "Update resources",
    maintenanceStartRefreshAll: "Refresh all",
    maintenanceStartAnnotate: "Start annotation",
    maintenanceReloaded: ", page refreshed",
    taskAnnotate: "LLM annotations",
    taskSyncMedia: "Sync",
    taskExportCorpus: "Export corpus",
    taskFetchLexicalResources: "Update word resources",
    taskRefreshAll: "Refresh all",
    scopeCurrentWord: "Current word",
    scopeFilteredWords: "Current filtered words",
    scopeFirstUnannotated: "First N missing examples",
    maintenanceEstimate: "About {count} examples; local LLM cache is checked first, API is used only for misses; source {source}, level {level}",
    maintenanceEstimateRefresh: "Regenerate about {count} examples and update the local LLM cache; source {source}, level {level}",
    maintenanceTaskSyncMedia: "Syncs Bangumi anime/subtitles and music, fetches LRCLIB lyrics, then refreshes the corpus",
    maintenanceTaskExportCorpus: "Uses existing local data only and regenerates the viewer corpus",
    maintenanceTaskFetchLexicalResources: "Downloads JMdict and KANJIDIC2; refresh the corpus afterwards to show them",
    maintenanceTaskRefreshAll: "Updates word/dictionary/lexical/anime data, syncs media, fetches lyrics, then refreshes the corpus",
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
  listLimit: WORD_LIST_PAGE_SIZE,
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
const searchIndexCache = new WeakMap();

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
    ...(word.level ? [statChip(word.level)] : []),
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

  header.append(titleRow, meanings, renderLexicalNotes(word), renderStatusActions(word));
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
    ...(word.level ? [statChip(word.level)] : []),
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
    card.append(renderLexicalNotes(word));
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
    const annotationBlock = renderExampleAnnotationBlock(word, example, {
      revealAnnotations,
      allowActions,
    });
    if (annotationBlock) {
      item.append(annotationBlock);
    }
    grid.append(item);
  });
  section.append(grid);
  return section;
}

function renderExampleActions(word, example) {
  const wrap = el("div", "example-actions");
  const button = el("button", "example-action-button", "↻");
  button.type = "button";
  button.title = t("reannotateExampleTitle");
  button.setAttribute("aria-label", t("reannotateExample"));
  button.disabled = !app.maintenance.enabled || app.maintenance.job?.status === "running";
  button.addEventListener("click", () => startExampleAnnotationJob(word, example, button));
  wrap.append(button);
  return wrap;
}

function renderExampleAnnotationBlock(word, example, options = {}) {
  const revealAnnotations = options.revealAnnotations ?? true;
  const allowActions = options.allowActions ?? true;
  const hasTranslation = revealAnnotations && example.translation_zh;
  const hasUsageNote = revealAnnotations && example.usage_note_zh;
  if (!hasTranslation && !hasUsageNote && !allowActions) {
    return null;
  }
  const block = el("div", `annotation-block ${hasTranslation || hasUsageNote ? "" : "empty"}`.trim());
  const lines = el("div", "annotation-lines");
  if (hasTranslation) {
    lines.append(el("div", "annotation-line translation-line", `${t("translation")}: ${example.translation_zh}`));
  }
  if (hasUsageNote) {
    lines.append(el("div", "annotation-line", `${t("usageNote")}: ${example.usage_note_zh}`));
  }
  block.append(lines);
  if (allowActions) {
    block.append(renderExampleActions(word, example));
  }
  return block;
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

function searchTerms(value) {
  return String(value || "")
    .normalize("NFKC")
    .trim()
    .split(/\s+/u)
    .map((term) => searchVariants(term))
    .filter((variants) => variants.length);
}

function searchScore(word, terms) {
  const index = searchIndexForWord(word);
  let total = 0;
  for (const variants of terms) {
    let best = 0;
    index.forEach((entry) => {
      variants.forEach((variant) => {
        best = Math.max(best, searchEntryScore(entry, variant));
      });
    });
    if (best <= 0) {
      return 0;
    }
    total += best;
  }
  return total;
}

function searchEntryScore(entry, term) {
  if (!term) {
    return 0;
  }
  const field = entry.value;
  if (!field || term.length > field.length + 6) {
    return 0;
  }
  if (field === term) {
    return 120 + entry.boost;
  }
  if (field.startsWith(term)) {
    return 95 + entry.boost;
  }
  if (field.includes(term)) {
    return 72 + entry.boost;
  }
  if (!allowsFuzzySearch(field, term)) {
    return 0;
  }
  const fuzzy = fuzzySubsequenceScore(field, term);
  return fuzzy > 0 ? fuzzy + Math.min(entry.boost, 20) : 0;
}

function searchIndexForWord(word) {
  const cached = searchIndexCache.get(word);
  if (cached) {
    return cached;
  }
  const entries = [];
  const add = (value, boost = 0) => {
    searchVariants(value).forEach((variant) => {
      if (variant) {
        entries.push({ value: variant, boost });
      }
    });
  };
  const notes = word.lexical_notes || {};
  const posText = [
    word.meaning_zh,
    word.meaning,
    ...asArray(notes.parts_of_speech),
  ].filter(Boolean).join(" ");

  add(word.word, 48);
  add(word.reading, 44);
  add(word.meaning_zh, 18);
  add(word.meaning, 12);
  add(word.level, 8);
  searchRootForms(word.word, posText).forEach((value) => add(value, 42));
  searchRootForms(word.reading, posText).forEach((value) => add(value, 38));

  asArray(notes.spellings).forEach((form) => {
    add(form.text, 40);
    searchRootForms(form.text, posText).forEach((value) => add(value, 36));
  });
  asArray(notes.readings).forEach((form) => {
    add(form.text, 38);
    searchRootForms(form.text, posText).forEach((value) => add(value, 34));
  });
  asArray(notes.parts_of_speech).forEach((value) => add(value, 12));
  asArray(notes.senses).forEach((sense) => {
    asArray(sense.glosses).forEach((value) => add(value, 10));
    asArray(sense.parts_of_speech).forEach((value) => add(value, 8));
    asArray(sense.tags).forEach((value) => add(value, 8));
  });
  asArray(notes.kanji).forEach((kanji) => {
    add(kanji.literal, 26);
    asArray(kanji.meanings).forEach((value) => add(value, 8));
    asArray(kanji.on_readings).forEach((value) => add(value, 16));
    asArray(kanji.kun_readings).forEach((value) => {
      add(value, 16);
      add(String(value || "").replace(/\./gu, ""), 18);
    });
  });
  asArray(notes.dictionary_examples).forEach((example) => {
    add(example.japanese, 8);
    Object.values(example.translations || {}).forEach((value) => add(value, 6));
  });
  asArray(word.sources).forEach((source) => {
    add(source.title, 14);
    add(source.artist, 12);
    add(source.album, 12);
  });
  asArray(word.examples).forEach((example) => {
    add(example.source_title, 12);
    add(example.source_artist, 12);
    add(example.source_album, 12);
    add(example.matched_text, 14);
    add(example.translation_zh, 4);
    add(example.usage_note_zh, 4);
  });

  const unique = [];
  const seen = new Set();
  entries.forEach((entry) => {
    const key = `${entry.value}\u0000${entry.boost}`;
    if (!seen.has(key)) {
      seen.add(key);
      unique.push(entry);
    }
  });
  searchIndexCache.set(word, unique);
  return unique;
}

function searchVariants(value) {
  const normalized = normalizeSearchValue(value);
  if (!normalized) {
    return [];
  }
  const variants = new Set([normalized]);
  const compact = compactSearchValue(normalized);
  if (compact) {
    variants.add(compact);
  }
  const romaji = kanaToRomaji(normalized);
  if (romaji && romaji !== normalized) {
    variants.add(compactSearchValue(romaji));
  }
  return [...variants].filter(Boolean);
}

function normalizeSearchValue(value) {
  return katakanaToHiragana(String(value || "").normalize("NFKC").toLowerCase().trim());
}

function compactSearchValue(value) {
  return normalizeSearchValue(value).replace(SEARCH_PUNCTUATION_RE, "");
}

function katakanaToHiragana(value) {
  return String(value || "").replace(/[\u30a1-\u30f6]/gu, (char) => {
    return String.fromCharCode(char.charCodeAt(0) - 0x60);
  });
}

function kanaToRomaji(value) {
  const textValue = katakanaToHiragana(value);
  if (!/[ぁ-ゖ]/u.test(textValue)) {
    return "";
  }
  let result = "";
  let doubleNext = false;
  for (let index = 0; index < textValue.length; index += 1) {
    const char = textValue[index];
    if (char === "っ") {
      doubleNext = true;
      continue;
    }
    const digraph = textValue.slice(index, index + 2);
    let roman = ROMAJI_DIGRAPHS[digraph];
    if (roman) {
      index += 1;
    } else if (char === "ー") {
      roman = result.slice(-1) || "";
    } else {
      roman = ROMAJI_KANA[char] || char;
    }
    if (doubleNext && /^[bcdfghjklmnpqrstvwxyz]/u.test(roman)) {
      result += roman[0];
    }
    doubleNext = false;
    result += roman;
  }
  return result;
}

function searchRootForms(value, posText = "") {
  const base = String(value || "").normalize("NFKC").trim();
  if (!base || !/[ぁ-ゖァ-ヺ一-龯々]/u.test(base)) {
    return [];
  }
  const forms = new Set();
  const add = (valueToAdd) => {
    if (valueToAdd && valueToAdd !== base) {
      forms.add(valueToAdd);
    }
  };
  const hiraBase = katakanaToHiragana(base);
  const pos = String(posText || "");

  if (base === "来る" || hiraBase === "くる") {
    ["来ない", "来ます", "来た", "来て", "来れば", "来よう", "こない", "きます", "きた", "きて", "くれば", "こよう"].forEach(add);
  }
  if (base.endsWith("する") || hiraBase.endsWith("する")) {
    const stem = base.slice(0, -2);
    ["し", "して", "した", "します", "しない", "すれば", "しよう", "される", "させる"].forEach((ending) => add(`${stem}${ending}`));
  }
  if ((pos.includes("一段") || pos.includes("Ichidan")) && base.endsWith("る")) {
    const stem = base.slice(0, -1);
    ["", "ない", "ます", "た", "て", "れば", "よう", "られる", "させる"].forEach((ending) => add(`${stem}${ending}`));
  } else if (pos.includes("五段") || pos.includes("Godan")) {
    addGodanSearchForms(base, add);
  }
  if ((pos.includes("い形容词") || pos.includes("adjective") || pos.includes("形容词")) && base.endsWith("い")) {
    const stem = base.slice(0, -1);
    ["く", "かった", "くない", "ければ", "そう"].forEach((ending) => add(`${stem}${ending}`));
  }
  return [...forms];
}

function addGodanSearchForms(base, add) {
  const ending = base.slice(-1);
  const rule = GODAN_ENDINGS[ending];
  if (!rule) {
    return;
  }
  const stem = base.slice(0, -1);
  const isIku = base === "行く" || katakanaToHiragana(base) === "いく" || katakanaToHiragana(base) === "ゆく";
  const teEnding = isIku ? "って" : rule.te;
  const taEnding = isIku ? "った" : rule.ta;
  [
    rule.a,
    `${rule.a}ない`,
    rule.i,
    `${rule.i}ます`,
    rule.e,
    `${rule.e}ば`,
    `${rule.o}う`,
    teEnding,
    taEnding,
    `${rule.a}れる`,
    `${rule.a}せる`,
  ].forEach((endingValue) => add(`${stem}${endingValue}`));
}

function allowsFuzzySearch(field, term) {
  if (term.length < 4 || field.length > 40) {
    return false;
  }
  if (/^[a-z0-9]+$/u.test(term) && term.length < 5) {
    return false;
  }
  if (/[ぁ-ゖー]/u.test(term)) {
    return /[ぁ-ゖー]/u.test(field);
  }
  if (/[\u3400-\u4dbf\u4e00-\u9fff]/u.test(term)) {
    return /[\u3400-\u4dbf\u4e00-\u9fff]/u.test(field);
  }
  return true;
}

function fuzzySubsequenceScore(field, term) {
  if (term.length < 2 || field.length > 80 || term.length > field.length) {
    return 0;
  }
  let position = 0;
  let firstMatch = -1;
  let lastMatch = -1;
  let gapPenalty = 0;
  for (const char of term) {
    const found = field.indexOf(char, position);
    if (found === -1) {
      return 0;
    }
    if (firstMatch === -1) {
      firstMatch = found;
    }
    if (lastMatch !== -1) {
      gapPenalty += Math.max(0, found - lastMatch - 1);
    }
    lastMatch = found;
    position = found + 1;
  }
  const span = lastMatch - firstMatch + 1;
  const density = term.length / span;
  return Math.max(12, Math.round(46 * density) - Math.min(gapPenalty, 20));
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
    return (left.level_number || 999) - (right.level_number || 999) || (right.count || 0) - (left.count || 0);
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

function renderLexicalNotes(word) {
  const notes = word.lexical_notes;
  if (!notes || typeof notes !== "object") {
    return document.createDocumentFragment();
  }
  const section = el("section", "lexical-notes");
  section.append(el("h3", "section-title", t("lexicalNotes")));
  const body = el("div", "lexical-note-grid");
  const spellingNodes = lexicalFormNodes(lexicalUsefulForms(notes.spellings, word.word));
  const readingNodes = lexicalFormNodes(lexicalUsefulForms(notes.readings, word.reading));
  const posNodes = lexicalPosNodes(notes.parts_of_speech);
  const senseNodes = app.lang === "zh" ? [] : lexicalSenseNodes(notes.senses);
  const kanjiNodes = app.lang === "zh" ? [] : lexicalKanjiNodes(notes.kanji, word);
  const dictionaryExampleNodes = lexicalDictionaryExampleNodes(notes.dictionary_examples);
  const hasUsefulNotes =
    spellingNodes.length > 0
    || readingNodes.length > 0
    || senseNodes.length > 0
    || kanjiNodes.length > 0
    || dictionaryExampleNodes.length > 0;
  if (!hasUsefulNotes) {
    return document.createDocumentFragment();
  }
  appendLexicalRow(body, t("lexicalSpellings"), spellingNodes);
  appendLexicalRow(body, t("lexicalReadings"), readingNodes);
  appendLexicalRow(body, t("lexicalPos"), posNodes);
  appendLexicalRow(body, t("lexicalSenses"), senseNodes, "lexical-note-values sense-values");
  appendLexicalRow(body, t("lexicalKanji"), kanjiNodes);
  appendLexicalRow(
    body,
    t("lexicalExamples"),
    dictionaryExampleNodes,
    "lexical-note-values lexical-example-values",
  );
  if (!body.childElementCount) {
    return document.createDocumentFragment();
  }
  section.append(body);
  return section;
}

function appendLexicalRow(parent, label, nodes, valueClassName = "lexical-note-values") {
  if (!nodes.length) {
    return;
  }
  const row = el("div", "lexical-note-row");
  row.append(el("span", "lexical-note-label", label));
  const values = el("div", valueClassName);
  nodes.forEach((node) => values.append(node));
  row.append(values);
  parent.append(row);
}

function lexicalUsefulForms(values, currentValue) {
  const forms = asArray(values).filter((form) => String(form.text || "").trim());
  if (forms.length <= 1 && forms[0]?.text === currentValue) {
    return [];
  }
  return forms;
}

function lexicalFormNodes(values) {
  return asArray(values).map((form) => {
    const chip = el("span", "lexical-chip lexical-form-chip");
    chip.append(document.createTextNode(String(form.text || "")));
    const tags = asArray(form.tags).filter(Boolean).join(" / ");
    if (tags) {
      chip.title = tags;
    }
    return chip;
  }).filter((node) => node.textContent.trim());
}

function lexicalTextNodes(values, className = "lexical-chip") {
  return asArray(values)
    .map((value) => String(value || "").trim())
    .filter(Boolean)
    .map((value) => el("span", className, value));
}

function lexicalPosNodes(values) {
  const labels = asArray(values)
    .map((value) => String(value || "").trim())
    .filter(Boolean);
  const visibleLabels = app.lang === "zh"
    ? labels.filter((label) => label !== "名词")
    : labels;
  return lexicalTextNodes(visibleLabels);
}

function lexicalSenseNodes(values) {
  return asArray(values).map((sense, index) => {
    const item = el("div", "lexical-sense");
    item.append(el("span", "lexical-sense-index", `${index + 1}.`));
    const textValue = asArray(sense.glosses)
      .map((value) => String(value || "").trim())
      .filter(Boolean)
      .join("; ");
    item.append(el("span", "lexical-sense-text", textValue));
    const tags = asArray(sense.tags).filter(Boolean);
    if (tags.length) {
      item.append(el("span", "lexical-sense-tags", tags.join(" / ")));
    }
    return item;
  }).filter((node) => node.textContent.trim());
}

function lexicalKanjiNodes(values, word) {
  if (isSingleKanjiWord(word.word)) {
    return [];
  }
  return asArray(values).map((kanji) => {
    const chip = el("span", "lexical-kanji-chip");
    chip.append(el("strong", "", String(kanji.literal || "")));
    const readings = [
      ...asArray(kanji.on_readings).slice(0, 2),
      ...asArray(kanji.kun_readings).slice(0, 1),
    ].filter(Boolean).slice(0, 4);
    if (readings.length) {
      chip.append(el("span", "lexical-kanji-reading", readings.join("・")));
    }
    return chip;
  }).filter((node) => node.textContent.trim());
}

function lexicalDictionaryExampleNodes(values) {
  return asArray(values).map((example) => {
    const japanese = String(example.japanese || example.sentence || "").trim();
    if (!japanese) {
      return null;
    }
    const item = el("div", "lexical-dictionary-example");
    item.append(el("div", "lexical-dictionary-example-ja", japanese));
    const translation = lexicalExampleTranslation(example);
    if (translation) {
      item.append(el("div", "lexical-dictionary-example-translation", translation));
    }
    return item;
  }).filter(Boolean);
}

function lexicalExampleTranslation(example) {
  const translations = example.translations || {};
  if (typeof translations === "string") {
    return translations.trim();
  }
  if (!translations || typeof translations !== "object") {
    return "";
  }
  if (app.lang === "zh") {
    return ["cmn", "zh", "zho", "chi"]
      .map((lang) => String(translations[lang] || "").trim())
      .find(Boolean) || "";
  }
  const preferred = ["eng", "en", "cmn", "zh", "zho", "chi"];
  for (const lang of preferred) {
    const value = String(translations[lang] || "").trim();
    if (value) {
      return value;
    }
  }
  return Object.values(translations)
    .map((value) => String(value || "").trim())
    .find(Boolean) || "";
}

function isSingleKanjiWord(value) {
  const textValue = String(value || "");
  return textValue.length === 1 && /[\u3400-\u4dbf\u4e00-\u9fff]/u.test(textValue);
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
    fetch_lexical_resources: "maintenanceTaskFetchLexicalResources",
    refresh_all: "maintenanceTaskRefreshAll",
  }[task];
  return key ? t(key) : "";
}

function maintenanceStartLabel(task) {
  const key = {
    sync_media: "maintenanceStartSyncMedia",
    export_corpus: "maintenanceStartExportCorpus",
    fetch_lexical_resources: "maintenanceStartFetchLexicalResources",
    refresh_all: "maintenanceStartRefreshAll",
    annotate: "maintenanceStartAnnotate",
  }[task];
  return key ? t(key) : t("maintenanceStart");
}

function maintenanceTaskLabel(task) {
  const key = {
    sync_media: "taskSyncMedia",
    export_corpus: "taskExportCorpus",
    fetch_lexical_resources: "taskFetchLexicalResources",
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

function asArray(value) {
  return Array.isArray(value) ? value : [];
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
