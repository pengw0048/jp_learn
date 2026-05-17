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


def test_reader_mode_has_read_aloud_strings_and_controls():
    i18n = (VIEWER_ASSET_DIR / "app_i18n.js").read_text(encoding="utf-8")
    app = (VIEWER_ASSET_DIR / "app.js").read_text(encoding="utf-8")
    reader = (VIEWER_ASSET_DIR / "app_reader.js").read_text(encoding="utf-8")
    reader_mode = (VIEWER_ASSET_DIR / "app_reader_mode.js").read_text(encoding="utf-8")
    sources = (VIEWER_ASSET_DIR / "app_sources.js").read_text(encoding="utf-8")
    storage = (VIEWER_ASSET_DIR / "app_storage.js").read_text(encoding="utf-8")
    tts = (VIEWER_ASSET_DIR / "app_tts.js").read_text(encoding="utf-8")
    css = (VIEWER_ASSET_DIR / "app.css").read_text(encoding="utf-8")

    assert 'readerReadAloud: "朗读"' in i18n
    assert 'readerStopReading: "停止"' in i18n
    assert 'readerPreparingSpeech: "准备中"' in i18n
    assert 'readerReadLine: "朗读这一句"' in i18n
    assert 'readerSetStartLine: "点这一行，把这里设为朗读起点"' in i18n
    assert 'readerFuriganaChoice: "注音"' in i18n
    assert 'readerSourceControl: "当前阅读"' in i18n
    assert "reader-speech-button" in app
    assert "reader-furigana-button" in app
    assert "reader-quick-actions" in app
    assert "reader-line-speech-button" in app
    assert "firstVisibleReaderLineKey" in app
    assert "singleLine: true" in reader
    assert "speechStartKey" in app
    assert "setReaderSpeechStartLine" in app
    assert "setReaderSpeechStartLine(null)" in app
    assert 'document.querySelectorAll(".reader-speech-button")' in app
    assert "prefetchReaderSpeechLine" in app
    assert "READER_SPEECH_PREFETCH_LINES = 3" in app
    assert "scheduleReaderSpeechPrefetchWindow(index + 1)" in app
    assert 'button.classList.toggle("loading", app.reader.tts.preparing)' in app
    assert "markReaderSpeechStart" in app
    assert "visibleHeight" in app
    assert "stopAllSpeech();" in app
    assert 'window.addEventListener("pagehide", stopAllSpeech)' in app
    assert "stopAllSpeech();" in reader_mode
    assert "renderReaderModeControlsSummary" in reader_mode
    assert "STORAGE_READER_FURIGANA" in storage
    assert 'el("ruby", "reader-ruby")' in reader
    assert "readerLineText" in reader
    assert "stopAllSpeech" in sources
    assert "prepareSpeech" in tts
    assert "speakPreparedText" in tts
    assert "reader-line-speaking" in css
    assert "reader-line-speech-anchor" in css
    assert "reader-line-speech-start" in css
    assert "reader-furigana-enabled" in css
    assert "reader-mode-controls-kicker" in css


def test_detail_orders_reader_context_before_lexical_notes():
    app = (VIEWER_ASSET_DIR / "app.js").read_text(encoding="utf-8")

    assert app.index("const nodes = [renderDetailHeader(word)]") < app.index("const readerContext = renderReaderContextPanel(word);")
    assert app.index("nodes.push(readerContext);") < app.index("nodes.push(renderLexicalNotes(word));")
    assert app.index("nodes.push(renderLexicalNotes(word));") < app.index("nodes.push(renderUserDictionaryResults(word));")
    assert app.index("nodes.push(renderUserDictionaryResults(word));") < app.index("nodes.push(renderExamples(word));")
    assert app.index("nodes.push(renderLexicalNotes(word));") < app.index("nodes.push(renderExamples(word));")


