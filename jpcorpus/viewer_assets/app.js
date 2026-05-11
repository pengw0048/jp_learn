const STORAGE_LANG = "jpcorpus.viewer.lang";
const STORAGE_STATUS = "jpcorpus.viewer.status.v1";
const STORAGE_STUDY_COUNTS = "jpcorpus.viewer.studyCounts.v1";
const STORAGE_STUDY_SESSION = "jpcorpus.viewer.studySession.v2";
const STORAGE_STUDY_SCHEDULE = "jpcorpus.viewer.studySchedule.v1";
const STORAGE_EXAMPLE_COLUMNS = "jpcorpus.viewer.exampleColumns.v1";
const STORAGE_MODE = "jpcorpus.viewer.mode.v1";
const STORAGE_SPLIT_RATIOS = "jpcorpus.viewer.splitRatios.v1";
const STORAGE_READER_WORD_LIST = "jpcorpus.viewer.readerWordList.v1";
const WORD_LIST_PAGE_SIZE = 600;
const DAILY_STUDY_LIMIT = 30;
const STUDY_REVIEW_DELAY_DAYS = 1;
const EXAMPLE_COLUMN_VALUES = new Set(["auto", "1", "2", "3"]);
const MODE_VALUES = new Set(["browse", "study", "read"]);
const READER_WORD_LIST_VALUES = new Set(["all", "study", "N5", "N4", "N3", "N2", "N1"]);
const SPLIT_DEFAULT_RATIOS = {
  browse: 0.28,
  study: 0.28,
  read: 0.72,
};
const SPLIT_LIMITS = {
  browse: { minLeft: 300, minRight: 420 },
  study: { minLeft: 300, minRight: 420 },
  read: { minLeft: 420, minRight: 340 },
};
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
    sourceTexts: "文本",
    loadingTitle: "正在读取 corpus.json",
    loadingBody: "如果这里停住了，请确认本地服务能访问 corpus.json。",
    loadErrorTitle: "没有读到 corpus.json",
    loadErrorBody: "先运行导出命令，再重新打开 viewer。",
    allLevels: "全部",
    wordsFound: "{count} 个词",
    studyWordsFound: "今日 {count} 个词（复习 {review} + 新词 {new}）",
    showMoreWords: "再显示 {count} 个",
    noWords: "没有匹配的词",
    noStudyWords: "当前筛选下没有可加入今日学习的词",
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
    readMode: "阅读",
    studyProgress: "今日 {current} / {total}",
    revealAnswer: "看答案",
    hideAnswer: "收起答案",
    nextWord: "下一个",
    studyUnsure: "模糊",
    studyAgain: "还不熟",
    studyKnown: "已经会了",
    studyMastered: "已记住",
    studyChecks: "勾 {count}/{target}",
    studyCheckButton: "打勾 +1",
    studyHint: "先复习到期的词，再补新词；今天见过就打勾，满 7 勾算记住。",
    studyReview: "复习",
    studyNew: "新词",
    shows: "作品",
    subtitles: "字幕",
    lyrics: "歌词",
    texts: "文本",
    studyWords: "单词",
    maintenance: "维护",
    maintenanceTitle: "维护",
    configTitle: "配置状态",
    configEdit: "填写或更新 key",
    configSave: "保存配置",
    configSaved: "已保存到本地 .env",
    configSaveFailed: "保存失败：{error}",
    configPath: "保存到 {path}；密码和 key 不会回显，留空表示不修改已有值。",
    configReady: "已配置",
    configMissing: "缺少 {keys}",
    configLlmBaseUrl: "LLM Base URL",
    configLlmModel: "LLM Model",
    configLlmApiKey: "LLM API Key",
    quickActionsTitle: "常用操作",
    quickActionsHelp: "平时点“刷新”就够了；词典或词表需要重拉时再用“完整刷新”。",
    sourceInventoryTitle: "来源概览",
    sourceInventoryHelp: "按当前页面语料统计，用来确认字幕、歌词、小说是否已经进库。",
    sourceInventoryEmpty: "还没有来源数据",
    sourceInventoryWords: "词",
    sourceInventoryExamples: "例句",
    sourceInventoryFiles: "文件",
    sourceInventoryTokens: "词形",
    sourceInventoryAnnotated: "标注",
    sourceInventoryUnknown: "未知来源",
    sourceInventoryView: "查看",
    sourceInventoryRead: "阅读",
    sourceInventoryBack: "返回",
    sourceInventoryEpisodes: "集",
    sourceInventoryTracks: "曲",
    sourceInventorySnippets: "片段",
    sourceInventoryExpand: "展开 {count} 集",
    sourceInventoryCollapse: "收起",
    sourceInventoryLines: "行",
    sourceReaderTitle: "阅读器",
    sourceReaderFallback: "当前 corpus 还没有完整阅读数据，先显示已抽取的例句片段；点“刷新”后会生成完整来源行。",
    sourceReaderEmpty: "这个来源还没有可显示的阅读内容",
    readerSourcesFound: "{count} 个来源",
    readerSourceChoice: "阅读来源",
    readerItemChoice: "阅读内容",
    readerWordListChoice: "高亮词表",
    readerWordListAll: "全部词",
    readerWordListStudy: "今日学习",
    readerCurrentHint: "点高亮词或右侧词 chip 查看解释",
    llmHelp: "使用配置里的 Provider；会先查本地缓存，缺失时才调用模型。任务中断后，重跑会复用已完成的缓存结果。",
    maintenanceScope: "范围",
    maintenanceProvider: "Provider",
    maintenanceLimit: "上限",
    maintenanceConcurrency: "并发",
    maintenanceRpm: "RPM",
    maintenanceOverwrite: "覆盖已有标注",
    maintenanceShowContext: "使用作品简介",
    maintenanceStartSyncMedia: "刷新",
    maintenanceStartExportCorpus: "刷新语料",
    maintenanceStartFetchLexicalResources: "更新资源",
    maintenanceStartRefreshAll: "完整刷新",
    maintenanceStartAnnotate: "开始标注",
    maintenanceReloaded: "，页面已刷新",
    taskAnnotate: "LLM 标注",
    taskSyncMedia: "刷新",
    taskExportCorpus: "刷新语料",
    taskFetchLexicalResources: "更新词语资源",
    taskRefreshAll: "完整刷新",
    scopeCurrentWord: "当前词",
    scopeFilteredWords: "当前筛选结果",
    scopeFirstUnannotated: "前 N 条缺失例句",
    maintenanceEstimate: "将处理约 {count} 条例句；会先查本地 LLM 缓存，缺失时才调用 API；来源：{source}；等级：{level}",
    maintenanceEstimateRefresh: "将重新生成约 {count} 条例句，并更新本地 LLM 缓存；来源：{source}；等级：{level}",
    maintenanceTaskSyncMedia: "同步动画、字幕、音乐和歌词，并重新生成页面语料",
    maintenanceTaskExportCorpus: "不联网，只用现有本地数据重新生成网页语料",
    maintenanceTaskFetchLexicalResources: "下载 JMdict 和 KANJIDIC2；之后点“刷新语料”才会出现在页面里",
    maintenanceTaskRefreshAll: "词典、词表和动画库也一起更新；平时不用点这个",
    maintenanceDisabled: "维护 API 未启用",
    maintenanceIdle: "还没有运行任务",
    maintenanceRunningTask: "正在运行：{task}，开始 {time}",
    maintenanceSucceededTask: "上次完成：{task}{reload}，完成 {time}",
    maintenanceFailedTask: "上次失败：{task}，结束 {time}",
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
    sourceTexts: "Texts",
    loadingTitle: "Loading corpus.json",
    loadingBody: "If this does not change, make sure the local server can read corpus.json.",
    loadErrorTitle: "Could not read corpus.json",
    loadErrorBody: "Export the corpus first, then reload the viewer.",
    allLevels: "All",
    wordsFound: "{count} words",
    studyWordsFound: "Today {count} words ({review} review + {new} new)",
    showMoreWords: "Show {count} more",
    noWords: "No matching words",
    noStudyWords: "No words can be added to today's study set in the current filter",
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
    readMode: "Read",
    studyProgress: "Today {current} / {total}",
    revealAnswer: "Reveal",
    hideAnswer: "Hide answer",
    nextWord: "Next",
    studyUnsure: "Unsure",
    studyAgain: "Still shaky",
    studyKnown: "Already know it",
    studyMastered: "Mastered",
    studyChecks: "{count}/{target} checks",
    studyCheckButton: "Add check +1",
    studyHint: "Review due words first, then fill with new words. Seven checks means mastered.",
    studyReview: "Review",
    studyNew: "New",
    shows: "Shows",
    subtitles: "Subtitles",
    lyrics: "Lyrics",
    texts: "Texts",
    studyWords: "Study words",
    maintenance: "Maintain",
    maintenanceTitle: "Maintenance",
    configTitle: "Configuration",
    configEdit: "Fill or update keys",
    configSave: "Save config",
    configSaved: "Saved to local .env",
    configSaveFailed: "Save failed: {error}",
    configPath: "Saved to {path}. Secrets are not echoed back; blank fields keep existing values.",
    configReady: "Configured",
    configMissing: "Missing {keys}",
    configLlmBaseUrl: "LLM Base URL",
    configLlmModel: "LLM model",
    configLlmApiKey: "LLM API key",
    quickActionsTitle: "Common actions",
    quickActionsHelp: "Use Refresh day to day; use Full refresh only when dictionaries or word lists need refetching.",
    sourceInventoryTitle: "Sources",
    sourceInventoryHelp: "Built from the current viewer corpus so you can confirm subtitles, lyrics, and texts were imported.",
    sourceInventoryEmpty: "No source data yet",
    sourceInventoryWords: "Words",
    sourceInventoryExamples: "Examples",
    sourceInventoryFiles: "Files",
    sourceInventoryTokens: "Tokens",
    sourceInventoryAnnotated: "Annotated",
    sourceInventoryUnknown: "Unknown source",
    sourceInventoryView: "View",
    sourceInventoryRead: "Read",
    sourceInventoryBack: "Back",
    sourceInventoryEpisodes: "Episodes",
    sourceInventoryTracks: "Tracks",
    sourceInventorySnippets: "Snippets",
    sourceInventoryExpand: "Show {count} more",
    sourceInventoryCollapse: "Collapse",
    sourceInventoryLines: "Lines",
    sourceReaderTitle: "Reader",
    sourceReaderFallback: "This corpus has no full reader data yet, so extracted examples are shown for now. Refresh to generate full source lines.",
    sourceReaderEmpty: "No readable content for this source yet",
    readerSourcesFound: "{count} sources",
    readerSourceChoice: "Reading source",
    readerItemChoice: "Reading item",
    readerWordListChoice: "Highlighted words",
    readerWordListAll: "All words",
    readerWordListStudy: "Today",
    readerCurrentHint: "Click highlighted words or right-side chips to inspect them",
    llmHelp: "Uses the configured provider. Local cache is checked before model calls; reruns reuse completed cached results after interruptions.",
    maintenanceScope: "Scope",
    maintenanceProvider: "Provider",
    maintenanceLimit: "Limit",
    maintenanceConcurrency: "Concurrency",
    maintenanceRpm: "RPM",
    maintenanceOverwrite: "Overwrite annotations",
    maintenanceShowContext: "Use show context",
    maintenanceStartSyncMedia: "Refresh",
    maintenanceStartExportCorpus: "Refresh corpus",
    maintenanceStartFetchLexicalResources: "Update resources",
    maintenanceStartRefreshAll: "Full refresh",
    maintenanceStartAnnotate: "Start annotation",
    maintenanceReloaded: ", page refreshed",
    taskAnnotate: "LLM annotations",
    taskSyncMedia: "Refresh",
    taskExportCorpus: "Export corpus",
    taskFetchLexicalResources: "Update word resources",
    taskRefreshAll: "Full refresh",
    scopeCurrentWord: "Current word",
    scopeFilteredWords: "Current filtered words",
    scopeFirstUnannotated: "First N missing examples",
    maintenanceEstimate: "About {count} examples; local LLM cache is checked first, API is used only for misses; source: {source}; level: {level}",
    maintenanceEstimateRefresh: "Regenerate about {count} examples and update the local LLM cache; source: {source}; level: {level}",
    maintenanceTaskSyncMedia: "Sync anime, subtitles, music, and lyrics, then regenerate the viewer corpus",
    maintenanceTaskExportCorpus: "Uses existing local data only and regenerates the viewer corpus",
    maintenanceTaskFetchLexicalResources: "Downloads JMdict and KANJIDIC2; refresh the corpus afterwards to show them",
    maintenanceTaskRefreshAll: "Also refetches dictionaries, word lists, and the anime database; rarely needed day to day",
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
  sourcePanelType: null,
  sourcePanelGroupKey: null,
  expandedSourceGroups: new Set(),
  reader: {
    sourceType: "all",
    groupKey: null,
    documentKey: null,
    wordList: readReaderWordList(),
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
  maintenance: {
    enabled: false,
    job: null,
    config: null,
    llm: null,
    task: "annotate",
    pollTimer: null,
    reloadedJobId: null,
  },
};
const searchIndexCache = new WeakMap();

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
  maintenanceScope: $("#maintenance-scope"),
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
  refs.configForm.addEventListener("toggle", () => {
    refs.configForm.dataset.userToggled = "1";
  });
  [
    refs.maintenanceScope,
    refs.configLlmProvider,
    refs.maintenanceLimit,
    refs.maintenanceConcurrency,
    refs.maintenanceRpm,
    refs.maintenanceOverwrite,
    refs.maintenanceShowContext,
  ].forEach((control) => {
    control.addEventListener("input", renderMaintenance);
    control.addEventListener("change", renderMaintenance);
  });
  refs.maintenanceStart.addEventListener("click", () => startMaintenanceJob("annotate"));
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

