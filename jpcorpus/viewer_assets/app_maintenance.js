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

    function visibleMaintenanceJob(job) {
      if (!job) {
        return null;
      }
      if (job.status === "succeeded" && maintenanceJobKind(job) === "refresh_imported_texts") {
        return null;
      }
      return job;
    }

    function maintenanceStatusLabel(job) {
      const visibleJob = visibleMaintenanceJob(job);
      if (!visibleJob) {
        return t("maintenanceIdle");
      }
      const task = maintenanceTaskLabel(maintenanceJobKind(visibleJob));
      const time = formatJobTime(visibleJob.finished_at || visibleJob.started_at);
      if (visibleJob.status === "running") {
        return t("maintenanceRunningTask", { task, time });
      }
      if (visibleJob.status === "succeeded") {
        let reload = "";
        if (visibleJob.result?.reload_corpus) {
          reload = app.maintenance.reloadedJobId === visibleJob.id
            ? t("maintenanceReloaded")
            : t("maintenanceReloadPending");
        }
        return t("maintenanceSucceededTask", {
          task,
          reload,
          time,
        });
      }
      if (visibleJob.status === "failed") {
        return t("maintenanceFailedTask", { task, time });
      }
      return t("maintenanceIdle");
    }

    function maintenanceJobKind(job) {
      return job.kind || job.spec?.type || maintenanceTask();
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
      visibleMaintenanceJob,
    };
  }

  return {
    createMaintenanceHelpers,
  };
})();
