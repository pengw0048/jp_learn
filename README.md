# jpcorpus / 个人日语语料

## 中文

`jpcorpus` 是一个本地优先的个人日语学习工具。它把你看过的动画、听过的歌、导入的小说和网页文章整理成一个可浏览、可阅读、可复习的日语语料库。

它目前主要做这些事：

- 从 Bangumi 同步动画和音乐收藏。
- 从 Jimaku 下载可用的日语字幕。
- 从 LRCLIB 拉取歌词。
- 导入 `texts/` 里的 `.txt` 和 `.epub`，也可以从网页或浏览器扩展导入文章。
- 从维护面板导入本地 Yomitan `.zip` 或 MDX `.mdx` 词典。
- 用本地词典、JLPT 词表、JMdict、zhwiktionary fallback 等资源生成单词表、例句、阅读视图和词语知识。
- 在网页阅读器或浏览器扩展里点词查词、标记学习状态，并按你的学习进度复习。

所有主要数据都保存在本机文件和本机状态库里。这个项目不是托管服务，也不需要线上账号系统。

### 快速开始

```bash
uv sync
uv run jpcorpus
```

打开后访问 <http://127.0.0.1:8767/>。如果还没有 `corpus.json`，应用会先创建一个很小的 starter corpus，让界面能正常打开。

日常使用通常只需要这一个命令：

```bash
uv run jpcorpus
```

然后在网页里的“维护”面板完成配置和刷新。

如果要开发或跑测试，请安装 dev 依赖：

```bash
uv sync --extra dev
uv run pytest
```

### 配置

你可以在网页 UI 里填写配置，也可以手动编辑 `.env`。

```bash
cp .env.example .env
$EDITOR .env
```

常用配置：

- Bangumi application: <https://bgm.tv/dev/app>
- Jimaku API key: <https://jimaku.cc/api/docs>
- `JPCORPUS_USER_AGENT`: Bangumi API 需要一个有意义的 User-Agent。默认值可以跑，但建议换成你自己的。
- 可选 LLM: 用于阅读时的临时解释，可以配置 Anthropic、OpenAI-compatible endpoint，或 macOS Apple Foundation Models。
- 可选朗读：默认使用浏览器的日语语音，可以在维护面板选择具体 voice、预览、调速度；如果想用 VOICEVOX，先在本机启动 VOICEVOX engine，让它监听 `127.0.0.1:50021`，然后切换到 VOICEVOX。音频按需生成，不会缓存到本地。

Shell 里的环境变量优先级高于 `.env`。网页 UI 只有在 `127.0.0.1` 打开时才会写入本地 `.env`。

### 刷新数据

维护面板里主要有两个按钮：

- **刷新**：日常使用。同步新媒体、本地文本、网页导入、字幕、歌词，并重建阅读器需要的数据。
- **完整刷新**：偶尔使用。除了日常刷新，还会重新拉词表、词典和动画数据库等基础资源。

第一次配置完以后，点一次“完整刷新”。以后一般点“刷新”就够了。

### 导入内容

支持的来源：

- **字幕**：从 Bangumi 收藏映射到外部动画条目，再通过 Jimaku 搜索和下载日语字幕。
- **歌词**：从 Bangumi 音乐收藏和曲目信息搜索 LRCLIB，缓存命中和 miss。
- **本地文本**：把日语 `.txt` 或 `.epub` 放进 `texts/`，然后点“刷新”。
- **网页文章**：使用 `browser_extension/` 里的 Chrome 扩展从网页导入选中文字或主要正文。

EPUB 会优先使用书内 metadata，文件名作为备用标题。

### 本地词典

维护面板里的“本地词典”支持导入：

- **Yomitan `.zip`**：适合 Yomitan/Anki 生态的结构化词典，导入后会建立本地索引。
- **MDX `.mdx`**：适合 MDict/FreeMdict 生态的词典，导入后索引词头，查询时按需读取原词典内容。

导入的词典保存在 `~/.jpcorpus/dictionaries/`。你可以在 UI 里启用/停用、调整优先级、重建索引或删除词典。启用的词典会作为“本地词典”显示在词条详情中；`corpus.json` 不需要因此重建。

### 学习和阅读

主界面提供两种常用方式：