function clampNumber(value, min, max) {
  if (!Number.isFinite(value)) {
    return min;
  }
  return Math.min(Math.max(value, min), max);
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
    const response = await fetch("/api/maintenance", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
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
  const spec = annotationJobSpec();
  const estimate = estimateAnnotationJob(spec);
  const job = app.maintenance.job;
  refs.maintenanceToggle.disabled = !app.maintenance.enabled;
  refs.maintenanceActionButtons.forEach((button) => {
    button.disabled = !app.maintenance.enabled || job?.status === "running";
    button.classList.toggle("active", button.dataset.maintenanceTask === task && job?.status === "running");
  });
  if (!app.maintenance.enabled) {
    refs.maintenanceEstimate.textContent = t("maintenanceDisabled");
  } else {
    refs.maintenanceEstimate.textContent = t(
      spec.bypass_cache ? "maintenanceEstimateRefresh" : "maintenanceEstimate",
      {
        count: formatNumber(estimate.planned),
        source: sourceLabel(spec.source),
        level: levelLabel(spec.level),
      },
    );
  }
  refs.maintenanceStart.disabled =
    !app.maintenance.enabled || job?.status === "running" || estimate.planned <= 0;
  refs.maintenanceStatus.textContent = job ? maintenanceStatusLabel(job) : t("maintenanceIdle");
  renderMaintenanceProgress(job);
  refs.maintenanceLog.textContent = job?.log?.join("\n") || "";
  updateExampleActionButtons();
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

function renderSourceInventory() {
  if (!refs.sourceInventory) {
    return;
  }
  if (refs.sourcePanel.hidden) {
    return;
  }
  const groups = buildSourceGroups(app.sourcePanelType);
  const selected = groups.find((group) => group.key === app.sourcePanelGroupKey);
  if (selected) {
    refs.sourceInventory.replaceChildren(renderSourceGroupDetail(selected));
    return;
  }
  if (groups.length === 0) {
    refs.sourceInventory.replaceChildren(emptyMessage(t("sourceInventoryEmpty")));
    return;
  }
  refs.sourceInventory.replaceChildren(...groups.map(renderSourceGroupItem));
}

function buildSourceItems() {
  const sourceStats = new Map(
    asArray(app.corpus?.shows).map((item) => [normalizedTextTitle(item.title), item]),
  );
  const sources = new Map();

  function ensureSource(type, title, artist = "", album = "") {
    const key = [type, title, artist, album].join("\u0000");
    if (!sources.has(key)) {
      const stats = sourceStats.get(normalizedTextTitle(title)) || {};
      sources.set(key, {
        type,
        title,
        artist,
        album,
        hasStats: Boolean(stats.total_tokens),
        files: new Set(),
        words: new Set(),
        sourceDocuments: [],
        readerLineCount: 0,
        exampleCount: 0,
        exampleItems: [],
        annotated: 0,
        fileCount: Number(stats.subtitle_file_count) || 0,
        tokens: Number(stats.total_tokens) || 0,
      });
    }
    return sources.get(key);
  }

  asArray(app.corpus?.sources).forEach((document) => {
    const type = document.source_type || "subtitle";
    const title = String(document.source_title || document.source_file || t("sourceInventoryUnknown")).trim();
    const artist = String(document.source_artist || "").trim();
    const album = String(document.source_album || "").trim();
    const entry = ensureSource(type, title, artist, album);
    entry.sourceDocuments.push(document);
    entry.readerLineCount += asArray(document.lines).length;
    if (!entry.hasStats) {
      entry.tokens += Number(document.token_count) || 0;
    }
    const file = document.source_file || document.subtitle_file;
    if (file) {
      entry.files.add(file);
    }
    asArray(document.lines).forEach((line) => {
      asArray(line.matches).forEach((match) => {
        if (match.word) {
          entry.words.add(match.word);
        }
      });
    });
  });

  app.words.forEach((word) => {
    asArray(word.examples).forEach((example) => {
      const type = example.source_type || "subtitle";
      const title = String(example.source_title || example.subtitle_file || t("sourceInventoryUnknown")).trim();
      const artist = String(example.source_artist || "").trim();
      const album = String(example.source_album || "").trim();
      const entry = ensureSource(type, title, artist, album);
      entry.exampleCount += 1;
      entry.exampleItems.push({ word, example });
      if (word.word) {
        entry.words.add(word.word);
      }
      const file = example.reference?.source_file || example.subtitle_file;
      if (file) {
        entry.files.add(file);
      }
      if (hasExampleAnnotations(example)) {
        entry.annotated += 1;
      }
    });
  });
  sources.forEach((entry) => {
    entry.fileCount = Math.max(entry.fileCount, entry.files.size);
  });
  return [...sources.values()].sort(compareSourceInventoryItems);
}

function buildSourceGroups(sourceType) {
  const groups = new Map();
  buildSourceItems()
    .filter((source) => !sourceType || source.type === sourceType)
    .forEach((source) => {
      const groupKey = sourceGroupKey(source);
      if (!groups.has(groupKey)) {
        groups.set(groupKey, createSourceGroup(source, groupKey));
      }
      addSourceToGroup(groups.get(groupKey), source);
    });
  return [...groups.values()].sort(compareSourceInventoryItems);
}

function sourceGroupKey(source) {
  if (source.type === "lyrics") {
    return [source.type, source.album || source.artist || source.title].join("\u0000");
  }
  return [source.type, source.title].join("\u0000");
}

function createSourceGroup(source, key) {
  const title = source.type === "lyrics"
    ? (source.album || source.artist || source.title)
    : source.title;
  const meta = source.type === "lyrics" && source.album
    ? source.artist
    : "";
  return {
    key,
    type: source.type,
    title,
    meta,
    files: new Set(),
    words: new Set(),
    sourceDocuments: [],
    children: [],
    readerLineCount: 0,
    exampleItems: [],
    exampleCount: 0,
    annotated: 0,
    fileCount: 0,
    tokens: 0,
  };
}

function addSourceToGroup(group, source) {
  source.files.forEach((file) => group.files.add(file));
  source.words.forEach((word) => group.words.add(word));
  group.sourceDocuments.push(...source.sourceDocuments);
  group.readerLineCount += source.readerLineCount;
  group.exampleItems.push(...source.exampleItems);
  group.exampleCount += source.exampleCount;
  group.annotated += source.annotated;
  group.fileCount += source.fileCount || source.files.size;
  group.tokens += source.tokens;
  group.children.push(...sourceChildren(source));
}

function sourceChildren(source) {
  if (source.sourceDocuments?.length) {
    return sourceDocumentChildren(source);
  }
  if (source.type === "subtitle") {
    return subtitleEpisodeChildren(source);
  }
  if (source.type === "lyrics") {
    return [{
      label: source.title,
      meta: [source.artist, source.album && source.album !== source.title ? source.album : ""]
        .filter(Boolean)
        .join(" · "),
      examples: source.exampleCount,
    }];
  }
  return [...source.files].sort().map((file) => ({
    label: source.title,
    meta: file,
    examples: countExamplesForFile(source, file),
  }));
}

function sourceDocumentChildren(source) {
  if (source.type === "subtitle") {
    return subtitleDocumentChildren(source);
  }
  return source.sourceDocuments
    .map((document) => ({
      label: source.type === "lyrics"
        ? (document.source_title || source.title)
        : cleanSourceFileLabel(document.source_file || document.source_title || source.title),
      meta: source.type === "lyrics"
        ? [document.source_artist, document.source_album && document.source_album !== document.source_title ? document.source_album : ""]
          .filter(Boolean)
          .join(" · ")
        : "",
      lines: asArray(document.lines).length,
      files: [document.source_file].filter(Boolean),
    }))
    .sort((left, right) => left.label.localeCompare(right.label, app.lang === "zh" ? "zh-CN" : "ja-JP"));
}

function subtitleDocumentChildren(source) {
  const episodes = new Map();
  source.sourceDocuments.forEach((document) => {
    const file = document.source_file || "";
    const episode = Number.isInteger(document.episode) ? document.episode : null;
    const key = episode === null ? `file:${file || source.title}` : `episode:${episode}`;
    if (!episodes.has(key)) {
      episodes.set(key, {
        episode,
        files: new Set(),
        lines: 0,
        label: episode === null ? cleanSourceFileLabel(file || source.title) : formatEpisodeLabel(episode),
      });
    }
    const entry = episodes.get(key);
    if (file) {
      entry.files.add(file);
    }
    entry.lines += asArray(document.lines).length;
  });
  return [...episodes.values()]
    .sort(compareSubtitleChildren)
    .map((entry) => ({
      label: entry.label,
      meta: entry.files.size > 1 ? `${formatNumber(entry.files.size)} ${t("sourceInventoryFiles")}` : "",
      lines: entry.lines,
      files: [...entry.files].sort(),
    }));
}

function subtitleEpisodeChildren(source) {
  const episodes = new Map();
  source.exampleItems.forEach(({ example }) => {
    const file = example.reference?.source_file || example.subtitle_file || "";
    const episode = Number.isInteger(example.episode) ? example.episode : null;
    const key = episode === null ? `file:${file || source.title}` : `episode:${episode}`;
    if (!episodes.has(key)) {
      episodes.set(key, {
        episode,
        files: new Set(),
        examples: 0,
        label: episode === null ? cleanSourceFileLabel(file || source.title) : formatEpisodeLabel(episode),
      });
    }
    const entry = episodes.get(key);
    if (file) {
      entry.files.add(file);
    }
    entry.examples += 1;
  });
  return [...episodes.values()]
    .sort(compareSubtitleChildren)
    .map((entry) => ({
      label: entry.label,
      meta: entry.files.size > 1 ? `${formatNumber(entry.files.size)} ${t("sourceInventoryFiles")}` : "",
      examples: entry.examples,
      files: [...entry.files].sort(),
    }));
}

function compareSubtitleChildren(left, right) {
  if (left.episode !== null && right.episode !== null) {
    return left.episode - right.episode;
  }
  if (left.episode !== null) {
    return -1;
  }
  if (right.episode !== null) {
    return 1;
  }
  return left.label.localeCompare(right.label, app.lang === "zh" ? "zh-CN" : "ja-JP");
}

function formatEpisodeLabel(episode) {
  return `EP${String(episode).padStart(2, "0")}`;
}

function cleanSourceFileLabel(value) {
  return fileStem(value)
    .replace(/\[[^\]]+\]/gu, "")
    .replace(/\([^)]*\)/gu, "")
    .replace(/[_．.]+/gu, " ")
    .replace(/\s+/gu, " ")
    .trim() || value;
}

