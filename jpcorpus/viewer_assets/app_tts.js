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
      STORAGE_TTS_VOICEVOX_SPEAKER,
    } = storage;
    let activeAudio = null;
    let activeAudioUrl = "";

    function bindTtsSettings() {
      if (!refs.ttsProvider || !refs.ttsVoicevoxSpeaker) {
        return;
      }
      refs.ttsProvider.value = app.tts.provider;
      refs.ttsProvider.addEventListener("change", (event) => {
        app.tts.provider = event.target.value === "voicevox" ? "voicevox" : "browser";
        app.tts.error = "";
        localStorage.setItem(STORAGE_TTS_PROVIDER, app.tts.provider);
        renderTtsSettings();
        if (app.tts.provider === "voicevox") {
          loadVoicevoxSpeakers();
        }
      });
      refs.ttsVoicevoxSpeaker.addEventListener("change", (event) => {
        app.tts.voicevoxSpeaker = event.target.value;
        localStorage.setItem(STORAGE_TTS_VOICEVOX_SPEAKER, app.tts.voicevoxSpeaker);
      });
      renderTtsSettings();
      loadVoicevoxSpeakers();
    }

    function renderTtsSettings() {
      if (!refs.ttsProvider || !refs.ttsVoicevoxSpeaker || !refs.ttsStatus) {
        return;
      }
      refs.ttsProvider.value = app.tts.provider;
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
      refs.ttsStatus.textContent = ttsStatusText(speakers.length);
    }

    function ttsStatusText(speakerCount) {
      if (app.tts.provider === "browser") {
        return t("ttsBrowserHelp");
      }
      if (app.tts.loading) {
        return t("ttsVoicevoxChecking");
      }
      if (app.tts.error) {
        return t("ttsVoicevoxFallback");
      }
      if (speakerCount > 0) {
        return t("ttsVoicevoxReady", { count: String(speakerCount) });
      }
      return t("ttsVoicevoxUnavailable");
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
        const value = typeof textValue === "function" ? textValue() : textValue;
        speakText(value);
      });
      return button;
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

    function speakBrowser(text) {
      if (!("speechSynthesis" in window) || typeof SpeechSynthesisUtterance === "undefined") {
        app.tts.error = t("ttsBrowserUnavailable");
        renderTtsSettings();
        return;
      }
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "ja-JP";
      utterance.rate = 0.92;
      const voice = preferredJapaneseVoice(window.speechSynthesis.getVoices());
      if (voice) {
        utterance.voice = voice;
      }
      window.speechSynthesis.speak(utterance);
    }

    function preferredJapaneseVoice(voices) {
      const list = Array.isArray(voices) ? voices : [];
      return list.find((voice) => /^ja\b/i.test(voice.lang || "") && /google/i.test(voice.name || ""))
        || list.find((voice) => /^ja\b/i.test(voice.lang || ""))
        || null;
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

    return {
      bindTtsSettings,
      renderSpeakButton,
      renderTtsSettings,
      speechTextForWord,
    };
  }

  return { createTtsHelpers };
})();
