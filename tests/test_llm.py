import json

import httpx

from jpcorpus.llm import (
    DEFAULT_ANTHROPIC_BASE_URL,
    DEFAULT_ANTHROPIC_MODEL,
    AnthropicClient,
    LLMConfig,
    build_annotation_prompt,
    parse_annotation_response,
)


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


def test_parse_annotation_response_rejects_empty_required_fields():
    try:
        parse_annotation_response('{"translation_zh": "", "usage_note_zh": "", "scene_description": ""}')
    except ValueError as exc:
        assert "missing required fields" in str(exc)
    else:
        raise AssertionError("empty required annotation fields should be rejected")


def test_build_annotation_prompt_keeps_scene_empty():
    prompt = build_annotation_prompt(
        {"word": "行く", "reading": "いく", "level": "N5"},
        {"sentence": "明日行く。", "matched_text": "行く"},
    )

    assert "- scene_description: 空字符串。" in prompt
    assert "不要出现英文单词或英文语法" in prompt
    assert "禁止照抄到输出中" in prompt


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