function countExamplesForFile(source, file) {
  return source.exampleItems.filter(({ example }) => (
    (example.reference?.source_file || example.subtitle_file) === file
  )).length;
}

function compareSourceInventoryItems(left, right) {
  const typeOrder = { subtitle: 0, lyrics: 1, text: 2 };
  const typeDiff = (typeOrder[left.type] ?? 9) - (typeOrder[right.type] ?? 9);
  if (typeDiff !== 0) {
    return typeDiff;
  }
  return left.title.localeCompare(right.title, app.lang === "zh" ? "zh-CN" : "ja-JP");
}

function renderSourceGroupItem(source) {
  const item = el("article", `source-card source-card-${source.type || "unknown"}`);
  const heading = el("div", "source-card-heading");
  const kind = el("span", "source-kind", sourceLabel(source.type));
  const title = el("strong", "source-title", source.title || t("sourceInventoryUnknown"));
  heading.append(kind, title);
  if (source.meta) {
    heading.append(el("span", "source-meta", source.meta));
  }

  const action = el("button", "source-view-button", t("sourceInventoryView"));
  action.type = "button";
  action.addEventListener("click", () => {
    app.sourcePanelGroupKey = source.key;
    renderSourceInventory();
  });
  const readAction = el("button", "source-read-button", t("sourceInventoryRead"));
  readAction.type = "button";
  readAction.addEventListener("click", () => {
    openSourceInReader(source);
  });
  const actions = el("div", "source-card-actions");
  actions.append(action, readAction);

  const top = el("div", "source-card-top");
  top.append(heading, actions);
  item.append(top, renderSourceMetrics(source));

  const collapsedPreviewLimit = source.type === "subtitle" ? 4 : 6;
  const canToggle = source.type === "subtitle" && source.children.length > collapsedPreviewLimit;
  const expanded = canToggle && app.expandedSourceGroups.has(source.key);
  const visibleChildren = expanded ? source.children : source.children.slice(0, collapsedPreviewLimit);
  const childList = renderSourceChildren(visibleChildren, source.type, {
    showFileDetails: false,
  });
  if (childList) {
    item.append(childList);
  }
  if (canToggle) {
    const toggle = el(
      "button",
      "source-expand-button",
      expanded
        ? t("sourceInventoryCollapse")
        : t("sourceInventoryExpand", { count: formatNumber(source.children.length - collapsedPreviewLimit) }),
    );
    toggle.type = "button";
    toggle.addEventListener("click", () => {
      if (expanded) {
        app.expandedSourceGroups.delete(source.key);
      } else {
        app.expandedSourceGroups.add(source.key);
      }
      renderSourceInventory();
    });
    item.append(toggle);
  }
  return item;
}