def test_dictionary_manager_assets_are_wired():
    html = (VIEWER_ASSET_DIR / "index.html").read_text(encoding="utf-8")
    app = (VIEWER_ASSET_DIR / "app.js").read_text(encoding="utf-8")
    api = (VIEWER_ASSET_DIR / "app_api.js").read_text(encoding="utf-8")
    lexical = (VIEWER_ASSET_DIR / "app_lexical.js").read_text(encoding="utf-8")
    i18n = (VIEWER_ASSET_DIR / "app_i18n.js").read_text(encoding="utf-8")
    css = (VIEWER_ASSET_DIR / "app.css").read_text(encoding="utf-8")

    assert 'id="dictionary-file"' in html
    assert 'id="dictionary-name"' not in html
    assert 'id="dictionary-list"' in html
    assert "renderDictionaryManager" in app
    assert "importDictionaryFromPicker" in app
    assert "clearLoadedWordDetails" in app
    assert "dictionaryName" not in app
    assert "importDictionary" in api
    assert "/api/dictionaries/import" in api
    assert "renderUserDictionaryResults" in lexical
    assert 'event.key === "Escape"' in lexical
    assert "dictionary-detail-reference" in lexical
    assert 'dictionaryManagerTitle: "本地词典"' in i18n
    assert 'userDictionaryResults: "本地词典"' in i18n
    assert ".user-dictionary-results" in css
    assert ".dictionary-detail-reference" in css
    assert ".dictionary-row" in css


