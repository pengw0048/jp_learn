window.JPCORPUS_STUDY = (() => {
  function createStudyHelpers({
    app,
    api,
    asArray,
    el,
    formatNumber,
    isActiveStudyStatus,
    storage,
    t,
  }) {
    const {
      STORAGE_STATUS,
      STORAGE_STUDY_COUNTS,
      STORAGE_STUDY_SESSION,
      STORAGE_STUDY_SCHEDULE,
      DAILY_STUDY_LIMIT,
      STUDY_REVIEW_DELAY_DAYS,
      STUDY_TARGET_COUNT,
      addDaysKey,
      clampStudyCount,
      todayKey,
    } = storage;
    let studySyncTimer = null;
    const pendingStudySyncWords = new Set();

    function statusFor(word) {
      const stored = app.statuses[word.word] || "none";
      if (stored === "ignored" || stored === "known" || isActiveStudyStatus(stored)) {
        return stored;
      }
      const count = studyCountFor(word);
      if (count >= STUDY_TARGET_COUNT) {
        return "known";
      }
      if (stored === "none" && count > 0) {
        return "learning";
      }
      return stored;
    }

    function setStatus(word, status) {
      if (status === "none") {
        delete app.statuses[word.word];
        setStudyCount(word, 0);
        clearStudySchedule(word);
      } else {
        app.statuses[word.word] = status;
        if (isActiveStudyStatus(status) && studyCountFor(word) >= STUDY_TARGET_COUNT) {
          setStudyCount(word, 0);
        }
        if (status === "known") {
          setStudyCount(word, STUDY_TARGET_COUNT);
        }
        if (status === "ignored") {
          setStudyCount(word, 0);
        }
        if (status === "known" || status === "ignored") {
          clearStudySchedule(word);
        }
      }
      localStorage.setItem(STORAGE_STATUS, JSON.stringify(app.statuses));
      queueStudyStateSync(word.word);
    }

    function studyCountFor(word) {
      return clampStudyCount(app.studyCounts[word.word] || 0);
    }

    function setStudyCount(word, count) {
      const normalized = clampStudyCount(count);
      if (normalized <= 0) {
        delete app.studyCounts[word.word];
      } else {
        app.studyCounts[word.word] = normalized;
      }
      localStorage.setItem(STORAGE_STUDY_COUNTS, JSON.stringify(app.studyCounts));
      queueStudyStateSync(word.word);
    }

    function studyDueDateFor(word) {
      const schedule = app.studySchedule[word.word] || {};
      return typeof schedule.due_date === "string" ? schedule.due_date : todayKey();
    }

    function scheduleStudyReview(word) {
      app.studySchedule[word.word] = {
        last_seen: todayKey(),
        due_date: addDaysKey(todayKey(), STUDY_REVIEW_DELAY_DAYS),
      };
      writeStudySchedule();
    }

    function clearStudySchedule(word) {
      if (!app.studySchedule[word.word]) {
        return;
      }
      delete app.studySchedule[word.word];
      writeStudySchedule();
    }

    function studyCheckLabel(word) {
      return t("studyChecks", {
        count: formatNumber(studyCountFor(word)),
        target: formatNumber(STUDY_TARGET_COUNT),
      });
    }

    function renderStudyCountBadge(word) {
      const count = studyCountFor(word);
      if (count <= 0 && app.mode !== "study") {
        return null;
      }
      const node = el("span", `study-count-badge ${count >= STUDY_TARGET_COUNT ? "mastered" : ""}`.trim());
      node.textContent = count >= STUDY_TARGET_COUNT ? t("studyMastered") : `${count}/${STUDY_TARGET_COUNT}`;
      node.title = studyCheckLabel(word);
      return node;
    }

    function writeStudySchedule() {
      localStorage.setItem(STORAGE_STUDY_SCHEDULE, JSON.stringify(app.studySchedule));
    }

    async function mergeRemoteStudyState() {
      try {
        const state = await api.studyState();
        if (!state) {
          return;
        }
        let changed = false;
        for (const [word, status] of Object.entries(normalizeRemoteStatusMap(state.statuses))) {
          const localStatus = app.statuses[word];
          if (!localStatus || localStatus === "none") {
            app.statuses[word] = status;
            changed = true;
          }
        }
        for (const [word, count] of Object.entries(normalizeRemoteStudyCounts(state.study_counts))) {
          const localCount = clampStudyCount(app.studyCounts[word] || 0);
          if (count > localCount) {
            app.studyCounts[word] = count;
            changed = true;
          }
        }
        for (const [word, schedule] of Object.entries(normalizeRemoteStudySchedule(state.study_schedule))) {
          if (!app.studySchedule[word]) {
            app.studySchedule[word] = schedule;
            changed = true;
          }
        }
        if (changed) {
          writeLocalStudyState();
        }
      } catch {
        // The viewer still works offline; web-extension study additions sync when the local API is available.
      }
    }

    function writeLocalStudyState() {
      localStorage.setItem(STORAGE_STATUS, JSON.stringify(app.statuses));
      localStorage.setItem(STORAGE_STUDY_COUNTS, JSON.stringify(app.studyCounts));
      localStorage.setItem(STORAGE_STUDY_SCHEDULE, JSON.stringify(app.studySchedule));
    }

    function queueStudyStateSync(word) {
      if (word) {
        pendingStudySyncWords.add(word);
      }
      window.clearTimeout(studySyncTimer);
      studySyncTimer = window.setTimeout(syncStudyStateToServer, 300);
    }

    async function syncStudyStateToServer() {
      const words = Array.from(pendingStudySyncWords);
      pendingStudySyncWords.clear();
      if (!words.length) {
        return;
      }
      try {
        await Promise.all(words.map((word) => api.saveWordStatus({
          word,
          status: statusFor({ word }),
          study_count: app.studyCounts[word] || 0,
          study_schedule: app.studySchedule[word] || null,
        })));
      } catch {
        words.forEach((word) => pendingStudySyncWords.add(word));
        // LocalStorage remains the primary viewer fallback if the API is unavailable.
      }
    }

    function normalizeRemoteStatusMap(value) {
      if (!value || typeof value !== "object") {
        return {};
      }
      return Object.fromEntries(
        Object.entries(value)
          .filter(([, status]) => ["learning", "uncertain", "known", "ignored"].includes(status)),
      );
    }

    function normalizeRemoteStudyCounts(value) {
      if (!value || typeof value !== "object") {
        return {};
      }
      return Object.fromEntries(
        Object.entries(value)
          .map(([word, count]) => [word, clampStudyCount(count)])
          .filter(([, count]) => count > 0),
      );
    }

    function normalizeRemoteStudySchedule(value) {
      if (!value || typeof value !== "object") {
        return {};
      }
      return Object.fromEntries(
        Object.entries(value)
          .map(([word, schedule]) => [
            word,
            {
              last_seen: typeof schedule?.last_seen === "string" ? schedule.last_seen : "",
              due_date: typeof schedule?.due_date === "string" ? schedule.due_date : todayKey(),
            },
          ])
          .filter(([word]) => word),
      );
    }

    function writeStudySession(session) {
      localStorage.setItem(STORAGE_STUDY_SESSION, JSON.stringify({
        date: session.date,
        words: asArray(session.words).slice(0, DAILY_STUDY_LIMIT),
      }));
    }

    function sameStudySession(left, right) {
      if (!left || !right || left.date !== right.date) {
        return false;
      }
      const leftWords = asArray(left.words);
      const rightWords = asArray(right.words);
      return leftWords.length === rightWords.length
        && leftWords.every((word, index) => word === rightWords[index]);
    }

    return {
      mergeRemoteStudyState,
      renderStudyCountBadge,
      sameStudySession,
      scheduleStudyReview,
      setStatus,
      setStudyCount,
      statusFor,
      studyCheckLabel,
      studyCountFor,
      studyDueDateFor,
      writeStudySession,
    };
  }

  return {
    createStudyHelpers,
  };
})();