function renderSourceGroupDetail(source) {
  const detail = el("article", `source-detail source-card-${source.type || "unknown"}`);
  const back = el("button", "source-back-button", `‹ ${t("sourceInventoryBack")}`);
  back.type = "button";
  back.addEventListener("click", () => {
    app.sourcePanelGroupKey = null;
    renderSourceInventory();
  });
  const heading = el("div", "source-detail-heading");
  heading.append(back, el("h3", "", source.title || t("sourceInventoryUnknown")));
  if (source.meta) {
    heading.append(el("span", "source-meta", source.meta));
  }
  const readAction = el("button", "source-read-button", t("sourceInventoryRead"));
  readAction.type = "button";
  readAction.addEventListener("click", () => {
    openSourceInReader(source);
  });
  heading.append(readAction);
  detail.append(heading, renderSourceMetrics(source));

  const children = renderSourceChildren(source.children, source.type, {
    showFileDetails: true,
  });
  if (children) {
    detail.append(children);
  }

  return detail;
}

function openSourceInReader(source) {
  app.mode = "read";
  localStorage.setItem(STORAGE_MODE, app.mode);
  app.reader.sourceType = source.type || "all";
  app.reader.groupKey = source.key;
  app.reader.documentKey = null;
  refs.maintenancePanel.hidden = true;
  refs.maintenanceToggle.classList.remove("active");
  hideSourcePanel();
  render();
}

