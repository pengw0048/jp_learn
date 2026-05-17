window.JPCORPUS_LEXICAL = (() => {
  const LEXICAL_POS_LABELS_ZH = {
    "noun or participle which takes the aux. verb suru": "动词",
    "nouns which may take the genitive case particle 'no'": "名词",
    "noun (common) (futsuumeishi)": "名词",
    "noun, used as a suffix": "接尾词",
    "pronoun": "代词",
    "adverb (fukushi)": "副词",
    "adjective (keiyoushi)": "い形容词",
    "adjectival nouns or quasi-adjectives (keiyodoshi)": "な形容词",
    "adverbial noun (fukushitekimeishi)": "副词",
    "adverb taking the 'to' particle": "副词",
    "expressions (phrases, clauses, etc.)": "表达",
    "noun or verb acting prenominally": "连体词",
    "auxiliary verb": "助动词",
    "auxiliary adjective": "辅助形容词",
    "conjunction": "接续词",
    "interjection (kandoushi)": "感叹词",
    "counter": "助数词",
    "particle": "助词",
    "prefix": "接头词",
    "suffix": "接尾词",
    "suru verb - special class": "动词",
    "suru verb - included": "动词",
    "numeric": "数词",
    "noun, used as a prefix": "接头词",
    "Ichidan verb": "动词",
    "Ichidan verb - kureru special class": "动词",
    "Ichidan verb - zuru verb (alternative form of -jiru verbs)": "动词",
    "Godan verb - Iku/Yuku special class": "动词",
    "'taru' adjective": "たる形容词",
    "pre-noun adjectival (rentaishi)": "连体词",
    "Godan verb with 'u' ending": "动词",
    "Godan verb with `u' ending": "动词",
    "Godan verb with 'ru' ending (irregular verb)": "动词",
    "Godan verb with 'ru' ending": "动词",
    "Godan verb with `ru' ending": "动词",
    "Godan verb with 'ku' ending": "动词",
    "Godan verb with `ku' ending": "动词",
    "Godan verb with 'gu' ending": "动词",
    "Godan verb with `gu' ending": "动词",
    "Godan verb with 'su' ending": "动词",
    "Godan verb with `su' ending": "动词",
    "Godan verb with 'tsu' ending": "动词",
    "Godan verb with `tsu' ending": "动词",
    "Godan verb with 'nu' ending": "动词",
    "Godan verb with `nu' ending": "动词",
    "Godan verb with 'bu' ending": "动词",
    "Godan verb with `bu' ending": "动词",
    "Godan verb with 'mu' ending": "动词",
    "Godan verb with `mu' ending": "动词",
    "Godan verb - -aru special class": "动词",
    "Godan verb with 'u' ending (special class)": "动词",
    "Kuru verb - special class": "动词",
    "Suru verb - special class": "动词",
    "Suru verb - included": "动词",
    "su verb - precursor to the modern suru": "动词",
    "'ku' adjective (archaic)": "形容词",
    "auxiliary": "助动词",
    "'shiku' adjective (archaic)": "形容词",
    "Nidan verb (lower class) with 'u' ending and 'we' conjugation (archaic)": "动词",
    "Nidan verb (upper class) with 'ru' ending (archaic)": "动词",
    "Nidan verb (lower class) with 'ru' ending (archaic)": "动词",
    "Yodan verb with 'ru' ending (archaic)": "动词",
    "transitive verb": "他动",
    "intransitive verb": "自动",
    n: "名词",
    pn: "代词",
    adv: "副词",
    "adj-i": "い形容词",
    "adj-na": "な形容词",
    v1: "动词",
    v5u: "动词",
    v5k: "动词",
    v5g: "动词",
    v5s: "动词",
    v5t: "动词",
    v5n: "动词",
    v5b: "动词",
    v5m: "动词",
    v5r: "动词",
    vt: "他动",
    vi: "自动",
    "自他动": "自他",
    "自他动1": "自他",
    "自他动2": "自他",
    "自他动3": "自他",
    unclassified: "未分类",
  };
  const HIDDEN_LEXICAL_POS_LABELS_ZH = new Set([
    "名词",
    "动词",
    "未分类",
  ]);

  function createLexicalHelpers({ el, t, getLanguage }) {
    const language = () => getLanguage?.() || "zh";

    function displayMeaningRaw(word) {
      if (language() === "zh") {
        return word.meaning_zh || "";
      }
      return word.meaning || word.meaning_zh || "";
    }

    function renderMeaningValue(word, className) {
      return renderParsedMeaning(parseMeaning(displayMeaningRaw(word)), className);
    }

    function renderParsedMeaning(meaning, className) {
      const wrap = el("div", className);
      if (!meaning.raw) {
        return wrap;
      }
      if (language() === "zh") {
        wrap.append(el("span", "meaning-text", meaning.text || meaning.raw));
        return wrap;
      }
      if (meaning.accent) {
        wrap.append(el("span", "meaning-chip meaning-accent", meaning.accent));
      }
      if (meaning.pos) {
        wrap.append(el("span", "meaning-chip meaning-pos", meaning.pos));
      }
      wrap.append(el("span", "meaning-text", meaning.text || meaning.raw));
      return wrap;
    }

    function renderLexicalNotes(word) {
      const notes = word.lexical_notes;
      if (!notes || typeof notes !== "object") {
        return document.createDocumentFragment();
      }
      const section = el("section", "lexical-notes");
      section.append(el("h3", "section-title", t("lexicalNotes")));
      const body = el("div", "lexical-note-grid");
      const spellingNodes = lexicalFormNodes(lexicalUsefulForms(notes.spellings, [word.word]));
      const readingNodes = lexicalFormNodes(lexicalUsefulForms(notes.readings, [word.reading, word.word]));
      const posLabels = lexicalVisiblePosLabels(notes.parts_of_speech);
      const posNodes = lexicalTextNodes(posLabels);
      const senseNodes = language() === "zh" ? [] : lexicalSenseNodes(notes.senses, new Set(posLabels));
      const dictionaryExampleNodes = lexicalDictionaryExampleNodes(notes.dictionary_examples);
      const hasUsefulNotes =
        spellingNodes.length > 0
        || readingNodes.length > 0
        || posNodes.length > 0
        || senseNodes.length > 0
        || dictionaryExampleNodes.length > 0;
      if (!hasUsefulNotes) {
        return document.createDocumentFragment();
      }
      appendLexicalRow(body, t("lexicalSpellings"), spellingNodes);
      appendLexicalRow(body, t("lexicalReadings"), readingNodes);
      appendLexicalRow(body, t("lexicalPos"), posNodes);
      appendLexicalRow(
        body,
        t("lexicalSenses"),
        senseNodes,
        "lexical-note-values lexical-sense-values",
      );
      appendLexicalRow(
        body,
        t("lexicalExamples"),
        dictionaryExampleNodes,
        "lexical-note-values lexical-example-values",
      );
      if (!body.childElementCount) {
        return document.createDocumentFragment();
      }
      section.append(body);
      return section;
    }

    function renderUserDictionaryResults(word) {
      const results = asArray(word.user_dictionary_results);
      if (!results.length) {
        return document.createDocumentFragment();
      }
      const section = el("section", "user-dictionary-results");
      section.append(el("h3", "section-title", t("userDictionaryResults")));
      const list = el("div", "user-dictionary-result-list");
      groupedUserDictionaryResults(results).slice(0, 4).forEach((group) => {
        const definitions = compactUserDictionaryDefinitions(group.results);
        const spellings = compactUserDictionaryReferences(group.results, "spelling");
        const references = compactUserDictionaryReferences(group.results, "see_also");
        if (!definitions.length && !spellings.length && !references.length) {
          return;
        }
        const item = el("article", "user-dictionary-result");
        let sourceTarget = null;
        if (definitions.length) {
          const content = el("p", "user-dictionary-definition", definitions.join("；"));
          item.append(content);
          sourceTarget = content;
        }
        if (spellings.length) {
          const line = userDictionaryReferenceLine(t("userDictionarySpellings"), spellings);
          item.append(line);
          sourceTarget ||= line;
        }
        if (references.length) {
          const line = userDictionaryReferenceLine(t("userDictionarySeeAlso"), references);
          item.append(line);
          sourceTarget ||= line;
        }
        if (group.name && sourceTarget) {
          appendUserDictionarySource(sourceTarget, group.name);
        }
        list.append(item);
      });
      if (!list.childElementCount) {
        return document.createDocumentFragment();
      }
      section.append(list);
      return section;
    }

    function groupedUserDictionaryResults(results) {
      const groups = [];
      const byKey = new Map();
      asArray(results).forEach((result) => {
        const key = result.dictionary_id || result.dictionary_name || result.format || "dictionary";
        if (!byKey.has(key)) {
          const group = {
            key,
            name: result.dictionary_name || t("userDictionaryUnknown"),
            results: [],
          };
          byKey.set(key, group);
          groups.push(group);
        }
        byKey.get(key).results.push(result);
      });
      return groups;
    }

    function compactUserDictionaryDefinitions(results) {
      return uniqueUserDictionaryStrings(
        results
          .filter((result) => result.kind !== "reference")
          .flatMap((result) => asArray(result.definitions).filter(Boolean)),
      ).slice(0, 8);
    }

    function userDictionaryReferenceLine(label, values) {
      const reference = el("p", "user-dictionary-reference");
      reference.append(el("span", "", `${label}：`), values.join("、"));
      return reference;
    }

    function appendUserDictionarySource(node, source) {
      const sourceNode = el("small", "user-dictionary-source", source);
      sourceNode.title = source;
      node.append(" ", sourceNode);
    }

    function compactUserDictionaryReferences(results, type) {
      return uniqueUserDictionaryStrings(
        results
          .filter((result) => result.kind === "reference")
          .filter((result) => (result.reference_type || "see_also") === type)
          .flatMap((result) => asArray(result.references).length ? result.references : result.definitions)
          .filter(Boolean),
      ).slice(0, 6);
    }

    function uniqueUserDictionaryStrings(values) {
      const seen = new Set();
      const output = [];
      asArray(values).forEach((value) => {
        const text = String(value || "").trim();
        if (!text || seen.has(text)) {
          return;
        }
        seen.add(text);
        output.push(text);
      });
      return output;
    }

    function appendLexicalRow(parent, label, nodes, valueClassName = "lexical-note-values") {
      if (!nodes.length) {
        return;
      }
      const row = el("div", "lexical-note-row");
      row.append(el("span", "lexical-note-label", label));
      const values = el("div", valueClassName);
      nodes.forEach((node) => values.append(node));
      row.append(values);
      parent.append(row);
    }

    function lexicalFormNodes(values) {
      return asArray(values).map((form) => {
        const chip = el("span", "lexical-chip lexical-form-chip");
        chip.append(document.createTextNode(String(form.text || "")));
        const tags = asArray(form.tags).filter(Boolean).join(" / ");
        if (tags) {
          chip.title = tags;
        }
        return chip;
      }).filter((node) => node.textContent.trim());
    }

    function lexicalTextNodes(values, className = "lexical-chip") {
      return asArray(values)
        .map((value) => String(value || "").trim())
        .filter(Boolean)
        .map((value) => el("span", className, value));
    }

    function lexicalPosNodes(values) {
      return lexicalTextNodes(lexicalVisiblePosLabels(values));
    }

    function lexicalVisiblePosLabels(values) {
      const labels = asArray(values)
        .map((value) => String(value || "").trim())
        .filter(Boolean);
      return language() === "zh"
        ? uniqueStrings(compactLexicalPosZh(labels.map(labelLexicalPosZh)))
          .filter((label) => !HIDDEN_LEXICAL_POS_LABELS_ZH.has(label))
        : labels;
    }

    function lexicalSenseNodes(values, repeatedLabels = new Set()) {
      return asArray(values).map((sense, index) => {
        if (!sense || typeof sense !== "object") {
          return null;
        }
        const glosses = uniqueStrings(asArray(sense.glosses)).slice(0, 3);
        const metaLabels = lexicalSenseMetaLabels(sense, repeatedLabels);
        if (!glosses.length && !metaLabels.length) {
          return null;
        }
        const item = el("div", "lexical-sense");
        const head = el("div", "lexical-sense-head");
        head.append(el("span", "lexical-sense-index", String(index + 1)));
        if (glosses.length) {
          head.append(el("span", "lexical-sense-glosses", glosses.join(language() === "zh" ? "；" : "; ")));
        }
        item.append(head);
        if (metaLabels.length) {
          const meta = el("div", "lexical-sense-meta");
          metaLabels.forEach((label) => meta.append(el("span", "lexical-chip", label)));
          item.append(meta);
        }
        return item;
      }).filter(Boolean);
    }

    function lexicalSenseMetaLabels(sense, repeatedLabels) {
      const posLabels = language() === "zh"
        ? asArray(sense.parts_of_speech).map(labelLexicalPosZh)
        : asArray(sense.parts_of_speech);
      const labels = uniqueStrings([
        ...posLabels,
        ...asArray(sense.tags),
      ]);
      const visibleLabels = language() === "zh"
        ? labels.filter((label) => !HIDDEN_LEXICAL_POS_LABELS_ZH.has(label))
        : labels;
      return visibleLabels.filter((label) => !repeatedLabels.has(label));
    }

    function lexicalDictionaryExampleNodes(values) {
      return asArray(values).map((example) => {
        const japanese = String(example.japanese || example.sentence || "").trim();
        if (!japanese) {
          return null;
        }
        const translation = lexicalExampleTranslation(example);
        if (language() === "zh" && !translation) {
          return null;
        }
        const item = el("div", "lexical-dictionary-example");
        item.append(el("div", "lexical-dictionary-example-ja", japanese));
        if (translation) {
          item.append(el("div", "lexical-dictionary-example-translation", translation));
        }
        return item;
      }).filter(Boolean);
    }

    function lexicalExampleTranslation(example) {
      const translations = example.translations || {};
      if (typeof translations === "string") {
        return translations.trim();
      }
      if (!translations || typeof translations !== "object") {
        return "";
      }
      if (language() === "zh") {
        return ["cmn", "zh", "zho", "chi"]
          .map((lang) => String(translations[lang] || "").trim())
          .find(Boolean) || "";
      }
      const preferred = ["eng", "en", "cmn", "zh", "zho", "chi"];
      for (const lang of preferred) {
        const value = String(translations[lang] || "").trim();
        if (value) {
          return value;
        }
      }
      return Object.values(translations)
        .map((value) => String(value || "").trim())
        .find(Boolean) || "";
    }

    return {
      displayMeaningRaw,
      renderLexicalNotes,
      renderMeaningValue,
      renderUserDictionaryResults,
    };
  }

  function lexicalUsefulForms(values, currentValues = []) {
    const currentKeys = new Set(asArray(currentValues).flatMap(lexicalFormKeys).filter(Boolean));
    const seenKeys = new Set();
    return asArray(values)
      .filter((form) => String(form.text || "").trim())
      .filter((form) => {
        const key = lexicalFormKey(form.text);
        if (!key || currentKeys.has(key) || seenKeys.has(key)) {
          return false;
        }
        seenKeys.add(key);
        return true;
      });
  }

  function lexicalFormKey(value) {
    return String(value || "").normalize("NFKC").trim();
  }

  function lexicalFormKeys(value) {
    const key = lexicalFormKey(value);
    if (!key) {
      return [];
    }
    return [
      key,
      ...key.split(/[;；,，、/・･\s]+/u).map(lexicalFormKey).filter(Boolean),
    ];
  }

  function uniqueStrings(values) {
    const seen = new Set();
    return asArray(values).filter((value) => {
      const textValue = String(value || "").trim();
      if (!textValue || seen.has(textValue)) {
        return false;
      }
      seen.add(textValue);
      return true;
    });
  }

  function labelLexicalPosZh(value) {
    const mapped = LEXICAL_POS_LABELS_ZH[value];
    if (mapped) {
      return mapped;
    }
    const compacted = compactFineGrainedLexicalPosZh(value);
    if (compacted) {
      return compacted;
    }
    return looksLikeEnglishLexicalLabel(value) ? "" : value;
  }

  function compactFineGrainedLexicalPosZh(value) {
    const text = String(value || "").trim();
    if (/^(?:五段・|一段(?:动词)?|一段・|カ变|サ变|す动词|古典.*动词)/u.test(text)) {
      return "动词";
    }
    if (text === "する名词") {
      return "动词";
    }
    if (text === "の名词") {
      return "名词";
    }
    if (text === "名词・接尾") {
      return "接尾词";
    }
    if (text === "名词・接头") {
      return "接头词";
    }
    if (text === "副词性名词" || text === "と副词") {
      return "副词";
    }
    return "";
  }

  function compactLexicalPosZh(labels) {
    if (!labels.includes("自动") || !labels.includes("他动")) {
      return labels;
    }
    const firstIndex = Math.min(labels.indexOf("自动"), labels.indexOf("他动"));
    const compacted = labels.filter((label) => label !== "自动" && label !== "他动");
    compacted.splice(firstIndex, 0, "自他");
    return compacted;
  }

  function looksLikeEnglishLexicalLabel(value) {
    const text = String(value || "");
    const asciiLetters = (text.match(/[A-Za-z]/g) || []).length;
    return asciiLetters >= 3 && asciiLetters >= text.length * 0.35;
  }

  function parseMeaning(value) {
    let textValue = stripLeadingReading(String(value || "").trim());
    const raw = textValue;
    let accent = "";
    let pos = "";
    const accentMatch = textValue.match(/^([⓪①②③④⑤⑥⑦⑧⑨]+)\s*/u);
    if (accentMatch) {
      accent = accentMatch[1];
      textValue = textValue.slice(accentMatch[0].length).trim();
    }
    const bracketPosMatch = textValue.match(/^【([^】]+)】\s*/u);
    if (bracketPosMatch) {
      pos = bracketPosMatch[1];
      textValue = textValue.slice(bracketPosMatch[0].length).trim();
    } else {
      const prefix = meaningPosPrefix(textValue);
      if (prefix) {
        pos = normalizeMeaningPos(prefix);
        textValue = textValue.slice(prefix.length).trim();
      }
    }
    return { raw, accent, pos, text: textValue };
  }

  function stripLeadingReading(value) {
    return value.replace(/^[（(][ぁ-んァ-ンー・\s0-9０-９⓪①②③④⑤⑥⑦⑧⑨/／;；]+[）)]\s*/u, "");
  }

  function meaningPosPrefix(value) {
    const prefixes = [
      "助动词",
      "连体词",
      "接续词",
      "感叹词",
      "形容词",
      "自动1",
      "自动2",
      "自动3",
      "自他动1",
      "自他动2",
      "自他动3",
      "自他动",
      "他动1",
      "他动2",
      "他动3",
      "自动",
      "他动",
      "动词",
      "名词",
      "代词",
      "副词",
      "数词",
      "助词",
      "动1",
      "动2",
      "动3",
      "动",
      "自サ",
      "他サ",
      "自他サ",
      "イ形",
      "ナ形",
      "连体",
      "名",
      "代",
      "副",
      "数",
    ];
    return prefixes.find((prefix) => value.startsWith(`${prefix} `) || value.startsWith(`${prefix}　`)) || "";
  }

  function normalizeMeaningPos(value) {
    const mapping = {
      名词: "名",
      代词: "代",
      副词: "副",
      数词: "数",
      动词: "动",
      自他动: "自他",
      自他动1: "自他",
      自他动2: "自他",
      自他动3: "自他",
      自动: "自动",
      自动1: "自动",
      自动2: "自动",
      自动3: "自动",
      他动: "他动",
      他动1: "他动",
      他动2: "他动",
      他动3: "他动",
      自サ: "自动",
      他サ: "他动",
      自他サ: "自他",
      动: "动",
    };
    return mapping[value] || value;
  }

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  return {
    createLexicalHelpers,
  };
})();
