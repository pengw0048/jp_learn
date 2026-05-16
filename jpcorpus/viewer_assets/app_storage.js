window.JPCORPUS_STORAGE = (() => {
  const STORAGE_LANG = "jpcorpus.viewer.lang";
  const STORAGE_STATUS = "jpcorpus.viewer.status.v1";
  const STORAGE_STUDY_COUNTS = "jpcorpus.viewer.studyCounts.v1";
  const STORAGE_STUDY_SESSION = "jpcorpus.viewer.studySession.v2";
  const STORAGE_STUDY_SCHEDULE = "jpcorpus.viewer.studySchedule.v1";
  const STORAGE_EXAMPLE_COLUMNS = "jpcorpus.viewer.exampleColumns.v1";
  const STORAGE_MODE = "jpcorpus.viewer.mode.v1";
  const STORAGE_SPLIT_RATIOS = "jpcorpus.viewer.splitRatios.v1";
  const STORAGE_READER_WORD_LIST = "jpcorpus.viewer.readerWordList.v1";
  const STORAGE_READER_FURIGANA = "jpcorpus.viewer.readerFurigana.v1";
  const STORAGE_READER_POSITIONS = "jpcorpus.viewer.readerPositions.v1";
  const STORAGE_TTS_PROVIDER = "jpcorpus.viewer.ttsProvider.v1";
  const STORAGE_TTS_BROWSER_VOICE = "jpcorpus.viewer.ttsBrowserVoice.v1";
  const STORAGE_TTS_VOICEVOX_SPEAKER = "jpcorpus.viewer.ttsVoicevoxSpeaker.v1";
  const STORAGE_TTS_RATE = "jpcorpus.viewer.ttsRate.v1";

  const DAILY_STUDY_LIMIT = 30;
  const STUDY_REVIEW_DELAY_DAYS = 1;
  const STUDY_TARGET_COUNT = 7;
  const EXAMPLE_COLUMN_VALUES = new Set(["auto", "1", "2", "3"]);
  const MODE_VALUES = new Set(["browse", "study", "read"]);
  const READER_WORD_LIST_VALUES = new Set(["focus", "all", "study", "piece", "N5", "N4", "N3", "N2", "N1"]);
  const TTS_PROVIDER_VALUES = new Set(["browser", "voicevox"]);
  const SPLIT_DEFAULT_RATIOS = {
    browse: 0.28,
    study: 0.28,
    read: 0.72,
  };

  function readJsonObject(key) {
    try {
      const value = JSON.parse(localStorage.getItem(key) || "{}");
      return value && typeof value === "object" && !Array.isArray(value) ? value : {};
    } catch {
      return {};
    }
  }

  function clampStorageNumber(value, min, max) {
    const number = Number(value);
    if (!Number.isFinite(number)) {
      return min;
    }
    return Math.min(max, Math.max(min, number));
  }

  function clampStudyCount(value) {
    const count = Number.parseInt(value, 10);
    if (!Number.isFinite(count) || count <= 0) {
      return 0;
    }
    return Math.min(count, STUDY_TARGET_COUNT);
  }

  function readStatuses() {
    return readJsonObject(STORAGE_STATUS);
  }

  function readStudyCounts() {
    return Object.fromEntries(
      Object.entries(readJsonObject(STORAGE_STUDY_COUNTS))
        .map(([word, count]) => [word, clampStudyCount(count)])
        .filter(([, count]) => count > 0),
    );
  }

  function todayKey(date = new Date()) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function addDaysKey(dateKey, days) {
    const [year, month, day] = String(dateKey || todayKey()).split("-").map((part) => Number.parseInt(part, 10));
    const date = Number.isFinite(year) && Number.isFinite(month) && Number.isFinite(day)
      ? new Date(year, month - 1, day)
      : new Date();
    date.setDate(date.getDate() + days);
    return todayKey(date);
  }

  function readStudySession() {
    const value = readJsonObject(STORAGE_STUDY_SESSION);
    const date = typeof value.date === "string" ? value.date : todayKey();
    const words = Array.isArray(value.words)
      ? value.words
        .map((word) => String(word || "").trim())
        .filter(Boolean)
        .slice(0, DAILY_STUDY_LIMIT)
      : [];
    return { date, words };
  }

  function readStudySchedule() {
    return Object.fromEntries(
      Object.entries(readJsonObject(STORAGE_STUDY_SCHEDULE))
        .map(([word, schedule]) => {
          const lastSeen = typeof schedule?.last_seen === "string" ? schedule.last_seen : "";
          const dueDate = typeof schedule?.due_date === "string" ? schedule.due_date : todayKey();
          return [word, { last_seen: lastSeen, due_date: dueDate }];
        })
        .filter(([word]) => word),
    );
  }

  function readExampleColumns() {
    const value = localStorage.getItem(STORAGE_EXAMPLE_COLUMNS) || "auto";
    return EXAMPLE_COLUMN_VALUES.has(value) ? value : "auto";
  }

  function readSplitRatios() {
    const value = readJsonObject(STORAGE_SPLIT_RATIOS);
    return Object.fromEntries(
      [...MODE_VALUES].map((mode) => {
        const ratio = Number(value[mode]);
        const fallback = SPLIT_DEFAULT_RATIOS[mode] ?? 0.3;
        return [mode, Number.isFinite(ratio) ? clampStorageNumber(ratio, 0.15, 0.85) : fallback];
      }),
    );
  }

  function readMode() {
    const value = localStorage.getItem(STORAGE_MODE) || "browse";
    return MODE_VALUES.has(value) ? value : "browse";
  }

  function readReaderWordList() {
    const value = localStorage.getItem(STORAGE_READER_WORD_LIST) || "focus";
    return READER_WORD_LIST_VALUES.has(value) ? value : "focus";
  }

  function readReaderFurigana() {
    return localStorage.getItem(STORAGE_READER_FURIGANA) === "on";
  }

  function readReaderPositions() {
    return Object.fromEntries(
      Object.entries(readJsonObject(STORAGE_READER_POSITIONS))
        .map(([key, entry]) => {
          const scrollTop = Math.max(0, Math.round(Number(entry?.scrollTop) || 0));
          const progress = Math.min(100, Math.max(0, Math.round(Number(entry?.progress) || 0)));
          const updatedAt = Math.max(0, Math.round(Number(entry?.updatedAt) || 0));
          return [key, { scrollTop, progress, updatedAt }];
        })
        .filter(([key]) => key),
    );
  }

  function readTtsProvider() {
    const value = localStorage.getItem(STORAGE_TTS_PROVIDER) || "browser";
    return TTS_PROVIDER_VALUES.has(value) ? value : "browser";
  }

  function readTtsBrowserVoice() {
    return localStorage.getItem(STORAGE_TTS_BROWSER_VOICE) || "";
  }

  function readTtsVoicevoxSpeaker() {
    const value = localStorage.getItem(STORAGE_TTS_VOICEVOX_SPEAKER) || "";
    return /^\d+$/.test(value) ? value : "";
  }

  function readTtsRate() {
    return clampStorageNumber(Number(localStorage.getItem(STORAGE_TTS_RATE) || "1"), 0.6, 1.4);
  }

  return {
    STORAGE_LANG,
    STORAGE_STATUS,
    STORAGE_STUDY_COUNTS,
    STORAGE_STUDY_SESSION,
    STORAGE_STUDY_SCHEDULE,
    STORAGE_EXAMPLE_COLUMNS,
    STORAGE_MODE,
    STORAGE_SPLIT_RATIOS,
    STORAGE_READER_WORD_LIST,
    STORAGE_READER_FURIGANA,
    STORAGE_READER_POSITIONS,
    STORAGE_TTS_PROVIDER,
    STORAGE_TTS_BROWSER_VOICE,
    STORAGE_TTS_VOICEVOX_SPEAKER,
    STORAGE_TTS_RATE,
    DAILY_STUDY_LIMIT,
    STUDY_REVIEW_DELAY_DAYS,
    STUDY_TARGET_COUNT,
    EXAMPLE_COLUMN_VALUES,
    MODE_VALUES,
    READER_WORD_LIST_VALUES,
    TTS_PROVIDER_VALUES,
    SPLIT_DEFAULT_RATIOS,
    readStatuses,
    readStudyCounts,
    todayKey,
    addDaysKey,
    readStudySession,
    readStudySchedule,
    readExampleColumns,
    readSplitRatios,
    readMode,
    readReaderWordList,
    readReaderFurigana,
    readReaderPositions,
    readTtsProvider,
    readTtsBrowserVoice,
    readTtsVoicevoxSpeaker,
    readTtsRate,
    clampStudyCount,
  };
})();