function renderSourceMetrics(source) {
  const metrics = el("div", "source-metrics");
  const childLabel = source.type === "lyrics" ? t("sourceInventoryTracks") : t("sourceInventoryEpisodes");
  [
    [source.type === "text" ? t("sourceInventoryFiles") : childLabel, source.children?.length || 0],
    [t("sourceInventoryFiles"), source.fileCount || source.files.size],
    [t("sourceInventoryTokens"), source.tokens],
    [t("sourceInventoryWords"), source.words.size],
    [t("sourceInventoryLines"), source.readerLineCount],
    [t("sourceInventoryExamples"), source.exampleCount],
    [t("sourceInventoryAnnotated"), `${formatNumber(source.annotated)}/${formatNumber(source.exampleCount)}`],
  ].forEach(([label, value], index) => {
    if ((value === 0 || value === "0/0") || (index === 1 && source.type === "text")) {
      return;
    }
    const metric = el("span", "source-metric");
    metric.append(el("span", "", label), strong(value));
    metrics.append(metric);
  });
  return metrics;
}

function renderSourceChildren(children, sourceType, options = {}) {
  const showFileDetails = options.showFileDetails ?? false;
  if (!children || children.length === 0 || sourceType === "text") {
    return null;
  }
  const list = el("div", "source-child-list");
  children.forEach((child) => {
    const row = el("div", "source-child-row");
    row.append(strong(child.label));
    row.append(el("span", "", child.meta || ""));
    if (child.examples || child.lines) {
      const count = child.examples || child.lines;
      const label = child.examples ? t("sourceInventoryExamples") : t("sourceInventoryLines");
      row.append(el("small", "", `${formatNumber(count)} ${label}`));
    }
    list.append(row);
    if (showFileDetails && child.files?.length > 0) {
      const files = el("div", "source-file-list");
      child.files.forEach((file) => {
        files.append(el("div", "", cleanSourceFileLabel(file)));
      });
      list.append(files);
    }
  });
  return list;
}

function renderSourceReader(source, options = {}) {
  const reader = el("section", `source-reader${options.full ? " reader-full" : ""}`);
  const heading = el("div", "source-reader-heading");
  heading.append(el("h4", "", t("sourceReaderTitle")));
  const documents = options.documents || readerDocumentsForSource(source);
  if (!source.sourceDocuments?.length && source.exampleItems.length > 0) {
    heading.append(el("span", "", t("sourceReaderFallback")));
  }
  reader.append(heading);
  if (documents.length === 0) {
    reader.append(emptyMessage(t("sourceReaderEmpty")));
    return reader;
  }
  documents.forEach((document, index) => {
    reader.append(renderReaderDocument(document, index === 0 || documents.length === 1, options));
  });
  return reader;
}

function readerDocumentsForSource(source) {
  if (source.sourceDocuments?.length) {
    return source.sourceDocuments
      .map(normalizeReaderDocument)
      .sort(compareReaderDocuments);
  }
  return fallbackReaderDocuments(source).sort(compareReaderDocuments);
}

