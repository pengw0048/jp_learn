from __future__ import annotations

import shutil
import subprocess
from html.parser import HTMLParser
from textwrap import dedent
from pathlib import Path

import pytest


VIEWER_ASSET_DIR = Path(__file__).resolve().parents[1] / "jpcorpus" / "viewer_assets"


class ScriptParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "script":
            return
        attrs_by_name = dict(attrs)
        src = attrs_by_name.get("src")
        if src:
            self.scripts.append(src)


def viewer_script_sources() -> list[str]:
    parser = ScriptParser()
    parser.feed((VIEWER_ASSET_DIR / "index.html").read_text(encoding="utf-8"))
    return parser.scripts


def test_viewer_index_references_existing_scripts_in_loader_order():
    sources = viewer_script_sources()

    assert sources[-1] == "/app.js"
    assert len(sources) == len(set(sources))
    assert "/app_storage.js" in sources
    assert "/app_i18n.js" in sources
    assert "/app_dom.js" in sources
    assert "/app_api.js" in sources
    assert "/app_detail.js" in sources

    app_index = sources.index("/app.js")
    for source in sources:
        assert source.startswith("/")
        script_path = VIEWER_ASSET_DIR / source.lstrip("/")
        assert script_path.is_file()
        if source != "/app.js":
            assert sources.index(source) < app_index


def test_viewer_javascript_files_parse_with_node():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")

    for script_path in sorted(VIEWER_ASSET_DIR.glob("*.js")):
        subprocess.run(
            [node, "--check", str(script_path)],
            check=True,
            capture_output=True,
            text=True,
        )


def test_corpus_sync_defers_reload_while_reading_and_applies_elsewhere():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")

    script = dedent(
        f"""
        const assert = require("node:assert/strict");
        global.window = {{}};
        global.setInterval = (callback, intervalMs) => ({{ callback, intervalMs }});
        global.clearInterval = () => {{}};
        require({str(VIEWER_ASSET_DIR / "app_sync.js")!r});

        function t(key, values = {{}}) {{
          if (values.error) {{
            return `${{key}}: ${{values.error}}`;
          }}
          return key;
        }}

        function makeRefs() {{
          return {{
            corpusSyncBanner: {{ hidden: true }},
            corpusSyncMessage: {{ textContent: "" }},
            corpusSyncApply: {{ disabled: false, textContent: "" }},
          }};
        }}

        async function runScenario(shouldDefer) {{
          const job = {{
            id: "job-1",
            status: "succeeded",
            result: {{ reload_corpus: true }},
            log: [],
            error: null,
          }};
          const app = {{
            maintenance: {{
              enabled: true,
              job: null,
              pollTimer: null,
              pollIntervalMs: null,
              pollInFlight: false,
              reloadedJobId: null,
              pendingReloadJob: null,
              syncApplying: false,
              syncError: "",
            }},
            sourceInventoryNoticeJobId: null,
            sourceInventoryBusy: false,
            sourceInventoryNotice: "",
          }};
          const refs = makeRefs();
          const calls = {{ reloads: 0, renders: 0, sourceRenders: 0 }};
          const helpers = window.JPCORPUS_SYNC.createCorpusSyncHelpers({{
            api: {{ currentJob: async () => ({{ job }}) }},
            app,
            refs,
            reloadCorpus: async () => {{ calls.reloads += 1; }},
            renderMaintenance: () => {{ calls.renders += 1; }},
            renderSourceInventory: () => {{ calls.sourceRenders += 1; }},
            shouldDeferCorpusReload: () => shouldDefer,
            t,
          }});
          await helpers.refreshMaintenanceJob();
          return {{ app, refs, calls, helpers }};
        }}

        (async () => {{
          const deferred = await runScenario(true);
          assert.equal(deferred.calls.reloads, 0);
          assert.equal(deferred.app.maintenance.pendingReloadJob.id, "job-1");
          assert.equal(deferred.app.maintenance.reloadedJobId, null);
          assert.equal(deferred.refs.corpusSyncBanner.hidden, false);
          assert.equal(deferred.refs.corpusSyncMessage.textContent, "corpusUpdateReady");

          await deferred.helpers.applyPendingCorpusReload();
          assert.equal(deferred.calls.reloads, 1);
          assert.equal(deferred.app.maintenance.pendingReloadJob, null);
          assert.equal(deferred.app.maintenance.reloadedJobId, "job-1");
          assert.equal(deferred.refs.corpusSyncBanner.hidden, true);

          const automatic = await runScenario(false);
          assert.equal(automatic.calls.reloads, 1);
          assert.equal(automatic.app.maintenance.pendingReloadJob, null);
          assert.equal(automatic.app.maintenance.reloadedJobId, "job-1");
          assert.equal(automatic.refs.corpusSyncBanner.hidden, true);
        }})().catch((error) => {{
          console.error(error);
          process.exit(1);
        }});
        """
    )
    subprocess.run([node, "-e", script], check=True, capture_output=True, text=True)


def test_maintenance_status_hides_successful_imported_text_refresh():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")

    script = dedent(
        f"""
        const assert = require("node:assert/strict");
        global.window = {{}};
        require({str(VIEWER_ASSET_DIR / "app_maintenance.js")!r});

        const helpers = window.JPCORPUS_MAINTENANCE.createMaintenanceHelpers({{
          app: {{ maintenance: {{ task: "sync_media", reloadedJobId: "job-1" }} }},
          formatNumber: (value) => String(value),
          refs: {{}},
          t: (key) => key,
        }});

        const succeededImportRefresh = {{
          id: "job-1",
          kind: "refresh_imported_texts",
          status: "succeeded",
          result: {{ reload_corpus: true }},
          finished_at: "2026-05-14T20:00:00Z",
        }};
        assert.equal(helpers.visibleMaintenanceJob(succeededImportRefresh), null);
        assert.equal(helpers.maintenanceStatusLabel(succeededImportRefresh), "maintenanceIdle");

        const failedImportRefresh = {{
          id: "job-2",
          kind: "refresh_imported_texts",
          status: "failed",
          finished_at: "2026-05-14T20:00:00Z",
        }};
        assert.equal(helpers.visibleMaintenanceJob(failedImportRefresh), failedImportRefresh);
        assert.equal(helpers.maintenanceStatusLabel(failedImportRefresh), "maintenanceFailedTask");
        """
    )
    subprocess.run([node, "-e", script], check=True, capture_output=True, text=True)
