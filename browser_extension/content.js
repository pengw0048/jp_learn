(() => {
  if (window.__jpcorpusPickerLoaded) {
    return;
  }
  window.__jpcorpusPickerLoaded = true;

  let picker = null;

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type === "START_AREA_PICKER") {
      startPicker();
      sendResponse({ ok: true });
      return false;
    }
    if (message?.type === "EXTRACT_MAIN_ARTICLE") {
      try {
        sendResponse({ ok: true, payload: extractMainArticle() });
      } catch (error) {
        sendResponse({ ok: false, error: error.message || String(error) });
      }
      return false;
    }
    return false;
  });

  function startPicker() {
    stopPicker();
    picker = {
      target: null,
      candidates: [],
      candidateIndex: 0,
      overlay: document.createElement("div"),
      label: document.createElement("div"),
      previousCursor: document.documentElement.style.cursor,
    };
    picker.overlay.id = "jpcorpus-picker-overlay";
    picker.label.id = "jpcorpus-picker-label";
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
      font: "12px/1.35 system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
      display: "none",
    });
    picker.label.textContent = "Click to import. [ smaller, ] larger, Esc cancel.";
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
    const candidates = textBlockCandidates(event.target);
    if (!candidates.length) {
      picker.target = null;
      picker.candidates = [];
      picker.candidateIndex = 0;
      picker.overlay.style.display = "none";
      picker.label.style.display = "none";
      return;
    }
    const previousTarget = picker.target;
    picker.candidates = candidates;
    if (previousTarget && candidates.includes(previousTarget)) {
      picker.candidateIndex = candidates.indexOf(previousTarget);
    } else {
      picker.candidateIndex = defaultCandidateIndex(candidates);
    }
    updatePickerTarget();
  }

  function updatePickerTarget() {
    if (!picker?.candidates.length) {
      return;
    }
    const target = picker.candidates[picker.candidateIndex] || picker.candidates[0];
    picker.target = target;
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
    picker.label.textContent = [
      `Click to import ${textLength} chars.`,
      picker.candidateIndex > 0 ? "[ smaller" : "",
      picker.candidateIndex < picker.candidates.length - 1 ? "] larger" : "",
      "Esc cancel",
    ].filter(Boolean).join(" · ");
  }

  function onClick(event) {
    if (!picker?.target) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
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
      return;
    }
    if (event.key === "[" || event.key === "ArrowUp") {
      event.preventDefault();
      event.stopPropagation();
      if (!picker.candidates.length) {
        return;
      }
      picker.candidateIndex = Math.max(0, picker.candidateIndex - 1);
      updatePickerTarget();
      return;
    }
    if (event.key === "]" || event.key === "ArrowDown") {
      event.preventDefault();
      event.stopPropagation();
      if (!picker.candidates.length) {
        return;
      }
      picker.candidateIndex = Math.min(picker.candidates.length - 1, picker.candidateIndex + 1);
      updatePickerTarget();
    }
  }

  function textBlockCandidates(node) {
    if (!(node instanceof Element)) {
      return [];
    }
    if (node.id === "jpcorpus-picker-overlay" || node.id === "jpcorpus-picker-label") {
      return picker?.candidates || [];
    }
    const candidates = [];
    let current = node;
    while (current && current !== document.body && current !== document.documentElement) {
      if (isUsableTextBlock(current)) {
        candidates.push(current);
      }
      current = current.parentElement;
    }
    return candidates;
  }

  function defaultCandidateIndex(candidates) {
    const usefulIndex = candidates.findIndex((candidate) => readableText(candidate).length >= 80);
    if (usefulIndex >= 0) {
      return usefulIndex;
    }
    return 0;
  }

  function isUsableTextBlock(element) {
    const tag = element.tagName.toLowerCase();
    if (["script", "style", "input", "textarea", "select", "button", "nav", "header", "footer"].includes(tag)) {
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
    const candidates = articleCandidates();
    const best = candidates
      .map((element) => ({ element, score: articleScore(element), text: readableText(element) }))
      .filter((candidate) => candidate.text.length >= 80)
      .sort((left, right) => right.score - left.score)[0];
    if (!best) {
      throw new Error("No readable article text found on this page.");
    }
    return {
      title: articleTitle(best.element) || document.title || "",
      url: location.href,
      text: best.text,
    };
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
      ".content",
      ".main",
      ".news_textbody",
      ".body",
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
    if (["script", "style", "nav", "header", "footer", "form", "aside"].includes(tag)) {
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
    const paragraphCount = Array.from(element.querySelectorAll("p, h1, h2, h3, li"))
      .filter((node) => readableText(node).length >= 20)
      .length;
    const selectorBonus = element.matches("article, main, [role='main'], #js-article-body, .article-body, .articleBody, .news_textbody")
      ? 600
      : 0;
    const japaneseCount = (text.match(/[\u3040-\u30ff\u3400-\u9fff]/g) || []).length;
    return (
      text.length
      + paragraphCount * 120
      + japaneseCount * 0.4
      + selectorBonus
      - linkDensity * 1800
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
    if (!(node instanceof Element)) {
      return;
    }
    const tag = node.tagName.toLowerCase();
    if (["rt", "rp", "script", "style", "noscript", "svg", "canvas", "button", "input", "select", "textarea", "form"].includes(tag)) {
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

  function cleanText(text) {
    return String(text || "")
      .replace(/\u00a0/g, " ")
      .replace(/[ \t　]+\n/g, "\n")
      .replace(/\n[ \t　]+/g, "\n")
      .replace(/[ \t　]{2,}/g, " ")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }
})();