def test_user_dictionary_results_render_compact_primary_definitions():
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
            userDictionaryResults: "本地词典",
            userDictionaryUnknown: "未命名词典",
            userDictionarySpellings: "写法",
            userDictionarySeeAlso: "参见",
            userDictionaryDetails: "详情",
          }}[key] || key),
          getLanguage: () => "zh",
        }});
        const section = helpers.renderUserDictionaryResults({{
          word: "行く",
          user_dictionary_results: [
            {{
              dictionary_id: "wty",
              dictionary_name: "wty-ja-zh",
              format: "yomitan",
              headword: "行く",
              tags: ["v", "godan"],
              definitions: ["去，前往", "送达", "离开，逝去"],
            }},
            {{
              dictionary_id: "wty",
              dictionary_name: "wty-ja-zh",
              format: "yomitan",
              headword: "行く",
              definitions: ["口语用法"],
            }},
            {{
              dictionary_id: "wty",
              dictionary_name: "wty-ja-zh",
              format: "yomitan",
              kind: "reference",
              reference_type: "spelling",
              headword: "行く",
              references: ["ゆく"],
            }},
          ],
        }});
        const text = section.textContent;

        assert.equal(text.includes("去，前往；送达；离开，逝去"), true);
        assert.equal(text.includes("口语用法"), true);
        assert.equal(text.includes("写法：ゆく"), true);
        assert.equal((text.match(/wty-ja-zh/g) || []).length, 1);
        assert.equal(text.includes("YOMITAN"), false);
        assert.equal(text.includes("godan"), false);
      """
    )
    subprocess.run([node, "-e", script], check=True, capture_output=True, text=True)


def test_long_user_dictionary_results_open_detail_button():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")

    script = dedent(
        f"""
        const assert = require("node:assert/strict");
        global.window = {{}};

        function makeTextNode(value) {{
          return {{ tag: "text", textContent: String(value || "") }};
        }}

        function makeNode(tag, className = "", value = "") {{
          return {{
            tag,
            className,
            value: String(value || ""),
            children: [],
            title: "",
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
            userDictionaryResults: "本地词典",
            userDictionaryUnknown: "未命名词典",
            userDictionarySpellings: "写法",
            userDictionarySeeAlso: "参见",
            userDictionaryDetails: "详情",
          }}[key] || key),
          getLanguage: () => "zh",
        }});
        const longText = Array.from({{ length: 12 }}, (_, index) => `释义 ${{index + 1}}`).join("\\n");
        const section = helpers.renderUserDictionaryResults({{
          word: "言う",
          user_dictionary_results: [
            {{
              dictionary_id: "mdx",
              dictionary_name: "新日漢大辭典",
              definitions: [longText],
            }},
          ],
        }});
        const line = section.children[1].children[0].children[0];
        const text = section.textContent;

        assert.equal(line.tag, "p");
        assert.equal(text.includes("详情"), true);
        assert.equal(text.includes("释义 5"), false);
        assert.equal((text.match(/新日漢大辭典/g) || []).length, 1);
      """
    )
    subprocess.run([node, "-e", script], check=True, capture_output=True, text=True)


def test_example_highlight_can_add_unmarked_word_to_study():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")

    script = dedent(
        f"""
        const assert = require("node:assert/strict");
        global.window = {{}};

        function makeTextNode(value) {{
          return {{ tag: "text", textContent: String(value || "") }};
        }}

        function makeNode(tag, className = "", value = "") {{
          const listeners = {{}};
          return {{
            tag,
            className,
            value: String(value || ""),
            children: [],
            attrs: {{}},
            type: "",
            title: "",
            append(...items) {{
              this.children.push(...items.map((item) => typeof item === "string" ? makeTextNode(item) : item));
            }},
            setAttribute(name, nextValue) {{
              this.attrs[name] = String(nextValue || "");
            }},
            addEventListener(name, handler) {{
              listeners[name] = handler;
            }},
            click() {{
              listeners.click?.({{
                preventDefault() {{}},
                stopPropagation() {{}},
              }});
            }},
            get textContent() {{
              return this.value + this.children.map((child) => child.textContent || "").join("");
            }},
          }};
        }}

        require({str(VIEWER_ASSET_DIR / "app_examples.js")!r});
        const calls = [];
        let rendered = 0;
        const word = {{ word: "行く" }};
        const helpers = window.JPCORPUS_EXAMPLES.createExampleHelpers({{
          app: {{ mode: "browse", exampleColumns: "1", exampleExplanations: {{}} }},
          el: makeNode,
          renderDetail: () => {{ rendered += 1; }},
          setStatus: (nextWord, status) => calls.push([nextWord.word, status]),
          statusFor: () => "none",
          storage: {{ STORAGE_EXAMPLE_COLUMNS: "columns" }},
          t: (key) => key === "exampleAddStudyTitle" ? "把这个词加入学习" : key,
        }});
        const parent = makeNode("div");
        helpers.appendHighlighted(parent, "明日行く。", "行く", {{ studyWord: word }});
        const button = parent.children.find((child) => child.tag === "button");

        assert.ok(button);
        assert.equal(button.className, "example-match-button");
        assert.equal(button.title, "把这个词加入学习");
        button.click();
        assert.deepEqual(calls, [["行く", "learning"]]);
        assert.equal(rendered, 1);
        """
    )
    subprocess.run([node, "-e", script], check=True, capture_output=True, text=True)


def test_study_card_reveals_answer_before_review_actions():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")

    script = dedent(
        f"""
        const assert = require("node:assert/strict");
        global.window = {{}};

        function makeTextNode(value) {{
          return {{ tag: "text", textContent: String(value || "") }};
        }}

        function makeNode(tag, className = "", value = "") {{
          const listeners = {{}};
          return {{
            tag,
            className,
            value: String(value || ""),
            children: [],
            attrs: {{}},
            type: "",
            title: "",
            append(...items) {{
              this.children.push(...items.map((item) => typeof item === "string" ? makeTextNode(item) : item));
            }},
            setAttribute(name, nextValue) {{
              this.attrs[name] = String(nextValue || "");
            }},
            addEventListener(name, handler) {{
              listeners[name] = handler;
            }},
            click() {{
              listeners.click?.({{
                preventDefault() {{}},
                stopPropagation() {{}},
              }});
            }},
            get textContent() {{
              return this.value + this.children.map((child) => child.textContent || "").join("");
            }},
          }};
        }}

        function nodes(node) {{
          return [node, ...(node.children || []).flatMap(nodes)];
        }}

        function buttonByText(root, text) {{
          return nodes(root).find((node) => node.tag === "button" && node.textContent === text);
        }}

        require({str(VIEWER_ASSET_DIR / "app_detail.js")!r});
        const app = {{ study: {{ showAnswer: false }}, lang: "zh", mode: "study" }};
        let rendered = 0;
        const helper = window.JPCORPUS_DETAIL.createDetailHelpers({{
          app,
          displayCount: () => 4,
          displayReading: (word) => word.reading || "",
          displayMeaningRaw: () => "去，到",
          el: makeNode,
          examplesForWord: () => [],
          formatNumber: (value) => String(value),
          render: () => {{ rendered += 1; }},
          renderExamples: () => makeNode("section", "examples"),
          renderLexicalNotes: () => makeNode("section", "lexical-notes"),
          renderMeaningValue: () => makeNode("div", "meaning-main", "去，到"),
          renderSpeakButton: null,
          scheduleStudyReview: () => {{}},
          setStatus: () => {{}},
          speechTextForWord: () => "",
          statChip: (value) => makeNode("span", "stat-chip", value),
          stateLabels: {{}},
          statusFor: () => "learning",
          studyActions: {{
            addStudyCheck: () => {{}},
            markStudyWord: () => {{}},
            nextStudyWord: () => {{}},
          }},
          studyCheckLabel: () => "进度 3/7",
          studyCountFor: () => 3,
          studyKindLabel: () => "复习",
          studyTargetCount: 7,
          t: (key, values = {{}}) => ({{
            studyProgress: `学习 ${{values.current}} / ${{values.total}}`,
            studyHint: "hint",
            count: "频次",
            examples: "例句",
            revealAnswer: "看答案",
            nextWord: "下一个",
            studyCheckButton: "确认一次",
            studyAgain: "还不熟",
            studyKnown: "直接认识",
          }}[key] || key),
        }});
        const word = {{ word: "行く", reading: "いく", level: "N5" }};
        const hidden = helper.renderStudyCard(word, 0, 2);
        assert.ok(buttonByText(hidden, "看答案"));
        assert.ok(buttonByText(hidden, "下一个"));
        assert.equal(Boolean(buttonByText(hidden, "确认一次")), false);
        assert.equal(nodes(hidden).filter((node) => node.className.includes("study-progress-dot filled")).length, 3);

        buttonByText(hidden, "看答案").click();
        assert.equal(app.study.showAnswer, true);
        assert.equal(rendered, 1);

        const shown = helper.renderStudyCard(word, 0, 2);
        assert.ok(buttonByText(shown, "确认一次"));
        assert.ok(buttonByText(shown, "还不熟"));
        assert.ok(buttonByText(shown, "直接认识"));
        assert.equal(Boolean(buttonByText(shown, "看答案")), false);
        """
    )
    subprocess.run([node, "-e", script], check=True, capture_output=True, text=True)


def test_tts_speech_text_skips_parentheticals():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")

    script = dedent(
        f"""
        (async () => {{
          const assert = require("node:assert/strict");
          global.window = {{}};
          require({str(VIEWER_ASSET_DIR / "app_tts.js")!r});

          let captured = "";
          const helpers = window.JPCORPUS_TTS.createTtsHelpers({{
            api: {{
              voicevoxSynthesize: async (payload) => {{
                captured = payload.text;
                return new Blob(["audio"]);
              }},
            }},
            app: {{
              tts: {{
                provider: "voicevox",
                voicevoxSpeaker: "1",
                rate: 1,
              }},
            }},
            el: () => null,
            refs: {{}},
            storage: {{}},
            t: (key) => key,
          }});

          await helpers.prepareSpeech("（かをり）ありがとう（拍手）");
          assert.equal(captured, "ありがとう");
          await helpers.prepareSpeech("今日は（小声）学校へ行く。");
          assert.equal(captured, "今日は学校へ行く。");
        }})();
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


