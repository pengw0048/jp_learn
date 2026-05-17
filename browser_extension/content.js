(() => {
  const SCRIPT_VERSION = "0.1.27";
  if (window.__jpcorpusContentVersion === SCRIPT_VERSION) {
    return;
  }
  window.__jpcorpusContentVersion = SCRIPT_VERSION;
  window.__jpcorpusPickerLoaded = true;
  const CJK_FONT_CSS = '"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", "Noto Sans SC", "Source Han Sans SC", "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif';
  const READER_TOOLBAR_POSITION_KEY = "jpcorpus.readerToolbarPosition.v1";
  const STUDY_TARGET_COUNT = 7;
  const SPEECH_SOFT_CHARS = 70;
  const SPEECH_MAX_CHARS = 120;
  const SPEECH_PREFETCH_UNITS = 3;
  const MESSAGES = {
    zh: {
      stillAnnotating: "日语阅读助手仍在标注这个页面...",
      readerOff: "日语阅读助手网页阅读模式已关闭。",
      annotating: "正在用日语阅读助手标注这个页面...",
      noJapaneseText: "没有在正文里找到日语文本。",
      cannotAnnotate: "无法标注这个页面。",
      annotated: "日语阅读助手标注了 {count} 个词。",
      noAnnotations: "没有应用标注。如果这里明显不对，可以刷新页面再试。",
      close: "关闭",
      noGlossary: "没有找到词典释义。",
      matchedForm: "匹配词形：{surface}",
      saving: "保存中...",
      cannotUpdateStudy: "无法更新学习状态。",
      addedStudy: "已加入学习：{word}",
      updatedStudy: "已更新学习状态：{word}",
      addStudy: "加入学习",
      confirmStudy: "确认一次",
      known: "直接认识",
      studying: "学习中",
      uncertain: "模糊",
      statusKnown: "已认识",
      statusIgnored: "已忽略",
      studyChecks: "学习进度 {count}/{target}",
      ignore: "忽略",
      ignored: "已忽略",
      clearStatus: "取消标记",
      importSelection: "导入选中",
      importArticle: "导入正文",
      pickImport: "点选导入",
      importingSelection: "正在导入选中文字...",
      extractingArticle: "正在提取正文...",
      noSelection: "没有选中文字可导入。",
      alreadyImported: "已经导入过 {title}。",
      imported: "已导入 {title}。",
      importFailed: "导入失败。",
      webTextTitle: "网页文本",
      readAll: "朗读全文",
      readParagraph: "朗读选段",
      pickParagraph: "点要朗读的段落。Esc 取消。",
      cancelPick: "取消选择",
      furigana: "假名",
      dragToolbar: "拖动工具栏",
      switchLanguage: "EN",
      stopReading: "停止",
      closeReader: "关闭",
      noReadableParagraph: "这个区域没有可朗读的日语。",
      pickerInitial: "点击导入高亮文本。Esc 取消。",
      pickerLabel: "点击导入 {count} 字 · Esc 取消",
      noReadableArticle: "没有在这个页面找到可读正文。",
    },
    en: {
      stillAnnotating: "Japanese Reading Companion is still annotating this page...",
      readerOff: "Japanese Reading Companion reading mode off.",
      annotating: "Annotating this page with Japanese Reading Companion...",
      noJapaneseText: "No Japanese text found in the main page content.",
      cannotAnnotate: "Could not annotate this page.",
      annotated: "Japanese Reading Companion annotated {count} words.",
      noAnnotations: "No annotations were applied. Try reloading the page if this looks wrong.",
      close: "Close",
      noGlossary: "No glossary entry found.",
      matchedForm: "Matched form: {surface}",
      saving: "Saving...",
      cannotUpdateStudy: "Could not update study status.",
      addedStudy: "Added to study: {word}",
      updatedStudy: "Updated study status: {word}",
      addStudy: "Add to study",
      confirmStudy: "Confirm once",
      known: "Mark known",
      studying: "Learning",
      uncertain: "Unsure",
      statusKnown: "Known",
      statusIgnored: "Ignored",
      studyChecks: "Study progress {count}/{target}",
      ignore: "Ignore",
      ignored: "Ignored",
      clearStatus: "Clear",
      importSelection: "Import selection",
      importArticle: "Import article",
      pickImport: "Pick import",
      importingSelection: "Importing selected text...",
      extractingArticle: "Extracting article text...",
      noSelection: "No selected text to import.",
      alreadyImported: "Already imported {title}.",
      imported: "Imported {title}.",
      importFailed: "Import failed.",
      webTextTitle: "web text",
      readAll: "Read all",
      readParagraph: "Read passage",
      pickParagraph: "Click a passage to read. Esc cancels.",
      cancelPick: "Cancel pick",
      furigana: "Furigana",
      dragToolbar: "Move toolbar",
      switchLanguage: "中",
      stopReading: "Stop",
      closeReader: "Close",
      noReadableParagraph: "No readable Japanese text in this area.",
      pickerInitial: "Click to import highlighted text. Esc cancel.",
      pickerLabel: "Click to import {count} chars. · Esc cancel",
      noReadableArticle: "No readable article text found on this page.",
    },
  };
  let extensionLang = "zh";

  let picker = null;
  let reader = null;
  let activeReaderUtterance = null;
  let activeReaderAudio = null;
  let activeReaderSpeechRunId = 0;
  let activeReaderSpeechButton = null;
  let activeReaderHighlightFallback = null;
  const READER_TOKEN_STATUS_CLASSES = [
    "jpcorpus-reader-token-learning",
    "jpcorpus-reader-token-uncertain",
    "jpcorpus-reader-token-known",
    "jpcorpus-reader-token-ignored",
  ];
  syncLanguage();
  chrome.storage?.onChanged?.addListener((changes, areaName) => {
    if (areaName === "local" && changes.lang) {
      extensionLang = normalizeLang(changes.lang.newValue);
    }
  });
  window.addEventListener("pagehide", stopReaderTransientState, true);
  document.addEventListener("visibilitychange", onReaderVisibilityChange, true);

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type === "START_AREA_PICKER") {
      syncLanguage()
        .then(() => {
          startPicker();
          sendResponse({ ok: true });
        })
        .catch((error) => sendResponse({ ok: false, error: error.message || String(error) }));
      return true;
    }
    if (message?.type === "TOGGLE_READING_MODE") {
      toggleReadingMode()
        .then((result) => sendResponse({ ok: true, ...result }))
        .catch((error) => sendResponse({ ok: false, error: error.message || String(error) }));
      return true;
    }
    if (message?.type === "EXTRACT_MAIN_ARTICLE") {
      syncLanguage()
        .then(() => sendResponse({ ok: true, payload: extractMainArticle() }))
        .catch((error) => sendResponse({ ok: false, error: error.message || String(error) }));
      return true;
    }
    if (message?.type === "SHOW_TOAST") {
      showToast(message.message || "", message.tone || "info");
      sendResponse({ ok: true });
      return false;
    }
    return false;
  });

  async function toggleReadingMode() {
    await syncLanguage();
    if (reader?.loading) {
      showToast(tr("stillAnnotating"));
      return { enabled: true, tokenCount: reader.tokenCount || 0, busy: true };
    }
    if (reader?.active) {
      disableReadingMode();
      showToast(tr("readerOff"));
      return { enabled: false, tokenCount: 0 };
    }
    return enableReadingMode();
  }

  async function enableReadingMode() {
    stopPicker();
    ensureReaderStyles();
    restoreOrphanedReaderAnnotations();
    reader = {
      active: false,
      loading: true,
      tokenCount: 0,
      replacements: [],
      selectedToken: null,
      panel: null,
      root: null,
      toolbar: null,
      toolbarStatus: null,
      toolbarStatusTimer: null,
      toolbarDrag: null,
      importSelectionButton: null,
      paragraphPicker: null,
      furigana: false,
    };
    showToast(tr("annotating"));
    try {
      const root = readerRoot();
      reader.root = root;
      const blocks = [];
      const nodesById = new Map();
      let totalChars = 0;
      collectReaderTextNodes(root).forEach((node) => {
        if (blocks.length >= 260 || totalChars >= 48000) {
          return;
        }
        const text = node.nodeValue || "";
        const remaining = 48000 - totalChars;
        if (remaining <= 0 || !hasJapaneseText(text)) {
          return;
        }
        const id = String(blocks.length);
        const blockText = text.length > remaining ? text.slice(0, remaining) : text;
        totalChars += blockText.length;
        nodesById.set(id, node);
        blocks.push({ id, text: blockText });
      });
      if (!blocks.length) {
        throw new Error(tr("noJapaneseText"));
      }
      const response = await chrome.runtime.sendMessage({
        type: "ANNOTATE_TEXT_BLOCKS",
        payload: { blocks },
      });
      if (!response?.ok) {
        throw new Error(response?.error || tr("cannotAnnotate"));
      }

      const tokenCount = applyReaderAnnotations(response.result?.blocks || [], nodesById);
      reader.active = true;
      reader.loading = false;
      reader.tokenCount = tokenCount;
      renderReaderToolbar();
      document.addEventListener("click", onReaderDocumentClick, true);
      showToast(tokenCount ? tr("annotated", { count: tokenCount }) : tr("noAnnotations"));
      return { enabled: true, tokenCount };
    } catch (error) {
      reader = null;
      restoreOrphanedReaderAnnotations();
      throw error;
    }
  }

  function disableReadingMode() {
    if (!reader) {
      restoreOrphanedReaderAnnotations();
      return;
    }
    document.removeEventListener("click", onReaderDocumentClick, true);
    stopReaderSpeech();
    stopReaderParagraphPicker();
    removeReaderToolbar();
    removeReaderPanel();
    reader.replacements.forEach(({ wrapper, text }) => {
      if (wrapper.parentNode) {
        wrapper.replaceWith(document.createTextNode(text));
      }
    });
    reader = null;
    restoreOrphanedReaderAnnotations();
  }

  function restoreOrphanedReaderAnnotations() {
    document.querySelectorAll("#jpcorpus-reader-panel").forEach((panel) => panel.remove());
    document.querySelectorAll("#jpcorpus-reader-toolbar").forEach((toolbar) => toolbar.remove());
    document.querySelectorAll(".jpcorpus-reader-speech-pick-target").forEach((target) => {
      target.classList.remove("jpcorpus-reader-speech-pick-target");
    });
    document.querySelectorAll(".jpcorpus-reader-wrapper").forEach((wrapper) => {
      if (wrapper.parentNode) {
        wrapper.replaceWith(document.createTextNode(wrapper.dataset.jpcorpusText || wrapper.textContent || ""));
      }
    });
    document.querySelectorAll(".jpcorpus-reader-token").forEach((token) => {
      if (token.parentNode) {
        token.replaceWith(document.createTextNode(token.textContent || ""));
      }
    });
  }

  function readerRoot() {
    const readabilityArticle = extractReadabilityArticle();
    const readabilityText = readabilityArticle?.text || "";
    const candidates = articleCandidates()
      .map((element) => ({
        element,
        score: articleScore(element),
        text: readableText(element),
      }))
      .filter((candidate) => candidate.text.length >= 80)
      .map((candidate) => {
        const matchScore = readabilityMatchScore(candidate.text, readabilityText);
        const lengthRatio = readabilityLengthRatio(candidate.text, readabilityText);
        return {
          ...candidate,
          score: candidate.score + matchScore,
          readabilityMatchScore: matchScore,
          readabilityLengthRatio: lengthRatio,
        };
      })
      .sort((left, right) => right.score - left.score);
    const readabilityMatched = candidates
      .filter((candidate) => candidate.readabilityMatchScore >= 1400 && candidate.readabilityLengthRatio >= 0.45)
      .sort((left, right) => (
        right.readabilityMatchScore - left.readabilityMatchScore
        || right.readabilityLengthRatio - left.readabilityLengthRatio
        || left.text.length - right.text.length
      ))[0];
    if (readabilityMatched) {
      return readabilityMatched.element;
    }
    return candidates[0]?.element || document.body;
  }

  function collectReaderTextNodes(root) {
    const nodes = [];
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        return isAnnotatableTextNode(node) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      },
    });
    while (walker.nextNode()) {
      nodes.push(walker.currentNode);
    }
    return nodes;
  }

  function isAnnotatableTextNode(node) {
    const text = node.nodeValue || "";
    if (!hasJapaneseText(text) || !text.trim()) {
      return false;
    }
    const parent = node.parentElement;
    if (!parent || parent.closest("#jpcorpus-reader-panel, .jpcorpus-reader-wrapper, .jpcorpus-import-toast, #jpcorpus-picker-overlay, #jpcorpus-picker-label")) {
      return false;
    }
    let current = parent;
    while (current && current !== document.body && current !== document.documentElement) {
      const tag = current.tagName.toLowerCase();
      if (["a", "button", "canvas", "input", "noscript", "rp", "rt", "script", "select", "style", "svg", "textarea"].includes(tag)) {
        return false;
      }
      const style = window.getComputedStyle(current);
      if (style.display === "none" || style.visibility === "hidden") {
        return false;
      }
      if (isSkippableElement(current)) {
        return false;
      }
      current = current.parentElement;
    }
    return true;
  }

  function applyReaderAnnotations(blocks, nodesById) {
    let tokenCount = 0;
    blocks.forEach((block) => {
      const node = nodesById.get(String(block.id));
      if (!node?.parentNode) {
        return;
      }
      const text = node.nodeValue || "";
      const ranges = validReaderRanges(block.ranges || [], text);
      if (!ranges.length) {
        return;
      }
      const wrapper = document.createElement("span");
      wrapper.className = "jpcorpus-reader-wrapper";
      wrapper.dataset.jpcorpusText = text;
      let cursor = 0;
      ranges.forEach((range) => {
        if (range.start > cursor) {
          wrapper.append(document.createTextNode(text.slice(cursor, range.start)));
        }
        const token = document.createElement("span");
        token.className = "jpcorpus-reader-token";
        const surface = text.slice(range.start, range.end);
        token.dataset.surface = surface;
        token.__jpcorpusAnnotation = range;
        renderReaderTokenText(token, range, false);
        applyReaderTokenStatusClass(token, range.status);
        token.addEventListener("click", onReaderTokenClick, true);
        wrapper.append(token);
        cursor = range.end;
        tokenCount += 1;
      });
      if (cursor < text.length) {
        wrapper.append(document.createTextNode(text.slice(cursor)));
      }
      node.parentNode.replaceChild(wrapper, node);
      reader.replacements.push({ wrapper, text });
    });
    return tokenCount;
  }

  function validReaderRanges(ranges, text) {
    let lastEnd = -1;
    return ranges
      .filter((range) => Number.isInteger(range.start) && Number.isInteger(range.end))
      .sort((left, right) => left.start - right.start)
      .filter((range) => {
        const valid = range.start >= 0 && range.end > range.start && range.end <= text.length && range.start >= lastEnd;
        if (valid) {
          lastEnd = range.end;
        }
        return valid;
      });
  }

  function onReaderTokenClick(event) {
    event.preventDefault();
    event.stopPropagation();
    const token = event.currentTarget;
    selectReaderToken(token);
    showReaderPanel(token.__jpcorpusAnnotation || {}, token);
  }

  function onReaderDocumentClick(event) {
    const target = event.target;
    if (target instanceof Element && target.closest("#jpcorpus-reader-panel, #jpcorpus-reader-toolbar, .jpcorpus-reader-token")) {
      return;
    }
    clearReaderSelection();
  }

  function selectReaderToken(token) {
    if (!reader) {
      return;
    }
    reader.selectedToken?.classList.remove("jpcorpus-reader-selected");
    reader.selectedToken = token;
    token.classList.add("jpcorpus-reader-selected");
  }

  function clearReaderSelection() {
    if (!reader) {
      return;
    }
    reader.selectedToken?.classList.remove("jpcorpus-reader-selected");
    reader.selectedToken = null;
    removeReaderPanel();
  }

  function showReaderPanel(annotation, anchor) {
    if (!reader) {
      return;
    }
    removeReaderPanel();
    const panel = document.createElement("aside");
    panel.id = "jpcorpus-reader-panel";
    panel.lang = extensionLang === "zh" ? "zh-Hans" : "en";
    const title = document.createElement("div");
    title.className = "jpcorpus-reader-panel-title";
    const word = document.createElement("strong");
    word.textContent = annotation.word || annotation.surface || "";
    const close = document.createElement("button");
    close.type = "button";
    close.textContent = tr("close");
    close.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      clearReaderSelection();
    });
    title.append(word, close);

    const meta = document.createElement("div");
    meta.className = "jpcorpus-reader-panel-meta";
    [
      annotation.reading,
      annotation.level,
      annotation.pos,
      readerStatusLabel(annotation),
      readerStudyCountLabel(annotation),
    ].filter(Boolean).forEach((item) => {
      const chip = document.createElement("span");
      chip.textContent = item;
      meta.append(chip);
    });

    const meaning = document.createElement("p");
    meaning.className = "jpcorpus-reader-panel-meaning";
    meaning.textContent = readerMeaning(annotation) || tr("noGlossary");

    const detail = document.createElement("p");
    detail.className = "jpcorpus-reader-panel-detail";
    detail.textContent = annotation.surface && annotation.surface !== annotation.word
      ? tr("matchedForm", { surface: annotation.surface })
      : "";

    panel.append(title, meta, meaning);
    if (detail.textContent) {
      panel.append(detail);
    }
    panel.append(renderReaderStudyActions(annotation));
    document.documentElement.append(panel);
    positionReaderPanel(panel, anchor);
    reader.panel = panel;
  }

  function renderReaderStudyActions(annotation) {
    const row = document.createElement("div");
    row.className = "jpcorpus-reader-panel-actions";
    refreshReaderStudyActions(row, annotation);
    return row;
  }

  function refreshReaderStudyActions(row, annotation) {
    row.replaceChildren();
    const currentStatus = normalizeReaderStatus(annotation.status);
    if (currentStatus === "learning" || currentStatus === "uncertain") {
      row.append(renderReaderStatusButton(row, annotation, {
        status: "learning",
        label: tr("confirmStudy"),
        action: "confirm",
      }));
    } else {
      row.append(renderReaderStatusButton(row, annotation, {
        status: "learning",
        label: tr("addStudy"),
      }));
    }
    row.append(
      renderReaderStatusButton(row, annotation, {
        status: "known",
        label: tr("known"),
      }),
      renderReaderStatusButton(row, annotation, {
        status: "ignored",
        label: currentStatus === "ignored" ? tr("ignored") : tr("ignore"),
      }),
    );
    if (currentStatus !== "none") {
      row.append(renderReaderStatusButton(row, annotation, {
        status: "none",
        label: tr("clearStatus"),
      }));
    }
  }

  function renderReaderStatusButton(row, annotation, options) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "jpcorpus-reader-status-button";
    button.textContent = options.label;
    const isActive = normalizeReaderStatus(annotation.status) === options.status
      || (options.status === "learning" && normalizeReaderStatus(annotation.status) === "uncertain");
    if (isActive && options.status !== "none") {
      button.classList.add("active");
    }
    button.setAttribute("aria-pressed", isActive && options.status !== "none" ? "true" : "false");
    button.addEventListener("click", async (event) => {
      event.preventDefault();
      event.stopPropagation();
      setReaderWordStatus(row, annotation, options.status, button, options.action);
    });
    return button;
  }

  function updateReaderAnnotationsForWord(word, status, studyCount) {
    document.querySelectorAll(".jpcorpus-reader-token").forEach((token) => {
      if (token.__jpcorpusAnnotation?.word !== word) {
        return;
      }
      token.__jpcorpusAnnotation.status = status;
      token.__jpcorpusAnnotation.study_count = studyCount;
      applyReaderTokenStatusClass(token, status);
    });
  }

  async function setReaderWordStatus(row, annotation, status, button, action = "") {
    const word = annotation.word || annotation.surface || "";
    if (!word) {
      showToast(tr("cannotUpdateStudy"), "error");
      return;
    }
    const nextStudyCount = action === "confirm"
      ? Math.min(readerStudyCount(annotation) + 1, STUDY_TARGET_COUNT)
      : undefined;
    const nextStatus = nextStudyCount >= STUDY_TARGET_COUNT ? "known" : status;
    const buttons = Array.from(row.querySelectorAll("button"));
    buttons.forEach((item) => {
      item.disabled = true;
    });
    button.textContent = tr("saving");
    try {
      const response = await chrome.runtime.sendMessage({
        type: "SET_WORD_STATUS",
        payload: {
          word,
          status: nextStatus,
          ...(nextStudyCount !== undefined ? { study_count: nextStudyCount } : {}),
        },
      });
      if (!response?.ok) {
        throw new Error(response?.error || tr("cannotUpdateStudy"));
      }
      annotation.status = normalizeReaderStatus(response.result?.status || nextStatus);
      annotation.study_count = response.result?.study_count || 0;
      updateReaderAnnotationsForWord(word, annotation.status, annotation.study_count);
      if (reader?.selectedToken) {
        showReaderPanel(annotation, reader.selectedToken);
      } else {
        refreshReaderStudyActions(row, annotation);
      }
      const toastKey = status === "learning" && action !== "confirm" ? "addedStudy" : "updatedStudy";
      showToast(tr(toastKey, { word }));
    } catch (error) {
      refreshReaderStudyActions(row, annotation);
      showToast(error.message || String(error), "error");
    }
  }

  function readerMeaning(annotation) {
    if (extensionLang === "zh") {
      return annotation.meaning_zh || "";
    }
    return annotation.meaning || annotation.meaning_zh || "";
  }

  function readerStudyCount(annotation) {
    const value = Number.parseInt(annotation.study_count, 10);
    if (!Number.isFinite(value) || value <= 0) {
      return 0;
    }
    return Math.min(value, STUDY_TARGET_COUNT);
  }

  function readerStatusLabel(annotation) {
    const status = normalizeReaderStatus(annotation.status);
    if (status === "learning") {
      return tr("studying");
    }
    if (status === "uncertain") {
      return tr("uncertain");
    }
    if (status === "known") {
      return tr("statusKnown");
    }
    if (status === "ignored") {
      return tr("statusIgnored");
    }
    return "";
  }

  function readerStudyCountLabel(annotation) {
    const count = readerStudyCount(annotation);
    if (count <= 0) {
      return "";
    }
    return tr("studyChecks", { count, target: STUDY_TARGET_COUNT });
  }

  function normalizeReaderStatus(status) {
    return ["learning", "uncertain", "known", "ignored", "none"].includes(status) ? status : "none";
  }

  function applyReaderTokenStatusClass(token, status) {
    token.classList.remove(...READER_TOKEN_STATUS_CLASSES);
    const normalized = normalizeReaderStatus(status);
    if (normalized !== "none") {
      token.classList.add(`jpcorpus-reader-token-${normalized}`);
    }
  }

  function renderReaderTokenText(token, annotation, withFurigana) {
    const surface = token.dataset.surface || annotation.surface || token.textContent || "";
    token.replaceChildren();
    token.classList.toggle("jpcorpus-reader-token-furigana", Boolean(withFurigana));
    const reading = readerFuriganaReading(surface, annotation);
    if (!withFurigana || !reading) {
      token.textContent = surface;
      return;
    }
    const ruby = document.createElement("ruby");
    ruby.append(document.createTextNode(surface));
    const rt = document.createElement("rt");
    rt.textContent = reading;
    ruby.append(rt);
    token.append(ruby);
  }

  function toggleReaderFurigana(button) {
    if (!reader) {
      return;
    }
    reader.furigana = !reader.furigana;
    button.classList.toggle("active", reader.furigana);
    button.setAttribute("aria-pressed", reader.furigana ? "true" : "false");
    document.querySelectorAll(".jpcorpus-reader-token").forEach((token) => {
      renderReaderTokenText(token, token.__jpcorpusAnnotation || {}, reader.furigana);
    });
  }

  function readerFuriganaReading(surface, annotation) {
    const text = String(surface || "").trim();
    const reading = firstReaderReading(annotation.reading);
    if (!text || !reading || !containsKanji(text) || reading === text) {
      return "";
    }
    return reading;
  }

  function firstReaderReading(value) {
    return String(value || "").split(/[;；,、]/u)[0].trim();
  }

  function containsKanji(value) {
    return /[\u3400-\u9fff々〆]/u.test(String(value || ""));
  }

  function renderReaderToolbar() {
    if (!reader) {
      return;
    }
    removeReaderToolbar();
    const toolbar = document.createElement("div");
    toolbar.id = "jpcorpus-reader-toolbar";
    toolbar.lang = extensionLang === "zh" ? "zh-Hans" : "en";
    toolbar.addEventListener("mousedown", (event) => {
      if (event.target instanceof HTMLButtonElement) {
        event.preventDefault();
      }
    });
    const actions = document.createElement("div");
    actions.className = "jpcorpus-reader-toolbar-actions";
    const status = document.createElement("div");
    status.className = "jpcorpus-reader-toolbar-status";
    status.hidden = true;

    const dragHandle = document.createElement("span");
    dragHandle.className = "jpcorpus-reader-toolbar-drag";
    dragHandle.textContent = "⋮⋮";
    dragHandle.title = tr("dragToolbar");
    dragHandle.setAttribute("role", "button");
    dragHandle.setAttribute("aria-label", tr("dragToolbar"));
    dragHandle.addEventListener("pointerdown", startReaderToolbarDrag);

    const importSelection = document.createElement("button");
    importSelection.type = "button";
    importSelection.className = "jpcorpus-reader-import-button";
    importSelection.textContent = tr("importSelection");
    importSelection.title = tr("noSelection");
    importSelection.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      importSelectedTextFromPage(importSelection);
    });
    reader.importSelectionButton = importSelection;
    updateReaderSelectionButton();
    document.addEventListener("selectionchange", updateReaderSelectionButton, true);

    const importArticle = document.createElement("button");
    importArticle.type = "button";
    importArticle.className = "jpcorpus-reader-import-button";
    importArticle.textContent = tr("importArticle");
    importArticle.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      importMainArticleFromPage(importArticle);
    });

    const pickImport = document.createElement("button");
    pickImport.type = "button";
    pickImport.className = "jpcorpus-reader-import-button";
    pickImport.textContent = tr("pickImport");
    pickImport.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      stopReaderSpeech();
      stopReaderParagraphPicker();
      setReaderToolbarStatus("");
      startPicker();
    });

    const readAll = document.createElement("button");
    readAll.type = "button";
    readAll.className = "jpcorpus-reader-speech-button";
    readAll.dataset.readerIdleLabel = tr("readAll");
    readAll.textContent = tr("readAll");
    readAll.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      const wasActive = activeReaderSpeechButton === readAll;
      if (activeReaderSpeechButton) {
        stopReaderSpeech();
      }
      if (wasActive) {
        return;
      }
      stopReaderParagraphPicker();
      setReaderToolbarStatus("");
      speakReaderParagraph(reader.root || readerRoot(), readAll);
    });

    const readParagraph = document.createElement("button");
    readParagraph.type = "button";
    readParagraph.className = "jpcorpus-reader-speech-button";
    readParagraph.dataset.readerIdleLabel = tr("readParagraph");
    readParagraph.textContent = tr("readParagraph");
    readParagraph.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      const wasActive = activeReaderSpeechButton === readParagraph;
      if (activeReaderSpeechButton) {
        stopReaderSpeech();
      }
      if (wasActive) {
        return;
      }
      if (reader.paragraphPicker) {
        stopReaderParagraphPicker();
        return;
      }
      startReaderParagraphPicker(readParagraph);
    });

    const furigana = document.createElement("button");
    furigana.type = "button";
    furigana.className = "jpcorpus-reader-furigana-button";
    furigana.textContent = tr("furigana");
    furigana.classList.toggle("active", Boolean(reader.furigana));
    furigana.setAttribute("aria-pressed", reader.furigana ? "true" : "false");
    furigana.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      toggleReaderFurigana(furigana);
    });

    const close = document.createElement("button");
    close.type = "button";
    close.textContent = tr("closeReader");
    close.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      showToast(tr("readerOff"));
      disableReadingMode();
    });

    const lang = document.createElement("button");
    lang.type = "button";
    lang.className = "jpcorpus-reader-lang-button";
    lang.textContent = tr("switchLanguage");
    lang.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      toggleExtensionLanguage();
    });

    actions.append(dragHandle, importSelection, importArticle, pickImport, readAll, readParagraph, furigana, lang, close);
    toolbar.append(actions, status);
    document.documentElement.append(toolbar);
    reader.toolbar = toolbar;
    reader.toolbarStatus = status;
    restoreReaderToolbarPosition(toolbar);
  }

  function restoreReaderToolbarPosition(toolbar) {
    chrome.storage?.local?.get({ [READER_TOOLBAR_POSITION_KEY]: null }, (result) => {
      if (!toolbar.isConnected) {
        return;
      }
      const position = result?.[READER_TOOLBAR_POSITION_KEY];
      if (!isStoredToolbarPosition(position)) {
        return;
      }
      applyReaderToolbarPosition(toolbar, position.left, position.top);
    });
  }

  function isStoredToolbarPosition(value) {
    return Boolean(value)
      && Number.isFinite(value.left)
      && Number.isFinite(value.top);
  }

  function startReaderToolbarDrag(event) {
    if (!reader?.toolbar || event.button !== 0) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    const toolbar = reader.toolbar;
    const rect = toolbar.getBoundingClientRect();
    reader.toolbarDrag = {
      pointerId: event.pointerId,
      offsetX: event.clientX - rect.left,
      offsetY: event.clientY - rect.top,
    };
    toolbar.classList.add("dragging");
    event.currentTarget.setPointerCapture?.(event.pointerId);
    document.addEventListener("pointermove", onReaderToolbarDrag, true);
    document.addEventListener("pointerup", finishReaderToolbarDrag, true);
    document.addEventListener("pointercancel", finishReaderToolbarDrag, true);
  }

  function onReaderToolbarDrag(event) {
    if (!reader?.toolbar || !reader.toolbarDrag || event.pointerId !== reader.toolbarDrag.pointerId) {
      return;
    }
    event.preventDefault();
    applyReaderToolbarPosition(
      reader.toolbar,
      event.clientX - reader.toolbarDrag.offsetX,
      event.clientY - reader.toolbarDrag.offsetY,
    );
    positionToastUnderToolbar();
  }

  function finishReaderToolbarDrag(event) {
    if (!reader?.toolbarDrag || event.pointerId !== reader.toolbarDrag.pointerId) {
      return;
    }
    const toolbar = reader.toolbar;
    reader.toolbarDrag = null;
    toolbar?.classList.remove("dragging");
    document.removeEventListener("pointermove", onReaderToolbarDrag, true);
    document.removeEventListener("pointerup", finishReaderToolbarDrag, true);
    document.removeEventListener("pointercancel", finishReaderToolbarDrag, true);
    if (!toolbar) {
      return;
    }
    const rect = toolbar.getBoundingClientRect();
    chrome.storage?.local?.set({
      [READER_TOOLBAR_POSITION_KEY]: {
        left: Math.round(rect.left),
        top: Math.round(rect.top),
      },
    });
  }

  function applyReaderToolbarPosition(toolbar, left, top) {
    const rect = toolbar.getBoundingClientRect();
    const maxLeft = Math.max(8, window.innerWidth - rect.width - 8);
    const maxTop = Math.max(8, window.innerHeight - rect.height - 8);
    const nextLeft = Math.min(Math.max(8, Number(left) || 8), maxLeft);
    const nextTop = Math.min(Math.max(8, Number(top) || 8), maxTop);
    toolbar.style.left = `${nextLeft}px`;
    toolbar.style.top = `${nextTop}px`;
    toolbar.style.right = "auto";
  }

  async function importSelectedTextFromPage(button) {
    const text = readerSelectedText();
    if (!text) {
      setReaderToolbarStatus(tr("noSelection"));
      updateReaderSelectionButton();
      return;
    }
    await runReaderToolbarAction(button, tr("importingSelection"), async () => {
      const response = await chrome.runtime.sendMessage({
        type: "IMPORT_TEXT",
        payload: {
          title: document.title || "",
          url: location.href,
          text,
        },
      });
      if (!response?.ok) {
        throw new Error(response?.error || tr("importFailed"));
      }
      setReaderToolbarStatus(importResultMessage(response.result), { transient: true });
    });
  }

  async function importMainArticleFromPage(button) {
    await runReaderToolbarAction(button, tr("extractingArticle"), async () => {
      const article = extractMainArticle();
      const response = await chrome.runtime.sendMessage({
        type: "IMPORT_TEXT",
        payload: article,
      });
      if (!response?.ok) {
        throw new Error(response?.error || tr("importFailed"));
      }
      setReaderToolbarStatus(importResultMessage(response.result), { transient: true });
    });
  }

  async function runReaderToolbarAction(button, busyLabel, action) {
    const idleLabel = button.textContent;
    button.disabled = true;
    button.classList.add("loading");
    setReaderToolbarStatus(busyLabel);
    try {
      await action();
    } catch (error) {
      setReaderToolbarStatus(error.message || String(error));
      showToast(error.message || String(error), "error");
    } finally {
      button.classList.remove("loading");
      button.textContent = idleLabel;
      if (button === reader?.importSelectionButton) {
        updateReaderSelectionButton();
      } else {
        button.disabled = false;
      }
    }
  }

  function importResultMessage(result) {
    const imported = result?.imported || {};
    const title = imported.title || tr("webTextTitle");
    return result?.duplicate || imported.duplicate
      ? tr("alreadyImported", { title })
      : tr("imported", { title });
  }

  async function toggleExtensionLanguage() {
    extensionLang = extensionLang === "zh" ? "en" : "zh";
    await chrome.storage?.local?.set?.({ lang: extensionLang });
    renderReaderToolbar();
    if (reader?.panel && reader.selectedToken) {
      showReaderPanel(reader.selectedToken.__jpcorpusAnnotation || {}, reader.selectedToken);
    }
  }

  function removeReaderToolbar() {
    stopReaderToolbarDrag();
    if (reader?.toolbarStatusTimer) {
      window.clearTimeout(reader.toolbarStatusTimer);
      reader.toolbarStatusTimer = null;
    }
    reader?.toolbar?.remove();
    document.removeEventListener("selectionchange", updateReaderSelectionButton, true);
    if (reader) {
      reader.toolbar = null;
      reader.toolbarStatus = null;
      reader.importSelectionButton = null;
    }
  }

  function stopReaderToolbarDrag() {
    if (!reader?.toolbarDrag) {
      return;
    }
    reader.toolbarDrag = null;
    reader.toolbar?.classList.remove("dragging");
    document.removeEventListener("pointermove", onReaderToolbarDrag, true);
    document.removeEventListener("pointerup", finishReaderToolbarDrag, true);
    document.removeEventListener("pointercancel", finishReaderToolbarDrag, true);
  }

  function readerSelectedText() {
    return String(window.getSelection()?.toString() || "").trim();
  }

  function updateReaderSelectionButton() {
    const button = reader?.importSelectionButton;
    if (!button) {
      return;
    }
    const hasSelection = Boolean(readerSelectedText());
    button.disabled = !hasSelection;
    button.title = hasSelection ? "" : tr("noSelection");
  }

  function setReaderToolbarStatus(message, options = {}) {
    if (!reader?.toolbarStatus) {
      return;
    }
    if (reader.toolbarStatusTimer) {
      window.clearTimeout(reader.toolbarStatusTimer);
      reader.toolbarStatusTimer = null;
    }
    const text = cleanText(message);
    reader.toolbarStatus.textContent = text;
    reader.toolbarStatus.hidden = !text;
    if (text && options.transient) {
      reader.toolbarStatusTimer = window.setTimeout(() => {
        if (reader?.toolbarStatus?.textContent === text) {
          setReaderToolbarStatus("");
        }
      }, 4200);
    }
  }

  function startReaderParagraphPicker(button) {
    if (!reader || reader.paragraphPicker) {
      return;
    }
    setReaderToolbarStatus(tr("pickParagraph"));
    button.textContent = tr("cancelPick");
    button.setAttribute("aria-pressed", "true");
    button.classList.add("active");
    reader.paragraphPicker = {
      button,
      target: null,
    };
    document.addEventListener("mousemove", onReaderParagraphMouseMove, true);
    document.addEventListener("click", onReaderParagraphClick, true);
    document.addEventListener("keydown", onReaderParagraphKeyDown, true);
  }

  function stopReaderParagraphPicker() {
    if (!reader?.paragraphPicker) {
      return;
    }
    const { button, target } = reader.paragraphPicker;
    target?.classList.remove("jpcorpus-reader-speech-pick-target");
    button.textContent = button.dataset.readerIdleLabel || tr("readParagraph");
    button.setAttribute("aria-pressed", "false");
    button.classList.remove("active");
    document.removeEventListener("mousemove", onReaderParagraphMouseMove, true);
    document.removeEventListener("click", onReaderParagraphClick, true);
    document.removeEventListener("keydown", onReaderParagraphKeyDown, true);
    reader.paragraphPicker = null;
    setReaderToolbarStatus("");
  }

  function onReaderParagraphMouseMove(event) {
    if (!reader?.paragraphPicker) {
      return;
    }
    const target = readerSpeechBlockCandidate(event.target);
    updateReaderParagraphPickerTarget(target);
  }

  function onReaderParagraphClick(event) {
    if (!reader?.paragraphPicker) {
      return;
    }
    if (event.target instanceof Element && event.target.closest("#jpcorpus-reader-toolbar, #jpcorpus-reader-panel")) {
      return;
    }
    const target = reader.paragraphPicker.target || readerSpeechBlockCandidate(event.target);
    event.preventDefault();
    event.stopPropagation();
    if (!target) {
      setReaderToolbarStatus(tr("noReadableParagraph"));
      return;
    }
    const button = reader.paragraphPicker.button;
    stopReaderParagraphPicker();
    speakReaderParagraph(target, button);
  }

  function onReaderParagraphKeyDown(event) {
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      stopReaderParagraphPicker();
    }
  }

  function updateReaderParagraphPickerTarget(target) {
    if (!reader?.paragraphPicker || reader.paragraphPicker.target === target) {
      return;
    }
    reader.paragraphPicker.target?.classList.remove("jpcorpus-reader-speech-pick-target");
    reader.paragraphPicker.target = target;
    target?.classList.add("jpcorpus-reader-speech-pick-target");
  }

  function positionReaderPanel(panel, anchor) {
    const rect = anchor.getBoundingClientRect();
    const panelWidth = Math.min(340, window.innerWidth - 24);
    const left = Math.max(12, Math.min(window.innerWidth - panelWidth - 12, rect.left));
    const top = Math.max(12, Math.min(window.innerHeight - 220, rect.bottom + 8));
    Object.assign(panel.style, {
      left: `${left}px`,
      top: `${top}px`,
      width: `${panelWidth}px`,
    });
  }

  function removeReaderPanel() {
    reader?.panel?.remove();
    if (reader) {
      reader.panel = null;
    }
  }

  async function speakReaderParagraph(target, button) {
    const units = readerSpeechUnitsForElement(target);
    if (!units.length) {
      showToast(tr("noReadableParagraph"));
      return;
    }
    stopReaderSpeech();
    const runId = activeReaderSpeechRunId + 1;
    activeReaderSpeechRunId = runId;
    activeReaderSpeechButton = button;
    button.textContent = tr("stopReading");
    button.setAttribute("aria-pressed", "true");
    button.classList.add("active");
    setReaderSpeechButtonLoading(button, true);
    try {
      const voicevoxResult = await speakReaderVoicevoxUnits(units, runId);
      if (!voicevoxResult.ok && isActiveReaderSpeech(runId)) {
        await speakReaderBrowserUnits(units.slice(voicevoxResult.nextIndex || 0), runId);
      }
    } finally {
      if (isActiveReaderSpeech(runId)) {
        finishReaderSpeech(button);
      }
    }
  }

  async function speakReaderVoicevoxUnits(units, runId) {
    if (!units.length) {
      return { ok: false, nextIndex: 0 };
    }
    const preparedAudio = new Map();
    const scheduleAudio = (index) => {
      if (index >= units.length || preparedAudio.has(index)) {
        return;
      }
      preparedAudio.set(index, prepareReaderVoicevoxUnit(units[index]).catch(() => ""));
    };
    try {
      for (let index = 0; index < Math.min(SPEECH_PREFETCH_UNITS, units.length); index += 1) {
        scheduleAudio(index);
      }
      for (let index = 0; index < units.length; index += 1) {
        if (!isActiveReaderSpeech(runId)) {
          return { ok: false, nextIndex: index };
        }
        setReaderSpeechButtonLoading(activeReaderSpeechButton, true);
        const dataUrl = await preparedAudio.get(index);
        preparedAudio.delete(index);
        if (!dataUrl) {
          setReaderSpeechButtonLoading(activeReaderSpeechButton, false);
          return { ok: false, nextIndex: index };
        }
        scheduleAudio(index + SPEECH_PREFETCH_UNITS);
        if (!isActiveReaderSpeech(runId)) {
          setReaderSpeechButtonLoading(activeReaderSpeechButton, false);
          return { ok: false, nextIndex: index };
        }
        setReaderSpeechButtonLoading(activeReaderSpeechButton, false);
        showReaderSpeechHighlight(units[index].range, units[index].fallbackElement);
        const played = await playReaderAudioUrl(dataUrl, runId);
        if (!played) {
          return { ok: false, nextIndex: index + 1 };
        }
      }
      return { ok: true, nextIndex: units.length };
    } catch {
      return { ok: false, nextIndex: 0 };
    }
  }

  async function prepareReaderVoicevoxUnit(unit) {
    const response = await chrome.runtime.sendMessage({
      type: "SYNTHESIZE_VOICEVOX",
      payload: { text: unit.text, rate: 1 },
    });
    return response?.ok && response.result?.dataUrl ? response.result.dataUrl : "";
  }

  function playReaderAudioUrl(dataUrl, runId) {
    return new Promise((resolve) => {
      if (!isActiveReaderSpeech(runId)) {
        resolve(false);
        return;
      }
      activeReaderAudio = new Audio(dataUrl);
      activeReaderAudio.addEventListener("ended", () => {
        activeReaderAudio = null;
        resolve(true);
      }, { once: true });
      activeReaderAudio.addEventListener("error", () => {
        activeReaderAudio = null;
        resolve(false);
      }, { once: true });
      activeReaderAudio.addEventListener("pause", () => {
        if (!isActiveReaderSpeech(runId)) {
          activeReaderAudio = null;
          resolve(false);
        }
      }, { once: true });
      activeReaderAudio.play().catch(() => {
        activeReaderAudio = null;
        resolve(false);
      });
    });
  }

  function speakReaderBrowserUnits(units, runId) {
    if (!units.length || !("speechSynthesis" in window) || typeof SpeechSynthesisUtterance === "undefined" || !isActiveReaderSpeech(runId)) {
      return Promise.resolve(false);
    }
    return units.reduce(
      (chain, unit) => chain.then((ok) => {
        if (ok && isActiveReaderSpeech(runId)) {
          showReaderSpeechHighlight(unit.range, unit.fallbackElement);
          return speakReaderBrowserSegment(unit.text, runId);
        }
        return false;
      }),
      Promise.resolve(true),
    );
  }

  function readerSpeechUnitsForElement(element) {
    const source = collectReaderSpeechText(element);
    return readerSpeechTextRanges(source.text)
      .map((range) => {
        const text = normalizeReaderSpeechText(source.text.slice(range.start, range.end));
        if (!text || !hasJapaneseText(text)) {
          return null;
        }
        const domRange = rangeForSpeechOffsets(source.pieces, range.start, range.end);
        return {
          text,
          range: domRange,
          fallbackElement: speechFallbackElement(source.pieces, range.start, range.end, element),
        };
      })
      .filter(Boolean);
  }

  function collectReaderSpeechText(root) {
    const pieces = [];
    let text = "";
    const appendBreak = () => {
      if (text && !/\n$/u.test(text)) {
        text += "\n";
      }
    };
    const appendText = (node) => {
      const value = node.nodeValue || "";
      if (!value.trim()) {
        return;
      }
      const start = text.length;
      text += value;
      pieces.push({ node, start, end: text.length });
    };
    const visit = (node) => {
      if (!node) {
        return;
      }
      if (node.nodeType === Node.TEXT_NODE) {
        if (isReadableSpeechTextNode(node)) {
          appendText(node);
        }
        return;
      }
      if (node.nodeType === Node.DOCUMENT_FRAGMENT_NODE) {
        node.childNodes.forEach(visit);
        return;
      }
      if (!(node instanceof Element) || isSpeechExcludedElement(node)) {
        return;
      }
      const tag = node.tagName.toLowerCase();
      const block = isBlockTag(tag);
      if (block) {
        appendBreak();
      }
      node.childNodes.forEach(visit);
      if (block) {
        appendBreak();
      }
    };
    visit(root);
    return { text, pieces };
  }

  function isReadableSpeechTextNode(node) {
    const text = node.nodeValue || "";
    if (!text.trim()) {
      return false;
    }
    const parent = node.parentElement;
    if (!parent) {
      return false;
    }
    let current = parent;
    while (current && current !== document.body && current !== document.documentElement) {
      if (isSpeechExcludedElement(current)) {
        return false;
      }
      current = current.parentElement;
    }
    return true;
  }

  function isSpeechExcludedElement(element) {
    const tag = element.tagName.toLowerCase();
    if (["button", "canvas", "form", "iframe", "input", "noscript", "rp", "rt", "script", "select", "style", "svg", "textarea"].includes(tag)) {
      return true;
    }
    if (element.closest("#jpcorpus-reader-panel, #jpcorpus-reader-toolbar, .jpcorpus-import-toast, #jpcorpus-picker-overlay, #jpcorpus-picker-label")) {
      return true;
    }
    if (isSkippableElement(element)) {
      return true;
    }
    const style = window.getComputedStyle(element);
    return style.display === "none" || style.visibility === "hidden";
  }

  function readerSpeechTextRanges(text) {
    const ranges = [];
    let start = 0;
    const pushRange = (end) => {
      const range = trimSpeechRange(text, start, end);
      if (range) {
        ranges.push(range);
      }
      start = end;
    };
    for (let index = 0; index < text.length; index += 1) {
      const char = text[index];
      if (/[。！？!?]/u.test(char)) {
        pushRange(index + 1);
      } else if (char === "\n") {
        pushRange(index);
        start = index + 1;
      } else if (/[、，,；;：:]/u.test(char) && index - start >= SPEECH_SOFT_CHARS) {
        pushRange(index + 1);
      } else if (index - start >= SPEECH_MAX_CHARS) {
        pushRange(index + 1);
      }
    }
    pushRange(text.length);
    return ranges;
  }

  function trimSpeechRange(text, start, end) {
    let from = start;
    let to = end;
    while (from < to && /\s/u.test(text[from])) {
      from += 1;
    }
    while (to > from && /\s/u.test(text[to - 1])) {
      to -= 1;
    }
    return to > from ? { start: from, end: to } : null;
  }

  function rangeForSpeechOffsets(pieces, start, end) {
    const textPieces = pieces.filter((piece) => piece.node && piece.end > start && piece.start < end);
    if (!textPieces.length) {
      return null;
    }
    const first = textPieces[0];
    const last = textPieces[textPieces.length - 1];
    const range = document.createRange();
    range.setStart(first.node, Math.max(0, start - first.start));
    range.setEnd(last.node, Math.min((last.node.nodeValue || "").length, end - last.start));
    return range;
  }

  function speechFallbackElement(pieces, start, end, fallback) {
    const piece = pieces.find((item) => item.node && item.end > start && item.start < end);
    const parent = piece?.node?.parentElement;
    return parent?.closest("p, li, dd, dt, blockquote, h1, h2, h3") || fallback;
  }

  function speakReaderBrowserSegment(text, runId) {
    return new Promise((resolve) => {
      setReaderSpeechButtonLoading(activeReaderSpeechButton, false);
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "ja-JP";
      const voice = preferredJapaneseVoice(window.speechSynthesis.getVoices());
      if (voice) {
        utterance.voice = voice;
      }
      utterance.onend = () => resolve(true);
      utterance.onerror = () => resolve(false);
      activeReaderUtterance = utterance;
      window.speechSynthesis.speak(utterance);
    });
  }

  function stopReaderSpeech() {
    activeReaderSpeechRunId += 1;
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    if (activeReaderAudio) {
      activeReaderAudio.pause();
      activeReaderAudio = null;
    }
    activeReaderUtterance = null;
    resetReaderSpeechButton(activeReaderSpeechButton);
    activeReaderSpeechButton = null;
    clearReaderSpeechHighlight();
    document.querySelectorAll(".jpcorpus-reader-speech-button.active").forEach(resetReaderSpeechButton);
  }

  function stopReaderTransientState() {
    stopReaderSpeech();
    stopReaderParagraphPicker();
    stopPicker();
  }

  function onReaderVisibilityChange() {
    if (document.hidden) {
      stopReaderTransientState();
    }
  }

  function finishReaderSpeech(button) {
    activeReaderUtterance = null;
    activeReaderAudio = null;
    resetReaderSpeechButton(button);
    activeReaderSpeechButton = null;
    clearReaderSpeechHighlight();
  }

  function resetReaderSpeechButton(button) {
    if (!button) {
      return;
    }
    button.textContent = button.dataset.readerIdleLabel || tr("readParagraph");
    button.setAttribute("aria-pressed", "false");
    setReaderSpeechButtonLoading(button, false);
    button.classList.remove("active");
  }

  function setReaderSpeechButtonLoading(button, loading) {
    if (!button) {
      return;
    }
    button.setAttribute("aria-busy", loading ? "true" : "false");
    button.classList.toggle("loading", Boolean(loading));
  }

  function isActiveReaderSpeech(runId) {
    return activeReaderSpeechRunId === runId;
  }

  function readerSpeechBlockCandidate(node) {
    if (!(node instanceof Element)) {
      return null;
    }
    const preferred = node.closest("p, li, dd, dt, blockquote, h1, h2, h3");
    if (preferred && isUsableReaderSpeechBlock(preferred)) {
      return preferred;
    }
    let current = node.closest(".jpcorpus-reader-wrapper")?.parentElement || node;
    while (current && current !== document.body && current !== document.documentElement) {
      if (isUsableReaderSpeechBlock(current)) {
        return current;
      }
      current = current.parentElement;
    }
    return null;
  }

  function isUsableReaderSpeechBlock(element) {
    if (!(element instanceof Element) || element.closest("#jpcorpus-reader-panel, #jpcorpus-reader-toolbar, .jpcorpus-import-toast")) {
      return false;
    }
    if (element.classList.contains("jpcorpus-reader-token") || element.classList.contains("jpcorpus-reader-wrapper")) {
      return false;
    }
    const text = normalizeReaderSpeechText(readableText(element));
    if (text.length < 4 || !hasJapaneseText(text)) {
      return false;
    }
    const rect = element.getBoundingClientRect();
    return rect.width >= 40 && rect.height >= 10;
  }

  function normalizeReaderSpeechText(value) {
    return stripReaderSpeechParentheticals(String(value || ""))
      .replace(/\s+/g, " ")
      .trim();
  }

  function stripReaderSpeechParentheticals(value) {
    const pairs = { "(": ")", "（": "）" };
    const closers = new Set(Object.values(pairs));
    const output = [];
    const stack = [];
    [...value].forEach((char) => {
      if (pairs[char]) {
        stack.push(pairs[char]);
        return;
      }
      if (stack.length > 0) {
        if (char === stack[stack.length - 1]) {
          stack.pop();
        }
        return;
      }
      if (!closers.has(char)) {
        output.push(char);
      }
    });
    return output.join("");
  }

  function showReaderSpeechHighlight(range, fallbackElement) {
    clearReaderSpeechHighlight();
    if (range && window.CSS?.highlights && typeof Highlight !== "undefined") {
      CSS.highlights.set("jpcorpus-reader-speaking", new Highlight(range));
      return;
    }
    activeReaderHighlightFallback = fallbackElement;
    activeReaderHighlightFallback?.classList.add("jpcorpus-reader-speaking-block");
  }

  function clearReaderSpeechHighlight() {
    if (window.CSS?.highlights) {
      CSS.highlights.delete("jpcorpus-reader-speaking");
    }
    activeReaderHighlightFallback?.classList.remove("jpcorpus-reader-speaking-block");
    activeReaderHighlightFallback = null;
  }

  function preferredJapaneseVoice(voices) {
    const list = Array.isArray(voices) ? voices : [];
    return list.find((voice) => /^ja\b/i.test(voice.lang || "") && /google/i.test(voice.name || ""))
      || list.find((voice) => /^ja\b/i.test(voice.lang || ""))
      || null;
  }

  function ensureReaderStyles() {
    if (document.querySelector("#jpcorpus-reader-style")) {
      return;
    }
    const style = document.createElement("style");
    style.id = "jpcorpus-reader-style";
    style.textContent = `
      .jpcorpus-reader-token {
        border-radius: 3px !important;
        box-shadow: inset 0 -0.28em rgba(20, 125, 115, 0.18) !important;
        cursor: pointer !important;
        transition: background 120ms ease, box-shadow 120ms ease, outline-color 120ms ease !important;
      }
      .jpcorpus-reader-token-learning,
      .jpcorpus-reader-token-uncertain {
        box-shadow: inset 0 -0.30em rgba(183, 90, 53, 0.26) !important;
      }
      .jpcorpus-reader-token-known {
        box-shadow: inset 0 -0.22em rgba(101, 113, 120, 0.16) !important;
      }
      .jpcorpus-reader-token-ignored {
        box-shadow: inset 0 -0.16em rgba(101, 113, 120, 0.10) !important;
        opacity: 0.78 !important;
      }
      .jpcorpus-reader-token:hover,
      .jpcorpus-reader-token.jpcorpus-reader-selected {
        background: rgba(255, 226, 132, 0.50) !important;
        opacity: 1 !important;
        box-shadow: inset 0 -0.36em rgba(255, 197, 61, 0.45) !important;
        outline: 1px solid rgba(183, 90, 53, 0.55) !important;
      }
      #jpcorpus-reader-toolbar {
        position: fixed !important;
        z-index: 2147483647 !important;
        top: 18px !important;
        right: 18px !important;
        display: flex !important;
        flex-direction: column !important;
        gap: 8px !important;
        align-items: stretch !important;
        padding: 8px !important;
        border: 1px solid #d6e0e3 !important;
        border-left: 4px solid #147d73 !important;
        border-radius: 10px !important;
        background: rgba(255, 255, 255, 0.96) !important;
        box-shadow: 0 14px 36px rgba(31, 39, 42, 0.18) !important;
        font: 760 13px/1 ${CJK_FONT_CSS} !important;
      }
      .jpcorpus-reader-toolbar-drag {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        min-width: 20px !important;
        height: 32px !important;
        border-radius: 7px !important;
        color: #657178 !important;
        cursor: grab !important;
        font: 900 15px/1 ${CJK_FONT_CSS} !important;
        letter-spacing: 1px !important;
        touch-action: none !important;
        user-select: none !important;
      }
      #jpcorpus-reader-toolbar.dragging,
      #jpcorpus-reader-toolbar.dragging .jpcorpus-reader-toolbar-drag {
        cursor: grabbing !important;
      }
      .jpcorpus-reader-toolbar-drag:hover {
        background: #edf4f4 !important;
        color: #147d73 !important;
      }
      .jpcorpus-reader-toolbar-actions {
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 8px !important;
        align-items: center !important;
      }
      .jpcorpus-reader-toolbar-status {
        max-width: 360px !important;
        padding: 1px 3px !important;
        color: #657178 !important;
        font: 650 12px/1.35 ${CJK_FONT_CSS} !important;
      }
      #jpcorpus-reader-toolbar button {
        min-height: 34px !important;
        padding: 7px 11px !important;
        border: 1px solid #d6e0e3 !important;
        border-radius: 8px !important;
        background: #ffffff !important;
        color: #657178 !important;
        font: inherit !important;
        cursor: pointer !important;
      }
      #jpcorpus-reader-toolbar button:hover,
      #jpcorpus-reader-toolbar button.active {
        border-color: #147d73 !important;
        background: #eef5f4 !important;
        color: #147d73 !important;
      }
      #jpcorpus-reader-toolbar button:disabled {
        cursor: default !important;
        opacity: 0.48 !important;
      }
      #jpcorpus-reader-toolbar button:disabled:hover {
        border-color: #d6e0e3 !important;
        background: #ffffff !important;
        color: #657178 !important;
      }
      #jpcorpus-reader-toolbar button.loading::after {
        content: "" !important;
        display: inline-block !important;
        width: 0.65em !important;
        height: 0.65em !important;
        margin-left: 0.45em !important;
        border: 2px solid currentColor !important;
        border-right-color: transparent !important;
        border-radius: 999px !important;
        vertical-align: -0.08em !important;
        animation: jpcorpus-reader-spin 800ms linear infinite !important;
      }
      .jpcorpus-reader-speech-pick-target {
        outline: 2px solid rgba(20, 125, 115, 0.58) !important;
        outline-offset: 3px !important;
        border-radius: 6px !important;
        background: rgba(20, 125, 115, 0.08) !important;
      }
      .jpcorpus-reader-token ruby {
        ruby-position: over !important;
      }
      .jpcorpus-reader-token rt {
        color: #147d73 !important;
        font: 700 0.58em/1 ${CJK_FONT_CSS} !important;
        letter-spacing: 0 !important;
        user-select: none !important;
      }
      #jpcorpus-reader-panel {
        position: fixed !important;
        z-index: 2147483647 !important;
        max-height: min(420px, calc(100vh - 24px)) !important;
        overflow: auto !important;
        box-sizing: border-box !important;
        padding: 14px !important;
        border: 1px solid #d6e0e3 !important;
        border-left: 4px solid #147d73 !important;
        border-radius: 10px !important;
        background: #ffffff !important;
        box-shadow: 0 18px 45px rgba(31, 39, 42, 0.20) !important;
        color: #1f272a !important;
        font: 14px/1.45 ${CJK_FONT_CSS} !important;
      }
      .jpcorpus-reader-panel-title {
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        gap: 12px !important;
        margin: 0 0 8px !important;
      }
      .jpcorpus-reader-panel-title strong {
        font-size: 24px !important;
        line-height: 1.1 !important;
      }
      .jpcorpus-reader-panel-title button {
        min-height: 28px !important;
        padding: 4px 8px !important;
        border: 1px solid #d6e0e3 !important;
        border-radius: 7px !important;
        background: #ffffff !important;
        color: #657178 !important;
        font: 700 12px/1 ${CJK_FONT_CSS} !important;
        cursor: pointer !important;
      }
      ::highlight(jpcorpus-reader-speaking) {
        background: rgba(20, 125, 115, 0.14);
      }
      .jpcorpus-reader-speaking-block {
        background: rgba(20, 125, 115, 0.10) !important;
        border-radius: 6px !important;
      }
      .jpcorpus-reader-panel-meta {
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 6px !important;
        margin: 0 0 10px !important;
      }
      .jpcorpus-reader-panel-meta span {
        padding: 3px 7px !important;
        border-radius: 999px !important;
        background: #eef5f4 !important;
        color: #147d73 !important;
        font-weight: 760 !important;
      }
      .jpcorpus-reader-panel-meaning,
      .jpcorpus-reader-panel-detail {
        margin: 8px 0 0 !important;
        color: #1f272a !important;
      }
      .jpcorpus-reader-panel-detail {
        color: #657178 !important;
        font-size: 12px !important;
      }
      .jpcorpus-reader-panel-actions {
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 8px !important;
        margin-top: 14px !important;
      }
      .jpcorpus-reader-status-button {
        min-height: 34px !important;
        padding: 6px 12px !important;
        border: 1px solid #d6e0e3 !important;
        border-radius: 8px !important;
        background: #ffffff !important;
        color: #657178 !important;
        font: 760 13px/1 ${CJK_FONT_CSS} !important;
        cursor: pointer !important;
      }
      .jpcorpus-reader-status-button:hover {
        border-color: #147d73 !important;
        color: #147d73 !important;
      }
      .jpcorpus-reader-status-button.active {
        border-color: #147d73 !important;
        background: #eef5f4 !important;
        color: #147d73 !important;
      }
      .jpcorpus-reader-status-button:disabled {
        opacity: 0.7 !important;
        cursor: default !important;
      }
      .jpcorpus-reader-status-button:disabled:hover {
        border-color: #d6e0e3 !important;
        color: #657178 !important;
      }
      .jpcorpus-reader-status-button.active:disabled:hover {
        border-color: #147d73 !important;
        color: #147d73 !important;
      }
      @keyframes jpcorpus-reader-spin {
        to { transform: rotate(360deg); }
      }
    `;
    document.documentElement.append(style);
  }

  function startPicker() {
    stopPicker();
    picker = {
      target: null,
      overlay: document.createElement("div"),
      label: document.createElement("div"),
      previousCursor: document.documentElement.style.cursor,
    };
    picker.overlay.id = "jpcorpus-picker-overlay";
    picker.label.id = "jpcorpus-picker-label";
    picker.label.lang = extensionLang === "zh" ? "zh-Hans" : "en";
    Object.assign(picker.overlay.style, {
      position: "fixed",
      zIndex: "2147483647",
      pointerEvents: "none",
      border: "2px solid #147d73",
      background: "rgba(20, 125, 115, 0.10)",
      boxShadow: "0 0 0 99999px rgba(31, 39, 42, 0.10)",
      borderRadius: "4px",
      display: "none",
    });
    Object.assign(picker.label.style, {
      position: "fixed",
      zIndex: "2147483647",
      pointerEvents: "none",
      maxWidth: "360px",
      padding: "6px 8px",
      borderRadius: "6px",
      background: "#147d73",
      color: "#ffffff",
      font: `12px/1.35 ${CJK_FONT_CSS}`,
      display: "none",
    });
    picker.label.textContent = tr("pickerInitial");
    document.documentElement.append(picker.overlay, picker.label);
    document.documentElement.style.cursor = "crosshair";
    window.addEventListener("mousemove", onMouseMove, true);
    window.addEventListener("click", onClick, true);
    window.addEventListener("keydown", onKeyDown, true);
  }

  function stopPicker() {
    if (!picker) {
      return;
    }
    picker.overlay.remove();
    picker.label.remove();
    document.documentElement.style.cursor = picker.previousCursor || "";
    window.removeEventListener("mousemove", onMouseMove, true);
    window.removeEventListener("click", onClick, true);
    window.removeEventListener("keydown", onKeyDown, true);
    picker = null;
  }

  function onMouseMove(event) {
    if (!picker) {
      return;
    }
    const target = textBlockCandidate(event.target);
    if (!target) {
      picker.target = null;
      picker.overlay.style.display = "none";
      picker.label.style.display = "none";
      return;
    }
    picker.target = target;
    updatePickerTarget(target);
  }

  function updatePickerTarget(target) {
    if (!picker || !target) {
      return;
    }
    const rect = target.getBoundingClientRect();
    const textLength = readableText(target).length;
    Object.assign(picker.overlay.style, {
      display: "block",
      left: `${Math.max(0, rect.left)}px`,
      top: `${Math.max(0, rect.top)}px`,
      width: `${Math.max(0, rect.width)}px`,
      height: `${Math.max(0, rect.height)}px`,
    });
    Object.assign(picker.label.style, {
      display: "block",
      left: `${Math.max(8, Math.min(window.innerWidth - 370, rect.left))}px`,
      top: `${Math.max(8, rect.top - 34)}px`,
    });
    picker.label.textContent = tr("pickerLabel", { count: textLength });
  }

  function onClick(event) {
    if (!picker) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    if (!picker.target) {
      return;
    }
    const text = readableText(picker.target);
    const title = articleTitle(picker.target) || document.title || "";
    stopPicker();
    importPickedText({ title, url: location.href, text });
  }

  async function importPickedText(payload) {
    try {
      const response = await chrome.runtime.sendMessage({
        type: "IMPORT_TEXT",
        payload,
      });
      if (!response?.ok) {
        throw new Error(response?.error || tr("importFailed"));
      }
      const message = importResultMessage(response.result);
      setReaderToolbarStatus(message, { transient: true });
      showToast(message, "success");
    } catch (error) {
      const message = error.message || String(error);
      setReaderToolbarStatus(message);
      showToast(message, "error");
    }
  }

  function onKeyDown(event) {
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      stopPicker();
    }
  }

  function textBlockCandidate(node) {
    if (!(node instanceof Element)) {
      return null;
    }
    if (node.id === "jpcorpus-picker-overlay" || node.id === "jpcorpus-picker-label") {
      return picker?.target || null;
    }
    let current = node;
    while (current && current !== document.body && current !== document.documentElement) {
      if (isUsableTextBlock(current)) {
        return current;
      }
      current = current.parentElement;
    }
    return null;
  }

  function isUsableTextBlock(element) {
    const tag = element.tagName.toLowerCase();
    if (isSkippableElement(element) || ["input", "textarea", "select", "button"].includes(tag)) {
      return false;
    }
    const text = readableText(element);
    if (text.length < 8) {
      return false;
    }
    const rect = element.getBoundingClientRect();
    if (rect.width < 40 || rect.height < 12) {
      return false;
    }
    return true;
  }

  function extractMainArticle() {
    const readabilityArticle = extractReadabilityArticle();
    if (readabilityArticle) {
      return readabilityArticle;
    }
    const candidates = articleCandidates();
    const best = candidates
      .map((element) => ({ element, score: articleScore(element), text: readableText(element) }))
      .filter((candidate) => candidate.text.length >= 80)
      .sort((left, right) => right.score - left.score)[0];
    if (!best) {
      throw new Error(tr("noReadableArticle"));
    }
    return {
      title: articleTitle(best.element) || document.title || "",
      url: location.href,
      text: best.text,
    };
  }

  function extractReadabilityArticle() {
    const ReadabilityCtor = globalThis.Readability || (typeof Readability === "function" ? Readability : null);
    if (typeof ReadabilityCtor !== "function") {
      return null;
    }
    try {
      const article = new ReadabilityCtor(document.cloneNode(true), {
        charThreshold: 80,
        classesToPreserve: [],
      }).parse();
      if (!article) {
        return null;
      }
      const contentText = readableHtmlText(article.content || "") || cleanText(article.textContent || "");
      const title = cleanText(article.title || document.title || "");
      if (!isReadableArticleText(contentText)) {
        return null;
      }
      return {
        title,
        url: location.href,
        text: cleanText([title, contentText].filter(Boolean).join("\n\n")),
      };
    } catch {
      return null;
    }
  }

  function readableHtmlText(html) {
    const template = document.createElement("template");
    template.innerHTML = html;
    return readableText(template.content);
  }

  function isReadableArticleText(text) {
    const clean = cleanText(text);
    if (clean.length < 80 || !hasJapaneseText(clean)) {
      return false;
    }
    const japaneseCount = (clean.match(/[\u3040-\u30ff\u3400-\u9fff々〆ヵヶー]/g) || []).length;
    return japaneseCount / clean.length >= 0.2;
  }

  function readabilityMatchScore(candidateText, readabilityText) {
    const candidate = compactArticleText(candidateText);
    const article = compactArticleText(readabilityText);
    if (candidate.length < 80 || article.length < 80) {
      return 0;
    }
    const anchors = readabilityAnchors(article);
    const hits = anchors.filter((anchor) => candidate.includes(anchor)).length;
    if (!hits) {
      return 0;
    }
    const hitRatio = hits / anchors.length;
    const lengthRatio = Math.min(candidate.length, article.length) / Math.max(candidate.length, article.length);
    const extraPenalty = Math.max(0, candidate.length - article.length) * 0.18;
    return hitRatio * 6000 + lengthRatio * 1200 - extraPenalty;
  }

  function readabilityLengthRatio(candidateText, readabilityText) {
    const candidate = compactArticleText(candidateText);
    const article = compactArticleText(readabilityText);
    if (candidate.length < 80 || article.length < 80) {
      return 0;
    }
    return Math.min(candidate.length, article.length) / Math.max(candidate.length, article.length);
  }

  function compactArticleText(text) {
    return cleanText(text)
      .replace(/\s+/gu, "")
      .replace(/[「」『』（）()\[\]【】]/gu, "");
  }

  function readabilityAnchors(articleText) {
    const anchorLength = Math.min(72, Math.max(32, Math.floor(articleText.length / 12)));
    if (articleText.length <= anchorLength) {
      return [articleText];
    }
    const starts = [
      0,
      Math.floor(articleText.length * 0.25),
      Math.floor(articleText.length * 0.5),
      Math.floor(articleText.length * 0.75),
      Math.max(0, articleText.length - anchorLength),
    ];
    return Array.from(new Set(starts.map((start) => articleText.slice(start, start + anchorLength))));
  }

  function articleCandidates() {
    const selectors = [
      "article",
      "main",
      "[role='main']",
      "#main",
      "#content",
      "#contents",
      "#js-article-body",
      ".article",
      ".article-body",
      ".articleBody",
      ".article-main",
      ".article__body",
      ".content",
      ".main",
      ".news_textbody",
      ".news_body",
      ".body",
      "[itemprop='articleBody']",
    ];
    const candidates = new Set();
    document.querySelectorAll(selectors.join(",")).forEach((element) => {
      if (isUsableArticleCandidate(element)) {
        candidates.add(element);
      }
    });
    document.querySelectorAll("p, section, div").forEach((element) => {
      let current = element;
      for (let depth = 0; depth < 5 && current && current !== document.body; depth += 1) {
        if (isUsableArticleCandidate(current)) {
          candidates.add(current);
        }
        current = current.parentElement;
      }
    });
    if (!candidates.size && isUsableArticleCandidate(document.body)) {
      candidates.add(document.body);
    }
    return Array.from(candidates);
  }

  function isUsableArticleCandidate(element) {
    if (!(element instanceof Element)) {
      return false;
    }
    const tag = element.tagName.toLowerCase();
    if (isSkippableElement(element) || ["script", "style", "form"].includes(tag)) {
      return false;
    }
    const text = readableText(element);
    if (text.length < 80) {
      return false;
    }
    const rect = element.getBoundingClientRect();
    return rect.width >= 120 && rect.height >= 40;
  }

  function articleScore(element) {
    const text = readableText(element);
    const linkText = Array.from(element.querySelectorAll("a"))
      .map((link) => readableText(link))
      .join("");
    const linkDensity = text.length ? linkText.length / text.length : 1;
    const linkCount = element.querySelectorAll("a").length;
    const paragraphCount = Array.from(element.querySelectorAll("p, h1, h2, h3, li"))
      .filter((node) => readableText(node).length >= 20)
      .length;
    const selectorBonus = element.matches("article, main, [role='main'], #js-article-body, .article-body, .articleBody, .article-main, .article__body, .news_textbody, .news_body, [itemprop='articleBody']")
      ? 600
      : 0;
    const japaneseCount = (text.match(/[\u3040-\u30ff\u3400-\u9fff]/g) || []).length;
    const effectiveLength = Math.min(text.length, 4500);
    const excessiveLengthPenalty = Math.max(0, text.length - 7000) * 0.6;
    const linkCountPenalty = Math.max(0, linkCount - paragraphCount - 3) * 80;
    return (
      effectiveLength
      + paragraphCount * 220
      + japaneseCount * 0.3
      + selectorBonus
      - linkDensity * 3200
      - excessiveLengthPenalty
      - linkCountPenalty
    );
  }

  function articleTitle(element) {
    const heading = element.querySelector("h1, h2") || document.querySelector("h1");
    return cleanText(heading ? readableText(heading) : "");
  }

  function readableText(element) {
    const chunks = [];
    collectReadableText(element, chunks);
    return cleanText(chunks.join(""));
  }

  function collectReadableText(node, chunks) {
    if (!node) {
      return;
    }
    if (node.nodeType === Node.TEXT_NODE) {
      chunks.push(node.nodeValue || "");
      return;
    }
    if (node.nodeType === Node.DOCUMENT_FRAGMENT_NODE) {
      node.childNodes.forEach((child) => collectReadableText(child, chunks));
      return;
    }
    if (!(node instanceof Element)) {
      return;
    }
    const tag = node.tagName.toLowerCase();
    if (["rt", "rp", "script", "style", "noscript", "svg", "canvas", "button", "input", "select", "textarea", "form"].includes(tag) || isSkippableElement(node)) {
      return;
    }
    const style = window.getComputedStyle(node);
    if (style.display === "none" || style.visibility === "hidden") {
      return;
    }
    if (isBlockTag(tag)) {
      chunks.push("\n");
    }
    node.childNodes.forEach((child) => collectReadableText(child, chunks));
    if (isBlockTag(tag)) {
      chunks.push("\n");
    }
  }

  function isBlockTag(tag) {
    return [
      "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt", "figcaption",
      "figure", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "li", "main",
      "ol", "p", "pre", "section", "table", "td", "th", "tr", "ul",
    ].includes(tag);
  }

  function isSkippableElement(element) {
    const tag = element.tagName.toLowerCase();
    if (["aside", "dialog", "footer", "header", "iframe", "nav"].includes(tag)) {
      return true;
    }
    if (element.getAttribute("aria-hidden") === "true") {
      return true;
    }
    const role = (element.getAttribute("role") || "").toLowerCase();
    if (["banner", "complementary", "contentinfo", "dialog", "navigation", "search"].includes(role)) {
      return true;
    }
    const marker = [
      element.id,
      classNameText(element),
      element.getAttribute("aria-label") || "",
      element.getAttribute("data-testid") || "",
    ].join(" ").toLowerCase();
    return /(^|[-_\s])(ad|ads|advert|banner|breadcrumb|cookie|globalnav|menu|nav|pager|pagination|pickup|promo|recommend|related|ranking|share|sidebar|sns|social|toolbar)([-_\s]|$)/.test(marker);
  }

  function classNameText(element) {
    if (typeof element.className === "string") {
      return element.className;
    }
    return element.className?.baseVal || "";
  }

  function hasJapaneseText(text) {
    return /[\u3040-\u30ff\u3400-\u9fff々〆ヵヶー]/.test(String(text || ""));
  }

  function cleanText(text) {
    return String(text || "")
      .replace(/\u00a0/g, " ")
      .replace(/[ \t　]+\n/g, "\n")
      .replace(/\n[ \t　]+/g, "\n")
      .replace(/[ \t　]{2,}/g, " ")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }

  function showToast(message, tone = "info") {
    const text = cleanText(message);
    if (!text) {
      return;
    }
    document.querySelectorAll(".jpcorpus-import-toast").forEach((node) => node.remove());
    const toast = document.createElement("div");
    toast.className = `jpcorpus-import-toast ${tone === "error" ? "error" : "info"}`;
    toast.textContent = text;
    Object.assign(toast.style, {
      position: "fixed",
      zIndex: "2147483647",
      maxWidth: "360px",
      padding: "10px 12px",
      borderRadius: "8px",
      boxShadow: "0 10px 30px rgba(31, 39, 42, 0.18)",
      background: tone === "error" ? "#b75a35" : "#147d73",
      color: "#ffffff",
      font: `600 13px/1.45 ${CJK_FONT_CSS}`,
      pointerEvents: "none",
      whiteSpace: "pre-wrap",
    });
    toast.lang = extensionLang === "zh" ? "zh-Hans" : "en";
    document.documentElement.append(toast);
    positionToastUnderToolbar(toast);
    window.setTimeout(() => {
      toast.remove();
    }, tone === "error" ? 8000 : 4200);
  }

  function positionToastUnderToolbar(toast = null) {
    const targetToast = toast || document.querySelector(".jpcorpus-import-toast");
    if (!targetToast) {
      return;
    }
    const toolbar = document.querySelector("#jpcorpus-reader-toolbar");
    if (!toolbar) {
      Object.assign(targetToast.style, {
        top: "18px",
        right: "18px",
      });
      return;
    }
    const rect = toolbar.getBoundingClientRect();
    const right = Math.max(8, window.innerWidth - rect.right);
    const top = Math.min(window.innerHeight - 48, rect.bottom + 8);
    Object.assign(targetToast.style, {
      top: `${Math.max(8, top)}px`,
      right: `${right}px`,
      maxWidth: `${Math.max(220, Math.min(360, rect.width))}px`,
    });
  }

  async function syncLanguage() {
    try {
      const response = await chrome.runtime.sendMessage({ type: "GET_EXTENSION_LANG" });
      extensionLang = normalizeLang(response?.lang);
    } catch {
      extensionLang = "zh";
    }
  }

  function tr(key, values = {}) {
    const template = MESSAGES[extensionLang]?.[key] || MESSAGES.en[key] || key;
    return template.replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? ""));
  }

  function normalizeLang(value) {
    return value === "en" ? "en" : "zh";
  }
})();
