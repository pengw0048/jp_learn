window.JPCORPUS_READER_MODE = (() => {
  function createReaderModeHelpers({
    app,
    asArray,
    buildSourceGroups,
    cleanSourceFileLabel,
    compareNullableNumbers,
    compareReaderDocuments,
    el,
    findWord,
    formatEpisodeLabel,
    formatNumber,
    isActiveStudyStatus,
    readerDocumentKey,
    readerDocumentLabel,
    readerDocumentsForSource,
    readerMarkedWordsForCurrentUnit,
    refs,
    render,
    sourceDocumentLineCount,
    sourceLabel,
    statusFor,
    storage,
    studyQueue,
    t,
    todayKey,
    clearReaderSelection,
    persistReaderPositions,
    stopAllSpeech,
  }) {
    const { STORAGE_READER_FURIGANA, STORAGE_READER_WORD_LIST } = storage;

    function currentReaderScrollTop() {
      return refs.wordList.querySelector(".reader-mode-scroll")?.scrollTop || 0;
    }

    function readerPositionKey(source, unit) {
      return [
        source?.type || "",
        source?.key || "",
        unit?.key || "",
      ].join("\u0000");
    }

    function saveReaderPosition(key, scroller) {
      if (!key || !scroller) {
        return;
      }
      const nextTop = Math.max(0, Math.round(scroller.scrollTop || 0));
      const maxScroll = Math.max(0, (scroller.scrollHeight || 0) - (scroller.clientHeight || 0));
      const progress = maxScroll > 0 ? Math.round((nextTop / maxScroll) * 100) : 0;
      const current = app.reader.positions[key];
      if (current?.scrollTop === nextTop && current?.progress === progress) {
        return;
      }
      app.reader.positions[key] = { scrollTop: nextTop, progress, updatedAt: Date.now() };
      if (app.reader.positionSaveTimer) {
        window.clearTimeout(app.reader.positionSaveTimer);
      }
      app.reader.positionSaveTimer = window.setTimeout(() => {
        app.reader.positionSaveTimer = null;
        persistReaderPositions();
      }, 150);
    }

    function renderReaderModeControls(groups, selected, units, selectedUnit) {
      const details = el("details", "reader-mode-controls");
      details.open = app.reader.controlsOpen;
      details.addEventListener("toggle", () => {
        app.reader.controlsOpen = details.open;
      });
      details.append(
        el("summary", "reader-mode-controls-summary", readerModeSummaryLabel(groups, selected, selectedUnit)),
        renderReaderModeToolbar(groups, selected, units, selectedUnit),
      );
      return details;
    }

    function readerModeSummaryLabel(groups, selected, selectedUnit) {
      const parts = [
        t("readerSourcesFound", { count: formatNumber(groups.length) }),
        selected.title,
      ];
      if (selectedUnit?.label && selectedUnit.label !== selected.title) {
        parts.push(selectedUnit.label);
      }
      return parts.filter(Boolean).join(" · ");
    }

    function renderReaderModeToolbar(groups, selected, units, selectedUnit) {
      const toolbar = el("div", "reader-mode-toolbar");
      const tabs = el("div", "reader-source-tabs");
      [
        ["all", t("sourceAll")],
        ["subtitle", t("sourceSubtitles")],
        ["lyrics", t("sourceLyrics")],
        ["text", t("sourceTexts")],
      ].forEach(([value, label]) => {
        const button = el("button", "", label);
        button.type = "button";
        button.classList.toggle("active", app.reader.sourceType === value);
        button.addEventListener("click", () => {
          stopAllSpeech();
          app.reader.sourceType = value;
          app.reader.groupKey = null;
          app.reader.documentKey = null;
          clearReaderSelection();
          render();
        });
        tabs.append(button);
      });

      const sourcePicker = el("label", "reader-source-picker");
      sourcePicker.append(el("span", "reader-source-picker-label", t("readerSourceChoice")));
      const select = el("select", "reader-source-select");
      groups.forEach((group) => {
        const option = el("option", "", group.title || t("sourceInventoryUnknown"));
        option.value = group.key;
        option.selected = group.key === selected.key;
        const meta = [
          sourceLabel(group.type),
          group.meta,
          `${formatNumber(group.readerLineCount || group.exampleCount)} ${group.readerLineCount ? t("sourceInventoryLines") : t("sourceInventoryExamples")}`,
          readerSourceProgressLabel(group),
        ].filter(Boolean).join(" · ");
        option.textContent = [group.title || t("sourceInventoryUnknown"), meta].filter(Boolean).join(" · ");
        select.append(option);
      });
      select.addEventListener("change", () => {
        stopAllSpeech();
        app.reader.groupKey = select.value;
        app.reader.documentKey = null;
        clearReaderSelection();
        render();
      });
      sourcePicker.append(select);
      toolbar.append(
        tabs,
        sourcePicker,
        renderReaderUnitPicker(units, selectedUnit),
        renderReaderWordListPicker(),
        renderReaderFuriganaPicker(),
      );
      return toolbar;
    }

    function renderReaderUnitPicker(units, selectedUnit) {
      const { source } = currentReaderSelectionSource();
      const picker = el("label", "reader-source-picker");
      picker.append(el("span", "reader-source-picker-label", t("readerItemChoice")));
      const select = el("select", "reader-source-select");
      if (!units.length) {
        select.disabled = true;
        select.append(el("option", "", t("sourceReaderEmpty")));
      }
      units.forEach((unit) => {
        const label = [readerUnitOptionLabel(unit), readerUnitProgressLabel(source, unit)].filter(Boolean).join(" · ");
        const option = el("option", "", label);
        option.value = unit.key;
        option.selected = unit.key === selectedUnit?.key;
        select.append(option);
      });
      select.addEventListener("change", () => {
        stopAllSpeech();
        app.reader.documentKey = select.value;
        clearReaderSelection();
        render();
      });
      picker.append(select);
      return picker;
    }

    function renderReaderWordListPicker() {
      const picker = el("div", "reader-word-list-picker");
      picker.append(el("span", "reader-source-picker-label", t("readerWordListChoice")));
      const options = el("div", "reader-word-list-tabs");
      [
        ["focus", t("readerWordListFocus")],
        ["all", t("readerWordListAll")],
        ["study", t("readerWordListStudy")],
        ["piece", t("readerWordListPiece")],
        ["N5", "N5"],
        ["N4", "N4"],
        ["N3", "N3"],
        ["N2", "N2"],
        ["N1", "N1"],
      ].forEach(([value, label]) => {
        const button = el("button", "", label);
        button.type = "button";
        button.classList.toggle("active", app.reader.wordList === value);
        button.addEventListener("click", () => {
          stopAllSpeech();
          app.reader.wordList = value;
          localStorage.setItem(STORAGE_READER_WORD_LIST, value);
          app.reader.preserveScrollOnRender = true;
          clearReaderSelection();
          render();
        });
        options.append(button);
      });
      picker.append(options);
      return picker;
    }

    function renderReaderFuriganaPicker() {
      const picker = el("div", "reader-furigana-picker");
      picker.append(el("span", "reader-source-picker-label", t("readerFuriganaChoice")));
      const options = el("div", "reader-furigana-tabs");
      [
        [false, t("readerFuriganaOff")],
        [true, t("readerFuriganaOn")],
      ].forEach(([value, label]) => {
        const button = el("button", "", label);
        button.type = "button";
        button.classList.toggle("active", app.reader.showFurigana === value);
        button.addEventListener("click", () => {
          app.reader.showFurigana = value;
          try {
            localStorage.setItem(STORAGE_READER_FURIGANA, value ? "on" : "off");
          } catch {
            // Keep the in-memory toggle working even if storage is unavailable.
          }
          app.reader.preserveScrollOnRender = true;
          render();
        });
        options.append(button);
      });
      picker.append(options);
      return picker;
    }

    function readerWordSet() {
      if (app.reader.wordList === "all") {
        return null;
      }
      if (app.reader.wordList === "study") {
        return new Set(readerStudyWords().map((word) => word.word));
      }
      if (app.reader.wordList === "focus") {
        return new Set(
          app.words
            .filter((word) => isFocusReaderWord(word))
            .map((word) => word.word),
        );
      }
      if (app.reader.wordList === "piece") {
        return new Set(readerMarkedWordsForCurrentUnit().map((entry) => entry.word.word));
      }
      return new Set(
        app.words
          .filter((word) => word.level === app.reader.wordList)
          .map((word) => word.word),
      );
    }

    function readerStudyWords() {
      const sessionWords = app.study.session?.date === todayKey()
        ? asArray(app.study.session.words).map(findWord).filter(Boolean)
        : [];
      return sessionWords.length ? sessionWords : studyQueue();
    }

    function isFocusReaderWord(word) {
      if (isActiveStudyStatus(statusFor(word))) {
        return true;
      }
      return ["N1", "N2", "N3"].includes(word.level);
    }

    function readerUnitsForSource(source) {
      const documents = readerDocumentsForSource(source);
      if (source.type === "subtitle") {
        return subtitleReaderUnits(documents);
      }
      return documents
        .map((document) => {
          const label = readerDocumentLabel(document);
          const meta = readerDocumentMeta(document);
          return createReaderUnit({
            key: readerDocumentKey(document),
            label,
            meta,
            documents: [document],
          });
        })
        .sort(compareReaderUnits);
    }

    function subtitleReaderUnits(documents) {
      const units = new Map();
      documents.forEach((document) => {
        const episode = Number.isInteger(document.episode) ? document.episode : null;
        const key = episode === null ? readerDocumentKey(document) : `episode:${episode}`;
        if (!units.has(key)) {
          units.set(key, {
            key,
            episode,
            label: episode === null ? readerDocumentLabel(document) : formatEpisodeLabel(episode),
            metaParts: new Set(),
            documents: [],
          });
        }
        const unit = units.get(key);
        const fileLabel = cleanSourceFileLabel(document.source_file || document.source_title || "");
        if (fileLabel && episode === null) {
          unit.metaParts.add(fileLabel);
        }
        unit.documents.push(document);
      });
      return [...units.values()]
        .map((unit) => {
          const documentsForUnit = unit.documents.sort(compareReaderDocuments);
          const selectedDocuments = unit.episode === null
            ? documentsForUnit
            : [preferredSubtitleDocument(documentsForUnit)];
          return createReaderUnit({
            key: unit.key,
            episode: unit.episode,
            label: unit.label,
            meta: unit.episode === null ? [...unit.metaParts][0] || "" : "",
            documents: selectedDocuments.filter(Boolean),
          });
        })
        .sort(compareReaderUnits);
    }

    function preferredSubtitleDocument(documents) {
      return [...documents].sort(comparePreferredSubtitleDocuments)[0] || null;
    }

    function comparePreferredSubtitleDocuments(left, right) {
      return subtitleDocumentPreferenceScore(right) - subtitleDocumentPreferenceScore(left)
        || compareReaderDocuments(left, right);
    }

    function subtitleDocumentPreferenceScore(document) {
      const file = String(document.source_file || document.source_title || "").toLowerCase();
      let score = sourceDocumentLineCount(document);
      if (/(^|[._\s-])ja($|[._\s-]|\[)/u.test(file) || /jpn|japanese/u.test(file)) {
        score += 80;
      }
      if (/ja[-_]?en|en[-_]?ja|dual|bilingual/u.test(file)) {
        score -= 120;
      }
      if (/netflix|web-?rip/u.test(file)) {
        score += 20;
      }
      return score;
    }

    function createReaderUnit({ key, episode = null, label, meta = "", documents }) {
      const words = new Set();
      const lineCount = documents.reduce((total, document) => {
        asArray(document.words).forEach((word) => {
          if (word) {
            words.add(word);
          }
        });
        asArray(document.lines).forEach((line) => {
          asArray(line.matches).forEach((match) => {
            if (match.word) {
              words.add(match.word);
            }
          });
        });
        return total + sourceDocumentLineCount(document);
      }, 0);
      return {
        key,
        episode,
        label,
        meta,
        documents,
        words,
        lineCount,
      };
    }

    function readerDocumentMeta(document) {
      if (document.source_type === "lyrics") {
        return [
          document.source_artist,
          document.source_album && document.source_album !== document.source_title ? document.source_album : "",
        ].filter(Boolean).join(" · ");
      }
      if (document.source_type === "text") {
        return [document.source_artist, cleanSourceFileLabel(document.source_file || "")]
          .filter(Boolean)
          .join(" · ");
      }
      return cleanSourceFileLabel(document.source_file || "");
    }

    function readerUnitOptionLabel(unit) {
      const meta = [
        unit.meta,
        `${formatNumber(unit.lineCount)} ${t("sourceInventoryLines")}`,
      ].filter(Boolean).join(" · ");
      return [unit.label, meta].filter(Boolean).join(" · ");
    }

    function readerUnitProgressLabel(source, unit) {
      if (!source || !unit) {
        return "";
      }
      const progress = app.reader.positions[readerPositionKey(source, unit)]?.progress;
      if (!Number.isFinite(progress) || progress <= 0) {
        return "";
      }
      return t("readerProgress", { percent: formatNumber(Math.min(100, Math.max(0, Math.round(progress)))) });
    }

    function readerSourceProgressLabel(source) {
      const units = readerUnitsForSource(source);
      const progressValues = units
        .map((unit) => app.reader.positions[readerPositionKey(source, unit)]?.progress)
        .filter((value) => Number.isFinite(value) && value > 0);
      if (progressValues.length === 0) {
        return "";
      }
      const progress = Math.max(...progressValues);
      return t("readerProgress", { percent: formatNumber(Math.min(100, Math.max(0, Math.round(progress)))) });
    }

    function compareReaderUnits(left, right) {
      const episodeDiff = compareNullableNumbers(left.episode, right.episode);
      if (episodeDiff !== 0) {
        return episodeDiff;
      }
      const locale = app.lang === "zh" ? "zh-CN" : "ja-JP";
      const labelDiff = String(left.label || "").localeCompare(String(right.label || ""), locale);
      if (labelDiff !== 0) {
        return labelDiff;
      }
      return String(left.meta || "").localeCompare(String(right.meta || ""), locale);
    }

    function renderReaderModeSummary(source, unit) {
      const summary = el("div", `reader-mode-summary source-card-${source.type || "unknown"}`);
      const title = el("div", "reader-mode-title");
      title.append(el("span", "source-kind", sourceLabel(source.type)), el("strong", "", source.title));
      if (source.meta) {
        title.append(el("span", "source-meta", source.meta));
      }
      if (unit) {
        title.append(el("span", "source-meta", unit.label));
      }
      const hint = !source.sourceDocuments?.length && source.exampleItems.length > 0
        ? t("sourceReaderFallback")
        : "";
      summary.append(title);
      if (hint) {
        summary.append(el("p", "", hint));
      }
      return summary;
    }

    function currentReaderSelectionSource() {
      const sourceType = app.reader.sourceType === "all" ? null : app.reader.sourceType;
      const groups = buildSourceGroups(sourceType);
      const source = groups.find((group) => group.key === app.reader.groupKey) || groups[0] || null;
      if (!source) {
        return { source: null, unit: null };
      }
      const units = readerUnitsForSource(source);
      const unit = units.find((item) => item.key === app.reader.documentKey) || units[0] || null;
      return { source, unit };
    }

    return {
      currentReaderScrollTop,
      currentReaderSelectionSource,
      readerPositionKey,
      readerUnitsForSource,
      readerWordSet,
      renderReaderModeControls,
      renderReaderModeSummary,
      saveReaderPosition,
    };
  }

  return { createReaderModeHelpers };
})();