- **浏览/学习单词**：按 JLPT、频次、五十音、状态等筛选单词；每个词可以加入学习、标记已认识、忽略或清除状态。
- **阅读模式**：选择字幕、歌词、小说或网页文章，直接在上下文里点词查词。右侧会显示释义、词性、例句、学习状态、朗读按钮和可选 AI 解释。

学习进度用本地状态保存，不依赖远端账号。

### 浏览器扩展

`browser_extension/` 是可选的 unpacked Chrome extension。它可以：

- 右键导入选中文字。
- 右键导入网页主要正文。
- 在当前网页直接高亮日语词，并显示浮动词典面板。
- 从浮动面板把词加入学习、标记已认识、忽略或清除状态。
- 在网页右上角用浮动工具条朗读全文或选择段落朗读，优先使用本地 VOICEVOX，失败时退回浏览器语音；也可以临时显示假名。

安装方式：

1. 打开 Chrome Extensions。
2. 开启 Developer mode。
3. 选择 Load unpacked。
4. 选择本仓库里的 `browser_extension/` 文件夹。

扩展默认连接 <http://127.0.0.1:8767/>。

### 主要数据文件

```text
data/
  anime-offline-database.json  # Anime Offline Database cache
  jlpt-words.json              # local JLPT word list
  jp-zh-dict.json              # Japanese-Chinese glossary
  zhwiktionary-ja-dict.json    # zhwiktionary Japanese entries used as fallback
  jimaku-cache/                # downloaded subtitles
  lyrics-cache/                # downloaded lyrics
texts/                         # local .txt/.epub inputs
texts/web/                     # web imports
corpus.json                    # full generated corpus
corpus.index.json              # compact viewer index
corpus.words/                  # per-word detail shards
corpus.sources/                # per-source reader/detail shards
browser_extension/             # optional Chrome extension
~/.jpcorpus/state.db           # local tokens, sync state, caches, study state
~/.jpcorpus/dictionaries/      # imported Yomitan/MDX dictionaries and indexes
```

`corpus.json` 和 sidecar 文件都是生成物；需要更新时从 UI 点“刷新”即可。

### 说明

JLPT 没有官方公开词表，所以项目里的 JLPT 等级只是学习参考，不是考试保证。

中文释义以本地日中词典为主，必要时使用 zhwiktionary fallback。fallback 会尽量过滤“参见”“旧写”“简写说明”等不适合作为释义的条目，但词典数据仍然可能有噪声。

---

## English

`jpcorpus` is a local-first personal Japanese learning app. It turns watched anime, songs, books, and web articles into a browsable corpus for vocabulary lookup, contextual examples, reading, and review.

It currently:

- Syncs anime and music collections from Bangumi.
- Downloads Japanese subtitles from Jimaku when available.
- Fetches lyrics from LRCLIB.
- Imports local `.txt` and `.epub` files from `texts/`, plus web articles from the viewer or Chrome extension.
- Imports local Yomitan `.zip` or MDX `.mdx` dictionaries from the Maintenance panel.
- Builds word lists, examples, reader views, and lexical notes from local dictionaries, JLPT data, JMdict, and zhwiktionary fallback data.
- Lets you click words in the viewer or extension, review vocabulary, and track local study progress.

The app is local-first and file-backed. It is not a hosted service and does not require hosted user accounts.

### Quick Start

```bash
uv sync
uv run jpcorpus
```

Open <http://127.0.0.1:8767/>. If `corpus.json` does not exist yet, the app creates a tiny starter corpus so the UI can open.

Day to day, this is the only command you normally need:

```bash
uv run jpcorpus
```

Then use the Maintenance panel in the viewer for configuration and refreshes.

For development and tests, install the dev extra:

```bash
uv sync --extra dev
uv run pytest
```

### Configuration

You can configure credentials in the viewer UI or by editing `.env` manually.

```bash
cp .env.example .env
$EDITOR .env
```

Common settings:

- Bangumi application: <https://bgm.tv/dev/app>
- Jimaku API key: <https://jimaku.cc/api/docs>
- `JPCORPUS_USER_AGENT`: Bangumi API clients should use a meaningful User-Agent. The default works, but setting your own is recommended.
- Optional LLM provider: used for on-demand reading explanations. Supported options include Anthropic, OpenAI-compatible endpoints, and macOS Apple Foundation Models.
- Optional read-aloud: browser Japanese speech is used by default, with voice selection, preview, and speed controls in Maintenance. To use VOICEVOX, start a local VOICEVOX engine on `127.0.0.1:50021`, then switch the provider to VOICEVOX. Audio is generated on demand and is not cached locally.

