window.JPCORPUS_FORMAT = (() => {
  function createFormatHelpers({ getLanguage }) {
    function formatNumber(value) {
      return new Intl.NumberFormat(getLanguage?.() === "zh" ? "zh-CN" : "en-US").format(value || 0);
    }

    function formatReference(example) {
      if (example.source_type === "lyrics") {
        return formatLyricReference(example);
      }
      if (example.source_type === "text") {
        return formatTextReference(example);
      }

      const parts = [];
      if (example.source_title) {
        parts.push(example.source_title);
      }
      if (Number.isInteger(example.episode)) {
        parts.push(`EP${String(example.episode).padStart(2, "0")}`);
      } else if (example.subtitle_file) {
        parts.push(example.subtitle_file);
      }
      if (Number.isInteger(example.start_ms)) {
        parts.push(formatTimestamp(example.start_ms));
      }
      return parts.join(" ");
    }

    function formatTextReference(example) {
      const parts = [];
      const title = String(example.source_title || "").trim();
      const author = String(example.source_artist || "").trim();
      const file = String(example.subtitle_file || "").trim();
      if (title) {
        parts.push(title);
      }
      if (author) {
        parts.push(author);
      }
      if (file && normalizedTextTitle(fileStem(file)) !== normalizedTextTitle(title)) {
        parts.push(file);
      }
      return parts.join(" · ");
    }

    function formatLyricReference(example) {
      const parts = [];
      if (example.source_title) {
        parts.push(`♪ ${example.source_title}`);
      }
      if (example.source_artist) {
        parts.push(example.source_artist);
      }
      if (example.source_album && example.source_album !== example.source_title) {
        parts.push(`《${example.source_album}》`);
      }
      if (Number.isInteger(example.start_ms)) {
        parts.push(formatTimestamp(example.start_ms));
      }
      return parts.join(" · ");
    }

    function formatTimestamp(milliseconds) {
      let seconds = Math.floor(milliseconds / 1000);
      const hours = Math.floor(seconds / 3600);
      seconds -= hours * 3600;
      const minutes = Math.floor(seconds / 60);
      seconds -= minutes * 60;
      if (hours > 0) {
        return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
      }
      return `${pad(minutes)}:${pad(seconds)}`;
    }

    function displayReading(word) {
      const surface = String(word?.word || "").trim();
      const reading = String(word?.reading || "").trim();
      if (!reading || reading === surface) {
        return "";
      }
      if (isKatakanaText(surface) && hiraganaToKatakana(reading) === surface) {
        return "";
      }
      return reading;
    }

    return {
      displayReading,
      exampleSourceClass,
      fileStem,
      formatNumber,
      formatReference,
      formatTimestamp,
      normalizedTextTitle,
    };
  }

  function fileStem(value) {
    const name = value.split(/[\\/]/u).pop() || value;
    return name.replace(/\.[^.]+$/u, "");
  }

  function normalizedTextTitle(value) {
    return String(value || "")
      .normalize("NFC")
      .replace(/[\s\u3000]+/gu, " ")
      .trim();
  }

  function exampleSourceClass(example) {
    if (example.source_type === "lyrics") {
      return "lyrics";
    }
    if (example.source_type === "text") {
      return "text";
    }
    return "subtitle";
  }

  function pad(value) {
    return String(value).padStart(2, "0");
  }

  function isKatakanaText(value) {
    return Boolean(value) && /^[ァ-ヺー・･]+$/u.test(value);
  }

  function hiraganaToKatakana(value) {
    return String(value || "").replace(/[ぁ-ゖ]/gu, (char) => (
      String.fromCharCode(char.charCodeAt(0) + 0x60)
    ));
  }

  return {
    createFormatHelpers,
  };
})();
