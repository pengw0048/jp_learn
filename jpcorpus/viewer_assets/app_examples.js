window.JPCORPUS_EXAMPLES = (() => {
  function createExampleHelpers({
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
    storage,
    t,
  }) {
    const { STORAGE_EXAMPLE_COLUMNS } = storage;

    function renderExamples(word, options = {}) {
      const revealAnnotations = options.revealAnnotations ?? true;
      const section = el("section", "examples");
      const header = el("div", "examples-header");
      header.append(el("h3", "section-title", t("examples")));
      if (app.mode !== "read") {
        header.append(renderExampleColumnControl());
      }
      section.append(header);
      const examples = examplesForWord(word);
      if (examples.length === 0) {
        const message = word._detailLoading && !word._detailLoaded
          ? t("wordDetailLoading")
          : t("noExamples");
        section.append(emptyMessage(message));
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
      const allowAiExplain = app.mode !== "study" || revealAnnotations;
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
      lines.append(renderExampleFooter(word, example, sourceClass, { allowAiExplain }));
      item.append(lines);
      const annotationBlock = renderExampleAnnotationBlock(word, example, {
        allowAiExplain,
        revealAnnotations,
      });
      if (annotationBlock) {
        item.append(annotationBlock);
      }
      return {
        item,
        weight: exampleCardWeight(example, beforeLines, afterLines),
      };
    }

    function renderExampleFooter(word, example, sourceClass, options = {}) {
      const footer = el("div", "example-footer");
      footer.append(el("small", `reference reference-${sourceClass}`, formatReference(example)));
      const actions = el("div", "example-footer-actions");
      if (renderSpeakButton) {
        actions.append(renderSpeakButton(example.sentence || example.matched_text || word.word, "tts-button example-tts-button"));
      }
      if (options.allowAiExplain) {
        actions.append(renderExampleExplainButton(word, example, exampleExplanationKey(word, example)));
      }
      if (actions.childNodes.length > 0) {
        footer.append(actions);
      }
      return footer;
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

    function renderExampleAnnotationBlock(word, example, options = {}) {
      const allowAiExplain = options.allowAiExplain ?? true;
      const revealAnnotations = options.revealAnnotations ?? true;
      const hasTranslation = revealAnnotations && example.translation_zh;
      const hasUsageNote = revealAnnotations && example.usage_note_zh;
      const key = exampleExplanationKey(word, example);
      const explanation = app.exampleExplanations[key];
      const explanationBlock = allowAiExplain ? renderExplanationResult(explanation, "example-explanation") : null;
      if (!hasTranslation && !hasUsageNote && !explanationBlock) {
        return null;
      }
      const block = el("div", "annotation-block");
      if (hasTranslation || hasUsageNote) {
        const lines = el("div", "annotation-lines");
        if (hasTranslation) {
          lines.append(el("div", "annotation-line translation-line", `${t("translation")}: ${example.translation_zh}`));
        }
        if (hasUsageNote) {
          lines.append(el("div", "annotation-line", `${t("usageNote")}: ${example.usage_note_zh}`));
        }
        block.append(lines);
      }
      if (explanationBlock) {
        block.append(explanationBlock);
      }
      return block;
    }

    function renderExampleExplainButton(word, example, key) {
      const button = el("button", "example-explain-button", "✨");
      const canExplain = canUseReaderAi();
      button.type = "button";
      button.title = t(canExplain ? "exampleExplainTitle" : "readerExplainUnavailable");
      button.setAttribute("aria-label", button.title);
      button.disabled = !canExplain || app.exampleExplanations[key]?.status === "loading";
      button.addEventListener("click", () => startExampleExplanation(word, example, key));
      return button;
    }

    async function startExampleExplanation(word, example, key) {
      app.exampleExplanations[key] = {
        status: "loading",
      };
      renderDetail();
      try {
        const payload = await api.explain({
          word: explanationWordPayload(word),
          example,
        });
        app.exampleExplanations[key] = {
          status: "succeeded",
          result: payload.explanation || {},
        };
      } catch (error) {
        app.exampleExplanations[key] = {
          status: "failed",
          error: error.message || String(error),
        };
      }
      renderDetail();
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

    return {
      appendHighlighted,
      renderExamples,
    };
  }

  return { createExampleHelpers };
})();
