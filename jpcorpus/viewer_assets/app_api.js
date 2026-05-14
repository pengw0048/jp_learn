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

  function importText(payload) {
    return postJson("/api/import-text", payload);
  }

  function explain(payload) {
    return postJson("/api/explain", payload);
  }

  function startMaintenanceJob(spec) {
    return postJson("/api/jobs/maintenance", spec);
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

  return {
    loadCorpusIndex,
    loadMaintenanceStatus,
    deleteImportedText,
    loadWordDetail,
    loadSourceDetails,
    saveConfig,
    importText,
    explain,
    startMaintenanceJob,
    currentJob,
    studyState,
    saveWordStatus,
  };
})();