Shell environment variables take precedence over `.env`. The viewer writes to `.env` only when opened on `127.0.0.1`.

### Refreshing Data

The Maintenance panel has two main actions:

- **Refresh**: the normal day-to-day action. It syncs new media, local text, web imports, subtitles, lyrics, and rebuilds viewer data.
- **Full refresh**: occasional maintenance. It also refetches base resources such as word lists, dictionaries, and the anime database.

After first-time setup, run one Full refresh. Later, Refresh is usually enough.

### Import Sources

Supported sources:

- **Subtitles**: Bangumi collection entries are mapped to anime IDs, then Jimaku is searched for Japanese subtitles.
- **Lyrics**: Bangumi music collections and track metadata are matched against LRCLIB; hits and misses are cached locally.
- **Local text**: put Japanese `.txt` or `.epub` files in `texts/`, then click Refresh.
- **Web articles**: use the Chrome extension in `browser_extension/` to import selected text or the main article body.

EPUB imports prefer book metadata and fall back to the file name.

### Local Dictionaries

The Local dictionaries section in Maintenance supports:

- **Yomitan `.zip`**: structured dictionaries from the Yomitan/Anki ecosystem. The app builds a local lookup index on import.
- **MDX `.mdx`**: dictionaries from the MDict/FreeMdict ecosystem. The app indexes headwords and reads entries from the original MDX on demand.

Imported dictionaries live under `~/.jpcorpus/dictionaries/`. The UI can enable/disable dictionaries, change priority, rebuild indexes, or delete them. Enabled dictionaries appear in word details under Local dictionaries; `corpus.json` does not need to be rebuilt for dictionary changes.

### Study and Reading

The viewer has two core workflows:

- **Browse/study vocabulary**: filter by JLPT level, frequency, gojuon order, source, and study state. Words can be added to review, marked known, ignored, or cleared.
- **Reader mode**: choose a subtitle, lyric, book, or web article and click words in context. The side panel shows meanings, parts of speech, examples, study state, read-aloud buttons, and optional AI explanations.

Study progress is stored locally.

### Browser Extension

`browser_extension/` is an optional unpacked Chrome extension. It can:

- Import selected text from the right-click menu.
- Import the main article text from the right-click menu.
- Highlight Japanese words directly on the current page.
- Show a floating glossary panel where words can be added to review, marked known, ignored, or cleared.
- Read the full page area or a picked paragraph from the floating page toolbar, preferring local VOICEVOX and falling back to browser speech; furigana can be toggled temporarily.

Install it with:

1. Open Chrome Extensions.
2. Enable Developer mode.
3. Choose Load unpacked.
4. Select this repository's `browser_extension/` directory.

The extension connects to <http://127.0.0.1:8767/> by default.

### Main Data Files

```text
data/
  anime-offline-database.json  # Anime Offline Database cache
  jlpt-words.json              # local JLPT word list
  jp-zh-dict.json              # Japanese-Chinese glossary
  zhwiktionary-ja-dict.json    # zhwiktionary Japanese entries used as fallback
  jimaku-cache/                # downloaded subtitles
  lyrics-cache/                # downloaded lyrics
texts/                         # local .txt/.epub inputs
texts/web/                     # web imports
corpus.json                    # full generated corpus
corpus.index.json              # compact viewer index
corpus.words/                  # per-word detail shards
corpus.sources/                # per-source reader/detail shards
browser_extension/             # optional Chrome extension
~/.jpcorpus/state.db           # local tokens, sync state, caches, study state
~/.jpcorpus/dictionaries/      # imported Yomitan/MDX dictionaries and indexes
```

`corpus.json` and its sidecars are generated files. Use Refresh in the UI to update them.

### Notes

JLPT does not publish an official vocabulary list, so JLPT levels here are study guidance rather than an exam guarantee.

Chinese meanings primarily come from a local Japanese-Chinese glossary, with zhwiktionary used as a fallback when useful. The fallback tries to filter out entries that are only redirects, old spellings, or abbreviation notes, but dictionary data can still contain noise.
