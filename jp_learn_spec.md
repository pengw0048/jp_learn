# 日语学习产品 — 设计与决策文档

> 这份文档汇总了一次产品 brainstorm 的全部决策与背景。下一个 agent 应**先读完整份**再动手。
>
> 作者备忘：本文档使用中英混排，技术术语保留英文。

---

## 0. TL;DR

把你已经看过的日语内容（动漫 / 电影 / 综艺 / 歌曲），变成你正在准备 JLPT 的私人教材。

**核心 framing**：「这个产品不要求你回看 — 它假设你已经看过，要做的是把记忆固化下来。」

**MVP（v0.1）**：CLI 工具，绑定 Bangumi → 拉看过列表 → 抓对应字幕 → 分词 → 生成"个人词频报告" + Anki deck 导出。2-3 周可发帖测水温。

---

## 1. 缘起 / 项目背景

最初讨论是探索一个"专精领域"——希望是 niche 但能做到顶尖的方向。经过几轮探讨：

1. **工作衍生方向**：MultiKueue / Lance 邻接 / 对象存储调优 / Flyte debugging / Ray Data — 都太接近本职，缺乏"业余领域"的味道
2. **GitHub 历史信号**：作者 GitHub 真正持续投入的主线是「中国互联网生态闭源协议 / 移动取证」
   - WechatExport-iOS 783⭐（2026-04 仍在维护）
   - BaiduOldDriver 263⭐（2026-04 仍在维护）
   - NeteaseReverseLadder 198⭐（2026-01 仍在维护）
3. **现代 RE 方向**：WeChat 4.0 macOS 空缺 / iMessage / Apple 生态 / 智能家居 / 电纸书 — 有机会但需另起炉灶
4. **AI 工具 proxy**：Cursor / Claude Code 黑盒透明化 — 太挤（LiteLLM / Helicone / Portkey 已占）
5. **收敛**：作者原本就有的 idea — 用观看历史辅助 JLPT 学习

**为何选这个方向**：

- 跟主业平行不冲突
- 用到全部技能栈（RE 字幕协议 + 数据 pipeline + LLM 应用 + 中日双语）
- 跟 GitHub 老本行（中文应用 RE）一脉相承
- 有真实的、可量化的产品空缺
- 用户付费意愿强（语言学习者）

---

## 2. 产品定位

### 一句话定位

> 把你已经看过的日语内容，变成你正在准备 JLPT 的私人教材。

### 与现有竞品的根本差异

| 工具 | 心智模型 |
|---|---|
| jpdb | 你来这里学，作品是工具 |
| Migaku | 你来看片，顺便学 |
| Language Reactor | 看 Netflix 时辅助 |
| **本产品** | **你已经看过了，我们帮你把它变成你的语言资产** |

每加一个 feature，都用这一句来检验是否帮助："X 帮不帮助把已看过的内容变成 JLPT 教材？"

### 目标用户

主要：

- JLPT 应试 + 动漫爱好者（中国 / 海外华人占多数）
- 日剧 / 日影 / J-pop 爱好者（次要但增长）
- 母语中文 > 母语英文

不是为：

- 纯入门者（没有"已看过"的资产）
- 纯沉浸式学习者（不刷 JLPT）

---

## 3. 竞品分析

