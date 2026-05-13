(() => {
  if (window.__jpcorpusPickerLoaded) {
    return;
  }
  window.__jpcorpusPickerLoaded = true;

  let picker = null;

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type !== "START_AREA_PICKER") {
      return false;
    }
    startPicker();
    sendResponse({ ok: true });
    return false;
  });

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
    picker.label.textContent = "Click to import this text block. Esc to cancel.";
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
    const target = bestTextBlock(event.target);
    picker.target = target;
    if (!target) {
      picker.overlay.style.display = "none";
      picker.label.style.display = "none";
      return;
    }
    const rect = target.getBoundingClientRect();
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
  }

  function onClick(event) {
    if (!picker?.target) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    const text = visibleText(picker.target);
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

  function bestTextBlock(node) {
    if (!(node instanceof Element)) {
      return null;
    }
    if (node.id === "jpcorpus-picker-overlay" || node.id === "jpcorpus-picker-label") {
      return picker?.target;
    }
    const candidates = [];
    let current = node;
    while (current && current !== document.body && current !== document.documentElement) {
      if (isUsableTextBlock(current)) {
        candidates.push(current);
      }
      current = current.parentElement;
    }
    if (!candidates.length) {
      return null;
    }
    return candidates.find((candidate) => visibleText(candidate).length >= 80) || candidates[0];
  }

  function isUsableTextBlock(element) {
    const tag = element.tagName.toLowerCase();
    if (["script", "style", "input", "textarea", "select", "button", "nav", "header", "footer"].includes(tag)) {
      return false;
    }
    const text = visibleText(element);
    if (text.length < 8) {
      return false;
    }
    const rect = element.getBoundingClientRect();
    if (rect.width < 40 || rect.height < 12) {
      return false;
    }
    return true;
  }

  function visibleText(element) {
    return String(element.innerText || element.textContent || "")
      .replace(/\u00a0/g, " ")
      .replace(/[ \t　]+\n/g, "\n")
      .replace(/\n[ \t　]+/g, "\n")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }
})();
