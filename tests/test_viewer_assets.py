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
    assert "/app_config.js" in sources
    assert "/app_dom.js" in sources
    assert "/app_api.js" in sources
    assert "/app_tts.js" in sources
    assert "/app_detail.js" in sources

    app_index = sources.index("/app.js")
    for source in sources:
        assert source.startswith("/")
        script_path = VIEWER_ASSET_DIR / source.lstrip("/")
        assert script_path.is_file()
        if source != "/app.js":
            assert sources.index(source) < app_index
    assert sources.index("/app_i18n.js") < sources.index("/app_config.js") < app_index
    assert sources.index("/app_api.js") < sources.index("/app_tts.js") < app_index


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


def test_i18n_uses_ui_refresh_language_for_corpus_updates():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")

    script = dedent(
        f"""
        const assert = require("node:assert/strict");
        global.window = {{}};
        require({str(VIEWER_ASSET_DIR / "app_i18n.js")!r});

        const text = window.JPCORPUS_TEXT;
        assert.equal(text.zh.taskExportCorpus, "重新生成语料");
        assert.equal(text.en.taskExportCorpus, "Regenerate corpus");
        assert.equal(text.zh.loadErrorBody.includes("导出命令"), false);
        assert.equal(text.en.loadErrorBody.includes("Export the corpus first"), false);
        assert.equal(text.zh.maintenanceTaskFetchLexicalResources.includes("JMdict"), false);
        assert.equal(text.en.maintenanceTaskFetchLexicalResources.includes("JMdict"), false);
        """
    )
    subprocess.run([node, "-e", script], check=True, capture_output=True, text=True)


def test_llm_config_labels_are_user_facing_and_localized():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")

    script = dedent(
        f"""
        const assert = require("node:assert/strict");
        global.window = {{}};
        require({str(VIEWER_ASSET_DIR / "app_i18n.js")!r});

        const text = window.JPCORPUS_TEXT;
        assert.equal(text.zh.maintenanceProvider, "LLM 接口类型");
        assert.equal(text.zh.configLlmBaseUrl, "LLM 接口地址");
        assert.equal(text.zh.llmProviderOpenAiCompatible, "OpenAI 兼容接口");
        assert.equal(text.zh.llmProviderApple, "Apple 本机模型");
        assert.equal(text.en.maintenanceProvider, "LLM connection");
        assert.equal(text.en.llmProviderOpenAiCompatible, "OpenAI-compatible endpoint");
        assert.equal(text.en.llmProviderApple, "Apple local model");
        """
    )
    subprocess.run([node, "-e", script], check=True, capture_output=True, text=True)


def test_config_status_labels_hide_environment_variable_names():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")

    script = dedent(
        f"""
        const assert = require("node:assert/strict");
        global.window = {{}};
        require({str(VIEWER_ASSET_DIR / "app_i18n.js")!r});
        require({str(VIEWER_ASSET_DIR / "app_config.js")!r});

        function translate(lang, key, values = {{}}) {{
          let value = window.JPCORPUS_TEXT[lang][key] || key;
          Object.entries(values).forEach(([name, replacement]) => {{
            value = value.replace(`{{${{name}}}}`, replacement);
          }});
          return value;
        }}

        const service = {{
          id: "llm",
          label: "AI explanation",
          missing: ["JPCORPUS_LLM_MODEL", "JPCORPUS_LLM_API_KEY"],
        }};
        const zhLabels = window.JPCORPUS_CONFIG.configMissingLabels(
          service,
          (key, values) => translate("zh", key, values),
        );
        const enLabels = window.JPCORPUS_CONFIG.configMissingLabels(
          service,
          (key, values) => translate("en", key, values),
        );

        assert.deepEqual(zhLabels, ["LLM 模型", "LLM API Key"]);
        assert.deepEqual(enLabels, ["LLM model", "LLM API key"]);
        assert.equal(
          window.JPCORPUS_CONFIG.configServiceLabel(service, (key) => translate("zh", key)),
          "AI 讲解",
        );
        assert.equal(zhLabels.join(", ").includes("JPCORPUS_"), false);
        assert.equal(enLabels.join(", ").includes("JPCORPUS_"), false);
        """
    )
    subprocess.run([node, "-e", script], check=True, capture_output=True, text=True)


