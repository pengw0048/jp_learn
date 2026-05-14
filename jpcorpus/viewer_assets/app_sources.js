window.JPCORPUS_SOURCES = (() => {
  function createSourceHelpers({
    app,
    api,
    asArray,
    el,
    emptyMessage,
    fileStem,
    formatNumber,
    hasExampleAnnotations,
    hideSourcePanel,
    normalizedTextTitle,
    refs,
    render,
    startMaintenanceJob,
    storageMode,
    strong,
    t,
  }) {
    function renderSourceInventory() {
      if (!refs.sourceInventory) {
        return;
      }
      if (refs.sourcePanel.hidden) {
        return;
      }
      const groups = buildSourceGroups(app.sourcePanelType);
      const selected = groups.find((group) => group.key === app.sourcePanelGroupKey);
      if (selected) {
        replaceSourceInventoryChildren(renderSourceGroupDetail(selected));
        return;
      }
      if (groups.length === 0) {
        replaceSourceInventoryChildren(emptyMessage(t("sourceInventoryEmpty")));
        return;
      }
      replaceSourceInventoryChildren(...groups.map(renderSourceGroupItem));
    }

    function replaceSourceInventoryChildren(...children) {
      const notice = app.sourceInventoryNotice
        ? el("p", "source-inventory-notice", app.sourceInventoryNotice)
        : null;
      refs.sourceInventory.replaceChildren(...[notice, ...children].filter(Boolean));
    }

    function buildSourceItems() {
      const sourceStats = new Map(
        asArray(app.corpus?.shows).map((item) => [normalizedTextTitle(item.title), item]),
      );
      const sources = new Map();

      function ensureSource(type, title, artist = "", album = "") {
        const key = [type, title, artist, album].join("\u0000");
        if (!sources.has(key)) {
          const stats = sourceStats.get(normalizedTextTitle(title)) || {};
          sources.set(key, {
            type,
            title,
            artist,
            album,
            hasStats: Boolean(stats.total_tokens),
            files: new Set(),
            words: new Set(),
            sourceDocuments: [],
            readerLineCount: 0,
            exampleCount: 0,
            exampleItems: [],
            annotated: 0,
            fileCount: Number(stats.subtitle_file_count) || 0,
            tokens: Number(stats.total_tokens) || 0,
          });
        }
        return sources.get(key);
      }

      asArray(app.corpus?.sources).forEach((document) => {
        document = sourceDocumentWithDetail(document);
        const type = document.source_type || "subtitle";
        const title = String(document.source_title || document.source_file || t("sourceInventoryUnknown")).trim();
        const artist = String(document.source_artist || "").trim();
        const album = String(document.source_album || "").trim();
        const entry = ensureSource(type, title, artist, album);
        entry.sourceDocuments.push(document);
        entry.readerLineCount += sourceDocumentLineCount(document);
        if (!entry.hasStats) {
          entry.tokens += Number(document.token_count) || 0;
        }
        const file = document.source_file || document.subtitle_file;
        if (file) {
          entry.files.add(file);
        }
        sourceDocumentWords(document).forEach((word) => entry.words.add(word));
      });

      app.words.forEach((word) => {
        asArray(word.examples).forEach((example) => {
          const type = example.source_type || "subtitle";
          const title = String(example.source_title || example.subtitle_file || t("sourceInventoryUnknown")).trim();
          const artist = String(example.source_artist || "").trim();
          const album = String(example.source_album || "").trim();
          const entry = ensureSource(type, title, artist, album);
          entry.exampleCount += 1;
          entry.exampleItems.push({ word, example });
          if (word.word) {
            entry.words.add(word.word);
          }
          const file = example.reference?.source_file || example.subtitle_file;
          if (file) {
            entry.files.add(file);
          }
          if (hasExampleAnnotations(example)) {
            entry.annotated += 1;
          }
        });
      });
      sources.forEach((entry) => {
        entry.fileCount = Math.max(entry.fileCount, entry.files.size);
      });
      return [...sources.values()].sort(compareSourceInventoryItems);
    }

    function sourceDocumentWithDetail(document) {
      const key = sourceDocumentKey(document);
      return key && app.sourceDetails.has(key) ? app.sourceDetails.get(key) : document;
    }

    function sourceDocumentKey(document) {
      return document?.source_key || [
        document?.source_type || "subtitle",
        document?.source_title || "",
        document?.source_artist || "",
        document?.source_album || "",
        document?.source_file || "",
        Number.isInteger(document?.episode) ? document.episode : "",
      ].join("\u0000");
    }

    function sourceDocumentLineCount(document) {
      const lines = asArray(document?.lines);
      return lines.length || Number(document?.line_count || 0);
    }

    function sourceDocumentWords(document) {
      const indexedWords = asArray(document?.words).filter(Boolean);
      if (indexedWords.length) {
        return indexedWords;
      }
      const words = new Set();
      asArray(document?.lines).forEach((line) => {
        asArray(line.matches).forEach((match) => {
          if (match.word) {
            words.add(match.word);
          }
        });
      });
      return [...words];
    }

    function buildSourceGroups(sourceType) {
      const groups = new Map();
      buildSourceItems()
        .filter((source) => !sourceType || source.type === sourceType)
        .forEach((source) => {
          const groupKey = sourceGroupKey(source);
          if (!groups.has(groupKey)) {
            groups.set(groupKey, createSourceGroup(source, groupKey));
          }
          addSourceToGroup(groups.get(groupKey), source);
        });
      return [...groups.values()].sort(compareSourceInventoryItems);
    }

    function sourceGroupKey(source) {
      if (source.type === "lyrics") {
        return [source.type, source.album || source.artist || source.title].join("\u0000");
      }
      return [source.type, source.title].join("\u0000");
    }

    function createSourceGroup(source, key) {
      const title = source.type === "lyrics"
        ? (source.album || source.artist || source.title)
        : source.title;
      const meta = source.type === "lyrics" && source.album
        ? source.artist
        : "";
      return {
        key,
        type: source.type,
        title,
        meta,
        files: new Set(),
        words: new Set(),
        sourceDocuments: [],
        children: [],
        readerLineCount: 0,
        exampleItems: [],
        exampleCount: 0,
        annotated: 0,
        fileCount: 0,
        tokens: 0,
      };
    }

    function addSourceToGroup(group, source) {
      source.files.forEach((file) => group.files.add(file));
      source.words.forEach((word) => group.words.add(word));
      group.sourceDocuments.push(...source.sourceDocuments);
      group.readerLineCount += source.readerLineCount;
      group.exampleItems.push(...source.exampleItems);
      group.exampleCount += source.exampleCount;
      group.annotated += source.annotated;
      group.fileCount += source.fileCount || source.files.size;
      group.tokens += source.tokens;
      group.children.push(...sourceChildren(source));
    }

    function sourceChildren(source) {
      if (source.sourceDocuments?.length) {
        return sourceDocumentChildren(source);
      }
      if (source.type === "subtitle") {
        return subtitleEpisodeChildren(source);
      }
      if (source.type === "lyrics") {
        return [{
          label: source.title,
          meta: [source.artist, source.album && source.album !== source.title ? source.album : ""]
            .filter(Boolean)
            .join(" · "),
          examples: source.exampleCount,
        }];
      }
      return [...source.files].sort().map((file) => ({
        label: source.title,
        meta: file,
        examples: countExamplesForFile(source, file),
      }));
    }

    function sourceDocumentChildren(source) {
      if (source.type === "subtitle") {
        return subtitleDocumentChildren(source);
      }
      return source.sourceDocuments
        .map((document) => ({
          label: source.type === "lyrics"
            ? (document.source_title || source.title)
            : cleanSourceFileLabel(document.source_file || document.source_title || source.title),
          meta: source.type === "lyrics"
            ? [document.source_artist, document.source_album && document.source_album !== document.source_title ? document.source_album : ""]
              .filter(Boolean)
              .join(" · ")
            : "",
          lines: sourceDocumentLineCount(document),
          files: [document.source_file].filter(Boolean),
        }))
        .sort((left, right) => left.label.localeCompare(right.label, app.lang === "zh" ? "zh-CN" : "ja-JP"));
    }

    function subtitleDocumentChildren(source) {
      const episodes = new Map();
      source.sourceDocuments.forEach((document) => {
        const file = document.source_file || "";
        const episode = Number.isInteger(document.episode) ? document.episode : null;
        const key = episode === null ? `file:${file || source.title}` : `episode:${episode}`;
        if (!episodes.has(key)) {
          episodes.set(key, {
            episode,
            files: new Set(),
            lines: 0,
            label: episode === null ? cleanSourceFileLabel(file || source.title) : formatEpisodeLabel(episode),
          });
        }
        const entry = episodes.get(key);
        if (file) {
          entry.files.add(file);
        }
        entry.lines += sourceDocumentLineCount(document);
      });
      return [...episodes.values()]
        .sort(compareSubtitleChildren)
        .map((entry) => ({
          label: entry.label,
          meta: entry.files.size > 1 ? `${formatNumber(entry.files.size)} ${t("sourceInventoryVersions")}` : "",
          lines: entry.lines,
          files: [...entry.files].sort(),
        }));
    }

    function subtitleEpisodeChildren(source) {
      const episodes = new Map();
      source.exampleItems.forEach(({ example }) => {
        const file = example.reference?.source_file || example.subtitle_file || "";
        const episode = Number.isInteger(example.episode) ? example.episode : null;
        const key = episode === null ? `file:${file || source.title}` : `episode:${episode}`;
        if (!episodes.has(key)) {
          episodes.set(key, {
            episode,
            files: new Set(),
            examples: 0,
            label: episode === null ? cleanSourceFileLabel(file || source.title) : formatEpisodeLabel(episode),
          });
        }
        const entry = episodes.get(key);
        if (file) {
          entry.files.add(file);
        }
        entry.examples += 1;
      });
      return [...episodes.values()]
        .sort(compareSubtitleChildren)
        .map((entry) => ({
          label: entry.label,
          meta: entry.files.size > 1 ? `${formatNumber(entry.files.size)} ${t("sourceInventoryVersions")}` : "",
          examples: entry.examples,
          files: [...entry.files].sort(),
        }));
    }

    function compareSubtitleChildren(left, right) {
      if (left.episode !== null && right.episode !== null) {
        return left.episode - right.episode;
      }
      if (left.episode !== null) {
        return -1;
      }
      if (right.episode !== null) {
        return 1;
      }
      return left.label.localeCompare(right.label, app.lang === "zh" ? "zh-CN" : "ja-JP");
    }

    function formatEpisodeLabel(episode) {
      return `EP${String(episode).padStart(2, "0")}`;
    }

    function cleanSourceFileLabel(value) {
      return fileStem(value)
        .replace(/\[[^\]]+\]/gu, "")
        .replace(/\([^)]*\)/gu, "")
        .replace(/[_．.]+/gu, " ")
        .replace(/\s+/gu, " ")
        .trim() || value;
    }

    function countExamplesForFile(source, file) {
      return source.exampleItems.filter(({ example }) => (
        (example.reference?.source_file || example.subtitle_file) === file
      )).length;
    }

    function compareSourceInventoryItems(left, right) {
      const typeOrder = { subtitle: 0, lyrics: 1, text: 2 };
      const typeDiff = (typeOrder[left.type] ?? 9) - (typeOrder[right.type] ?? 9);
      if (typeDiff !== 0) {
        return typeDiff;
      }
      return left.title.localeCompare(right.title, app.lang === "zh" ? "zh-CN" : "ja-JP");
    }

    function renderSourceGroupItem(source) {
      const item = el("article", `source-card source-card-${source.type || "unknown"}`);
      const actionsDisabled = sourceInventoryActionsDisabled();
      const heading = el("div", "source-card-heading");
      const kind = el("span", "source-kind", sourceLabel(source.type));
      const title = el("strong", "source-title", source.title || t("sourceInventoryUnknown"));
      heading.append(kind, title);
      if (source.meta) {
        heading.append(el("span", "source-meta", source.meta));
      }

      const action = el("button", "source-view-button", t("sourceInventoryView"));
      action.type = "button";
      action.disabled = actionsDisabled;
      action.addEventListener("click", () => {
        app.sourcePanelGroupKey = source.key;
        renderSourceInventory();
      });
      const readAction = el("button", "source-read-button", t("sourceInventoryRead"));
      readAction.type = "button";
      readAction.disabled = actionsDisabled;
      readAction.addEventListener("click", () => {
        openSourceInReader(source);
      });
      const actions = el("div", "source-card-actions");
      actions.append(action, readAction);
      if (canDeleteImportedSource(source)) {
        actions.append(renderDeleteImportedSourceButton(source));
      }

      const top = el("div", "source-card-top");
      top.append(heading, actions);
      item.append(top);
      const summary = renderSourceSummary(source);
      if (summary) {
        item.append(summary);
      }

      const collapsedPreviewLimit = source.type === "subtitle" ? 4 : 6;
      const canToggle = source.type === "subtitle" && source.children.length > collapsedPreviewLimit;
      const expanded = canToggle && app.expandedSourceGroups.has(source.key);
      const visibleChildren = expanded ? source.children : source.children.slice(0, collapsedPreviewLimit);
      const childList = renderSourceChildren(visibleChildren, source.type, {
        showFileDetails: false,
      });
      if (childList) {
        item.append(childList);
      }
      if (canToggle) {
        const toggle = el(
          "button",
          "source-expand-button",
          expanded
            ? t("sourceInventoryCollapse")
            : t("sourceInventoryExpand", { count: formatNumber(source.children.length - collapsedPreviewLimit) }),
        );
        toggle.type = "button";
        toggle.disabled = actionsDisabled;
        toggle.addEventListener("click", () => {
          if (expanded) {
            app.expandedSourceGroups.delete(source.key);
          } else {
            app.expandedSourceGroups.add(source.key);
          }
          renderSourceInventory();
        });
        item.append(toggle);
      }
      return item;
    }

    function renderSourceGroupDetail(source) {
      const detail = el("article", `source-detail source-card-${source.type || "unknown"}`);
      const actionsDisabled = sourceInventoryActionsDisabled();
      const back = el("button", "source-back-button", `‹ ${t("sourceInventoryBack")}`);
      back.type = "button";
      back.disabled = actionsDisabled;
      back.addEventListener("click", () => {
        app.sourcePanelGroupKey = null;
        renderSourceInventory();
      });
      const heading = el("div", "source-detail-heading");
      heading.append(back, el("h3", "", source.title || t("sourceInventoryUnknown")));
      if (source.meta) {
        heading.append(el("span", "source-meta", source.meta));
      }
      const readAction = el("button", "source-read-button", t("sourceInventoryRead"));
      readAction.type = "button";
      readAction.disabled = actionsDisabled;
      readAction.addEventListener("click", () => {
        openSourceInReader(source);
      });
      heading.append(readAction);
      if (canDeleteImportedSource(source)) {
        heading.append(renderDeleteImportedSourceButton(source));
      }
      detail.append(heading);
      const summary = renderSourceSummary(source);
      if (summary) {
        detail.append(summary);
      }

      const children = renderSourceChildren(source.children, source.type, {
        showFileDetails: true,
      });
      if (children) {
        detail.append(children);
      }

      return detail;
    }

    function openSourceInReader(source) {
      app.mode = "read";
      localStorage.setItem(storageMode, app.mode);
      app.reader.sourceType = source.type || "all";
      app.reader.groupKey = source.key;
      app.reader.documentKey = null;
      refs.maintenancePanel.hidden = true;
      refs.maintenanceToggle.classList.remove("active");
      hideSourcePanel();
      render();
    }

    function renderDeleteImportedSourceButton(source) {
      const deleteAction = el("button", "source-delete-button", t("sourceInventoryDelete"));
      deleteAction.type = "button";
      deleteAction.disabled = sourceInventoryActionsDisabled();
      deleteAction.addEventListener("click", () => deleteImportedSource(source));
      return deleteAction;
    }

    function sourceInventoryActionsDisabled() {
      return app.sourceInventoryBusy || app.maintenance.job?.status === "running";
    }

    function canDeleteImportedSource(source) {
      return importedSourceFiles(source).length > 0;
    }

    function importedSourceFiles(source) {
      if (source.type !== "text") {
        return [];
      }
      return [...new Set(asArray(source.sourceDocuments)
        .map((document) => String(document.source_file || ""))
        .filter((sourceFile) => sourceFile.startsWith("web/") && sourceFile.endsWith(".txt")))];
    }

    async function deleteImportedSource(source) {
      const sourceFiles = importedSourceFiles(source);
      if (!sourceFiles.length) {
        return;
      }
      const title = source.title || t("sourceInventoryUnknown");
      if (!window.confirm(t("sourceInventoryDeleteConfirm", { title }))) {
        return;
      }
      app.sourceInventoryBusy = true;
      app.sourceInventoryNoticeJobId = null;
      app.sourceInventoryNotice = t("sourceInventoryDeleting", { title });
      renderSourceInventory();
      try {
        await api.deleteImportedText(sourceFiles);
        app.sourcePanelGroupKey = null;
        app.sourceInventoryNotice = t("sourceInventoryDeleted", { title });
        renderSourceInventory();
        const job = await startMaintenanceJob("refresh_imported_texts");
        if (job?.id) {
          app.sourceInventoryNoticeJobId = job.id;
          renderSourceInventory();
        } else {
          app.sourceInventoryBusy = false;
          app.sourceInventoryNotice = t("sourceInventoryDeleteFailed", { error: app.maintenance.job?.log?.[0] || "could not start rebuild" });
          renderSourceInventory();
        }
      } catch (error) {
        app.sourceInventoryBusy = false;
        app.sourceInventoryNoticeJobId = null;
        app.sourceInventoryNotice = t("sourceInventoryDeleteFailed", { error: error.message || String(error) });
        renderSourceInventory();
      }
    }

    function renderSourceSummary(source) {
      const childLabel = source.type === "lyrics" ? t("sourceInventoryTracks") : t("sourceInventoryEpisodes");
      const childCount = source.type === "text"
        ? source.fileCount || source.files.size || source.children?.length || 0
        : source.children?.length || 0;
      const parts = [
        childCount ? `${formatNumber(childCount)} ${source.type === "text" ? t("sourceInventoryFiles") : childLabel}` : "",
        source.readerLineCount ? `${formatNumber(source.readerLineCount)} ${t("sourceInventoryLines")}` : "",
        !source.readerLineCount && source.exampleCount ? `${formatNumber(source.exampleCount)} ${t("sourceInventoryExamples")}` : "",
      ].filter(Boolean);
      return parts.length ? el("div", "source-summary", parts.join(" · ")) : null;
    }

    function renderSourceChildren(children, sourceType, options = {}) {
      const showFileDetails = options.showFileDetails ?? false;
      if (!children || children.length === 0 || sourceType === "text") {
        return null;
      }
      const list = el("div", "source-child-list");
      children.forEach((child) => {
        const row = el("div", "source-child-row");
        row.append(strong(child.label));
        const meta = showFileDetails || sourceType !== "subtitle" ? child.meta || "" : "";
        row.append(el("span", "", meta));
        if (child.examples || child.lines) {
          const count = child.examples || child.lines;
          const label = child.examples ? t("sourceInventoryExamples") : t("sourceInventoryLines");
          row.append(el("small", "", `${formatNumber(count)} ${label}`));
        }
        list.append(row);
        if (showFileDetails && child.files?.length > 0) {
          const files = el("div", "source-file-list");
          child.files.forEach((file) => {
            files.append(el("div", "", cleanSourceFileLabel(file)));
          });
          list.append(files);
        }
      });
      return list;
    }

    function sourceLabel(source) {
      if (source === "subtitle") {
        return t("sourceSubtitles");
      }
      if (source === "lyrics") {
        return t("sourceLyrics");
      }
      if (source === "text") {
        return t("sourceTexts");
      }
      return t("sourceAll");
    }

    return {
      buildSourceGroups,
      cleanSourceFileLabel,
      formatEpisodeLabel,
      renderSourceInventory,
      sourceDocumentKey,
      sourceDocumentLineCount,
      sourceDocumentWithDetail,
      sourceDocumentWords,
      sourceLabel,
    };
  }

  return {
    createSourceHelpers,
  };
})();
