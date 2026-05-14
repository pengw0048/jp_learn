window.JPCORPUS_LAYOUT = (() => {
  const SPLIT_LIMITS = {
    browse: { minLeft: 300, minRight: 420 },
    study: { minLeft: 300, minRight: 420 },
    read: { minLeft: 420, minRight: 340 },
  };

  function createLayoutHelpers({
    app,
    clampNumber,
    refs,
    storage,
  }) {
    const {
      SPLIT_DEFAULT_RATIOS,
      STORAGE_SPLIT_RATIOS,
    } = storage;

    function updateWorkspaceMode() {
      const reading = app.mode === "read";
      refs.workspace.classList.toggle("reader-workspace", reading);
      refs.sidebar.classList.toggle("reader-sidebar", reading);
      applyWorkspaceSplit();
    }

    function bindSplitResizer() {
      if (!refs.splitResizer) {
        return;
      }
      refs.splitResizer.addEventListener("pointerdown", (event) => {
        if (window.matchMedia("(max-width: 860px)").matches) {
          return;
        }
        event.preventDefault();
        refs.splitResizer.setPointerCapture(event.pointerId);
        refs.workspace.classList.add("resizing");
        updateWorkspaceSplitFromPointer(event.clientX);
      });
      refs.splitResizer.addEventListener("pointermove", (event) => {
        if (!refs.workspace.classList.contains("resizing")) {
          return;
        }
        updateWorkspaceSplitFromPointer(event.clientX);
      });
      refs.splitResizer.addEventListener("pointerup", (event) => {
        finishSplitResize(event.pointerId);
      });
      refs.splitResizer.addEventListener("pointercancel", (event) => {
        finishSplitResize(event.pointerId);
      });
      refs.splitResizer.addEventListener("keydown", (event) => {
        if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
          return;
        }
        event.preventDefault();
        const ratio = splitRatioForMode();
        const step = event.shiftKey ? 0.08 : 0.03;
        let nextRatio = ratio;
        if (event.key === "ArrowLeft") {
          nextRatio -= step;
        } else if (event.key === "ArrowRight") {
          nextRatio += step;
        } else if (event.key === "Home") {
          nextRatio = 0.22;
        } else if (event.key === "End") {
          nextRatio = 0.78;
        }
        setSplitRatioForMode(nextRatio);
        applyWorkspaceSplit();
      });
    }

    function finishSplitResize(pointerId) {
      refs.workspace.classList.remove("resizing");
      if (refs.splitResizer?.hasPointerCapture(pointerId)) {
        refs.splitResizer.releasePointerCapture(pointerId);
      }
    }

    function updateWorkspaceSplitFromPointer(clientX) {
      const rect = refs.workspace.getBoundingClientRect();
      const availableWidth = splitAvailableWidth(rect.width);
      if (availableWidth <= 0) {
        return;
      }
      const leftWidth = clientX - rect.left;
      setSplitRatioForMode(leftWidth / availableWidth);
      applyWorkspaceSplit();
    }

    function applyWorkspaceSplit() {
      if (!refs.workspace || window.matchMedia("(max-width: 860px)").matches) {
        return;
      }
      const availableWidth = splitAvailableWidth(refs.workspace.getBoundingClientRect().width);
      if (availableWidth <= 0) {
        return;
      }
      const ratio = clampedSplitRatio(splitRatioForMode(), availableWidth);
      const leftWidth = Math.round(ratio * availableWidth);
      refs.workspace.style.setProperty("--split-left-width", `${leftWidth}px`);
      refs.splitResizer?.setAttribute("aria-valuenow", String(Math.round(ratio * 100)));
      setSplitRatioForMode(ratio, { persist: false });
    }

    function splitAvailableWidth(totalWidth) {
      const resizerWidth = refs.splitResizer?.offsetWidth || 9;
      return Math.max(totalWidth - resizerWidth, 1);
    }

    function splitRatioForMode() {
      return app.splitRatios[app.mode] ?? SPLIT_DEFAULT_RATIOS[app.mode] ?? 0.3;
    }

    function setSplitRatioForMode(ratio, options = {}) {
      const persist = options.persist ?? true;
      const availableWidth = splitAvailableWidth(refs.workspace.getBoundingClientRect().width);
      const nextRatio = clampedSplitRatio(ratio, availableWidth);
      app.splitRatios = {
        ...app.splitRatios,
        [app.mode]: nextRatio,
      };
      if (persist) {
        localStorage.setItem(STORAGE_SPLIT_RATIOS, JSON.stringify(app.splitRatios));
      }
    }

    function clampedSplitRatio(ratio, availableWidth) {
      const limits = SPLIT_LIMITS[app.mode] || SPLIT_LIMITS.browse;
      const minRatio = Math.min(limits.minLeft / availableWidth, 0.82);
      const maxRatio = Math.max(1 - limits.minRight / availableWidth, minRatio);
      return clampNumber(Number(ratio), minRatio, maxRatio);
    }

    return {
      applyWorkspaceSplit,
      bindSplitResizer,
      updateWorkspaceMode,
    };
  }

  return { createLayoutHelpers };
})();
