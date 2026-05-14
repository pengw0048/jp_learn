window.JPCORPUS_DOM = (() => {
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

  function badge(value) {
    return el("span", "level-badge", value);
  }

  function statChip(value) {
    return el("span", "stat-chip", value);
  }

  function emptyMessage(value) {
    return el("div", "empty-list", value);
  }

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function clampNumber(value, min, max) {
    if (!Number.isFinite(value)) {
      return min;
    }
    return Math.min(Math.max(value, min), max);
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

  return {
    asArray,
    badge,
    clampNumber,
    contextPreview,
    el,
    emptyMessage,
    statChip,
    strong,
  };
})();