| 工具 | 做什么 | 缺口 |
|---|---|---|
| [jpdb.io](https://jpdb.io) | 按作品组织 deck，最强同类 | 不知道你看过什么；要手动选；纯文本无情境；不接 Bangumi/豆瓣 |
| Migaku | 看片实时挖句子 | 高门槛；付费；不接已有观看历史 |
| Language Reactor | Netflix 字幕双语 | 仅 Netflix；无学习闭环 |
| Asbplayer + Yomitan + Anki | 高玩组合 | 配置门槛极高 |
| Animelon | 在线看带学习字幕 | 仅在线播放；不个性化 |

### 真空地带

1. **Bangumi / 豆瓣 / Last.fm / 网易云 整合** — 西方工具不做中文区
2. **LLM 驱动的语义匹配 / 难度评估 / 场景重要性** — 现有工具都是字符串匹配
3. **歌词 + 字幕 + 视频字幕 的统一语料库** — 没人覆盖全
4. **"私人教材"的产品 framing** — 大家都做"语料库"，没人做"已知 + 私人"

---

## 4. 用户模式 & MVP 选择

### 4 种基础模式

| 模式 | 描述 | 留存 | 差异化 | MVP? |
|---|---|---|---|---|
| 1. 词表 SRS | 选词表 → 每天复习 → 卡片用你看过内容的例句 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ |
| 2. 作品 Explore | 选作品 → 查词频 → 加入个人词包 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ |
| 3. 单点 Lookup | "出る 怎么用" 搜索 | ⭐ | ⭐⭐⭐ | 🟡 v1 引流入口 |
| 4. Chat Tutor | 自然语言提问，agent 调工具回答 | ⭐⭐ | ⭐⭐⭐ | ❌ v2 |

### 模式 1 + 2 的耦合（MVP）

```
登录 Bangumi（30 秒）
  ↓
"你看过 47 部，匹配到 38 部有字幕。"
  ↓
首页 = 模式 2：作品列表 + 每部"待学词"数
  ↓ 用户点击《孤独摇滚》
"这部里你不会的 N3 词有 187 个。要不要每天学 10 个？"
  ↓ [开始学]
每日复习 = 模式 1：今日 10 张卡
  每张卡 = 词 + 剧中原句 + 5 秒原音 + 截图（如可得）+ 翻译
```

### 词表选择 / 导入

| 优先级 | 选项 | 实现 |
|---|---|---|
| MVP 必备 | 预置 JLPT N5-N1 | 一键选 |
| MVP 必备 | 作品自动 deck | 模式 2 生成 |
| MVP 必备 | 复习时手动加 | 一键添加 |
| v1 | AI 智能词表 | 基于历史生成 200 词 |
| v1 | Anki / jpdb 导入 | 上传文件 |
| v1+ | 字幕粘贴抽词 | 选段加入 |

---

## 5. 数据源策略

### 5.1 字幕源（按降级链）

| 优先级 | 来源 | 覆盖 | 备注 |
|---|---|---|---|
| 1 | [Jimaku](https://jimaku.cc) | 现代 anime 主力 | 有 API、维护好 |
| 2 | Kitsunekko | 老 anime / 部分电影 | 静态文件 |
| 3 | [assrt.net](https://assrt.net)（伪射手）| 中文字幕，双语对照 | 有 API |
| 4 | OpenSubtitles | 电影 / 部分日剧 | 全球，付费档 |
| 5 | B 站 CC 字幕 / 弹幕 | 正版番剧 | PRC 关键源（合规边界要谨慎） |
| 6 | Whisper ASR | 任何视频兜底 | ~$1/小时，用 large-v3 |
| 7 | 用户上传 .srt | 真正边角 | 0 摩擦 |

**关键洞察**：anime 字幕被 1+2+5 覆盖 90%，**变综/电影/日剧基本得靠 Whisper** — 这是好消息，因为 ASR 是均匀解决方案，不依赖各家字幕站维护好坏。

### 5.2 观看历史源

| 用户类型 | 主源 | 阶段 |
|---|---|---|
| 中文 anime 用户 | Bangumi.tv（API + OAuth） | **MVP** |
| 西方 anime | MAL / AniList | v1 |
| 中文综合 | 豆瓣（无 API，scrape） | v1 |
| 美剧 / 电影 | Trakt / Letterboxd | v2 |
| 日影日剧 | Filmarks | v2 |
| 音乐 | Last.fm / 网易云 / Spotify | v1（歌词模式入口）|
| 散视频 | YouTube Takeout / B 站历史 | v2 |

### 5.3 内容类型与处理层级

| 类型 | 已有日字 | 处理时长 |
|---|---|---|
| anime | 充足 | 即时（Tier A）|
| 日影 / 日剧 | 部分有 | 几秒-几分钟（Tier B）|
| 日综 | 几乎没有 | 视频长度的 30%（Tier C，必须 Whisper）|
| 音乐 / 歌词 | 充足（uta-net / J-Lyric / 网易云）| 即时（Tier A）|

UX 上：

```
"《葬送のフリーレン》第 12 集"  → 立即可用 ✅
"《罗曼史》（电影）"            → "正在准备字幕，约 2 分钟" 🟡
"《有吉的壁》最新一集"          → "需 Whisper，约 25 分钟" + 费用 🔴
```

---

## 6. 架构决策

### 6.1 数据库选型：Postgres + tsvector + pgvector（**不用 Lance**）

数据规模实算：

- 字幕总量 ~30-50M 行
- 每行 ~500 byte 元数据 + 3 KB（int8 量化 768 byte）embedding
- 全库 ~30 GB（量化后）

→ 一台 MacBook SSD 装得下，根本不是大数据。

| 选项 | 评估 | 决定 |
|---|---|---|
| Postgres + pgvector + tsvector | 服务端 MVP，一个 service 全搞定 | **🥇 主选** |
| SQLite + sqlite-vec | 客户端分发整个语料库，local-first | 🥈 备用方案 |
| DuckDB + VSS | 离线 batch pipeline | 🥉 处理层用 |
| Qdrant / Milvus | 纯向量 | 不必要 |
| Elasticsearch | 全文 + 向量 | overkill，运维重 |
| **Lance** | S3-native PB 级 | **❌ 明确否决**（数据量小用不到优势） |

唯一例外：未来若加大量影视截图 / 短视频片段，可考虑 Lance。**MVP 阶段绝对不要**。

### 6.2 LLM × 向量 × Agent 的责任划分

#### LLM 不擅长（重要！避免误用）

- **长上下文 join**："几万 vs 几万一次匹配"会失败 — 注意力退化 + 幻觉
- **数值连续打分**：校准差，要用类别（low/med/high）或对比（A vs B）
- **全语料"记忆"**：必须 RAG，永远不要假设它"看过"语料库
- **长链推理 + 长输出**：错误累积放大

#### LLM 擅长

- **Pointwise 分类器**：小输入小输出，独立调用
- **尾部歧义裁决**：hybrid pipeline 最后 2-5%
- **小输出生成**：recap / 翻译 / 解释
- **Top-K rerank**：5-10 个候选里挑

#### 三层检索路由

```
用户 query
    ↓
Router LLM（小模型分类）
    ↓
┌────────┬────────┬──────────┬────────┐
│ SQL    │ BM25   │ Vector   │ Agent  │
│ 70%    │ 15%    │ 10%      │ 5%     │
└────────┴────────┴──────────┴────────┘
    ↓
LLM rerank top-K（统一最后一步）
```

- 70% 是结构化合取查询 → SQL filter（依赖 LLM 标注列）
- 15% 关键词 + 元数据 → tsvector + scalar
- 10% 真模糊语义 → pgvector ANN
- 5% 探索性 / 教学复合 → Agent + 工具调用（多轮）

→ **embedding 是工具不是骨架**，70% 查询根本不用向量。

### 6.3 标题映射（Bangumi ↔ Jimaku）的正确做法

**错的**：把几万 Bangumi 标题 + 几万 Jimaku 文件名扔给 LLM 一次 join。

**对的**（三段式）：

1. **Stage 1 Deterministic（覆盖 80%）**：
   - 用 [Anime Offline Database](https://github.com/manami-project/anime-offline-database)（社区维护的 ID 映射表，MAL ↔ AniDB ↔ AniList ↔ Kitsu ↔ ...）
   - 标题归一化（NFKC + 去标点）+ 年份 + 集数精确匹配

2. **Stage 2 Embedding 检索（覆盖 18%）**：
   - BGE-M3 多语 embedding
   - 每个 query 取 top-5 候选

3. **Stage 3 LLM 单点裁决（覆盖 2%）**：
   - 1 query + 5 候选 + metadata → which match (or none)
   - 上下文 < 2k token，零幻觉风险

---

## 7. LLM 使用细则（按 pipeline 阶段）

### 7.1 一次性 batch（per subtitle line，独立调用）

每条字幕生成一组列：

| 字段 | 说明 |
|---|---|
| `sense_id` | 词义消歧（基于 JMdict sense 列表）|
| `reading` | 读音消歧（生 = なま / せい / いき）|
| `grammar_tags` | 语法 pattern 标签（〜てしまう、〜ば 等）|
| `difficulty` | 难度（easy/medium/hard，类别非数值）|
| `scene_score` | 场景重要性 1-10（输入 = 行 + 5 行上下文）|
| `translation_zh` | 学习者友好的中文翻译 |
| `line_type` | dialogue / sign / song / staff |

**成本估算**：~10M 行 × 便宜模型（Haiku 4.5 / Qwen2.5 / DeepSeek）≈ 几千美元一次性。

**模型选择**：
- bulk：Haiku 4.5 或 Qwen2.5-7B 自部署（看预算）
- 在线：Sonnet 4.6 / Opus 4.7（magic moments 才用）

### 7.2 在线（per query / per user，按需）

- 微 recap 生成（卡片背面"这是哪个场景"）
- 例句精排（top-10 → top-3 + 解释）
- Chat tutor 回答
- Agent 多轮搜索

### 7.3 反幻觉

LLM 生成的场景 recap → embed → 跟原字幕 embed 算相似度 → 差太远 = 编造 → 重新生成。这是廉价且有效的兜底。

---

## 8. 交互层

### 8.1 评分（按"记忆锚点 × 摩擦低"）

| 形态 | 锚点 | 摩擦 | 阶段 |
|---|---|---|---|
| 传统 SRS 卡片 | ⭐⭐ | ⭐⭐⭐⭐ | **MVP 主形态** |
| 看片实时挖句子 | ⭐⭐⭐⭐⭐ | ⭐ | v2，门槛高 |
| 5 秒视频片段卡 | ⭐⭐⭐⭐ | ⭐⭐⭐ | v1 可探索 |
| Chat tutor | ⭐⭐⭐ | ⭐⭐⭐⭐ | v1.5 |
| 每日 AI podcast | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **重点 v1，独家** |
| 锁屏 / 通知 drip | ⭐⭐ | ⭐⭐⭐⭐⭐ | v1 |
| 浏览器插件 | ⭐⭐⭐⭐ | ⭐⭐⭐ | v2 |

### 8.2 三个差异化交互（按价值）

#### A. 每日 AI 通勤电台 ⭐（独家杀手 feature）

```
每天早上 6 点，生成一个 5 分钟的 mp3：
- 前 30 秒：复述昨天你追的《孤独摇滚》第 3 集亮点
- 接 3 分钟：今日要学的 7 个词
  每个词配剧中原片段（5 秒原音）+ TTS 中文解释 + 情境
- 最后 1 分钟：明天要看哪一集（剧透屏蔽）的预告 + 准备词汇
```

**市面上完全没有这个形态**。Podcast feed 形式发布即可，零 app。

#### B. Agent 式 chat tutor

```
用户: "千与千寻里那个'生きろ'是什么意思来着？"
Agent: 调 search → 找到原句、前后 5 行、汤婆婆的语气
回答: "你想的是无脸男在第 X 分钟说的，意思是..."
       附带：原片段 5 秒回放 / 类似用法在你看过的别作里 3 处
```

#### C. 每日推送一词

```
锁屏 / Telegram / iMessage：
"你昨天在看《孤独摇滚》。
 解锁了一个词：生意気（なまいき）
 后藤独这么形容自己：'私生意気だね'
 [听原音] [背下来] [换一个]"
```

---

## 9. 跳转播放策略

**关键决定**：MVP 不做。复习场景下用户其实不需要回看视频。卡片背面 = 文本 + 截图 + 5 秒 TTS 已经足够。

降级阶梯（如要做，按可行性）：

1. **B 站正版番剧**：`bilibili.com/bangumi/play/ep{epid}?t={seconds}` — 精确到秒
2. **多源候选列表**：B 站搜 / Animelon / Crunchyroll / YouTube — 用户挑能用的
3. **本地播放器集成**：asbplayer / mpv URL handler
4. **完全不跳转**：纯文本 + 截图 + TTS（**MVP 选这个**）

综艺 / 电影的跳转**完全无解** — 给搜索链接即可。

→ 这个限制反而加强了产品 framing："已经看过的东西，本来就不用回看，要靠记忆复活"。

---

## 10. 数据库 Schema 草案（v0.5 起点）

```sql
-- 公共表
CREATE TABLE shows (
  id BIGSERIAL PRIMARY KEY,
  bangumi_id INT,
  mal_id INT,
  anidb_id INT,
  anilist_id INT,
  title_jp TEXT,
  title_en TEXT,
  title_zh TEXT,
  type TEXT, -- 'anime', 'movie', 'drama', 'variety', 'music'
  year INT,
  episode_count INT,
  metadata JSONB
);

CREATE TABLE episodes (
  id BIGSERIAL PRIMARY KEY,
  show_id BIGINT REFERENCES shows,
  episode_number INT,
  title TEXT,
  duration_seconds INT
);

CREATE TABLE subtitle_lines (
  id BIGSERIAL PRIMARY KEY,
  episode_id BIGINT REFERENCES episodes,
  start_ms INT,
  end_ms INT,
  text_jp TEXT,
  -- LLM 标注列
  difficulty TEXT, -- easy/medium/hard
  scene_score SMALLINT, -- 1-10
  line_type TEXT, -- dialogue/sign/song/staff
  translation_zh TEXT,
  -- 全文索引
  text_jp_tsv TSVECTOR,
  -- v1+ 才加
  embedding VECTOR(768)
);

CREATE INDEX subtitle_lines_tsv_idx ON subtitle_lines USING GIN(text_jp_tsv);
CREATE INDEX subtitle_lines_episode_idx ON subtitle_lines(episode_id);

CREATE TABLE words (
  id BIGSERIAL PRIMARY KEY,
  jmdict_id INT,
  surface_form TEXT,
  reading TEXT,
  jlpt_level INT, -- 5 to 1
  frequency_rank INT
);

CREATE TABLE words_in_lines (
  id BIGSERIAL PRIMARY KEY,
  line_id BIGINT REFERENCES subtitle_lines,
  word_id BIGINT REFERENCES words,
  sense_id INT, -- JMdict sense
  reading TEXT,
  position_in_line INT
);

-- 用户表
CREATE TABLE users (
  id BIGSERIAL PRIMARY KEY,
  bangumi_user_id INT,
  email TEXT,
  created_at TIMESTAMPTZ
);

CREATE TABLE user_watched_shows (
  user_id BIGINT REFERENCES users,
  show_id BIGINT REFERENCES shows,
  watched_at TIMESTAMPTZ,
  source TEXT, -- 'bangumi','manual','mal'
  PRIMARY KEY (user_id, show_id)
);

CREATE TABLE user_cards (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT REFERENCES users,
  word_id BIGINT REFERENCES words,
  due_at TIMESTAMPTZ,
  ease_factor REAL,
  interval_days INT,
  source_line_id BIGINT REFERENCES subtitle_lines, -- 推荐时挑的那一句
  created_at TIMESTAMPTZ
);

-- 用户上传的字幕（私有可见）
CREATE TABLE user_uploaded_episodes (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT REFERENCES users,
  show_id BIGINT REFERENCES shows, -- 可能 NULL（完全自定义）
  visibility TEXT DEFAULT 'private'
  -- 子句存到 subtitle_lines 同一张表，加 owner 字段
);
```

---

## 11. 阶段路线图

### v0.1（2-3 周，CLI，验证想法）

**目标**：作者自己跑通，生成自己的本地语料库和学习视图，看数据质量是否有用。

**功能**：

```
$ jpcorpus link bangumi      # OAuth
$ jpcorpus sync              # 拉看过列表 + 字幕
$ jpcorpus                  # 打开本地 viewer
$ jpcorpus export anki       # 导出 .apkg
```

**不做**：web、SRS、LLM 标注、向量检索。

**栈**：Python，依赖：

- `httpx`（API 调用）
- `fugashi[unidic]`（日语分词）
- `genanki`（Anki 包导出）
- `typer`（CLI）

**数据源**：

- Bangumi API：`/v0/users/-/collections`（OAuth 范围 `mark_episode`）
- Anime Offline Database（GitHub: `manami-project/anime-offline-database`）做 Bangumi → MAL/AniDB ID 映射
- Jimaku API：注册账号，按 MAL ID 拉字幕
- JLPT 词表：[Tanos](http://tangorin.com/) 或社区维护的 jlpt-word-list

**卖点**：「我把你看过的动画变成了一个 Anki deck」— 一句话能讲清楚。

### v0.5（再 1 个月，正式 MVP，简单 web）

**功能**：

- bangumi sync + 选 N3/N4 词表 + 每日 10 张卡 SRS
- 模式 2 作品浏览 + 模式 1 词表复习
- 卡片背面 = 文本 + 截图（公开数据库）+ TTS（Azure / OpenAI Voice）
- 字幕 LLM 标注上线（先做 difficulty + scene_score + line_type，义项消歧待 v1）

**不做**：AI podcast、chat tutor、视频上传、模糊召回。

**栈**：Postgres + tsvector + Next.js / FastAPI + Bangumi OAuth。Supabase 起步省事。

### v1.0（再 2-3 个月）

- LLM 完整标注（义项消歧 + 语法 pattern + 翻译生成）
- 模式 3 单点查询作为公共入口（SEO 流量，可分享链接）
- Bangumi 没有的剧集 → 用户上传 .srt → 按需 LLM 标注
- 每日 AI 通勤电台 podcast（mp3 feed）
- 推送一词（Telegram bot 起步）
- 歌词模式（接 Last.fm / 网易云）
- pgvector 上线（用于模糊召回）

### v2.0（半年后）

- Whisper ASR 视频上传（综艺 / 电影 / YouTube 链接）
- Chat tutor（agent + 工具调用）
- 浏览器插件（B 站 / YouTube 看片实时挖句）
- 移动端
- 接 MAL / AniList / 豆瓣 / Trakt
- 用户互助词包共享

---

## 12. 开放问题（需要用户决定）

1. **Bangumi 唯一性**：MAL/AniList 是否第一阶段也接？倾向不接，先看 Bangumi 用户增长。
2. **音乐何时上**：歌词模式技术简单但是新交互，v0.5 还是 v1？
3. **付费模型**：完全免费 / 订阅 / freemium？影响 OAuth 范围。
4. **B 站字幕抓取的合规边界**：法务上要谨慎，可能要避开。
5. **TTS 选型**：Azure / OpenAI / ElevenLabs / 本地？影响成本。
6. **截图来源**：公开数据库 / 用户上传 / 不展示？涉及版权。
7. **首发市场**：国内（B 站、小红书宣发）还是海外（reddit r/LearnJapanese）？
8. **域名 / 品牌**：还没想。
9. **作者自己日语进度**：N 几？现在用什么工具？最痛 gap 在哪？这个会影响 dogfooding 的能用度判断。

---

## 13. 给下一个 agent 的第一阶段任务（v0.1）

### Task 1：调研 + setup（半天）

1. 注册 Bangumi 应用（[https://bgm.tv/dev/app](https://bgm.tv/dev/app)），拿到 client_id / secret
2. 注册 Jimaku 账号，拿 API key
3. 下载最新 Anime Offline Database 数据（一个 JSON 文件）
4. 找一份 JLPT N5-N1 词表（json/csv 即可，社区维护版本）
5. 创建项目骨架：

```
~/jp-learn/
├── README.md
├── pyproject.toml
├── jpcorpus/           # CLI 包
│   ├── __init__.py
│   ├── cli.py          # typer 入口
│   ├── bangumi.py      # OAuth + collection API
│   ├── jimaku.py       # 字幕拉取
│   ├── anime_db.py     # ID 映射
│   ├── tokenize.py     # fugashi wrapping
│   ├── jlpt.py         # JLPT 词表加载
│   ├── corpus_export.py # 结构化语料导出
│   └── anki_export.py  # genanki 导出
├── data/
│   ├── anime-offline-database.json  # 缓存
│   ├── jlpt-words.json               # 缓存
│   └── jimaku-cache/                 # 字幕本地缓存
└── tests/
```

### Task 2：Bangumi OAuth + 拉看过列表（半天）

- 实现 `jpcorpus link bangumi` — 启 local 8080 接 OAuth callback
- 实现 `jpcorpus sync` 第一步：拉用户看过列表（type=2 表示 watched，subject_type=2 表示 anime）
- 持久化到本地 sqlite（项目内 `~/.jpcorpus/state.db`）

### Task 3：ID 映射 + Jimaku 拉字幕（半天）

- 用 Anime Offline DB 把 Bangumi ID → MAL ID
- Jimaku API 按 MAL ID 拉字幕（有日字优先）
- 报告匹配率：47 部里多少能找到字幕

### Task 4：分词 + 词频统计（半天）

- fugashi + UniDic 分词
- 词形归一化（活用 → 基本形）
- 跟 JLPT 词表 join，标 N 级
- 生成报告：

```markdown
# 你的日语个人词频报告

总览：
- 47 部看过 → 38 部有字幕 → 412,834 个词形 → 12,847 个独特词
- 已涵盖 JLPT N5: 98% / N4: 87% / N3: 54% / N2: 31% / N1: 12%

## 你最该学的 N3 词（按"出现频次 × 你不会"排序）
| 词 | 假名 | 频次 | 来自作品 |
|---|---|---|---|
| 出る | でる | 1,247 | 千与千寻、孤独摇滚、葬送のフリーレン... |
| ...

## 按作品的覆盖
| 作品 | 总词形 | N3 你不会的 |
|---|---|---|
| 孤独摇滚 | 12,400 | 187 |
...
```

### Task 5：Anki 导出（半天）

- genanki 生成 .apkg
- 卡片字段：`word | reading | translation | example_sentence | source`
- 例句先用第一次出现的字幕原句（不做 LLM 优选 — 那是 v0.5）

### Task 6：作者自己跑一次（半天）

- 全程自跑一遍
- 看数据质量、看报告是否真的有用、看 Anki deck 是否值得每天用
- 如果"我自己愿意每天用这个 deck" → 继续 v0.5
- 如果"还差点意思" → 找出差在哪，调整

---

## 14. 项目目录约定

下一个 agent 操作时建议路径结构：

```
~/jp-learn/                # 项目根
├── SPEC.md                # 这份文档（建议把本文件软链接进去）
├── jpcorpus/              # v0.1 CLI 工具
├── web/                   # v0.5+ web 应用
├── pipeline/              # 字幕 LLM 标注 batch（v0.5+）
└── notes/                 # 探索性笔记
```

---

## 15. 重要边界 / 不要做的事情

- ❌ 不要无脑用 Lance（数据量不够，徒增复杂）
- ❌ 不要让 LLM 一次性 join 大集合（标题映射要走 ID 表 + retrieval）
- ❌ 不要 MVP 阶段就想做"完美跳转回看视频"（不可解，且不是核心）
- ❌ 不要先做向量检索系统（70% 查询用 SQL 就够，向量是 v1 加）
- ❌ 不要先做 chat tutor（没数据底层时是花瓶）
- ❌ 不要 v0.1 阶段做 web（CLI 验证想法 + 发帖测水温优先）

---

## 16. 决策一句话总结

| 维度 | 决定 |
|---|---|
| 产品定位 | "把你看过的内容变成你的 JLPT 教材" |
| MVP | CLI + Bangumi → Anki deck（v0.1，2-3 周）|
| 核心模式 | 模式 1（词表 SRS）+ 模式 2（作品浏览） |
| 数据库 | Postgres + tsvector + pgvector，**不要 Lance** |
| 向量检索 | v1 才上，70% 查询不用 |
| LLM 用法 | 单点 + 尾部裁决，**绝不让它做大集合 join** |
| 字幕来源 | Jimaku 主 + Whisper 兜底 |
| 观看历史 | Bangumi only（MVP）|
| 跳转回看 | MVP 不做 |
| 杀手 feature（v1）| 每日 AI 通勤电台 podcast |

---

文档结束。下一个 agent 请从 §13 Task 1 开始。
