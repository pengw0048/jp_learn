window.JPCORPUS_MAINTENANCE = (() => {
  function createMaintenanceHelpers({
    app,
    formatNumber,
    refs,
    t,
  }) {
    function maintenanceTask() {
      return app.maintenance.task || "sync_media";
    }

    function maintenanceJobSpec(task = maintenanceTask()) {
      return {
        type: task,
      };
    }

    function maintenanceTaskLabel(task) {
      const key = {
        sync_media: "taskSyncMedia",
        export_corpus: "taskExportCorpus",
        refresh_imported_texts: "taskRefreshImportedTexts",
        fetch_lexical_resources: "taskFetchLexicalResources",
        refresh_all: "taskRefreshAll",
      }[task];
      return key ? t(key) : task || t("maintenance");
    }

    function maintenanceStatusLabel(job) {
      const task = maintenanceTaskLabel(job.kind || job.spec?.type || maintenanceTask());
      const time = formatJobTime(job.finished_at || job.started_at);
      if (job.status === "running") {
        return t("maintenanceRunningTask", { task, time });
      }
      if (job.status === "succeeded") {
        let reload = "";
        if (job.result?.reload_corpus) {
          reload = app.maintenance.reloadedJobId === job.id
            ? t("maintenanceReloaded")
            : t("maintenanceReloadPending");
        }
        return t("maintenanceSucceededTask", {
          task,
          reload,
          time,
        });
      }
      if (job.status === "failed") {
        return t("maintenanceFailedTask", { task, time });
      }
      return t("maintenanceIdle");
    }

    function renderMaintenanceProgress(job) {
      const progress = job?.progress || null;
      if (!progress || !refs.maintenanceProgress) {
        refs.maintenanceProgress.hidden = true;
        return;
      }
      const total = Number(progress.total || 0);
      const completed = Number(progress.completed || 0);
      const percent = Number.isFinite(Number(progress.percent))
        ? Number(progress.percent)
        : total > 0
          ? (completed / total) * 100
          : 0;
      const boundedPercent = Math.max(0, Math.min(100, percent));
      refs.maintenanceProgress.hidden = false;
      refs.maintenanceProgressFill.style.width = `${boundedPercent}%`;
      refs.maintenanceProgress.querySelector("[role='progressbar']").setAttribute(
        "aria-valuenow",
        String(Math.round(boundedPercent)),
      );
      refs.maintenanceProgressLabel.textContent = maintenanceProgressLabel(progress);
    }

    function maintenanceProgressLabel(progress) {
      const phase = progress.phase || "";
      const completed = formatNumber(progress.completed || 0);
      const total = formatNumber(progress.total || 0);
      if (phase === "steps" || phase === "export") {
        return t("maintenanceProgressSteps", {
          completed,
          total,
          step: progress.current_step || maintenanceTaskLabel(maintenanceTask()),
        });
      }
      return t("maintenanceProgressGeneric", { completed, total });
    }

    function formatJobTime(value) {
      if (!value) {
        return "--";
      }
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) {
        return "--";
      }
      return date.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    }

    return {
      maintenanceJobSpec,
      maintenanceStatusLabel,
      maintenanceTask,
      renderMaintenanceProgress,
    };
  }

  return {
    createMaintenanceHelpers,
  };
})();