def test_display_reading_hides_plain_katakana_transliteration():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")

    script = dedent(
        f"""
        const assert = require("node:assert/strict");
        global.window = {{}};
        require({str(VIEWER_ASSET_DIR / "app_format.js")!r});

        const helpers = window.JPCORPUS_FORMAT.createFormatHelpers({{
          getLanguage: () => "zh",
        }});

        assert.equal(helpers.displayReading({{ word: "パスタ", reading: "ぱすた" }}), "");
        assert.equal(helpers.displayReading({{ word: "パスタ", reading: "パスタ" }}), "");
        assert.equal(helpers.displayReading({{ word: "音", reading: "おと" }}), "おと");
        assert.equal(helpers.displayReading({{ word: "良い", reading: "よい; いい" }}), "よい; いい");
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
            corpusSyncApply: {{ disabled: false, hidden: false, textContent: "" }},
          }};
        }}

        async function runScenario(shouldDefer, kind = "sync_media") {{
          const job = {{
            id: "job-1",
            kind,
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
              syncNotice: "",
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
          assert.equal(deferred.app.maintenance.syncNotice, "corpusUpdateApplied");
          assert.equal(deferred.refs.corpusSyncBanner.hidden, false);
          assert.equal(deferred.refs.corpusSyncApply.hidden, true);

          const automatic = await runScenario(false);
          assert.equal(automatic.calls.reloads, 1);
          assert.equal(automatic.app.maintenance.pendingReloadJob, null);
          assert.equal(automatic.app.maintenance.reloadedJobId, "job-1");
          assert.equal(automatic.app.maintenance.syncNotice, "corpusUpdateApplied");
          assert.equal(automatic.refs.corpusSyncBanner.hidden, false);

          const imported = await runScenario(false, "refresh_imported_texts");
          assert.equal(imported.calls.reloads, 1);
          assert.equal(imported.app.maintenance.syncNotice, "");

          const deferredImported = await runScenario(true, "refresh_imported_texts");
          assert.equal(deferredImported.calls.reloads, 0);
          assert.equal(deferredImported.refs.corpusSyncMessage.textContent, "corpusUpdateImportedReady");
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


def test_source_groups_show_imported_text_domain_meta():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")

    script = dedent(
        f"""
        const assert = require("node:assert/strict");
        global.window = {{}};
        require({str(VIEWER_ASSET_DIR / "app_sources.js")!r});

        const helpers = window.JPCORPUS_SOURCES.createSourceHelpers({{
          app: {{
            corpus: {{
              shows: [],
              sources: [{{
                source_type: "text",
                source_title: "NHK 記事",
                source_artist: "www3.nhk.or.jp",
                source_file: "web/nhk.txt",
                line_count: 3,
                words: ["学校"],
              }}],
            }},
            words: [],
            expandedSourceGroups: new Set(),
            sourceDetails: new Map(),
            sourceDetailRequests: new Map(),
            sourceDetailFailures: new Set(),
          }},
          api: {{}},
          asArray: (value) => Array.isArray(value) ? value : [],
          el: () => null,
          emptyMessage: () => null,
          fileStem: (value) => String(value || ""),
          formatNumber: (value) => String(value),
          hasExampleAnnotations: () => false,
          hideSourcePanel: () => {{}},
          normalizedTextTitle: (value) => String(value || ""),
          refs: {{ sourceInventory: null, sourcePanel: {{ hidden: true }} }},
          render: () => {{}},
          startMaintenanceJob: async () => null,
          stopAllSpeech: () => {{}},
          storageMode: "mode",
          strong: () => null,
          t: (key) => key,
        }});

        const groups = helpers.buildSourceGroups("text");

        assert.equal(groups.length, 1);
        assert.equal(groups[0].title, "NHK 記事");
        assert.equal(groups[0].meta, "www3.nhk.or.jp");
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
            lexicalExamples: "词典例句",
          }}[key] || key),
          getLanguage: () => "zh",
        }});
        const section = helpers.renderLexicalNotes({{
          word: "やる",
          reading: "やる",
          meaning_zh: "做",
          lexical_notes: {{
            parts_of_speech: ["Godan verb with 'ru' ending", "transitive verb", "intransitive verb", "自他动1", "接尾词", "unknown English grammar label"],
            senses: [
              {{
                glosses: ["to do", "to undertake"],
                parts_of_speech: ["Godan verb with 'ru' ending", "transitive verb"],
                tags: ["旧语"],
              }},
            ],
            dictionary_examples: [
              {{
                japanese: "英語だけの例です。",
                translations: {{ eng: "English only." }},
              }},
              {{
                japanese: "中国語訳のある例です。",
                translations: {{ cmn: "这是有中文翻译的例句。" }},
              }},
            ],
          }},
        }});
        const text = section.textContent;

        assert.equal(text.includes("五段・る"), false);
        assert.equal((text.match(/自他/g) || []).length, 1);
        assert.equal(text.includes("自他动1"), false);
        assert.equal(text.includes("transitive verb"), false);
        assert.equal(text.includes("unknown English grammar label"), false);
        assert.equal(text.includes("他动"), false);
        assert.equal(text.includes("自动"), false);
        assert.equal(text.includes("动词"), false);
        assert.equal(text.includes("to do"), false);
        assert.equal(text.includes("词典义项"), false);
        assert.equal(text.includes("旧语"), false);
        assert.equal(text.includes("英語だけの例です"), false);
        assert.equal(text.includes("中国語訳のある例です"), true);
        assert.equal(text.includes("这是有中文翻译的例句。"), true);

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

        assert.equal(fallbackText.includes("五段・る"), false);
        assert.equal((fallbackText.match(/他动/g) || []).length, 1);
        assert.equal(fallbackText.includes("动词"), false);
        assert.equal(fallbackText.includes("to do"), false);
        assert.equal(fallbackText.includes("词典义项"), false);
        assert.equal(fallbackText.includes("旧语"), false);
        assert.equal(helpers.displayMeaningRaw({{ meaning: "sound" }}), "");
        assert.equal(helpers.displayMeaningRaw({{ meaning_zh: "声音", meaning: "sound" }}), "声音");
        const parsedMeaning = helpers.renderMeaningValue({{
          meaning_zh: "（いい/よい）①【イ形】好的",
        }}, "meaning-main").textContent;
        assert.equal(parsedMeaning, "好的");
        const staleMeaning = helpers.renderMeaningValue({{
          meaning_zh: "③ 自他动1 道歉，谢罪",
        }}, "meaning-main").textContent;
        assert.equal(staleMeaning, "道歉，谢罪");

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
