window.JPCORPUS_LEXICAL = (() => {
  const LEXICAL_POS_LABELS_ZH = {
    "noun or participle which takes the aux. verb suru": "する名词",
    "nouns which may take the genitive case particle 'no'": "の名词",
    "noun (common) (futsuumeishi)": "名词",
    "noun, used as a suffix": "名词・接尾",
    "pronoun": "代词",
    "adverb (fukushi)": "副词",
    "adjective (keiyoushi)": "い形容词",
    "adjectival nouns or quasi-adjectives (keiyodoshi)": "な形容词",
    "adverbial noun (fukushitekimeishi)": "副词性名词",
    "adverb taking the 'to' particle": "と副词",
    "expressions (phrases, clauses, etc.)": "表达",
    "noun or verb acting prenominally": "连体用法",
    "auxiliary verb": "助动词",
    "auxiliary adjective": "辅助形容词",
    "conjunction": "接续词",
    "interjection (kandoushi)": "感叹词",
    "counter": "助数词",
    "particle": "助词",
    "prefix": "接头词",
    "suffix": "接尾词",
    "suru verb - special class": "サ变",
    "suru verb - included": "サ变",
    "numeric": "数词",
    "noun, used as a prefix": "名词・接头",
    "Ichidan verb": "一段动词",
    "Ichidan verb - kureru special class": "一段・くれる",
    "Ichidan verb - zuru verb (alternative form of -jiru verbs)": "一段・ずる",
    "Godan verb - Iku/Yuku special class": "五段・行く",
    "'taru' adjective": "たる形容词",
    "pre-noun adjectival (rentaishi)": "连体词",
    "Godan verb with 'u' ending": "五段・う",
    "Godan verb with `u' ending": "五段・う",
    "Godan verb with 'ru' ending (irregular verb)": "五段・る特殊",
    "Godan verb with 'ru' ending": "五段・る",
    "Godan verb with `ru' ending": "五段・る",
    "Godan verb with 'ku' ending": "五段・く",
    "Godan verb with `ku' ending": "五段・く",
    "Godan verb with 'gu' ending": "五段・ぐ",
    "Godan verb with `gu' ending": "五段・ぐ",
    "Godan verb with 'su' ending": "五段・す",
    "Godan verb with `su' ending": "五段・す",
    "Godan verb with 'tsu' ending": "五段・つ",
    "Godan verb with `tsu' ending": "五段・つ",
    "Godan verb with 'nu' ending": "五段・ぬ",
    "Godan verb with `nu' ending": "五段・ぬ",
    "Godan verb with 'bu' ending": "五段・ぶ",
    "Godan verb with `bu' ending": "五段・ぶ",
    "Godan verb with 'mu' ending": "五段・む",
    "Godan verb with `mu' ending": "五段・む",
    "Godan verb - -aru special class": "五段・ある",
    "Godan verb with 'u' ending (special class)": "五段・う特殊",
    "Kuru verb - special class": "カ变",
    "Suru verb - special class": "サ变",
    "Suru verb - included": "サ变",
    "su verb - precursor to the modern suru": "す动词",
    "'ku' adjective (archaic)": "く形容词・古语",
    "auxiliary": "助动词",
    "'shiku' adjective (archaic)": "しく形容词・古语",
    "Nidan verb (lower class) with 'u' ending and 'we' conjugation (archaic)": "古典二段动词",
    "Nidan verb (upper class) with 'ru' ending (archaic)": "古典二段动词",
    "Nidan verb (lower class) with 'ru' ending (archaic)": "古典二段动词",
    "Yodan verb with 'ru' ending (archaic)": "古典四段动词",
    "transitive verb": "他动",
    "intransitive verb": "自动",
    n: "名词",
    pn: "代词",
    adv: "副词",
    "adj-i": "い形容词",
    "adj-na": "な形容词",
    v1: "一段动词",
    v5u: "五段・う",
    v5k: "五段・く",
    v5g: "五段・ぐ",
    v5s: "五段・す",
    v5t: "五段・つ",
    v5n: "五段・ぬ",
    v5b: "五段・ぶ",
    v5m: "五段・む",
    v5r: "五段・る",
    vt: "他动",
    vi: "自动",
    unclassified: "未分类",
  };
  const HIDDEN_LEXICAL_POS_LABELS_ZH = new Set([
    "名词",
    "未分类",
  ]);

  function createLexicalHelpers({ el, t, getLanguage }) {
    const language = () => getLanguage?.() || "zh";

    function displayMeaningRaw(word) {
      if (language() === "zh") {
        return word.meaning_zh || word.meaning || "";
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
        ? compactLexicalPosZh(uniqueStrings(labels.map(labelLexicalPosZh)))
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
        const item = el("div", "lexical-dictionary-example");
        item.append(el("div", "lexical-dictionary-example-ja", japanese));
        const translation = lexicalExampleTranslation(example);
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
    return looksLikeEnglishLexicalLabel(value) ? "" : value;
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
      "他动1",
      "他动2",
      "他动3",
      "名词",
      "代词",
      "副词",
      "数词",
      "助词",
      "动1",
      "动2",
      "动3",
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
