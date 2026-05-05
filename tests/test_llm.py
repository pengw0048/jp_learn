from jpcorpus.llm import annotate_corpus, parse_annotation_response
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
