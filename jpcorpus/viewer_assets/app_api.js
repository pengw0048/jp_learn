window.JPCORPUS_API = (() => {
  async function jsonFromResponse(response) {
    let payload = {};
    try {
      payload = await response.json();
    } catch {
      payload = {};
    }
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    return payload;
  }

  async function fetchJson(url, options = {}) {
    return jsonFromResponse(await fetch(url, options));
  }

  function postJson(url, payload) {
    return fetchJson(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  async function postBlob(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      let message = `HTTP ${response.status}`;
      try {
        const error = await response.json();
        message = error.error || message;
      } catch {
        const text = await response.text();
        message = text || message;
      }
      throw new Error(message);
    }
    return response.blob();
  }

  async function loadCorpusIndex() {
    const indexResponse = await fetch("/corpus.index.json", { cache: "no-store" });
    if (indexResponse.ok) {
      return indexResponse.json();
    }
    return fetchJson("/corpus.json", { cache: "no-store" });
  }

  function loadMaintenanceStatus() {
    return fetchJson("/api/maintenance", { cache: "no-store" });
  }

  function loadDictionaries() {
    return fetchJson("/api/dictionaries", { cache: "no-store" });
  }

  function deleteImportedText(sourceFiles) {
    return postJson("/api/delete-imported-text", { source_files: sourceFiles });
  }

  function loadWordDetail(word) {
    return fetchJson(`/api/word-detail?word=${encodeURIComponent(word)}`, { cache: "no-store" });
  }

  function loadSourceDetails(keys) {
    const params = new URLSearchParams();
    keys.forEach((key) => params.append("key", key));
    return fetchJson(`/api/source-detail?${params.toString()}`, { cache: "no-store" });
  }

  function saveConfig(payload) {
    return postJson("/api/config", payload);
  }

  function explain(payload) {
    return postJson("/api/explain", payload);
  }

  function startMaintenanceJob(spec) {
    return postJson("/api/jobs/maintenance", spec);
  }

  function importDictionary({ file, name }) {
    const form = new FormData();
    form.append("file", file);
    if (name) {
      form.append("name", name);
    }
    return fetchJson("/api/dictionaries/import", {
      method: "POST",
      body: form,
    });
  }

  function updateDictionary(payload) {
    return postJson("/api/dictionaries/update", payload);
  }

  function deleteDictionary(payload) {
    return postJson("/api/dictionaries/delete", payload);
  }

  function reindexDictionary(payload) {
    return postJson("/api/dictionaries/reindex", payload);
  }

  function currentJob() {
    return fetchJson("/api/jobs/current", { cache: "no-store" });
  }

  async function studyState() {
    const response = await fetch("/api/study-state", { cache: "no-store" });
    return response.ok ? response.json() : null;
  }

  function saveWordStatus(payload) {
    return postJson("/api/word-status", payload);
  }

  function voicevoxSpeakers() {
    return fetchJson("/api/tts/voicevox-speakers", { cache: "no-store" });
  }

  function voicevoxSynthesize(payload) {
    return postBlob("/api/tts/voicevox", payload);
  }

  return {
    loadCorpusIndex,
    loadMaintenanceStatus,
    loadDictionaries,
    deleteImportedText,
    loadWordDetail,
    loadSourceDetails,
    saveConfig,
    explain,
    startMaintenanceJob,
    importDictionary,
    updateDictionary,
    deleteDictionary,
    reindexDictionary,
    currentJob,
    studyState,
    saveWordStatus,
    voicevoxSpeakers,
    voicevoxSynthesize,
  };
})();