function normalizeReaderDocument(document) {
  return {
    source_type: document.source_type || "subtitle",
    source_title: document.source_title || document.source_file || "",
    source_artist: document.source_artist || "",
    source_album: document.source_album || "",
    source_file: document.source_file || "",
    episode: Number.isInteger(document.episode) ? document.episode : null,
    lines: asArray(document.lines).map((line) => ({
      text: line.text || "",
      start_ms: Number.isInteger(line.start_ms) ? line.start_ms : null,
      end_ms: Number.isInteger(line.end_ms) ? line.end_ms : null,
      matches: normalizeReaderMatches(line.text || "", line.matches),
    })),
  };
}

function fallbackReaderDocuments(source) {
  const documents = new Map();
  source.exampleItems.forEach(({ word, example }) => {
    const file = example.reference?.source_file || example.subtitle_file || "";
    const key = [
      example.source_type || source.type,
      example.source_title || source.title,
      example.source_artist || "",
      example.source_album || "",
      file,
      Number.isInteger(example.episode) ? example.episode : "",
    ].join("\u0000");
    if (!documents.has(key)) {
      documents.set(key, {
        source_type: example.source_type || source.type,
        source_title: example.source_title || source.title,
        source_artist: example.source_artist || "",
        source_album: example.source_album || "",
        source_file: file,
        episode: Number.isInteger(example.episode) ? example.episode : null,
        lines: [],
      });
    }
    const document = documents.get(key);
    const text = example.sentence || "";
    const lineKey = [example.start_ms ?? "", text].join("\u0000");
    let line = document.lines.find((item) => item.key === lineKey);
    if (!line) {
      line = {
        key: lineKey,
        text,
        start_ms: Number.isInteger(example.start_ms) ? example.start_ms : null,
        end_ms: Number.isInteger(example.end_ms) ? example.end_ms : null,
        matches: [],
      };
      document.lines.push(line);
    }
    const matchedText = example.matched_text || word.word || "";
    const start = matchedText ? text.indexOf(matchedText) : -1;
    line.matches.push({
      word: word.word || matchedText,
      matched_text: matchedText,
      reading: word.reading || "",
      level: Number.isInteger(word.level_number) ? word.level_number : null,
      start: start >= 0 ? start : null,
      end: start >= 0 ? start + matchedText.length : null,
    });
  });
  return [...documents.values()].map((document) => ({
    ...document,
    lines: document.lines
      .map(({ key, ...line }) => ({
        ...line,
        matches: normalizeReaderMatches(line.text, line.matches),
      }))
      .sort(compareReaderLines),
  }));
}

function normalizeReaderMatches(text, matches) {
  return asArray(matches)
    .map((match) => {
      const word = String(match.word || match.matched_text || "").trim();
      const matchedText = String(match.matched_text || word).trim();
      let start = Number.isInteger(match.start) ? match.start : null;
      let end = Number.isInteger(match.end) ? match.end : null;
      if ((start === null || end === null) && matchedText) {
        const index = text.indexOf(matchedText);
        if (index >= 0) {
          start = index;
          end = index + matchedText.length;
        }
      }
      return {
        ...match,
        word,
        matched_text: matchedText,
        start,
        end,
      };
    })
    .filter((match) => match.word && match.matched_text);
}

function renderReaderDocument(document, open, options = {}) {
  const details = el("details", "reader-document");
  details.open = open;
  const summary = el("summary", "");
  summary.append(
    strong(readerDocumentLabel(document)),
    el("span", "", `${formatNumber(document.lines.length)} ${t("sourceInventoryLines")}`),
  );
  details.append(summary);
  const lines = el("div", "reader-lines");
  document.lines.forEach((line) => {
    lines.append(renderReaderLine(line, options));
  });
  details.append(lines);
  return details;
}

function readerDocumentLabel(document) {
  if (document.source_type === "subtitle") {
    const episode = Number.isInteger(document.episode) ? `${formatEpisodeLabel(document.episode)} ` : "";
    return `${episode}${cleanSourceFileLabel(document.source_file || document.source_title)}`;
  }
  if (document.source_type === "lyrics") {
    return [document.source_title, document.source_artist].filter(Boolean).join(" · ");
  }
  return cleanSourceFileLabel(document.source_file || document.source_title);
}

function renderReaderLine(line, options = {}) {
  const row = el("div", "reader-line");
  const time = Number.isInteger(line.start_ms) ? formatTimestamp(line.start_ms) : "";
  row.append(el("span", "reader-line-time", time));
  const textLine = el("div", "reader-line-text");
  appendReaderHighlighted(textLine, line.text, line.matches, options);
  row.append(textLine);
  const words = uniqueReaderWords(line.matches, options);
  if (words.length > 0) {
    const wordList = el("div", "reader-line-words");
    words.forEach((match) => {
      const word = findWord(match.word);
      const chip = el("button", "reader-word-chip", match.word);
      chip.type = "button";
      if (word?.level) {
        chip.append(el("small", "", word.level));
      }
      chip.dataset.word = match.word;
      chip.addEventListener("click", () => selectReaderWord(match.word));
      wordList.append(chip);
    });
    row.append(wordList);
  }
  return row;
}

function appendReaderHighlighted(target, text, matches, options = {}) {
  const validMatches = asArray(matches)
    .filter((match) => readerWordAllowed(match.word, options.wordSet))
    .filter((match) => Number.isInteger(match.start) && Number.isInteger(match.end))
    .filter((match) => match.start >= 0 && match.end > match.start && match.end <= text.length)
    .sort((left, right) => left.start - right.start || right.end - left.end);
  let cursor = 0;
  validMatches.forEach((match) => {
    if (match.start < cursor) {
      return;
    }
    if (match.start > cursor) {
      target.append(document.createTextNode(text.slice(cursor, match.start)));
    }
    const button = el("button", "reader-token", text.slice(match.start, match.end));
    button.type = "button";
    button.title = match.word;
    button.dataset.word = match.word;
    button.addEventListener("click", () => selectReaderWord(match.word));
    target.append(button);
    cursor = match.end;
  });
  if (cursor < text.length) {
    target.append(document.createTextNode(text.slice(cursor)));
  }
  if (target.childNodes.length === 0) {
    target.textContent = text;
  }
}

function uniqueReaderWords(matches, options = {}) {
  const seen = new Set();
  const result = [];
  matches.forEach((match) => {
    if (!match.word || seen.has(match.word) || !readerWordAllowed(match.word, options.wordSet) || !findWord(match.word)) {
      return;
    }
    seen.add(match.word);
    result.push(match);
  });
  return result;
}

