import io
import json
import pytest
from fastapi.testclient import TestClient

from deep_persona.llm.base import BaseLLM, LLMResponse
from deep_persona.persona.extractor import StoryPersonaExtractor, extract_json_from_llm_response
from deep_persona.web.server import app

SAMPLE_EXTRACTED_JSON = {
    "id": "xianglin_sao",
    "name": "祥林嫂",
    "age": 40,
    "role": "鲁镇鲁四老爷家的女帮工",
    "scenario_title": "阿毛之殇的反复倾诉与求证",
    "scenario_initial_context": "祥林嫂在鲁镇街头遇到镇上的熟人，眼神呆滞，反复念叨起阿毛被狼叼走的故事，求证人死后是否有灵魂。",
    "scenario_user_role": "鲁镇茶馆同乡",
    "scenario_persona_role": "祥林嫂",
    "communication_style": ["反复唠叨同一句话", "声音凄凉发颤", "眼神空洞游移"],
    "emotional_tone": ["麻木", "极度自责", "惶恐不安"],
    "observable_behavior": ["双手神经质地搓着围裙", "眼角挂着干涸的泪痕", "缩着头弓着背"],
    "beliefs": ["人死后真的有阎罗王和灵魂", "阿毛的死全是因为自己没看好屋门"],
    "conditional_secrets": [
        {
            "id": "landlord_temple_threshold",
            "content": "我听说捐了土地庙门槛千人踏万人跨就能赎清罪孽，可为什么他们祭祀时还是不让我端酒杯？",
            "reveal_if": ["trust >= 0.50"],
        }
    ],
    "motivations": ["赎罪渴望", "对阿毛灵魂安息的执念", "在宗法礼教压迫下寻求一缕心理安全感"],
    "fears": ["死后被阎王锯开分给两个丈夫", "阿毛在阴间受冻挨饿", "再次被所有人鄙弃推开"],
    "psychological_needs": ["被接纳感", "解除罪恶感"],
}


class MockExtractorLLM(BaseLLM):
    def generate(self, messages, system_prompt=None, temperature=0.7, max_tokens=1024, **kwargs) -> LLMResponse:
        return LLMResponse(
            content=f"```json\n{json.dumps(SAMPLE_EXTRACTED_JSON, ensure_ascii=False)}\n```",
            model="mock",
        )


def test_extract_json_from_llm_response():
    # 1. Direct JSON
    res1 = extract_json_from_llm_response('{"a": 1, "b": "hello"}')
    assert res1 == {"a": 1, "b": "hello"}

    # 2. Markdown fence
    res2 = extract_json_from_llm_response('```json\n{"name": "Leo", "age": 10}\n```')
    assert res2 == {"name": "Leo", "age": 10}

    # 3. Text wrapper
    res3 = extract_json_from_llm_response('Here is the profile:\n{"role": "detective"}\nHope this helps!')
    assert res3 == {"role": "detective"}


def test_story_persona_extractor_mock():
    mock_llm = MockExtractorLLM()
    extractor = StoryPersonaExtractor(llm=mock_llm)
    extracted = extractor.extract_from_story(
        story_text="旧历的年底毕竟最像年底，村镇上不必说，就在天空中也显出将到新年的气象来...",
        character_name="祥林嫂",
    )
    assert extracted["id"] == "xianglin_sao"
    assert extracted["name"] == "祥林嫂"
    assert len(extracted["communication_style"]) == 3
    assert len(extracted["conditional_secrets"]) == 1
    assert extracted["conditional_secrets"][0]["id"] == "landlord_temple_threshold"


def test_api_extract_story_text(monkeypatch):
    client = TestClient(app)

    # Mock the LLM inside StoryPersonaExtractor
    monkeypatch.setattr(
        "deep_persona.persona.extractor.GeminiLLM",
        MockExtractorLLM,
    )

    response = client.post(
        "/api/personas/extract",
        data={
            "character_name": "祥林嫂",
            "story_text": "旧历的年底毕竟最像年底，村镇上不必说，就在天空中也显出将到新年的气象来。祥林嫂走到街上...",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["character_name"] == "祥林嫂"
    assert data["extracted"]["id"] == "xianglin_sao"


def test_api_extract_txt_file_utf8(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(
        "deep_persona.persona.extractor.GeminiLLM",
        MockExtractorLLM,
    )

    file_content = "旧历的年底毕竟最像年底，村镇上不必说，就在天空中也显出将到新年的气象来。祥林嫂的故事...".encode("utf-8")
    response = client.post(
        "/api/personas/extract",
        data={"character_name": "祥林嫂"},
        files={"file": ("blessing.txt", io.BytesIO(file_content), "text/plain")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["extracted"]["name"] == "祥林嫂"


def test_api_extract_txt_file_gbk(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(
        "deep_persona.persona.extractor.GeminiLLM",
        MockExtractorLLM,
    )

    file_content = "旧历的年底毕竟最像年底，村镇上不必说，就在天空中也显出将到新年的气象来。祥林嫂的故事...".encode("gb18030")
    response = client.post(
        "/api/personas/extract",
        data={"character_name": "祥林嫂"},
        files={"file": ("blessing_gbk.txt", io.BytesIO(file_content), "text/plain")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


def test_api_extract_validation_errors():
    client = TestClient(app)

    # 1. Missing character name
    r1 = client.post("/api/personas/extract", data={"character_name": "", "story_text": "some text here"})
    assert r1.status_code in (400, 422)

    # 2. Non-txt file
    r2 = client.post(
        "/api/personas/extract",
        data={"character_name": "Leo"},
        files={"file": ("story.pdf", io.BytesIO(b"pdf content"), "application/pdf")},
    )
    assert r2.status_code in (400, 422)
