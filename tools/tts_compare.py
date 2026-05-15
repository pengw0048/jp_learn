from __future__ import annotations

import json
import subprocess
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import parse, request


HOST = "127.0.0.1"
PORT = 8787
VOICEVOX_URL = "http://127.0.0.1:50021"
MAX_TEXT_LENGTH = 300


PAGE = """<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>日语 TTS 临时对比</title>
    <style>
      :root {
        --font: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", "Noto Sans SC", system-ui, sans-serif;
        --ink: #1f272a;
        --muted: #66737a;
        --line: #d8e1e4;
        --soft: #f4f7f7;
        --teal: #147d73;
        --blue: #24799b;
        --gold: #9a6a05;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        color: var(--ink);
        background: #fbfcfc;
        font: 16px/1.55 var(--font);
      }
      main {
        width: min(1160px, calc(100vw - 32px));
        margin: 0 auto;
        padding: 28px 0 48px;
      }
      header {
        display: flex;
        justify-content: space-between;
        gap: 18px;
        align-items: flex-start;
        margin-bottom: 22px;
      }
      h1 {
        margin: 0 0 6px;
        font-size: 28px;
        letter-spacing: 0;
      }
      p {
        margin: 0;
        color: var(--muted);
      }
      .input-card,
      .card,
      table {
        border: 1px solid var(--line);
        background: #fff;
        border-radius: 8px;
        box-shadow: 0 16px 36px rgba(29, 54, 62, 0.08);
      }
      .input-card {
        display: grid;
        gap: 12px;
        padding: 16px;
        margin-bottom: 18px;
      }
      label {
        display: grid;
        gap: 6px;
        color: var(--muted);
        font-size: 13px;
        font-weight: 760;
      }
      textarea,
      select,
      input {
        width: 100%;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: #fff;
        color: var(--ink);
        font: inherit;
      }
      textarea {
        min-height: 92px;
        padding: 10px 12px;
        resize: vertical;
      }
      select,
      input {
        min-height: 40px;
        padding: 7px 10px;
      }
      button {
        min-height: 40px;
        padding: 8px 14px;
        border: 1px solid var(--teal);
        border-radius: 8px;
        background: var(--teal);
        color: #fff;
        font: inherit;
        font-weight: 760;
        cursor: pointer;
      }
      button.secondary {
        background: #fff;
        color: var(--teal);
      }
      button:disabled {
        opacity: 0.56;
        cursor: not-allowed;
      }
      .grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 16px;
      }
      .card {
        display: grid;
        gap: 12px;
        padding: 16px;
        align-content: start;
      }
      .card h2 {
        margin: 0;
        font-size: 20px;
      }
      .tag {
        display: inline-flex;
        width: fit-content;
        padding: 3px 9px;
        border-radius: 999px;
        background: var(--soft);
        color: var(--muted);
        font-size: 13px;
        font-weight: 760;
      }
      .tag.local { color: var(--teal); }
      .tag.cloud { color: var(--blue); }
      .tag.dictionary { color: var(--gold); }
      .status {
        min-height: 22px;
        color: var(--muted);
        font-size: 14px;
      }
      .player {
        width: 100%;
      }
      table {
        width: 100%;
        margin-top: 18px;
        border-collapse: collapse;
        overflow: hidden;
      }
      th,
      td {
        padding: 11px 13px;
        border-bottom: 1px solid var(--line);
        text-align: left;
        vertical-align: top;
      }
      th {
        background: var(--soft);
      }
      tr:last-child td { border-bottom: 0; }
      .small {
        font-size: 13px;
      }
      @media (max-width: 900px) {
        header { display: grid; }
        .grid { grid-template-columns: 1fr; }
      }
    </style>
  </head>
  <body>
    <main>
      <header>
        <div>
          <h1>日语 TTS 临时对比</h1>
          <p>用同一句话听一下几条路线的差异。这个页面只是实验工具，不接入正式语料。</p>
        </div>
        <button class="secondary" id="reset-text" type="button">恢复示例文本</button>
      </header>

      <section class="input-card">
        <label>
          测试文本
          <textarea id="text">おはようございます。今日はいい天気ですね。もう少しゆっくり話してください。</textarea>
        </label>
        <label>
          语速
          <input id="rate" type="range" min="0.6" max="1.25" step="0.05" value="0.9" />
        </label>
      </section>

      <section class="grid">
        <article class="card">
          <span class="tag local">浏览器内置</span>
          <h2>Web Speech API</h2>
          <p>最快接入，不需要后端。真实质量取决于当前浏览器和系统声音。</p>
          <label>
            声音
            <select id="browser-voice"></select>
          </label>
          <button id="browser-play" type="button">播放</button>
          <p class="status" id="browser-status"></p>
        </article>

        <article class="card">
          <span class="tag local">macOS 本机</span>
          <h2>macOS say</h2>
          <p>使用 Mac 已安装日语声音。适合本机体验，但只能在 macOS 上跑。</p>
          <label>
            声音
            <select id="macos-voice"></select>
          </label>
          <button id="macos-play" type="button">生成并播放</button>
          <audio class="player" id="macos-audio" controls></audio>
          <p class="status" id="macos-status"></p>
        </article>

        <article class="card">
          <span class="tag local">本地服务</span>
          <h2>VOICEVOX</h2>
          <p>如果你本机开了 VOICEVOX Engine，这里会调用 127.0.0.1:50021。声音更角色化。</p>
          <label>
            说话人
            <select id="voicevox-speaker"></select>
          </label>
          <button id="voicevox-play" type="button">生成并播放</button>
          <audio class="player" id="voicevox-audio" controls></audio>
          <p class="status" id="voicevox-status"></p>
        </article>
      </section>

      <table>
        <thead>
          <tr>
            <th>路线</th>
            <th>优点</th>
            <th>问题</th>
            <th>我对产品接入的判断</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Web Speech API</td>
            <td>零配置、前端直接用、适合单词和例句按钮。</td>
            <td>不同设备声音不同；音调不保证词典级准确。</td>
            <td>最适合先做 MVP。</td>
          </tr>
          <tr>
            <td>macOS say</td>
            <td>本地、隐私好、Mac 上声音还可以。</td>
            <td>需要后端生成音频；跨平台差。</td>
            <td>适合个人 Mac 版可选项。</td>
          </tr>
          <tr>
            <td>VOICEVOX</td>
            <td>本地 HTTP API，音色明显，比传统 TTS 有表现力。</td>
            <td>要额外安装/启动；角色声不一定适合词典发音。</td>
            <td>适合“读句子”实验，不一定适合默认单词读音。</td>
          </tr>
          <tr>
            <td>Forvo</td>
            <td>真人单词读音，学习词典感最强。</td>
            <td>外部 API、授权和缓存策略要小心；不适合句子。</td>
            <td>如果你想要“词典小喇叭”，后面值得接。</td>
          </tr>
        </tbody>
      </table>
      <p class="small" style="margin-top: 12px;">注：Open JTalk 没放进页面，因为需要额外安装字典/声音；它更适合作为离线后端，而不是快速试听。</p>
    </main>
    <script>
      const sampleText = "おはようございます。今日はいい天気ですね。もう少しゆっくり話してください。";
      const textInput = document.querySelector("#text");
      const rateInput = document.querySelector("#rate");
      const browserVoice = document.querySelector("#browser-voice");
      const browserStatus = document.querySelector("#browser-status");
      const macosVoice = document.querySelector("#macos-voice");
      const macosStatus = document.querySelector("#macos-status");
      const macosAudio = document.querySelector("#macos-audio");
      const voicevoxSpeaker = document.querySelector("#voicevox-speaker");
      const voicevoxStatus = document.querySelector("#voicevox-status");
      const voicevoxAudio = document.querySelector("#voicevox-audio");

      document.querySelector("#reset-text").addEventListener("click", () => {
        textInput.value = sampleText;
      });

      function currentText() {
        return textInput.value.trim().slice(0, 300);
      }

      function currentRate() {
        return Number(rateInput.value || 0.9);
      }

      function setOptions(select, options, emptyLabel) {
        select.replaceChildren();
        if (!options.length) {
          select.append(new Option(emptyLabel, ""));
          select.disabled = true;
          return;
        }
        select.disabled = false;
        options.forEach((item) => {
          select.append(new Option(item.label, item.value));
        });
      }

      function loadBrowserVoices() {
        const voices = speechSynthesis.getVoices();
        const japanese = voices
          .filter((voice) => /^ja[-_]/i.test(voice.lang || ""))
          .map((voice) => ({
            label: `${voice.name} (${voice.lang})`,
            value: voice.name,
          }));
        setOptions(browserVoice, japanese, "没有找到 ja-JP 声音");
        browserStatus.textContent = japanese.length
          ? `找到 ${japanese.length} 个浏览器日语声音`
          : "当前浏览器没有暴露日语声音";
      }

      loadBrowserVoices();
      if ("onvoiceschanged" in speechSynthesis) {
        speechSynthesis.onvoiceschanged = loadBrowserVoices;
      }

      document.querySelector("#browser-play").addEventListener("click", () => {
        const text = currentText();
        if (!text) return;
        speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = "ja-JP";
        utterance.rate = currentRate();
        const selected = browserVoice.value;
        const voice = speechSynthesis.getVoices().find((item) => item.name === selected);
        if (voice) utterance.voice = voice;
        speechSynthesis.speak(utterance);
      });

      async function loadMacVoices() {
        const response = await fetch("/api/macos-voices");
        const payload = await response.json();
        setOptions(
          macosVoice,
          payload.voices.map((voice) => ({
            label: `${voice.name} (${voice.lang})`,
            value: voice.name,
          })),
          "没有找到 macOS 日语声音",
        );
        macosStatus.textContent = payload.voices.length
          ? `找到 ${payload.voices.length} 个 macOS 日语声音`
          : "没有找到 macOS 日语声音";
      }

      document.querySelector("#macos-play").addEventListener("click", async () => {
        const text = currentText();
        if (!text || !macosVoice.value) return;
        macosStatus.textContent = "正在生成...";
        const response = await fetch("/api/macos-say", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, voice: macosVoice.value, rate: Math.round(currentRate() * 200) }),
        });
        if (!response.ok) {
          macosStatus.textContent = await response.text();
          return;
        }
        const blob = await response.blob();
        macosAudio.src = URL.createObjectURL(blob);
        await macosAudio.play();
        macosStatus.textContent = "已生成";
      });

      async function loadVoicevoxSpeakers() {
        try {
          const response = await fetch("/api/voicevox-speakers");
          const payload = await response.json();
          setOptions(
            voicevoxSpeaker,
            payload.speakers.map((speaker) => ({
              label: speaker.label,
              value: String(speaker.id),
            })),
            "VOICEVOX 未启动",
          );
          voicevoxStatus.textContent = payload.speakers.length
            ? `找到 ${payload.speakers.length} 个 VOICEVOX 声音`
            : "VOICEVOX 未启动";
        } catch {
          setOptions(voicevoxSpeaker, [], "VOICEVOX 未启动");
          voicevoxStatus.textContent = "VOICEVOX 未启动";
        }
      }

      document.querySelector("#voicevox-play").addEventListener("click", async () => {
        const text = currentText();
        if (!text || !voicevoxSpeaker.value) return;
        voicevoxStatus.textContent = "正在生成...";
        const response = await fetch("/api/voicevox-say", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, speaker: Number(voicevoxSpeaker.value) }),
        });
        if (!response.ok) {
          voicevoxStatus.textContent = await response.text();
          return;
        }
        const blob = await response.blob();
        voicevoxAudio.src = URL.createObjectURL(blob);
        await voicevoxAudio.play();
        voicevoxStatus.textContent = "已生成";
      });

      loadMacVoices().catch((error) => {
        macosStatus.textContent = error.message || String(error);
      });
      loadVoicevoxSpeakers();
    </script>
  </body>
</html>
"""


class TtsCompareHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A002
        return

    def do_GET(self) -> None:
        if self.path == "/" or self.path.startswith("/?"):
            self._send_bytes(PAGE.encode("utf-8"), "text/html; charset=utf-8")
            return
        if self.path == "/api/macos-voices":
            self._send_json({"voices": macos_voices()})
            return
        if self.path == "/api/voicevox-speakers":
            self._send_json({"speakers": voicevox_speakers()})
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        try:
            if self.path == "/api/macos-say":
                payload = self._read_json()
                content = synthesize_macos(payload)
                self._send_bytes(content, "audio/mp4")
                return
            if self.path == "/api/voicevox-say":
                payload = self._read_json()
                content = synthesize_voicevox(payload)
                self._send_bytes(content, "audio/wav")
                return
        except Exception as exc:
            self._send_text(str(exc), status=HTTPStatus.BAD_REQUEST)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0:
            return {}
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload

    def _send_json(self, payload: dict) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(content, "application/json; charset=utf-8")

    def _send_text(self, text: str, *, status: HTTPStatus) -> None:
        self.send_response(status)
        content = text.encode("utf-8")
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_bytes(self, content: bytes, content_type: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)


def macos_voices() -> list[dict[str, str]]:
    result = subprocess.run(["say", "-v", "?"], check=True, capture_output=True, text=True)
    voices = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        marker_index = line.find("#")
        meta = line[:marker_index].rstrip() if marker_index >= 0 else line
        columns = meta.rsplit(None, 1)
        if len(columns) != 2:
            continue
        name, lang = columns
        if lang == "ja_JP":
            voices.append({"name": name.strip(), "lang": lang})
    return voices