def test_apple_llm_provider_disables_unneeded_inputs():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")

    script = dedent(
        f"""
        const assert = require("node:assert/strict");
        global.window = {{}};
        require({str(VIEWER_ASSET_DIR / "app_i18n.js")!r});
        require({str(VIEWER_ASSET_DIR / "app_config.js")!r});

        const zh = (key) => window.JPCORPUS_TEXT.zh[key] || key;
        const en = (key) => window.JPCORPUS_TEXT.en[key] || key;

        assert.deepEqual(window.JPCORPUS_CONFIG.llmInputState("apple", zh), {{
          disabled: true,
          placeholder: "Apple 本机模型不需要填写",
        }});
        assert.deepEqual(window.JPCORPUS_CONFIG.llmInputState("apple", en), {{
          disabled: true,
          placeholder: "Not needed for Apple local model",
        }});
        assert.deepEqual(window.JPCORPUS_CONFIG.llmInputState("openai-compatible", zh), {{
          disabled: false,
          placeholder: "",
        }});
        """
    )
    subprocess.run([node, "-e", script], check=True, capture_output=True, text=True)


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


def test_lexical_notes_hide_dictionary_senses_in_chinese_ui():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")

    script = dedent(
        f"""
        const assert = require("node:assert/strict");
        global.window = {{}};
        global.document = {{
          createDocumentFragment: () => makeNode("fragment"),
          createTextNode: (value) => makeTextNode(value),
        }};

        function makeTextNode(value) {{
          return {{
            get textContent() {{
              return String(value || "");
            }},
          }};
        }}

        function makeNode(tag, className = "", value = "") {{
          return {{
            tag,
            className,
            title: "",
            children: [],
            value: String(value || ""),
            append(...items) {{
              this.children.push(...items.map((item) => typeof item === "string" ? makeTextNode(item) : item));
            }},
            get childElementCount() {{
              return this.children.filter((child) => child && child.tag).length;
            }},
            get textContent() {{
              return this.value + this.children.map((child) => child.textContent || "").join("");
            }},
            set textContent(nextValue) {{
              this.value = String(nextValue || "");
              this.children = [];
            }},
          }};
        }}

        require({str(VIEWER_ASSET_DIR / "app_lexical.js")!r});
        const helpers = window.JPCORPUS_LEXICAL.createLexicalHelpers({{
          el: makeNode,
          t: (key) => ({{
            lexicalNotes: "词语知识",
            lexicalPos: "词性",
            lexicalSenses: "词典义项",
          }}[key] || key),
          getLanguage: () => "zh",
        }});
        const section = helpers.renderLexicalNotes({{
          word: "やる",
          reading: "やる",
          meaning_zh: "做",
          lexical_notes: {{
            parts_of_speech: ["五段・る", "他动", "自动", "接尾词"],
            senses: [
              {{
                glosses: ["to do", "to undertake"],
                parts_of_speech: ["五段・る", "他动"],
                tags: ["旧语"],
              }},
            ],
          }},
        }});
        const text = section.textContent;

        assert.equal((text.match(/五段・る/g) || []).length, 1);
        assert.equal((text.match(/他动/g) || []).length, 1);
        assert.equal(text.includes("to do"), false);
        assert.equal(text.includes("词典义项"), false);
        assert.equal(text.includes("旧语"), false);

        const fallbackSection = helpers.renderLexicalNotes({{
          word: "やる",
          reading: "やる",
          lexical_notes: {{
            parts_of_speech: ["五段・る", "他动"],
            senses: [
              {{
                glosses: ["to do", "to undertake"],
                parts_of_speech: ["五段・る", "他动"],
                tags: ["旧语"],
              }},
            ],
          }},
        }});
        const fallbackText = fallbackSection.textContent;

        assert.equal((fallbackText.match(/五段・る/g) || []).length, 1);
        assert.equal((fallbackText.match(/他动/g) || []).length, 1);
        assert.equal(fallbackText.includes("to do"), false);
        assert.equal(fallbackText.includes("词典义项"), false);
        assert.equal(fallbackText.includes("旧语"), false);
        const parsedMeaning = helpers.renderMeaningValue({{
          meaning_zh: "（いい/よい）①【イ形】好的",
        }}, "meaning-main").textContent;
        assert.equal(parsedMeaning, "好的");

        const enHelpers = window.JPCORPUS_LEXICAL.createLexicalHelpers({{
          el: makeNode,
          t: (key) => ({{
            lexicalNotes: "Word knowledge",
            lexicalPos: "Grammar",
            lexicalSenses: "Senses",
          }}[key] || key),
          getLanguage: () => "en",
        }});
        const enSection = enHelpers.renderLexicalNotes({{
          word: "やる",
          reading: "やる",
          lexical_notes: {{
            parts_of_speech: ["五段・る", "他动"],
            senses: [
              {{
                glosses: ["to do", "to undertake"],
                parts_of_speech: ["五段・る", "他动"],
              }},
            ],
          }},
        }});
        const enText = enSection.textContent;
        assert.match(enText, /Senses1to do/);
        """
    )
    subprocess.run([node, "-e", script], check=True, capture_output=True, text=True)