function compareReaderDocuments(left, right) {
  const episodeDiff = compareNullableNumbers(left.episode, right.episode);
  if (episodeDiff !== 0) {
    return episodeDiff;
  }
  return readerDocumentLabel(left).localeCompare(readerDocumentLabel(right), app.lang === "zh" ? "zh-CN" : "ja-JP");
}

function compareReaderLines(left, right) {
  const timeDiff = compareNullableNumbers(left.start_ms, right.start_ms);
  if (timeDiff !== 0) {
    return timeDiff;
  }
  return String(left.text || "").localeCompare(String(right.text || ""), "ja-JP");
}

function compareNullableNumbers(left, right) {
  const leftNumber = Number.isFinite(left) ? left : null;
  const rightNumber = Number.isFinite(right) ? right : null;
  if (leftNumber !== null && rightNumber !== null) {
    return leftNumber - rightNumber;
  }
  if (leftNumber !== null) {
    return -1;
  }
  if (rightNumber !== null) {
    return 1;
  }
  return 0;
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

function selectReaderWord(wordText) {
  const word = findWord(wordText);
  if (!word) {
    return;
  }
  if (app.mode !== "read") {
    openWordFromSource(wordText);
    return;
  }
  app.selectedWord = word;
  app.study.showAnswer = false;
  renderDetail();
  renderMaintenance();
  updateReaderActiveTokens();
}

function updateReaderActiveTokens() {
  if (!refs.wordList) {
    return;
  }
  const selected = app.selectedWord?.word || "";
  refs.wordList.querySelectorAll(".reader-token, .reader-word-chip").forEach((node) => {
    node.classList.toggle("active", Boolean(selected) && node.dataset.word === selected);
  });
}

function findWord(wordText) {
  return app.words.find((item) => item.word === wordText);
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
    const response = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || `HTTP ${response.status}`);
    }
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
  const readerWords = readerWordSet();
  const sourceType = app.reader.sourceType === "all" ? null : app.reader.sourceType;
  const groups = buildSourceGroups(sourceType);
  if (groups.length === 0) {
    app.reader.groupKey = null;
    app.reader.documentKey = null;
    refs.resultCount.textContent = t("readerSourcesFound", { count: formatNumber(0) });
    refs.wordList.replaceChildren(emptyMessage(t("sourceReaderEmpty")));
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
  refs.resultCount.textContent = [
    t("readerSourcesFound", { count: formatNumber(groups.length) }),
    selected.title,
    selectedUnit?.label,
  ].filter(Boolean).join(" · ");

  const pane = el("div", "reader-mode-pane");
  pane.append(renderReaderModeToolbar(groups, selected, units, selectedUnit));
  const scroller = el("div", "reader-mode-scroll");
  scroller.append(
    renderReaderModeSummary(selected, selectedUnit),
    renderSourceReader(selected, {
      full: true,
      wordSet: readerWords,
      documents: selectedUnit?.documents || [],
    }),
  );
  pane.append(scroller);
  refs.wordList.replaceChildren(pane);
  updateReaderActiveTokens();
}

function syncSelectedWordToReaderSource(readingTarget, wordSet) {
  const words = readingTarget?.words || new Set();
  if (words.has(app.selectedWord?.word) && readerWordAllowed(app.selectedWord.word, wordSet)) {
    return;
  }
  const firstWord = [...words]
    .map(findWord)
    .find((word) => word && readerWordAllowed(word.word, wordSet));
  if (firstWord) {
    app.selectedWord = firstWord;
    app.study.showAnswer = false;
  } else {
    app.selectedWord = null;
  }
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
    ].filter(Boolean).join(" · ");
    option.textContent = [group.title || t("sourceInventoryUnknown"), meta].filter(Boolean).join(" · ");
    select.append(option);
  });
  select.addEventListener("change", () => {
    app.reader.groupKey = select.value;
    app.reader.documentKey = null;
    render();
  });
  sourcePicker.append(select);
  toolbar.append(tabs, sourcePicker, renderReaderUnitPicker(units, selectedUnit), renderReaderWordListPicker());
  return toolbar;
}

function renderReaderUnitPicker(units, selectedUnit) {
  const picker = el("label", "reader-source-picker");
  picker.append(el("span", "reader-source-picker-label", t("readerItemChoice")));
  const select = el("select", "reader-source-select");
  if (!units.length) {
    select.disabled = true;
    select.append(el("option", "", t("sourceReaderEmpty")));
  }
  units.forEach((unit) => {
    const option = el("option", "", readerUnitOptionLabel(unit));
    option.value = unit.key;
    option.selected = unit.key === selectedUnit?.key;
    select.append(option);
  });
  select.addEventListener("change", () => {
    app.reader.documentKey = select.value;
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
    const fileLabel = cleanSourceFileLabel(document.source_file || "");
    if (fileLabel && episode === null) {
      unit.metaParts.add(fileLabel);
    }
    unit.documents.push(document);
  });
  return [...units.values()]
    .map((unit) => createReaderUnit({
      key: unit.key,
      episode: unit.episode,
      label: unit.label,
      meta: unit.documents.length > 1
        ? `${formatNumber(unit.documents.length)} ${t("sourceInventoryFiles")}`
        : [...unit.metaParts][0] || "",
      documents: unit.documents.sort(compareReaderDocuments),
    }))
    .sort(compareReaderUnits);
}

