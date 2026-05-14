window.JPCORPUS_DETAIL = (() => {
  function createDetailHelpers({
    app,
    displayCount,
    displayMeaningRaw,
    el,
    examplesForWord,
    formatNumber,
    render,
    renderExamples,
    renderLexicalNotes,
    renderMeaningValue,
    scheduleStudyReview,
    setStatus,
    statChip,
    stateLabels,
    statusFor,
    studyActions,
    studyCheckLabel,
    studyKindLabel,
    t,
  }) {
    function renderDetailHeader(word) {
      const header = el("header", "detail-header");
      const titleRow = el("div", "detail-title-row");
      const title = el("div", "detail-title");
      title.append(el("h2", "", word.word || ""), el("span", "reading", word.reading || ""));
      const stats = el("div", "detail-stats");
      const examples = examplesForWord(word);
      const exampleCount = examples.length || Number(word.example_count || 0);
      stats.append(
        ...(word.level ? [statChip(word.level)] : []),
        statChip(`${t("count")} ${formatNumber(displayCount(word))}`),
        statChip(`${t("examples")} ${formatNumber(exampleCount)}`),
        statChip(studyCheckLabel(word)),
      );
      titleRow.append(title, stats);

      const meanings = el("div", "meaning-block");
      const mainMeaning = displayMeaningRaw(word);
      meanings.append(mainMeaning ? renderMeaningValue(word, "meaning-main") : el("div", "meaning-main", "—"));
      if (!mainMeaning) {
        meanings.append(el("div", "meaning-alt", t("missingMeaning")));
      }

      header.append(titleRow, meanings, renderStatusActions(word));
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
      }));
      return card;
    }

    function renderStudyActions(word) {
      const actions = el("div", "study-actions");
      const check = el("button", "study-primary-action", t("studyCheckButton"));
      check.type = "button";
      check.addEventListener("click", () => {
        studyActions.addStudyCheck(word);
      });

      const shaky = el("button", "study-secondary-action", t("studyAgain"));
      shaky.type = "button";
      shaky.addEventListener("click", () => {
        studyActions.markStudyWord("learning");
      });

      const reveal = el("button", "study-answer-action", t(app.study.showAnswer ? "hideAnswer" : "revealAnswer"));
      reveal.type = "button";
      reveal.addEventListener("click", () => {
        app.study.showAnswer = !app.study.showAnswer;
        render();
      });

      const next = el("button", "study-next-action", t("nextWord"));
      next.type = "button";
      next.addEventListener("click", studyActions.nextStudyWord);

      actions.append(check, shaky, reveal, next);
      return actions;
    }

    function renderStatusActions(word) {
      if (app.mode === "read") {
        return renderReaderStudyActions(word);
      }
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

    function renderReaderStudyActions(word) {
      const wrap = el("div", "status-actions reader-study-actions");
      const status = statusFor(word);
      [
        {
          label: t("readerAddStudy"),
          active: status === "learning" || status === "uncertain",
          className: "reader-study-primary",
          action: () => addWordToStudyFromReader(word),
        },
        {
          label: t("readerKnown"),
          active: status === "known",
          action: () => setStatus(word, "known"),
        },
        {
          label: t("readerIgnore"),
          active: status === "ignored",
          action: () => setStatus(word, "ignored"),
        },
      ].forEach((item) => {
        const button = el("button", item.className || "", item.label);
        button.type = "button";
        button.classList.toggle("active", item.active);
        button.addEventListener("click", () => {
          item.action();
          app.reader.preserveScrollOnRender = true;
          render();
        });
        wrap.append(button);
      });
      if (status !== "none") {
        const clear = el("button", "", t("readerClearMark"));
        clear.type = "button";
        clear.addEventListener("click", () => {
          setStatus(word, "none");
          app.reader.preserveScrollOnRender = true;
          render();
        });
        wrap.append(clear);
      }
      return wrap;
    }

    function addWordToStudyFromReader(word) {
      setStatus(word, "learning");
      scheduleStudyReview(word);
    }

    return {
      renderDetailHeader,
      renderStudyCard,
    };
  }

  return { createDetailHelpers };
})();
