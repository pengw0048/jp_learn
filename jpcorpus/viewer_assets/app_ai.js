window.JPCORPUS_AI = (() => {
  function createAiHelpers({
    api,
    app,
    displayMeaningRaw,
    el,
    renderDetail,
    t,
  }) {
    function canUseReaderAi() {
      const llm = app.maintenance.llm || {};
      return Boolean(
        app.maintenance.enabled
        && llm.api_key_configured
        && (llm.provider === "apple" || llm.model),
      );
    }

    function renderExplanationResult(explanation, loadingClass = "reader-explanation") {
      if (!explanation) {
        return null;
      }
      const block = el("div", `${loadingClass} ${explanation.status || ""}`.trim());
      if (explanation.status === "loading") {
        block.append(el("div", "annotation-line", t("readerExplainLoading")));
        return block;
      }
      if (explanation.status === "failed") {
        block.append(el("div", "annotation-line", t("readerExplainFailed", { error: explanation.error || "" })));
        return block;
      }
      const result = explanation.result || {};
      if (result.translation_zh) {
        block.append(el("div", "annotation-line translation-line", `${t("readerTranslation")}: ${result.translation_zh}`));
      }
      if (result.usage_note_zh) {
        block.append(el("div", "annotation-line", `${t("readerUsage")}: ${result.usage_note_zh}`));
      }
      return block.childNodes.length ? block : null;
    }

    function renderReaderExplanation(selection) {
      const explanation = app.reader.explanation;
      if (!explanation || explanation.key !== selection.key) {
        return null;
      }
      return renderExplanationResult(explanation);
    }

    function renderReaderQuestionForm(word, selection) {
      const form = el("form", "reader-question-form");
      const input = el("input", "reader-question-input");
      input.type = "text";
      input.placeholder = t("readerQuestionPlaceholder");
      input.disabled = !canUseReaderAi() || app.reader.question?.status === "loading";
      const button = el("button", "reader-question-submit", t("readerQuestionSubmit"));
      button.type = "submit";
      button.disabled = input.disabled;
      if (!canUseReaderAi()) {
        input.title = t("readerExplainUnavailable");
        button.title = t("readerExplainUnavailable");
      }
      form.append(input, button);
      form.addEventListener("submit", (event) => {
        event.preventDefault();
        const question = input.value.trim();
        if (!question) {
          return;
        }
        startReaderQuestion(word, selection, question);
      });
      return form;
    }

    function renderReaderQuestionAnswer(selection) {
      const question = app.reader.question;
      if (!question || question.key !== selection.key) {
        return null;
      }
      const block = el("div", `reader-question-answer ${question.status || ""}`.trim());
      if (question.status === "loading") {
        block.append(el("div", "annotation-line", t("readerQuestionLoading")));
        return block;
      }
      if (question.status === "failed") {
        block.append(el("div", "annotation-line", t("readerQuestionFailed", { error: question.error || "" })));
        return block;
      }
      if (question.answer) {
        block.append(
          el("div", "annotation-line translation-line", `${t("readerQuestionAnswer")}: ${question.answer}`),
        );
      }
      return block.childNodes.length ? block : null;
    }

    async function startReaderExplanation(word, selection) {
      if (!selection) {
        return;
      }
      app.reader.explanation = {
        key: selection.key,
        status: "loading",
      };
      renderDetail();
      try {
        const payload = await api.explain({
          word: explanationWordPayload(word),
          example: selection.example,
        });
        app.reader.explanation = {
          key: selection.key,
          status: "succeeded",
          result: payload.explanation || {},
        };
      } catch (error) {
        app.reader.explanation = {
          key: selection.key,
          status: "failed",
          error: error.message || String(error),
        };
      }
      renderDetail();
    }

    async function startReaderQuestion(word, selection, question) {
      if (!selection) {
        return;
      }
      app.reader.question = {
        key: selection.key,
        status: "loading",
        prompt: question,
      };
      renderDetail();
      try {
        const payload = await api.explain({
          word: explanationWordPayload(word),
          example: selection.example,
          question,
        });
        app.reader.question = {
          key: selection.key,
          status: "succeeded",
          prompt: question,
          answer: payload.answer || "",
        };
      } catch (error) {
        app.reader.question = {
          key: selection.key,
          status: "failed",
          prompt: question,
          error: error.message || String(error),
        };
      }
      renderDetail();
    }

    function explanationWordPayload(word) {
      return {
        word: word.word || "",
        reading: word.reading || "",
        level: word.level || "",
        meaning_zh: word.meaning_zh || displayMeaningRaw(word) || "",
        meaning: word.meaning || "",
      };
    }

    return {
      canUseReaderAi,
      explanationWordPayload,
      renderExplanationResult,
      renderReaderExplanation,
      renderReaderQuestionAnswer,
      renderReaderQuestionForm,
      startReaderExplanation,
    };
  }

  return { createAiHelpers };
})();