function createReaderUnit({ key, episode = null, label, meta = "", documents }) {
  const words = new Set();
  const lineCount = documents.reduce((total, document) => {
    asArray(document.lines).forEach((line) => {
      asArray(line.matches).forEach((match) => {
        if (match.word) {
          words.add(match.word);
        }
      });
    });
    return total + asArray(document.lines).length;
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

function readerDocumentKey(document) {
  return [
    document.source_type || "subtitle",
    document.source_title || "",
    document.source_artist || "",
    document.source_album || "",
    document.source_file || "",
    Number.isInteger(document.episode) ? document.episode : "",
  ].join("\u0000");
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

function compareReaderUnits(left, right) {
  const episodeDiff = compareNullableNumbers(left.episode, right.episode);
  if (episodeDiff !== 0) {
    return episodeDiff;
  }
  return String(left.label || "").localeCompare(String(right.label || ""), app.lang === "zh" ? "zh-CN" : "ja-JP");
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
    allowActions: app.study.showAnswer,
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
    app.selectedWord = app.selectedWord || chooseInitialWord(filteredWords());
  } else {
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
  header.append(el("h3", "section-title", t("examples")));
  if (app.mode !== "read") {
    header.append(renderExampleColumnControl());
  }
  section.append(header);
  const examples = examplesForWord(word);
  if (examples.length === 0) {
    section.append(emptyMessage(t("noExamples")));
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
      allowActions,
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
  const allowActions = options.allowActions ?? true;
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
  lines.append(el("small", `reference reference-${sourceClass}`, formatReference(example)));
  item.append(lines);
  const annotationBlock = renderExampleAnnotationBlock(word, example, {
    revealAnnotations,
    allowActions,
  });
  if (annotationBlock) {
    item.append(annotationBlock);
  }
  return {
    item,
    weight: exampleCardWeight(example, beforeLines, afterLines),
  };
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
    && examplesForWord(word).length > 0;
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

function examplesForWord(word) {
  const examples = Array.isArray(word.examples) ? word.examples : [];
  if (app.source === "all") {
    return examples;
  }
  return examples.filter((example) => example.source_type === app.source);
}

function maintenanceTask() {
  return app.maintenance.task || "annotate";
}

function maintenanceJobSpec(task = maintenanceTask()) {
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
  if (source === "text") {
    return t("sourceTexts");
  }
  return t("sourceAll");
}

function levelLabel(level) {
  return level === "all" ? t("allLevels") : level;
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
  if (example.source_type === "text") {
    return formatTextReference(example);
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

function formatTextReference(example) {
  const parts = [];
  const title = String(example.source_title || "").trim();
  const author = String(example.source_artist || "").trim();
  const file = String(example.subtitle_file || "").trim();
  if (title) {
    parts.push(title);
  }
  if (author) {
    parts.push(author);
  }
  if (file && normalizedTextTitle(fileStem(file)) !== normalizedTextTitle(title)) {
    parts.push(file);
  }
  return parts.join(" · ");
}

function fileStem(value) {
  const name = value.split(/[\\/]/u).pop() || value;
  return name.replace(/\.[^.]+$/u, "");
}

function normalizedTextTitle(value) {
  return String(value || "")
    .normalize("NFC")
    .replace(/[\s\u3000]+/gu, " ")
    .trim();
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

function exampleSourceClass(example) {
  if (example.source_type === "lyrics") {
    return "lyrics";
  }
  if (example.source_type === "text") {
    return "text";
  }
  return "subtitle";
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
    clearStudySchedule(word);
  } else {
    app.statuses[word.word] = status;
    if (status === "known") {
      setStudyCount(word, STUDY_TARGET_COUNT);
    }
    if (status === "known" || status === "ignored") {
      clearStudySchedule(word);
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

function studyDueDateFor(word) {
  const schedule = app.studySchedule[word.word] || {};
  return typeof schedule.due_date === "string" ? schedule.due_date : todayKey();
}

function scheduleStudyReview(word) {
  app.studySchedule[word.word] = {
    last_seen: todayKey(),
    due_date: addDaysKey(todayKey(), STUDY_REVIEW_DELAY_DAYS),
  };
  writeStudySchedule();
}

function clearStudySchedule(word) {
  if (!app.studySchedule[word.word]) {
    return;
  }
  delete app.studySchedule[word.word];
  writeStudySchedule();
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

function todayKey(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function addDaysKey(dateKey, days) {
  const [year, month, day] = String(dateKey || todayKey()).split("-").map((part) => Number.parseInt(part, 10));
  const date = Number.isFinite(year) && Number.isFinite(month) && Number.isFinite(day)
    ? new Date(year, month - 1, day)
    : new Date();
  date.setDate(date.getDate() + days);
  return todayKey(date);
}

function readStudySession() {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_STUDY_SESSION) || "{}");
    if (!value || typeof value !== "object") {
      return { date: todayKey(), words: [] };
    }
    const date = typeof value.date === "string" ? value.date : todayKey();
    const words = asArray(value.words)
      .map((word) => String(word || "").trim())
      .filter(Boolean)
      .slice(0, DAILY_STUDY_LIMIT);
    return { date, words };
  } catch {
    return { date: todayKey(), words: [] };
  }
}

function readStudySchedule() {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_STUDY_SCHEDULE) || "{}");
    if (!value || typeof value !== "object") {
      return {};
    }
    return Object.fromEntries(
      Object.entries(value)
        .map(([word, schedule]) => {
          const lastSeen = typeof schedule?.last_seen === "string" ? schedule.last_seen : "";
          const dueDate = typeof schedule?.due_date === "string" ? schedule.due_date : todayKey();
          return [word, { last_seen: lastSeen, due_date: dueDate }];
        })
        .filter(([word]) => word),
    );
  } catch {
    return {};
  }
}

function writeStudySchedule() {
  localStorage.setItem(STORAGE_STUDY_SCHEDULE, JSON.stringify(app.studySchedule));
}

function writeStudySession(session) {
  localStorage.setItem(STORAGE_STUDY_SESSION, JSON.stringify({
    date: session.date,
    words: asArray(session.words).slice(0, DAILY_STUDY_LIMIT),
  }));
}

function sameStudySession(left, right) {
  if (!left || !right || left.date !== right.date) {
    return false;
  }
  const leftWords = asArray(left.words);
  const rightWords = asArray(right.words);
  return leftWords.length === rightWords.length
    && leftWords.every((word, index) => word === rightWords[index]);
}

function readExampleColumns() {
  const value = localStorage.getItem(STORAGE_EXAMPLE_COLUMNS) || "auto";
  return EXAMPLE_COLUMN_VALUES.has(value) ? value : "auto";
}

function readSplitRatios() {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_SPLIT_RATIOS) || "{}");
    if (!value || typeof value !== "object") {
      return { ...SPLIT_DEFAULT_RATIOS };
    }
    return Object.fromEntries(
      [...MODE_VALUES].map((mode) => {
        const ratio = Number(value[mode]);
        const fallback = SPLIT_DEFAULT_RATIOS[mode] ?? 0.3;
        return [mode, Number.isFinite(ratio) ? clampNumber(ratio, 0.15, 0.85) : fallback];
      }),
    );
  } catch {
    return { ...SPLIT_DEFAULT_RATIOS };
  }
}

function readMode() {
  const value = localStorage.getItem(STORAGE_MODE) || "browse";
  return MODE_VALUES.has(value) ? value : "browse";
}

function readReaderWordList() {
  const value = localStorage.getItem(STORAGE_READER_WORD_LIST) || "all";
  return READER_WORD_LIST_VALUES.has(value) ? value : "all";
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
