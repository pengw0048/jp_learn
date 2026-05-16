window.JPCORPUS_SYNC = (() => {
  function createCorpusSyncHelpers({
    api,
    app,
    refs,
    reloadCorpus,
    renderMaintenance,
    renderSourceInventory,
    shouldDeferCorpusReload,
    t,
  }) {
    let corpusNoticeTimer = null;

    function renderCorpusSyncBanner() {
      if (!refs.corpusSyncBanner) {
        return;
      }
      const job = app.maintenance.pendingReloadJob;
      const visible = Boolean(job) && app.maintenance.reloadedJobId !== job.id;
      const notice = String(app.maintenance.syncNotice || "");
      refs.corpusSyncBanner.hidden = !visible && !notice;
      refs.corpusSyncBanner.classList?.toggle("notice", !visible && Boolean(notice));
      refs.corpusSyncApply.hidden = !visible;
      if (!visible && !notice) {
        refs.corpusSyncMessage.textContent = "";
        refs.corpusSyncApply.disabled = false;
        return;
      }
      if (!visible) {
        refs.corpusSyncMessage.textContent = notice;
        refs.corpusSyncApply.disabled = false;
        return;
      }
      refs.corpusSyncApply.textContent = t("corpusUpdateApply");
      refs.corpusSyncApply.disabled = app.maintenance.syncApplying;
      if (app.maintenance.syncApplying) {
        refs.corpusSyncMessage.textContent = t("corpusUpdateApplying");
      } else if (app.maintenance.syncError) {
        refs.corpusSyncMessage.textContent = t("corpusUpdateFailed", { error: app.maintenance.syncError });
      } else {
        refs.corpusSyncMessage.textContent = t("corpusUpdateReady");
      }
    }

    function pollMaintenanceJob() {
      refreshMaintenanceJob();
      startMaintenanceStatusSync(1500);
    }

    function startMaintenanceStatusSync(intervalMs) {
      if (!app.maintenance.enabled) {
        return;
      }
      if (app.maintenance.pollTimer && app.maintenance.pollIntervalMs === intervalMs) {
        return;
      }
      if (app.maintenance.pollTimer) {
        clearInterval(app.maintenance.pollTimer);
      }
      app.maintenance.pollIntervalMs = intervalMs;
      app.maintenance.pollTimer = setInterval(() => {
        refreshMaintenanceJob({ quiet: true });
      }, intervalMs);
    }

    async function refreshMaintenanceJob({ quiet = false } = {}) {
      if (!app.maintenance.enabled || app.maintenance.pollInFlight) {
        return;
      }
      app.maintenance.pollInFlight = true;
      try {
        const payload = await api.currentJob();
        app.maintenance.job = payload.job || null;
        renderMaintenance();
        const job = app.maintenance.job;
        if (!job || job.status === "running") {
          startMaintenanceStatusSync(job?.status === "running" ? 1500 : 6000);
          return;
        }
        startMaintenanceStatusSync(6000);
        const clearsSourceNotice = app.sourceInventoryNoticeJobId === job.id;
        if (job.status === "succeeded" && job.result?.reload_corpus && app.maintenance.reloadedJobId !== job.id) {
          await handleCorpusReloadJob(job);
        }
        if (clearsSourceNotice) {
          app.sourceInventoryBusy = false;
          app.sourceInventoryNoticeJobId = null;
          app.sourceInventoryNotice = job.status === "succeeded"
            ? ""
            : t("sourceInventoryDeleteFailed", { error: job.error || job.log?.at(-1) || "rebuild failed" });
          renderSourceInventory();
        }
      } catch (error) {
        if (!quiet) {
          app.maintenance.job = {
            status: "failed",
            log: [String(error.message || error)],
          };
          if (app.sourceInventoryBusy) {
            app.sourceInventoryBusy = false;
            app.sourceInventoryNoticeJobId = null;
            app.sourceInventoryNotice = t("sourceInventoryDeleteFailed", { error: error.message || String(error) });
          }
          renderMaintenance();
          renderSourceInventory();
        }
      } finally {
        app.maintenance.pollInFlight = false;
        renderCorpusSyncBanner();
      }
    }

    async function handleCorpusReloadJob(job) {
      if (app.maintenance.reloadedJobId === job.id || app.maintenance.pendingReloadJob?.id === job.id) {
        return;
      }
      if (shouldDeferCorpusReload()) {
        app.maintenance.pendingReloadJob = job;
        app.maintenance.syncError = "";
        renderMaintenance();
        renderCorpusSyncBanner();
        return;
      }
      await applyCorpusReload(job);
    }

    async function applyPendingCorpusReload() {
      if (!app.maintenance.pendingReloadJob || app.maintenance.syncApplying) {
        return;
      }
      await applyCorpusReload(app.maintenance.pendingReloadJob);
    }

    async function applyCorpusReload(job) {
      app.maintenance.syncApplying = true;
      app.maintenance.syncError = "";
      renderCorpusSyncBanner();
      try {
        app.maintenance.reloadedJobId = job.id;
        app.maintenance.pendingReloadJob = null;
        await reloadCorpus();
        showCorpusNotice(corpusNoticeLabel(job));
      } catch (error) {
        app.maintenance.reloadedJobId = null;
        app.maintenance.pendingReloadJob = job;
        app.maintenance.syncError = error.message || String(error);
      } finally {
        app.maintenance.syncApplying = false;
        renderMaintenance();
        renderCorpusSyncBanner();
      }
    }

    function showCorpusNotice(message) {
      if (!message) {
        return;
      }
      app.maintenance.syncNotice = message;
      if (corpusNoticeTimer) {
        clearTimeout(corpusNoticeTimer);
      }
      corpusNoticeTimer = setTimeout(() => {
        app.maintenance.syncNotice = "";
        corpusNoticeTimer = null;
        renderCorpusSyncBanner();
      }, 4200);
      corpusNoticeTimer.unref?.();
    }

    function corpusNoticeLabel(job) {
      return (job.kind || job.spec?.type) === "refresh_imported_texts"
        ? t("corpusUpdateImported")
        : t("corpusUpdateApplied");
    }

    return {
      applyPendingCorpusReload,
      pollMaintenanceJob,
      refreshMaintenanceJob,
      renderCorpusSyncBanner,
      startMaintenanceStatusSync,
    };
  }

  return { createCorpusSyncHelpers };
})();