def synthesize_macos(payload: dict) -> bytes:
    text = clean_text(payload.get("text"))
    voice = str(payload.get("voice") or "").strip()
    rate = clamp_int(payload.get("rate"), 80, 320, 180)
    allowed = {item["name"] for item in macos_voices()}
    if voice not in allowed:
        raise ValueError("Unknown macOS voice.")
    with tempfile.TemporaryDirectory(prefix="jpcorpus-tts-") as tmp:
        directory = Path(tmp)
        aiff = directory / "sample.aiff"
        m4a = directory / "sample.m4a"
        subprocess.run(["say", "-v", voice, "-r", str(rate), "-o", str(aiff), text], check=True)
        subprocess.run(["afconvert", str(aiff), str(m4a), "-f", "m4af", "-d", "aac"], check=True)
        return m4a.read_bytes()


def voicevox_speakers() -> list[dict[str, str | int]]:
    try:
        with request.urlopen(f"{VOICEVOX_URL}/speakers", timeout=1.5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return []
    speakers = []
    for speaker in payload:
        name = speaker.get("name") or "VOICEVOX"
        for style in speaker.get("styles") or []:
            style_name = style.get("name") or "default"
            style_id = style.get("id")
            if style_id is not None:
                speakers.append({"id": int(style_id), "label": f"{name} / {style_name}"})
    return speakers


def synthesize_voicevox(payload: dict) -> bytes:
    text = clean_text(payload.get("text"))
    speaker = clamp_int(payload.get("speaker"), 0, 9999, 1)
    query_url = f"{VOICEVOX_URL}/audio_query?{parse.urlencode({'text': text, 'speaker': speaker})}"
    with request.urlopen(request.Request(query_url, method="POST"), timeout=10) as response:
        audio_query = response.read()
    synthesis_url = f"{VOICEVOX_URL}/synthesis?{parse.urlencode({'speaker': speaker})}"
    synthesis_request = request.Request(
        synthesis_url,
        data=audio_query,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(synthesis_request, timeout=30) as response:
        return response.read()


def clean_text(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("Text is required.")
    return text[:MAX_TEXT_LENGTH]


def clamp_int(value: object, minimum: int, maximum: int, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return min(max(number, minimum), maximum)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), TtsCompareHandler)
    print(f"Serving temporary TTS comparison: http://{HOST}:{PORT}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped TTS comparison server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
