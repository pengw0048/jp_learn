window.JPCORPUS_TTS = (() => {
  function createTtsHelpers({
    api,
    app,
    el,
    refs,
    storage,
    t,
  }) {
    const {
      STORAGE_TTS_PROVIDER,
      STORAGE_TTS_BROWSER_VOICE,
      STORAGE_TTS_VOICEVOX_SPEAKER,
      STORAGE_TTS_RATE,
    } = storage;
    let activeAudio = null;
    let activeAudioUrl = "";

    function bindTtsSettings() {
      if (!refs.ttsProviderButtons?.length) {
        return;
      }
      refs.ttsProviderButtons.forEach((button) => {
        button.addEventListener("click", () => setTtsProvider(button.dataset.ttsProvider));
      });
      refs.ttsBrowserVoice?.addEventListener("change", (event) => {
        app.tts.browserVoice = event.target.value;
        localStorage.setItem(STORAGE_TTS_BROWSER_VOICE, app.tts.browserVoice);
      });
      refs.ttsVoicevoxSpeaker.addEventListener("change", (event) => {
        app.tts.voicevoxSpeaker = event.target.value;
        localStorage.setItem(STORAGE_TTS_VOICEVOX_SPEAKER, app.tts.voicevoxSpeaker);
      });
      refs.ttsRate?.addEventListener("input", (event) => {
        app.tts.rate = clampTtsRate(event.target.value);
        localStorage.setItem(STORAGE_TTS_RATE, String(app.tts.rate));
        renderTtsRate();
      });
      refs.ttsPreview?.addEventListener("click", () => playFromButton(refs.ttsPreview, () => t("ttsPreviewSample")));
      if ("speechSynthesis" in window) {
        if (typeof window.speechSynthesis.addEventListener === "function") {
          window.speechSynthesis.addEventListener("voiceschanged", loadBrowserVoices);
        } else {
          window.speechSynthesis.onvoiceschanged = loadBrowserVoices;
        }
      }
      loadBrowserVoices();
      renderTtsSettings();
      loadVoicevoxSpeakers();
    }

    function renderTtsSettings() {
      if (!refs.ttsProviderButtons?.length || !refs.ttsVoicevoxSpeaker || !refs.ttsStatus) {
        return;
      }
      refs.ttsProviderButtons.forEach((button) => {
        const active = button.dataset.ttsProvider === app.tts.provider;
        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", active ? "true" : "false");
      });
      renderBrowserVoices();
      renderVoicevoxSpeakers();
      renderTtsRate();
      refs.ttsStatus.textContent = ttsStatusText();
      if (!refs.ttsPreview.classList.contains("tts-loading")) {
        refs.ttsPreview.disabled = !canPreviewTts();
      }
    }

    function renderBrowserVoices() {
      if (!refs.ttsBrowserVoice) {
        return;
      }
      refs.ttsBrowserVoiceField.hidden = app.tts.provider !== "browser";
      const voices = Array.isArray(app.tts.browserVoices) ? app.tts.browserVoices : [];
      if (!voices.some((voice) => voice.key === app.tts.browserVoice)) {
        app.tts.browserVoice = preferredBrowserVoice(voices)?.key || "";
      }
      refs.ttsBrowserVoice.replaceChildren(
        ...(
          voices.length > 0
            ? voices.map((voice) => {
              const option = el("option", "", voice.label);
              option.value = voice.key;
              option.selected = voice.key === app.tts.browserVoice;
              return option;
            })
            : [el("option", "", t("ttsBrowserNoVoices"))]
        ),
      );
      refs.ttsBrowserVoice.disabled = app.tts.provider !== "browser" || voices.length === 0;
    }

    function renderVoicevoxSpeakers() {
      refs.ttsVoicevoxSpeakerField.hidden = app.tts.provider !== "voicevox";
      const speakers = Array.isArray(app.tts.voicevoxSpeakers) ? app.tts.voicevoxSpeakers : [];
      if (!speakers.some((speaker) => String(speaker.id) === String(app.tts.voicevoxSpeaker))) {
        app.tts.voicevoxSpeaker = speakers[0] ? String(speakers[0].id) : "";
      }
      refs.ttsVoicevoxSpeaker.replaceChildren(
        ...(
          speakers.length > 0
            ? speakers.map((speaker) => {
              const option = el("option", "", speaker.label || String(speaker.id));
              option.value = String(speaker.id);
              option.selected = String(speaker.id) === String(app.tts.voicevoxSpeaker);
              return option;
            })
            : [el("option", "", t("ttsVoicevoxNoSpeakers"))]
        ),
      );
      refs.ttsVoicevoxSpeaker.disabled = app.tts.provider !== "voicevox" || speakers.length === 0;
    }

    function renderTtsRate() {
      if (!refs.ttsRate || !refs.ttsRateValue) {
        return;
      }
      app.tts.rate = clampTtsRate(app.tts.rate);
      refs.ttsRate.value = String(app.tts.rate);
      refs.ttsRateValue.textContent = `${app.tts.rate.toFixed(2)}x`;
    }

    function ttsStatusText() {
      if (app.tts.provider === "browser") {
        if (!("speechSynthesis" in window)) {
          return t("ttsBrowserUnavailable");
        }
        const voiceCount = Array.isArray(app.tts.browserVoices) ? app.tts.browserVoices.length : 0;
        return voiceCount > 0
          ? t("ttsBrowserReady", { count: String(voiceCount) })
          : t("ttsBrowserNoVoices");
      }
      if (app.tts.loading) {
        return t("ttsVoicevoxChecking");
      }
      if (app.tts.error) {
        return t("ttsVoicevoxFallback");
      }
      const speakerCount = Array.isArray(app.tts.voicevoxSpeakers) ? app.tts.voicevoxSpeakers.length : 0;
      if (speakerCount > 0) {
        return t("ttsVoicevoxReady", { count: String(speakerCount) });
      }
      return t("ttsVoicevoxUnavailable");
    }

    function setTtsProvider(provider) {
      app.tts.provider = provider === "voicevox" ? "voicevox" : "browser";
      app.tts.error = "";
      localStorage.setItem(STORAGE_TTS_PROVIDER, app.tts.provider);
      renderTtsSettings();
      if (app.tts.provider === "voicevox") {
        loadVoicevoxSpeakers();
      }
    }

    function loadBrowserVoices() {
      if (!("speechSynthesis" in window)) {
        app.tts.browserVoices = [];
        renderTtsSettings();
        return;
      }
      app.tts.browserVoices = window.speechSynthesis.getVoices()
        .filter((voice) => /^ja\b/i.test(voice.lang || ""))
        .map((voice) => ({
          key: browserVoiceKey(voice),
          label: `${voice.name} (${voice.lang})`,
        }))
        .sort(compareBrowserVoices);
      renderTtsSettings();
    }

    async function loadVoicevoxSpeakers() {
      if (app.tts.loading) {
        return;
      }
      app.tts.loading = true;
      app.tts.error = "";
      renderTtsSettings();
      try {
        const payload = await api.voicevoxSpeakers();
        app.tts.voicevoxSpeakers = Array.isArray(payload.speakers) ? payload.speakers : [];
      } catch (error) {
        app.tts.voicevoxSpeakers = [];
        app.tts.error = error.message || String(error);
      } finally {
        app.tts.loading = false;
        renderTtsSettings();
      }
    }

    function renderSpeakButton(textValue, className = "tts-button") {
      const button = el("button", className, "▶");
      button.type = "button";
      button.title = t("ttsPlay");
      button.setAttribute("aria-label", button.title);
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        playFromButton(button, textValue);
      });
      return button;
    }

    async function playFromButton(button, textValue) {
      if (button.classList.contains("tts-loading")) {
        return;
      }
      const value = typeof textValue === "function" ? textValue() : textValue;
      const text = normalizeSpeechText(value);
      if (!text) {
        return;
      }
      setButtonLoading(button, true);
      try {
        await speakText(text);
      } finally {
        setButtonLoading(button, false);
      }
    }

    async function speakText(value) {
      const text = normalizeSpeechText(value);
      if (!text) {
        return;
      }
      if (app.tts.provider === "voicevox") {
        const ok = await speakVoicevox(text);
        if (ok) {
          return;
        }
      }
      speakBrowser(text);
    }

    async function speakVoicevox(text) {
      try {
        stopActiveAudio();
        const blob = await api.voicevoxSynthesize({
          text,
          speaker: app.tts.voicevoxSpeaker,
          rate: app.tts.rate,
        });
        activeAudioUrl = URL.createObjectURL(blob);
        activeAudio = new Audio(activeAudioUrl);
        activeAudio.addEventListener("ended", stopActiveAudio, { once: true });
        activeAudio.addEventListener("error", stopActiveAudio, { once: true });
        await activeAudio.play();
        app.tts.error = "";
        renderTtsSettings();
        return true;
      } catch (error) {
        stopActiveAudio();
        app.tts.error = error.message || String(error);
        renderTtsSettings();
        return false;
      }
    }

    function setButtonLoading(button, loading) {
      button.classList.toggle("tts-loading", loading);
      button.disabled = loading || (!button.classList.contains("tts-button") && !canPreviewTts());
      button.setAttribute("aria-busy", loading ? "true" : "false");
      if (loading) {
        button.dataset.originalTitle = button.title || "";
        button.dataset.originalAriaLabel = button.getAttribute("aria-label") || "";
        button.title = t("ttsLoading");
        button.setAttribute("aria-label", t("ttsLoading"));
        return;
      }
      if (button.dataset.originalTitle) {
        button.title = button.dataset.originalTitle;
      } else {
        button.removeAttribute("title");
      }
      if (button.dataset.originalAriaLabel) {
        button.setAttribute("aria-label", button.dataset.originalAriaLabel);
      } else {
        button.removeAttribute("aria-label");
      }
      delete button.dataset.originalTitle;
      delete button.dataset.originalAriaLabel;
    }

    function speakBrowser(text) {
      if (!("speechSynthesis" in window) || typeof SpeechSynthesisUtterance === "undefined") {
        app.tts.error = t("ttsBrowserUnavailable");
        renderTtsSettings();
        return;
      }
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "ja-JP";
      utterance.rate = app.tts.rate;
      const voice = selectedBrowserVoice(window.speechSynthesis.getVoices())
        || preferredJapaneseVoice(window.speechSynthesis.getVoices());
      if (voice) {
        utterance.voice = voice;
      }
      window.speechSynthesis.speak(utterance);
    }

    function selectedBrowserVoice(voices) {
      const list = Array.isArray(voices) ? voices : [];
      return list.find((voice) => browserVoiceKey(voice) === app.tts.browserVoice) || null;
    }

    function preferredJapaneseVoice(voices) {
      const list = Array.isArray(voices) ? voices : [];
      return list.find((voice) => /^ja\b/i.test(voice.lang || "") && /google/i.test(voice.name || ""))
        || list.find((voice) => /^ja\b/i.test(voice.lang || ""))
        || null;
    }

    function preferredBrowserVoice(voices) {
      const list = Array.isArray(voices) ? voices : [];
      return list.find((voice) => /google/i.test(voice.label || "")) || list[0] || null;
    }

    function compareBrowserVoices(left, right) {
      const leftRank = /google/i.test(left.label) ? 0 : 1;
      const rightRank = /google/i.test(right.label) ? 0 : 1;
      return leftRank - rightRank || left.label.localeCompare(right.label);
    }

    function browserVoiceKey(voice) {
      return [voice.voiceURI || "", voice.name || "", voice.lang || ""].join("::");
    }

    function canPreviewTts() {
      if (app.tts.provider === "voicevox") {
        return Array.isArray(app.tts.voicevoxSpeakers) && app.tts.voicevoxSpeakers.length > 0;
      }
      return "speechSynthesis" in window;
    }

    function stopActiveAudio() {
      if (activeAudio) {
        activeAudio.pause();
        activeAudio = null;
      }
      if (activeAudioUrl) {
        URL.revokeObjectURL(activeAudioUrl);
        activeAudioUrl = "";
      }
    }

    function speechTextForWord(word) {
      const reading = String(word?.reading || "").split(/[;；,、]/)[0].trim();
      return reading || word?.word || "";
    }

    function normalizeSpeechText(value) {
      return String(value || "").replace(/\s+/g, " ").trim();
    }

    function clampTtsRate(value) {
      const rate = Number(value);
      if (!Number.isFinite(rate)) {
        return 1;
      }
      const stepped = Math.round(rate / 0.05) * 0.05;
      return Number(Math.min(1.4, Math.max(0.6, stepped)).toFixed(2));
    }

    return {
      bindTtsSettings,
      renderSpeakButton,
      renderTtsSettings,
      speechTextForWord,
    };
  }

  return { createTtsHelpers };
})();
