window.JPCORPUS_DETAIL = (() => {
  function createDetailHelpers({
    app,
    displayCount,
    displayReading,
    displayMeaningRaw,
    el,
    examplesForWord,
    formatNumber,
    render,
    renderExamples,
    renderLexicalNotes,
    renderMeaningValue,
    renderSpeakButton,
    setStatus,
    setStudyCount,
    speechTextForWord,
    statChip,
    stateLabels,
    statusFor,
    studyActions,
    studyCheckLabel,
    studyCountFor,
    studyKindLabel,
    studyTargetCount,
    t,
  }) {
    function renderDetailHeader(word) {
      const header = el("header", "detail-header");
      const titleRow = el("div", "detail-title-row");
      const title = el("div", "detail-title");
      title.append(el("h2", "", word.word || ""), el("span", "reading", displayReading(word)));
      if (renderSpeakButton) {
        title.append(renderSpeakButton(() => speechTextForWord(word), "tts-button detail-tts-button"));
      }
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
      title.append(el("h2", "", word.word || ""), el("span", "reading", displayReading(word)));
      if (renderSpeakButton) {
        title.append(renderSpeakButton(() => speechTextForWord(word), "tts-button detail-tts-button"));
      }
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
      card.append(renderStudyProgressTrack(word));

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
      if (!app.study.showAnswer) {
        const reveal = el("button", "study-primary-action", t("revealAnswer"));
        reveal.type = "button";
        reveal.addEventListener("click", () => {
          app.study.showAnswer = true;
          render();
        });
        const next = el("button", "study-next-action", t("nextWord"));
        next.type = "button";
        next.addEventListener("click", studyActions.nextStudyWord);
        actions.append(reveal, next);
        return actions;
      }

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

      const known = el("button", "study-answer-action", t("studyKnown"));
      known.type = "button";
      known.addEventListener("click", () => {
        studyActions.markStudyWord("known");
      });

      const next = el("button", "study-next-action", t("nextWord"));
      next.type = "button";
      next.addEventListener("click", studyActions.nextStudyWord);

      actions.append(check, shaky, known, next);
      return actions;
    }

    function renderStudyProgressTrack(word) {
      const countText = studyCheckLabel(word);
      const track = el("div", "study-progress-track");
      track.title = countText;
      track.setAttribute("aria-label", countText);
      const current = studyCountFor(word);
      const target = studyTargetCount;
      for (let index = 0; index < target; index += 1) {
        const dot = el("span", `study-progress-dot ${index < current ? "filled" : ""}`.trim());
        track.append(dot);
      }
      return track;
    }

    function renderStatusActions(word) {
      if (app.mode === "read") {
        return renderReaderStudyActions(word);
      }
      const wrap = el("div", "status-actions");
      ["learning", "known", "none"].forEach((status) => {
        const button = el("button", "");
        button.type = "button";
        button.textContent = stateLabels[status][app.lang];
        const active = statusFor(word) === status;
        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", active ? "true" : "false");
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
      const items = [];
      if (status === "learning") {
        items.push({
          label: t("studyCheckButton"),
          active: true,
          className: "reader-study-primary",
          action: () => recordReaderStudyProgress(word),
        });
      } else if (status !== "known") {
        items.push({
          label: t("readerAddStudy"),
          active: false,
          className: "reader-study-primary",
          action: () => addWordToStudyFromReader(word),
        });
      }
      items.push(
        {
          label: t("readerKnown"),
          active: status === "known",
          action: () => setStatus(word, "known"),
        },
      );
      items.forEach((item) => {
        const button = el("button", item.className || "", item.label);
        button.type = "button";
        button.classList.toggle("active", item.active);
        button.setAttribute("aria-pressed", item.active ? "true" : "false");
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
    }

    function recordReaderStudyProgress(word) {
      const nextCount = Math.min(studyCountFor(word) + 1, studyTargetCount);
      setStudyCount(word, nextCount);
      setStatus(word, nextCount >= studyTargetCount ? "known" : "learning");
    }

    return {
      renderDetailHeader,
      renderStudyCard,
    };
  }

  return { createDetailHelpers };
})();
