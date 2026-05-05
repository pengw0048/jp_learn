const STORAGE_LANG = "jpcorpus.viewer.lang";
const STORAGE_STATUS = "jpcorpus.viewer.status.v1";
const STORAGE_EXAMPLE_COLUMNS = "jpcorpus.viewer.exampleColumns.v1";
const EXAMPLE_COLUMN_VALUES = new Set(["auto", "1", "2", "3"]);

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
    statusLearning: "想学",
    statusKnown: "认识",
    statusIgnored: "忽略",
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
    noWords: "没有匹配的词",
    count: "频次",
    examples: "例句",
    exampleColumns: "列数",
    exampleColumnsAuto: "自动",
    chineseMeaning: "日中",
    fallbackMeaning: "英文释义",
    noExamples: "这个词暂时没有例句",
    scene: "场景",
    translation: "翻译",
    usageNote: "用法",
    shows: "作品",
    subtitles: "字幕",
    lyrics: "歌词",
    studyWords: "单词",
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
    statusLearning: "Study",
    statusKnown: "Known",
    statusIgnored: "Ignored",
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
    noWords: "No matching words",
    count: "Count",
    examples: "Examples",
    exampleColumns: "Columns",
    exampleColumnsAuto: "Auto",
    chineseMeaning: "ZH",
    noExamples: "No examples for this word yet",
    scene: "Scene",
    translation: "Translation",
    usageNote: "Usage",
    shows: "Shows",
    subtitles: "Subtitles",
    lyrics: "Lyrics",
    studyWords: "Study words",
  },
};

const stateLabels = {
  none: { zh: "未标记", en: "Unmarked", symbol: "·" },
  learning: { zh: "想学", en: "Study", symbol: "★" },
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
  statuses: readStatuses(),
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
};

init();

async function init() {
  bindControls();
  applyLanguage();
  try {
    const response = await fetch("/corpus.json", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    app.corpus = await response.json();
    app.words = Array.isArray(app.corpus.words) ? app.corpus.words : [];
    app.selectedWord = chooseInitialWord();
    render();
  } catch (error) {
    renderLoadError(error);
  }
}

function bindControls() {
  refs.searchInput.addEventListener("input", (event) => {
    app.query = event.target.value.trim().toLowerCase();
    app.selectedWord = chooseInitialWord(filteredWords());
    render();
  });
  refs.sortSelect.addEventListener("change", (event) => {
    app.sort = event.target.value;
    render();
  });
  refs.statusFilter.addEventListener("change", (event) => {
    app.status = event.target.value;
    app.selectedWord = chooseInitialWord(filteredWords());
    render();
  });
  refs.sourceFilter.addEventListener("change", (event) => {
    app.source = event.target.value;
    app.selectedWord = chooseInitialWord(filteredWords());
    render();
  });
  document.querySelectorAll("[data-lang]").forEach((button) => {
    button.addEventListener("click", () => {
      app.lang = button.dataset.lang;
      localStorage.setItem(STORAGE_LANG, app.lang);
      applyLanguage();
      render();
    });
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
}

function render() {
  if (!app.corpus) {
    return;
  }
  renderHeader();
  renderLevelFilter();
  renderWordList();
  renderDetail();
}

function renderHeader() {
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
        app.selectedWord = chooseInitialWord(filteredWords());
        render();
      });
      return button;
    }),
  );
}

function renderWordList() {
  const words = filteredWords();
  refs.resultCount.textContent = t("wordsFound", { count: formatNumber(words.length) });
  if (words.length === 0) {
    refs.wordList.replaceChildren(emptyMessage(t("noWords")));
    return;
  }
  refs.wordList.replaceChildren(...words.map(renderWordRow));
  if (!app.selectedWord || !words.some((word) => word.word === app.selectedWord.word)) {
    app.selectedWord = words[0];
  }
}

function renderWordRow(word) {
  const button = el("button", "word-row");
  button.type = "button";
  button.classList.toggle("active", app.selectedWord?.word === word.word);
  button.addEventListener("click", () => {
    app.selectedWord = word;
    render();
  });

  const main = el("div", "word-main");
  const wordText = el("div", "word-text", word.word || "");
  const badges = el("div", "word-badges");
  badges.append(badge(word.level || ""), statusDot(statusFor(word)));
  main.append(wordText, badges);

  const meta = el(
    "div",
    "word-meta",
    `${word.reading || ""} · ${t("count")} ${formatNumber(displayCount(word))}`,
  );
  const meaning = el("div", "word-meaning", displayMeaning(word));
  button.append(main, meta, meaning);
  return button;
}

function renderDetail() {
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
  );
  titleRow.append(title, stats);

  const meanings = el("div", "meaning-block");
  const mainMeaning = displayMeaning(word);
  meanings.append(el("div", "meaning-main", mainMeaning || "—"));
  if (app.lang === "zh" && word.meaning_zh && word.meaning && word.meaning_zh !== word.meaning) {
    meanings.append(el("div", "meaning-alt", `${t("fallbackMeaning")}: ${word.meaning}`));
  }

  header.append(titleRow, meanings, renderStatusActions(word));
  return header;
}

function renderStatusActions(word) {
  const wrap = el("div", "status-actions");
  ["learning", "known", "ignored", "none"].forEach((status) => {
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

function renderExamples(word) {
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
    const item = el("div", "example");
    const lines = el("div", "example-lines");
    appendContextBlock(lines, contextPreview(example.context_before, "before"), "before");
    const current = el("div", "example-current");
    appendHighlighted(current, example.sentence || "", example.matched_text || word.word);
    lines.append(current);
    appendContextBlock(lines, contextPreview(example.context_after, "after"), "after");
    lines.append(el("small", "reference", formatReference(example)));
    item.append(lines);
    if (example.translation_zh) {
      item.append(el("div", "annotation-line translation-line", `${t("translation")}: ${example.translation_zh}`));
    }
    if (example.usage_note_zh) {
      item.append(el("div", "annotation-line", `${t("usageNote")}: ${example.usage_note_zh}`));
    }
    grid.append(item);
  });
  section.append(grid);
  return section;
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

function displayMeaning(word) {
  if (app.lang === "zh") {
    return word.meaning_zh || word.meaning || "";
  }
  return word.meaning || word.meaning_zh || "";
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

function formatReference(example) {
  const parts = [];
  if (example.source_title) {
    parts.push(example.source_title);
  }
  if (example.source_type === "lyrics") {
    if (example.source_artist) {
      parts.push(example.source_artist);
    }
    if (example.source_album && example.source_album !== example.source_title) {
      parts.push(example.source_album);
    }
  }
  if (Number.isInteger(example.episode)) {
    parts.push(`EP${String(example.episode).padStart(2, "0")}`);
  } else if (example.source_type !== "lyrics" && example.subtitle_file) {
    parts.push(example.subtitle_file);
  }
  if (Number.isInteger(example.start_ms)) {
    parts.push(formatTimestamp(example.start_ms));
  }
  return parts.join(" ");
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
  return app.statuses[word.word] || "none";
}

function setStatus(word, status) {
  if (status === "none") {
    delete app.statuses[word.word];
  } else {
    app.statuses[word.word] = status;
  }
  localStorage.setItem(STORAGE_STATUS, JSON.stringify(app.statuses));
}

function readStatuses() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_STATUS) || "{}");
  } catch {
    return {};
  }
}

function readExampleColumns() {
  const value = localStorage.getItem(STORAGE_EXAMPLE_COLUMNS) || "auto";
  return EXAMPLE_COLUMN_VALUES.has(value) ? value : "auto";
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
