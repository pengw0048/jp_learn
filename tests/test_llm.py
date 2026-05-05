import json

import httpx

from jpcorpus.llm import (
    DEFAULT_ANTHROPIC_BASE_URL,
    DEFAULT_ANTHROPIC_MODEL,
    AnthropicClient,
    LLMConfig,
    annotate_corpus,
    build_annotation_prompt,
    parse_annotation_response,
)
from jpcorpus.state import State


class FakeAnnotationClient:
    def __init__(self) -> None:
        self.calls = 0

    def annotate_example(self, word, example):
        self.calls += 1
        return {
            "translation_zh": f"翻译: {example['sentence']}",
            "usage_note_zh": f"{word['word']} 在这里是目标词。",
            "scene_description": "简短场景。",
        }


class FailingAnnotationClient:
    def annotate_example(self, word, example):
        if "失敗" in example["sentence"]:
            raise RuntimeError("intentional failure")
        return {
            "translation_zh": f"翻译: {example['sentence']}",
            "usage_note_zh": f"{word['word']} 在这里是目标词。",
            "scene_description": "",
        }


def test_parse_annotation_response_accepts_json_fence():
    payload = parse_annotation_response(
        """```json
        {
          "translation_zh": "我明天去。",
          "usage_note_zh": "行く表示移动。",
          "scene_description": "角色在说明计划。"
        }
        ```"""
    )

    assert payload["translation_zh"] == "我明天去。"
    assert payload["usage_note_zh"] == "行く表示移动。"
    assert payload["scene_description"] == "角色在说明计划。"


def test_parse_annotation_response_accepts_json_like_lines():
    payload = parse_annotation_response(
        """
        {
          "translation_zh": "请问岡崎さん，有什么话要说吗？",
          "usage_note_zh": "言う表示"说"。",
          "scene_description": "角色在询问对方。"
        }
        """
    )

    assert payload["translation_zh"] == "请问岡崎さん，有什么话要说吗？"
    assert payload["usage_note_zh"] == '言う表示"说"。'


def test_build_annotation_prompt_keeps_scene_empty():
    prompt = build_annotation_prompt(
        {"word": "行く", "reading": "いく", "level": "N5"},
        {"sentence": "明日行く。", "matched_text": "行く"},
    )

    assert "- scene_description: an empty string." in prompt


def test_anthropic_client_uses_messages_api():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert str(request.url) == f"{DEFAULT_ANTHROPIC_BASE_URL}/messages"
        assert request.headers["x-api-key"] == "test-key"
        assert request.headers["anthropic-version"] == "2023-06-01"
        assert body["model"] == DEFAULT_ANTHROPIC_MODEL
        assert body["messages"][0]["role"] == "user"
        return httpx.Response(
            200,
            json={
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "translation_zh": "我明天去。",
                                "usage_note_zh": "行く表示移动。",
                                "scene_description": "",
                            },
                            ensure_ascii=False,
                        ),
                    }
                ]
            },
        )

    client = AnthropicClient(
        LLMConfig(
            model=DEFAULT_ANTHROPIC_MODEL,
            base_url=DEFAULT_ANTHROPIC_BASE_URL,
            api_key="test-key",
            transport=httpx.MockTransport(handler),
        )
    )

    payload = client.annotate_example(
        {"word": "行く", "reading": "いく", "level": "N5"},
        {"sentence": "明日行く。", "matched_text": "行く"},
    )

    assert payload["translation_zh"] == "我明天去。"
    assert payload["usage_note_zh"] == "行く表示移动。"
    assert payload["scene_description"] == ""


def test_annotate_corpus_adds_missing_example_annotations():
    corpus = {
        "schema_version": 3,
        "words": [
            {
                "word": "行く",
                "examples": [
                    {"sentence": "明日行く。"},
                    {
                        "sentence": "学校へ行く。",
                        "translation_zh": "去学校。",
                        "usage_note_zh": "已有。",
                        "scene_description": "已有。",
                    },
                ],
            }
        ],
    }
    client = FakeAnnotationClient()

    payload, count = annotate_corpus(corpus, client=client, limit=10)

    assert count == 1
    assert client.calls == 1
    assert payload["schema_version"] == 6
    assert payload["annotation"]["fields"] == [
        "translation_zh",
        "usage_note_zh",
        "scene_description",
    ]
    assert payload["words"][0]["examples"][0]["translation_zh"] == "翻译: 明日行く。"
    assert payload["words"][0]["examples"][1]["translation_zh"] == "去学校。"


def test_annotate_corpus_reuses_versioned_cache(tmp_path):
    corpus = {
        "schema_version": 6,
        "words": [
            {
                "word": "行く",
                "reading": "いく",
                "level": "N5",
                "examples": [{"sentence": "明日行く。"}],
            }
        ],
    }
    state = State(tmp_path / "state.db")
    first_client = FakeAnnotationClient()
    second_client = FakeAnnotationClient()

    annotate_corpus(
        corpus,
        client=first_client,
        limit=10,
        cache_state=state,
        cache_context={"provider": "test", "model": "fake"},
    )
    corpus["words"][0]["examples"][0]["translation_zh"] = None
    corpus["words"][0]["examples"][0]["usage_note_zh"] = None
    corpus["words"][0]["examples"][0]["scene_description"] = None
    annotate_corpus(
        corpus,
        client=second_client,
        limit=10,
        cache_state=state,
        cache_context={"provider": "test", "model": "fake"},
    )

    assert first_client.calls == 1
    assert second_client.calls == 0
    assert corpus["words"][0]["examples"][0]["translation_zh"] == "翻译: 明日行く。"


def test_annotate_corpus_concurrency_continues_after_failures():
    corpus = {
        "schema_version": 6,
        "words": [
            {
                "word": "行く",
                "examples": [
                    {"sentence": "明日行く。"},
                    {"sentence": "これは失敗する。"},
                    {"sentence": "学校へ行く。"},
                ],
            }
        ],
    }
    errors = []

    payload, count = annotate_corpus(
        corpus,
        client=FailingAnnotationClient(),
        limit=3,
        concurrency=2,
        on_error=lambda word, example, exc: errors.append((word, example, exc)),
    )

    examples = payload["words"][0]["examples"]
    assert count == 2
    assert len(errors) == 1
    assert examples[0]["translation_zh"] == "翻译: 明日行く。"
    assert "translation_zh" not in examples[1]
    assert examples[2]["translation_zh"] == "翻译: 学校へ行く。"
