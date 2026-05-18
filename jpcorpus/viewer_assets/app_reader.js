window.JPCORPUS_READER = (() => {
  function createReaderHelpers({
    app,
    asArray,
    cleanSourceFileLabel,
    el,
    emptyMessage,
    formatEpisodeLabel,
    formatNumber,
    formatTimestamp,
    readerWordAllowed,
    selectReaderWord,
    sourceDocumentKey,
    sourceDocumentLineCount,
    sourceDocumentWords,
    setReaderSpeechStartLine,
    startReaderSpeechFromLine,
    statusFor,
    strong,
    t,
  }) {
    function renderSourceReader(source, options = {}) {
      const reader = el("section", `source-reader${options.full ? " reader-full" : ""}`);
      const heading = el("div", "source-reader-heading");
      heading.append(el("h4", "", t("sourceReaderTitle")));
      const documents = options.documents || readerDocumentsForSource(source);
      const exampleItems = asArray(source.exampleItems);
      if (!source.sourceDocuments?.length && exampleItems.length > 0) {
        heading.append(el("span", "", t("sourceReaderFallback")));
      }
      reader.append(heading);
      if (documents.length === 0) {
        reader.append(emptyMessage(t("sourceReaderEmpty")));
        return reader;
      }
      documents.forEach((document, index) => {
        reader.append(renderReaderDocument(document, index === 0 || documents.length === 1, options));
      });
      return reader;
    }

    function readerDocumentsForSource(source) {
      if (source.sourceDocuments?.length) {
        return source.sourceDocuments
          .map(normalizeReaderDocument)
          .sort(compareReaderDocuments);
      }
      return fallbackReaderDocuments(source).sort(compareReaderDocuments);
    }

    function normalizeReaderDocument(document) {
      return {
        source_key: sourceDocumentKey(document),
        source_type: document.source_type || "subtitle",
        source_title: document.source_title || document.source_file || "",
        source_artist: document.source_artist || "",
        source_album: document.source_album || "",
        source_file: document.source_file || "",
        episode: Number.isInteger(document.episode) ? document.episode : null,
        line_count: Number(document.line_count) || 0,
        words: sourceDocumentWords(document),
        lines: asArray(document.lines).map((line) => ({
          text: line.text || "",
          start_ms: Number.isInteger(line.start_ms) ? line.start_ms : null,
          end_ms: Number.isInteger(line.end_ms) ? line.end_ms : null,
          matches: normalizeReaderMatches(line.text || "", line.matches),
        })),
      };
    }

    function fallbackReaderDocuments(source) {
      const documents = new Map();
      asArray(source.exampleItems).forEach(({ word, example }) => {
        const file = example.reference?.source_file || example.subtitle_file || "";
        const key = [
          example.source_type || source.type,
          example.source_title || source.title,
          example.source_artist || "",
          example.source_album || "",
          file,
          Number.isInteger(example.episode) ? example.episode : "",
        ].join("\u0000");
        if (!documents.has(key)) {
          documents.set(key, {
            source_type: example.source_type || source.type,
            source_title: example.source_title || source.title,
            source_artist: example.source_artist || "",
            source_album: example.source_album || "",
            source_file: file,
            episode: Number.isInteger(example.episode) ? example.episode : null,
            lines: [],
          });
        }
        const document = documents.get(key);
        const text = example.sentence || "";
        const lineKey = [example.start_ms ?? "", text].join("\u0000");
        let line = document.lines.find((item) => item.key === lineKey);
        if (!line) {
          line = {
            key: lineKey,
            text,
            start_ms: Number.isInteger(example.start_ms) ? example.start_ms : null,
            end_ms: Number.isInteger(example.end_ms) ? example.end_ms : null,
            matches: [],
          };
          document.lines.push(line);
        }
        const matchedText = example.matched_text || word.word || "";
        const start = matchedText ? text.indexOf(matchedText) : -1;
        line.matches.push({
          word: word.word || matchedText,
          matched_text: matchedText,
          reading: word.reading || "",
          level: Number.isInteger(word.level_number) ? word.level_number : null,
          start: start >= 0 ? start : null,
          end: start >= 0 ? start + matchedText.length : null,
        });
      });
      return [...documents.values()].map((document) => ({
        ...document,
        lines: document.lines
          .map(({ key, ...line }) => ({
            ...line,
            matches: normalizeReaderMatches(line.text, line.matches),
          }))
          .sort(compareReaderLines),
      }));
    }

    function normalizeReaderMatches(text, matches) {
      return asArray(matches)
        .map((match) => {
          const word = String(match.word || match.matched_text || "").trim();
          const matchedText = String(match.matched_text || word).trim();
          let start = Number.isInteger(match.start) ? match.start : null;
          let end = Number.isInteger(match.end) ? match.end : null;
          if ((start === null || end === null) && matchedText) {
            const index = text.indexOf(matchedText);
            if (index >= 0) {
              start = index;
              end = index + matchedText.length;
            }
          }
          return {
            ...match,
            word,
            matched_text: matchedText,
            start,
            end,
          };
        })
        .filter((match) => match.word && match.matched_text);
    }

    function renderReaderDocument(document, open, options = {}) {
      const details = el("details", "reader-document");
      details.open = open;
      const summary = el("summary", "");
      summary.append(
        strong(readerDocumentLabel(document)),
        el("span", "", `${formatNumber(sourceDocumentLineCount(document))} ${t("sourceInventoryLines")}`),
      );
      details.append(summary);
      const lines = el("div", "reader-lines");
      document.lines.forEach((line, index) => {
        lines.append(renderReaderLine(line, { ...options, document, lineIndex: index }));
      });
      details.append(lines);
      return details;
    }

    function readerDocumentLabel(document) {
      if (document.source_type === "subtitle") {
        const episode = Number.isInteger(document.episode) ? `${formatEpisodeLabel(document.episode)} ` : "";
        return `${episode}${cleanSourceFileLabel(document.source_file || document.source_title)}`;
      }
      if (document.source_type === "lyrics") {
        return [document.source_title, document.source_artist].filter(Boolean).join(" · ");
      }
      return cleanSourceFileLabel(document.source_file || document.source_title);
    }

    function renderReaderLine(line, options = {}) {
      const row = el("div", "reader-line");
      row.dataset.readerLineKey = readerLineDomKey(options.document || {}, line, options.lineIndex);
      row.dataset.readerLineText = line.text || "";
      row.title = t("readerSetStartLine");
      row.addEventListener("click", (event) => {
        if (event.target instanceof Element && event.target.closest(".reader-token, button, select, input, textarea, label, a")) {
          return;
        }
        setReaderSpeechStartLine(row.dataset.readerLineKey);
      });
      const time = Number.isInteger(line.start_ms) ? formatTimestamp(line.start_ms) : "";
      row.append(el("span", "reader-line-time", time));
      if (options.full) {
        const speechButton = el("button", "reader-line-speech-button", "▶");
        speechButton.type = "button";
        speechButton.title = t("readerReadLine");
        speechButton.setAttribute("aria-label", speechButton.title);
        speechButton.dataset.readerSpeechLineKey = row.dataset.readerLineKey;
        speechButton.addEventListener("click", (event) => {
          event.stopPropagation();
          startReaderSpeechFromLine(row.dataset.readerLineKey, { singleLine: true });
        });
        row.append(speechButton);
      }
      const textLine = el("div", "reader-line-text");
      textLine.classList.toggle("reader-furigana-enabled", Boolean(app.reader.showFurigana));
      appendReaderHighlighted(textLine, line.text, line.matches, { ...options, line });
      row.append(textLine);
      return row;
    }

    function appendReaderHighlighted(target, text, matches, options = {}) {
      const validMatches = asArray(matches)
        .filter((match) => readerWordAllowed(match.word, options.wordSet))
        .filter((match) => Number.isInteger(match.start) && Number.isInteger(match.end))
        .filter((match) => match.start >= 0 && match.end > match.start && match.end <= text.length)
        .sort((left, right) => left.start - right.start || right.end - left.end);
      let cursor = 0;
      validMatches.forEach((match) => {
        if (match.start < cursor) {
          return;
        }
        if (match.start > cursor) {
          target.append(document.createTextNode(text.slice(cursor, match.start)));
        }
        const button = el(
          "button",
          ["reader-token", readerTokenStatusClass(match)].filter(Boolean).join(" "),
        );
        button.type = "button";
        button.title = match.word;
        button.dataset.word = match.word;
        appendReaderTokenText(button, text.slice(match.start, match.end), match.reading || "");
        button.addEventListener("click", (event) => {
          event.stopPropagation();
          selectReaderWord(match.word, readerSelectionForLine(options.line || { text }, match, options));
        });
        target.append(button);
        cursor = match.end;
      });
      if (cursor < text.length) {
        target.append(document.createTextNode(text.slice(cursor)));
      }
      if (target.childNodes.length === 0) {
        target.textContent = text;
      }
    }

    function appendReaderTokenText(target, surface, reading) {
      if (!app.reader.showFurigana) {
        target.textContent = surface;
        return;
      }
      const parts = readerRubyParts(surface, reading);
      if (!parts.some((part) => part.rt)) {
        target.textContent = surface;
        return;
      }
      parts.forEach((part) => {
        if (!part.rt) {
          target.append(document.createTextNode(part.text));
          return;
        }
        const ruby = el("ruby", "reader-ruby");
        ruby.append(document.createTextNode(part.text), el("rt", "", part.rt));
        target.append(ruby);
      });
    }

    function readerRubyParts(surface, reading) {
      const text = String(surface || "");
      const rubyReading = primaryRubyReading(reading);
      if (!text || !rubyReading || !hasCjkText(text)) {
        return [{ text, rt: "" }];
      }
      const segments = splitRubySegments(text);
      const parts = [];
      let readingIndex = 0;
      segments.forEach((segment, index) => {
        if (!segment.cjk) {
          parts.push({ text: segment.text, rt: "" });
          readingIndex = advanceReadingIndex(rubyReading, readingIndex, segment.text);
          return;
        }
        const nextAnchor = nextKanaAnchor(segments, index + 1);
        const nextIndex = nextAnchor ? rubyReading.indexOf(nextAnchor, readingIndex) : -1;
        const rt = nextIndex >= readingIndex
          ? rubyReading.slice(readingIndex, nextIndex)
          : rubyReading.slice(readingIndex);
        parts.push({ text: segment.text, rt: rt && rt !== toHiragana(segment.text) ? rt : "" });
        readingIndex = nextIndex >= readingIndex ? nextIndex : rubyReading.length;
      });
      return parts;
    }

    function primaryRubyReading(reading) {
      return toHiragana(
        String(reading || "")
          .split(/[;；,、]/)[0]
          .trim(),
      ).replace(/\s+/g, "");
    }

    function splitRubySegments(text) {
      const segments = [];
      [...text].forEach((char) => {
        const cjk = isCjkChar(char);
        const current = segments[segments.length - 1];
        if (current && current.cjk === cjk) {
          current.text += char;
        } else {
          segments.push({ text: char, cjk });
        }
      });
      return segments;
    }

    function nextKanaAnchor(segments, startIndex) {
      for (let index = startIndex; index < segments.length; index += 1) {
        if (!segments[index].cjk) {
          const anchor = kanaAnchor(segments[index].text);
          if (anchor) {
            return anchor;
          }
        }
      }
      return "";
    }

    function advanceReadingIndex(reading, index, surface) {
      const anchor = kanaAnchor(surface);
      if (!anchor) {
        return index;
      }
      if (reading.startsWith(anchor, index)) {
        return index + anchor.length;
      }
      return index;
    }

    function kanaAnchor(value) {
      return toHiragana(value).replace(/[^\u3040-\u309fー]/g, "");
    }

    function toHiragana(value) {
      return String(value || "").replace(/[\u30a1-\u30f6]/g, (char) => (
        String.fromCharCode(char.charCodeAt(0) - 0x60)
      ));
    }

    function hasCjkText(value) {
      return /[\u3400-\u9fff々〆ヶ]/.test(value);
    }

    function isCjkChar(char) {
      return /^[\u3400-\u9fff々〆ヶ]$/.test(char);
    }

    function readerTokenStatusClass(match) {
      const status = statusFor({ word: match.word });
      return ["learning", "known"].includes(status) ? `status-${status}` : "";
    }

    function readerLineDomKey(document, line, lineIndex) {
      return `line-${stableHash([
        readerDocumentKey(document || {}),
        Number.isInteger(lineIndex) ? lineIndex : "",
        Number.isInteger(line.start_ms) ? line.start_ms : "",
        line.text || "",
      ].join("\n"))}`;
    }

    function stableHash(value) {
      let hash = 2166136261;
      for (let index = 0; index < value.length; index += 1) {
        hash ^= value.charCodeAt(index);
        hash = Math.imul(hash, 16777619);
      }
      return (hash >>> 0).toString(36);
    }

    function compareReaderDocuments(left, right) {
      const episodeDiff = compareNullableNumbers(left.episode, right.episode);
      if (episodeDiff !== 0) {
        return episodeDiff;
      }
      return readerDocumentLabel(left).localeCompare(readerDocumentLabel(right), app.lang === "zh" ? "zh-CN" : "ja-JP");
    }

    function compareReaderLines(left, right) {
      const timeDiff = compareNullableNumbers(left.start_ms, right.start_ms);
      if (timeDiff !== 0) {
        return timeDiff;
      }
      return String(left.text || "").localeCompare(String(right.text || ""), "ja-JP");
    }

    function compareNullableNumbers(left, right) {
      const leftNumber = Number.isFinite(left) ? left : null;
      const rightNumber = Number.isFinite(right) ? right : null;
      if (leftNumber !== null && rightNumber !== null) {
        return leftNumber - rightNumber;
      }
      if (leftNumber !== null) {
        return -1;
      }
      if (rightNumber !== null) {
        return 1;
      }
      return 0;
    }

    function readerSelectionForLine(line, match, options = {}) {
      const document = options.document || {};
      const lineIndex = Number.isInteger(options.lineIndex) ? options.lineIndex : -1;
      const lines = asArray(document.lines);
      const contextBefore = lineIndex >= 0
        ? lines.slice(Math.max(0, lineIndex - 2), lineIndex).map((item) => item.text || "").filter(Boolean)
        : [];
      const contextAfter = lineIndex >= 0
        ? lines.slice(lineIndex + 1, lineIndex + 3).map((item) => item.text || "").filter(Boolean)
        : [];
      const sourceFile = document.source_file || "";
      const example = {
        source_type: document.source_type || "subtitle",
        source_title: document.source_title || "",
        source_artist: document.source_artist || "",
        source_album: document.source_album || "",
        source_file: sourceFile,
        subtitle_file: sourceFile,
        episode: Number.isInteger(document.episode) ? document.episode : null,
        start_ms: Number.isInteger(line.start_ms) ? line.start_ms : null,
        end_ms: Number.isInteger(line.end_ms) ? line.end_ms : null,
        matched_text: match.matched_text || match.word || "",
        sentence: line.text || "",
        context_before: contextBefore,
        context_after: contextAfter,
      };
      return {
        key: readerSelectionKey(match.word, example),
        word: match.word || "",
        example,
      };
    }

    function readerSelectionKey(wordText, example) {
      return [
        wordText || "",
        example.source_type || "",
        example.source_title || "",
        example.source_artist || "",
        example.source_album || "",
        example.source_file || "",
        Number.isInteger(example.episode) ? example.episode : "",
        Number.isInteger(example.start_ms) ? example.start_ms : "",
        example.matched_text || "",
        example.sentence || "",
      ].join("\u0000");
    }

    function exampleExplanationKey(word, example) {
      const sourceFile = example.source_file || example.subtitle_file || "";
      return readerSelectionKey(word.word || "", {
        ...example,
        source_file: sourceFile,
      });
    }

    function readerDocumentKey(document) {
      return [
        document.source_type || "subtitle",
        document.source_title || "",
        document.source_artist || "",
        document.source_album || "",
        document.source_file || "",
        Number.isInteger(document.episode) ? document.episode : "",
      ].join("\u0000");
    }

    return {
      compareNullableNumbers,
      compareReaderDocuments,
      exampleExplanationKey,
      readerDocumentKey,
      readerDocumentLabel,
      readerDocumentsForSource,
      readerLineDomKey,
      readerSelectionForLine,
      renderSourceReader,
    };
  }

  return { createReaderHelpers };
})();
