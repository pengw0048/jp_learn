(() => {
  const SCRIPT_VERSION = "0.1.13";
  if (window.__jpcorpusContentVersion === SCRIPT_VERSION) {
    return;
  }
  window.__jpcorpusContentVersion = SCRIPT_VERSION;
  window.__jpcorpusPickerLoaded = true;
  const CJK_FONT_CSS = '"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", "Noto Sans SC", "Source Han Sans SC", "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif';
  const MESSAGES = {
    zh: {
      stillAnnotating: "jpcorpus 仍在标注这个页面...",
      readerOff: "jpcorpus 网页阅读模式已关闭。",
      annotating: "正在用 jpcorpus 标注这个页面...",
      noJapaneseText: "没有在正文里找到日语文本。",
      cannotAnnotate: "无法标注这个页面。",
      annotated: "jpcorpus 标注了 {count} 个词。",
      noAnnotations: "没有应用标注。如果这里明显不对，可以刷新页面再试。",
      close: "关闭",
      noGlossary: "没有找到词典释义。",
      matchedForm: "匹配词形：{surface}",
      saving: "保存中...",
      cannotUpdateStudy: "无法更新学习状态。",
      addedStudy: "已加入学习：{word}",
      updatedStudy: "已更新学习状态：{word}",
      addStudy: "加入学习",
      known: "已认识",
      studying: "复习中",
      ignore: "忽略",
      ignored: "已忽略",
      clearStatus: "取消标记",
      readSentence: "朗读",
      pickerInitial: "点击导入高亮文本。Esc 取消。",
      pickerLabel: "点击导入 {count} 字 · Esc 取消",
      noReadableArticle: "没有在这个页面找到可读正文。",
    },
    en: {
      stillAnnotating: "jpcorpus is still annotating this page...",
      readerOff: "jpcorpus reading mode off.",
      annotating: "Annotating this page with jpcorpus...",
      noJapaneseText: "No Japanese text found in the main page content.",
      cannotAnnotate: "Could not annotate this page.",
      annotated: "jpcorpus annotated {count} words.",
      noAnnotations: "No annotations were applied. Try reloading the page if this looks wrong.",
      close: "Close",
      noGlossary: "No glossary entry found.",
      matchedForm: "Matched form: {surface}",
      saving: "Saving...",
      cannotUpdateStudy: "Could not update study status.",
      addedStudy: "Added to study: {word}",
      updatedStudy: "Updated study status: {word}",
      addStudy: "Add to study",
      known: "Known",
      studying: "Reviewing",
      ignore: "Ignore",
      ignored: "Ignored",
      clearStatus: "Clear",
      readSentence: "Read",
      pickerInitial: "Click to import highlighted text. Esc cancel.",
      pickerLabel: "Click to import {count} chars. · Esc cancel",
      noReadableArticle: "No readable article text found on this page.",
    },
  };
  let extensionLang = "zh";

  let picker = null;
  let reader = null;
  let activeReaderUtterance = null;
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
    };
    showToast(tr("annotating"));
    try {
      const root = readerRoot();
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
    document.querySelectorAll(".jpcorpus-reader-wrapper").forEach((wrapper) => {
      if (wrapper.parentNode) {
        wrapper.replaceWith(document.createTextNode(wrapper.textContent || ""));
      }
    });
    document.querySelectorAll(".jpcorpus-reader-token").forEach((token) => {
      if (token.parentNode) {
        token.replaceWith(document.createTextNode(token.textContent || ""));
      }
    });
  }

  function readerRoot() {
    const candidates = articleCandidates()
      .map((element) => ({ element, score: articleScore(element), text: readableText(element) }))
      .filter((candidate) => candidate.text.length >= 80)
      .sort((left, right) => right.score - left.score);
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
      let cursor = 0;
      ranges.forEach((range) => {
        if (range.start > cursor) {
          wrapper.append(document.createTextNode(text.slice(cursor, range.start)));
        }
        const token = document.createElement("span");
        token.className = "jpcorpus-reader-token";
        token.textContent = text.slice(range.start, range.end);
        token.__jpcorpusAnnotation = range;
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
    if (target instanceof Element && target.closest("#jpcorpus-reader-panel, .jpcorpus-reader-token")) {
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
    const read = document.createElement("button");
    read.type = "button";
    read.className = "jpcorpus-reader-speech-button";
    read.textContent = tr("readSentence");
    read.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      speakReaderSentence(anchor, read);
    });
    title.append(word, read, close);

    const meta = document.createElement("div");
    meta.className = "jpcorpus-reader-panel-meta";
    [annotation.reading, annotation.level, annotation.pos].filter(Boolean).forEach((item) => {
      const chip = document.createElement("span");
      chip.textContent = item;
      meta.append(chip);
    });

    const meaning = document.createElement("p");
    meaning.className = "jpcorpus-reader-panel-meaning";
    meaning.textContent = annotation.meaning_zh || annotation.meaning || tr("noGlossary");

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
    row.append(
      renderReaderStatusButton(row, annotation, {
        status: "learning",
        label: currentStatus === "learning" || currentStatus === "uncertain" ? tr("studying") : tr("addStudy"),
      }),
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
      setReaderWordStatus(row, annotation, options.status, button);
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

  async function setReaderWordStatus(row, annotation, status, button) {
    const word = annotation.word || annotation.surface || "";
    if (!word) {
      showToast(tr("cannotUpdateStudy"), "error");
      return;
    }
    const buttons = Array.from(row.querySelectorAll("button"));
    buttons.forEach((item) => {
      item.disabled = true;
    });
    button.textContent = tr("saving");
    try {
      const response = await chrome.runtime.sendMessage({
        type: "SET_WORD_STATUS",
        payload: { word, status },
      });
      if (!response?.ok) {
        throw new Error(response?.error || tr("cannotUpdateStudy"));
      }
      annotation.status = normalizeReaderStatus(response.result?.status || status);
      annotation.study_count = response.result?.study_count || 0;
      updateReaderAnnotationsForWord(word, annotation.status, annotation.study_count);
      refreshReaderStudyActions(row, annotation);
      showToast(tr(status === "learning" ? "addedStudy" : "updatedStudy", { word }));
    } catch (error) {
      refreshReaderStudyActions(row, annotation);
      showToast(error.message || String(error), "error");
    }
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
    stopReaderSpeech();
    reader?.panel?.remove();
    if (reader) {
      reader.panel = null;
    }
  }

  function speakReaderSentence(anchor, button) {
    const sentence = readerSentenceForToken(anchor);
    const text = sentence.text || anchor.textContent || "";
    if (!text.trim() || !("speechSynthesis" in window) || typeof SpeechSynthesisUtterance === "undefined") {
      return;
    }
    stopReaderSpeech();
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    showReaderSpeechHighlight(sentence.range, sentence.fallbackElement);
    const utterance = new SpeechSynthesisUtterance(text.replace(/\s+/g, " ").trim());
    utterance.lang = "ja-JP";
    const voice = preferredJapaneseVoice(window.speechSynthesis.getVoices());
    if (voice) {
      utterance.voice = voice;
    }
    const finish = () => {
      if (activeReaderUtterance !== utterance) {
        return;
      }
      activeReaderUtterance = null;
      button.disabled = false;
      button.removeAttribute("aria-busy");
      clearReaderSpeechHighlight();
    };
    utterance.onend = finish;
    utterance.onerror = finish;
    activeReaderUtterance = utterance;
    window.speechSynthesis.speak(utterance);
  }

  function stopReaderSpeech() {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    activeReaderUtterance = null;
    clearReaderSpeechHighlight();
    document.querySelectorAll(".jpcorpus-reader-speech-button[aria-busy='true']").forEach((button) => {
      button.disabled = false;
      button.removeAttribute("aria-busy");
    });
  }

  function readerSentenceForToken(token) {
    const fallbackElement = token.closest("p, li, dd, dt, div, section, article") || token;
    const root = token.closest(".jpcorpus-reader-wrapper") || token.parentNode || token;
    const fullText = root.textContent || token.textContent || "";
    const tokenOffset = textOffsetWithin(root, token);
    const bounds = sentenceBounds(fullText, tokenOffset);
    const range = rangeForTextOffsets(root, bounds.start, bounds.end);
    return {
      text: fullText.slice(bounds.start, bounds.end).trim() || token.textContent || "",
      range,
      fallbackElement,
    };
  }

  function textOffsetWithin(root, target) {
    let offset = 0;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (target.contains(node)) {
        return offset;
      }
      offset += (node.nodeValue || "").length;
    }
    return 0;
  }

  function sentenceBounds(text, offset) {
    const punctuation = /[。！？!?]/u;
    let start = 0;
    for (let index = Math.max(0, offset - 1); index >= 0; index -= 1) {
      if (punctuation.test(text[index]) || text[index] === "\n") {
        start = index + 1;
        break;
      }
    }
    let end = text.length;
    for (let index = Math.max(0, offset); index < text.length; index += 1) {
      if (punctuation.test(text[index]) || text[index] === "\n") {
        end = index + 1;
        break;
      }
    }
    while (start < end && /\s/u.test(text[start])) {
      start += 1;
    }
    while (end > start && /\s/u.test(text[end - 1])) {
      end -= 1;
    }
    return { start, end };
  }

  function rangeForTextOffsets(root, start, end) {
    const range = document.createRange();
    let offset = 0;
    let started = false;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      const length = (node.nodeValue || "").length;
      const nextOffset = offset + length;
      if (!started && start <= nextOffset) {
        range.setStart(node, Math.max(0, start - offset));
        started = true;
      }
      if (started && end <= nextOffset) {
        range.setEnd(node, Math.max(0, end - offset));
        return range;
      }
      offset = nextOffset;
    }
    range.selectNodeContents(root);
    return range;
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
      .jpcorpus-reader-panel-title .jpcorpus-reader-speech-button {
        margin-left: auto !important;
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
    stopPicker();
    chrome.runtime.sendMessage({
      type: "IMPORT_TEXT",
      payload: {
        title: document.title || "",
        url: location.href,
        text,
      },
    });
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
      for (let depth = 0; depth < 3 && current && current !== document.body; depth += 1) {
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
      top: "18px",
      right: "18px",
      maxWidth: "360px",
      padding: "10px 12px",
      borderRadius: "8px",
      boxShadow: "0 10px 30px rgba(31, 39, 42, 0.18)",
      background: tone === "error" ? "#b75a35" : "#147d73",
      color: "#ffffff",
      font: `600 13px/1.45 ${CJK_FONT_CSS}`,
      whiteSpace: "pre-wrap",
    });
    toast.lang = extensionLang === "zh" ? "zh-Hans" : "en";
    document.documentElement.append(toast);
    window.setTimeout(() => {
      toast.remove();
    }, tone === "error" ? 8000 : 4200);
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
