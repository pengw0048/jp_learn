window.JPCORPUS_SEARCH = (() => {
  const SEARCH_PUNCTUATION_RE = /[\s!"#$%&'()*+,\-./:;<=>?@[\\\]^_`{|}~、。，．・･；;：:！？!?「」『』【】（）()［］\[\]〈〉《》…〜～·]+/gu;
  const GODAN_ENDINGS = {
    "う": { a: "わ", i: "い", e: "え", o: "お", te: "って", ta: "った" },
    "く": { a: "か", i: "き", e: "け", o: "こ", te: "いて", ta: "いた" },
    "ぐ": { a: "が", i: "ぎ", e: "げ", o: "ご", te: "いで", ta: "いだ" },
    "す": { a: "さ", i: "し", e: "せ", o: "そ", te: "して", ta: "した" },
    "つ": { a: "た", i: "ち", e: "て", o: "と", te: "って", ta: "った" },
    "ぬ": { a: "な", i: "に", e: "ね", o: "の", te: "んで", ta: "んだ" },
    "ぶ": { a: "ば", i: "び", e: "べ", o: "ぼ", te: "んで", ta: "んだ" },
    "む": { a: "ま", i: "み", e: "め", o: "も", te: "んで", ta: "んだ" },
    "る": { a: "ら", i: "り", e: "れ", o: "ろ", te: "って", ta: "った" },
  };
  const ROMAJI_DIGRAPHS = {
    きゃ: "kya", きゅ: "kyu", きょ: "kyo",
    ぎゃ: "gya", ぎゅ: "gyu", ぎょ: "gyo",
    しゃ: "sha", しゅ: "shu", しょ: "sho",
    じゃ: "ja", じゅ: "ju", じょ: "jo",
    ちゃ: "cha", ちゅ: "chu", ちょ: "cho",
    にゃ: "nya", にゅ: "nyu", にょ: "nyo",
    ひゃ: "hya", ひゅ: "hyu", ひょ: "hyo",
    びゃ: "bya", びゅ: "byu", びょ: "byo",
    ぴゃ: "pya", ぴゅ: "pyu", ぴょ: "pyo",
    みゃ: "mya", みゅ: "myu", みょ: "myo",
    りゃ: "rya", りゅ: "ryu", りょ: "ryo",
  };
  const ROMAJI_KANA = {
    あ: "a", い: "i", う: "u", え: "e", お: "o",
    か: "ka", き: "ki", く: "ku", け: "ke", こ: "ko",
    が: "ga", ぎ: "gi", ぐ: "gu", げ: "ge", ご: "go",
    さ: "sa", し: "shi", す: "su", せ: "se", そ: "so",
    ざ: "za", じ: "ji", ず: "zu", ぜ: "ze", ぞ: "zo",
    た: "ta", ち: "chi", つ: "tsu", て: "te", と: "to",
    だ: "da", ぢ: "ji", づ: "zu", で: "de", ど: "do",
    な: "na", に: "ni", ぬ: "nu", ね: "ne", の: "no",
    は: "ha", ひ: "hi", ふ: "fu", へ: "he", ほ: "ho",
    ば: "ba", び: "bi", ぶ: "bu", べ: "be", ぼ: "bo",
    ぱ: "pa", ぴ: "pi", ぷ: "pu", ぺ: "pe", ぽ: "po",
    ま: "ma", み: "mi", む: "mu", め: "me", も: "mo",
    や: "ya", ゆ: "yu", よ: "yo",
    ら: "ra", り: "ri", る: "ru", れ: "re", ろ: "ro",
    わ: "wa", を: "o", ん: "n",
    ゔ: "vu",
    ぁ: "a", ぃ: "i", ぅ: "u", ぇ: "e", ぉ: "o",
    ゃ: "ya", ゅ: "yu", ょ: "yo",
  };
  const searchIndexCache = new WeakMap();

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function wordText(word) {
    return typeof word === "string" ? word : String(word?.word || "");
  }

  function wordReading(word) {
    return typeof word === "string" ? word : String(word?.reading || word?.word || "");
  }

  function clearSearchIndexForWord(word) {
    if (word && typeof word === "object") {
      searchIndexCache.delete(word);
    }
  }

  function searchTerms(value) {
    return String(value || "")
      .normalize("NFKC")
      .trim()
      .split(/\s+/u)
      .map((term) => searchVariants(term))
      .filter((variants) => variants.length);
  }

  function searchScore(word, terms) {
    const index = searchIndexForWord(word);
    let total = 0;
    for (const variants of terms) {
      let best = 0;
      index.forEach((entry) => {
        variants.forEach((variant) => {
          best = Math.max(best, searchEntryScore(entry, variant));
        });
      });
      if (best <= 0) {
        return 0;
      }
      total += best;
    }
    return total;
  }

  function searchEntryScore(entry, term) {
    if (!term) {
      return 0;
    }
    const field = entry.value;
    if (!field || term.length > field.length + 6) {
      return 0;
    }
    if (field === term) {
      return 120 + entry.boost;
    }
    if (field.startsWith(term)) {
      return 95 + entry.boost;
    }
    if (field.includes(term)) {
      return 72 + entry.boost;
    }
    if (!allowsFuzzySearch(field, term)) {
      return 0;
    }
    const fuzzy = fuzzySubsequenceScore(field, term);
    return fuzzy > 0 ? fuzzy + Math.min(entry.boost, 20) : 0;
  }

  function searchIndexForWord(word) {
    const cached = searchIndexCache.get(word);
    if (cached) {
      return cached;
    }
    const entries = [];
    const add = (value, boost = 0) => {
      searchVariants(value).forEach((variant) => {
        if (variant) {
          entries.push({ value: variant, boost });
        }
      });
    };
    const notes = word.lexical_notes || {};
    const posText = [
      word.meaning_zh,
      word.meaning,
      ...asArray(notes.parts_of_speech),
    ].filter(Boolean).join(" ");

    add(word.word, 48);
    add(word.reading, 44);
    add(word.meaning_zh, 18);
    add(word.meaning, 12);
    add(word.level, 8);
    asArray(word.search_terms).forEach((value) => add(value, 6));
    searchRootForms(word.word, posText).forEach((value) => add(value, 42));
    searchRootForms(word.reading, posText).forEach((value) => add(value, 38));

    asArray(notes.spellings).forEach((form) => {
      add(form.text, 40);
      searchRootForms(form.text, posText).forEach((value) => add(value, 36));
    });
    asArray(notes.readings).forEach((form) => {
      add(form.text, 38);
      searchRootForms(form.text, posText).forEach((value) => add(value, 34));
    });
    asArray(notes.parts_of_speech).forEach((value) => add(value, 12));
    asArray(notes.senses).forEach((sense) => {
      asArray(sense.glosses).forEach((value) => add(value, 10));
      asArray(sense.parts_of_speech).forEach((value) => add(value, 8));
      asArray(sense.tags).forEach((value) => add(value, 8));
    });
    asArray(notes.kanji).forEach((kanji) => {
      add(kanji.literal, 26);
      asArray(kanji.meanings).forEach((value) => add(value, 8));
      asArray(kanji.on_readings).forEach((value) => add(value, 16));
      asArray(kanji.kun_readings).forEach((value) => {
        add(value, 16);
        add(String(value || "").replace(/\./gu, ""), 18);
      });
    });
    asArray(notes.dictionary_examples).forEach((example) => {
      add(example.japanese, 8);
      Object.values(example.translations || {}).forEach((value) => add(value, 6));
    });
    asArray(word.sources).forEach((source) => {
      add(source.title, 14);
      add(source.artist, 12);
      add(source.album, 12);
    });
    asArray(word.examples).forEach((example) => {
      add(example.source_title, 12);
      add(example.source_artist, 12);
      add(example.source_album, 12);
      add(example.matched_text, 14);
      add(example.translation_zh, 4);
      add(example.usage_note_zh, 4);
    });

    const unique = [];
    const seen = new Set();
    entries.forEach((entry) => {
      const key = `${entry.value}\u0000${entry.boost}`;
      if (!seen.has(key)) {
        seen.add(key);
        unique.push(entry);
      }
    });
    searchIndexCache.set(word, unique);
    return unique;
  }

  function searchVariants(value) {
    const normalized = normalizeSearchValue(value);
    if (!normalized) {
      return [];
    }
    const variants = new Set([normalized]);
    const compact = compactSearchValue(normalized);
    if (compact) {
      variants.add(compact);
    }
    const romaji = kanaToRomaji(normalized);
    if (romaji && romaji !== normalized) {
      variants.add(compactSearchValue(romaji));
    }
    return [...variants].filter(Boolean);
  }

  function normalizeSearchValue(value) {
    return katakanaToHiragana(String(value || "").normalize("NFKC").toLowerCase().trim());
  }

  function compactSearchValue(value) {
    return normalizeSearchValue(value).replace(SEARCH_PUNCTUATION_RE, "");
  }

  function katakanaToHiragana(value) {
    return String(value || "").replace(/[\u30a1-\u30f6]/gu, (char) => {
      return String.fromCharCode(char.charCodeAt(0) - 0x60);
    });
  }

  function kanaToRomaji(value) {
    const textValue = katakanaToHiragana(value);
    if (!/[ぁ-ゖ]/u.test(textValue)) {
      return "";
    }
    let result = "";
    let doubleNext = false;
    for (let index = 0; index < textValue.length; index += 1) {
      const char = textValue[index];
      if (char === "っ") {
        doubleNext = true;
        continue;
      }
      const digraph = textValue.slice(index, index + 2);
      let roman = ROMAJI_DIGRAPHS[digraph];
      if (roman) {
        index += 1;
      } else if (char === "ー") {
        roman = result.slice(-1) || "";
      } else {
        roman = ROMAJI_KANA[char] || char;
      }
      if (doubleNext && /^[bcdfghjklmnpqrstvwxyz]/u.test(roman)) {
        result += roman[0];
      }
      doubleNext = false;
      result += roman;
    }
    return result;
  }

  function searchRootForms(value, posText = "") {
    const base = String(value || "").normalize("NFKC").trim();
    if (!base || !/[ぁ-ゖァ-ヺ一-龯々]/u.test(base)) {
      return [];
    }
    const forms = new Set();
    const add = (valueToAdd) => {
      if (valueToAdd && valueToAdd !== base) {
        forms.add(valueToAdd);
      }
    };
    const hiraBase = katakanaToHiragana(base);
    const pos = String(posText || "");

    if (base === "来る" || hiraBase === "くる") {
      ["来ない", "来ます", "来た", "来て", "来れば", "来よう", "こない", "きます", "きた", "きて", "くれば", "こよう"].forEach(add);
    }
    if (base.endsWith("する") || hiraBase.endsWith("する")) {
      const stem = base.slice(0, -2);
      ["し", "して", "した", "します", "しない", "すれば", "しよう", "される", "させる"].forEach((ending) => add(`${stem}${ending}`));
    }
    if ((pos.includes("一段") || pos.includes("Ichidan")) && base.endsWith("る")) {
      const stem = base.slice(0, -1);
      ["", "ない", "ます", "た", "て", "れば", "よう", "られる", "させる"].forEach((ending) => add(`${stem}${ending}`));
    } else if (pos.includes("五段") || pos.includes("Godan")) {
      addGodanSearchForms(base, add);
    }
    if ((pos.includes("い形容词") || pos.includes("adjective") || pos.includes("形容词")) && base.endsWith("い")) {
      const stem = base.slice(0, -1);
      ["く", "かった", "くない", "ければ", "そう"].forEach((ending) => add(`${stem}${ending}`));
    }
    return [...forms];
  }

  function addGodanSearchForms(base, add) {
    const ending = base.slice(-1);
    const rule = GODAN_ENDINGS[ending];
    if (!rule) {
      return;
    }
    const stem = base.slice(0, -1);
    const isIku = base === "行く" || katakanaToHiragana(base) === "いく" || katakanaToHiragana(base) === "ゆく";
    const teEnding = isIku ? "って" : rule.te;
    const taEnding = isIku ? "った" : rule.ta;
    [
      rule.a,
      `${rule.a}ない`,
      rule.i,
      `${rule.i}ます`,
      rule.e,
      `${rule.e}ば`,
      `${rule.o}う`,
      teEnding,
      taEnding,
      `${rule.a}れる`,
      `${rule.a}せる`,
    ].forEach((endingValue) => add(`${stem}${endingValue}`));
  }

  function allowsFuzzySearch(field, term) {
    if (term.length < 4 || field.length > 40) {
      return false;
    }
    if (/^[a-z0-9]+$/u.test(term) && term.length < 5) {
      return false;
    }
    if (/[ぁ-ゖー]/u.test(term)) {
      return /[ぁ-ゖー]/u.test(field);
    }
    if (/[\u3400-\u4dbf\u4e00-\u9fff]/u.test(term)) {
      return /[\u3400-\u4dbf\u4e00-\u9fff]/u.test(field);
    }
    return true;
  }

  function fuzzySubsequenceScore(field, term) {
    if (term.length < 2 || field.length > 80 || term.length > field.length) {
      return 0;
    }
    let position = 0;
    let firstMatch = -1;
    let lastMatch = -1;
    let gapPenalty = 0;
    for (const char of term) {
      const found = field.indexOf(char, position);
      if (found === -1) {
        return 0;
      }
      if (firstMatch === -1) {
        firstMatch = found;
      }
      if (lastMatch !== -1) {
        gapPenalty += Math.max(0, found - lastMatch - 1);
      }
      lastMatch = found;
      position = found + 1;
    }
    const span = lastMatch - firstMatch + 1;
    const density = term.length / span;
    return Math.max(12, Math.round(46 * density) - Math.min(gapPenalty, 20));
  }

  function compareKana(left, right) {
    const readingCompare = kanaSortKey(left).localeCompare(
      kanaSortKey(right),
      "ja",
    );
    if (readingCompare !== 0) {
      return readingCompare;
    }
    return wordText(left).localeCompare(wordText(right), "ja");
  }

  function kanaSortKey(word) {
    let value = wordReading(word).normalize("NFKC").trim();
    value = value.replace(/^[（(][^）)]*[）)]\s*/u, "");
    value = value.replace(/^[^ぁ-ゖァ-ヺ一-龯々]+/u, "");
    return value || wordText(word);
  }

  return {
    clearSearchIndexForWord,
    compareKana,
    searchScore,
    searchTerms,
  };
})();
