"""Tests for Dedicated Persona Creation Studio endpoints, intermediate artifacts, and editing workflow."""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import yaml

from deep_persona.llm.base import BaseLLM, LLMResponse
from deep_persona.web.server import app

client = TestClient(app)

SAMPLE_STORY = """
第一章 鲁镇的冬日
旧历的年底毕竟最像年底，村镇上不必说，就在天空中也显出将到新年的气象来。
祥林嫂在鲁镇街头拦住我，眼神空洞，步履迟缓。她对我说道：'人死了之后，究竟有没有灵魂的？'
她双手神经质地搓着洗得发白的粗布围裙，两眼直视前方，呆呆地立着。
"""

SAMPLE_MOCK_PERSONA = {
    "id": "xianglin_sao",
    "name": "祥林嫂",
    "age": 42,
    "role": "鲁镇帮工女仆",
    "scenario_title": "鲁镇冬日街头的灵魂追问",
    "scenario_initial_context": "新年前夕，祥林嫂在鲁镇街头拦住返乡的读书人，急切证实人死后是否有灵魂。",
    "scenario_user_role": "同乡读书人",
    "scenario_persona_role": "祥林嫂",
    "communication_style": ["重复念叨同一句话", "语气怯懦发颤"],
    "emotional_tone": ["麻木哀绝", "神经质惶恐"],
    "observable_behavior": ["双手神经质地搓粗布围裙", "两眼直视前方"],
    "beliefs": ["人死后真的有阎罗地狱", "做了错事死后会被锯开分给两个男人"],
    "conditional_secrets": [
        {
            "id": "threshold_donation",
            "content": "我在土地庙捐了门槛，本以为替自己赎了身，但祭祀时他们还是不许我沾手祭具。",
            "reveal_if": ["trust >= 0.50"],
        }
    ],
    "motivations": ["赎罪渴望", "对阿毛灵魂安息的执念"],
    "fears": ["死后被阎王锯开分尸", "阿毛在阴间受冻挨饿"],
    "psychological_needs": ["解除罪恶感", "被同乡视为普通活人接纳"],
}


class MockStudioExtractorLLM(BaseLLM):
    def generate(self, messages, system_prompt=None, temperature=0.7, max_tokens=1024, **kwargs) -> LLMResponse:
        return LLMResponse(
            content=f"```json\n{json.dumps(SAMPLE_MOCK_PERSONA, ensure_ascii=False)}\n```",
            model="mock",
        )


def test_serve_create_page():
    """Verify /create and /create.html serve the dedicated creation studio page."""
    res1 = client.get("/create")
    assert res1.status_code == 200
    assert "Deep Persona Forge" in res1.text or "create-container" in res1.text

    res2 = client.get("/create.html")
    assert res2.status_code == 200
    assert "Deep Persona Forge" in res2.text or "create-container" in res2.text


def test_extract_persona_with_intermediate_artifacts(monkeypatch):
    """Verify /api/personas/extract returns extracted persona plus intermediate scenes, evidence, and critique report."""
    monkeypatch.setattr(
        "deep_persona.persona.extractor.GeminiLLM",
        MockStudioExtractorLLM,
    )

    response = client.post(
        "/api/personas/extract",
        data={
            "character_name": "祥林嫂",
            "story_text": SAMPLE_STORY,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["character_name"] == "祥林嫂"
    assert "extracted" in data
    assert data["extracted"]["id"] == "xianglin_sao"

    # Verify intermediate artifacts are present
    assert "intermediate" in data
    intermediate = data["intermediate"]
    assert "scenes" in intermediate
    assert len(intermediate["scenes"]) >= 1
    assert "evidence_list" in intermediate
    assert "critique_report" in intermediate
    report = intermediate["critique_report"]
    assert "grounded_ratio" in report
    assert "total_hypotheses" in report


def test_compile_from_evidence_api():
    """Verify /api/personas/compile-from-evidence re-compiles and audits from structured evidence."""
    sample_evidence = [
        {
            "id": "ev_001",
            "source": {"chapter": 1, "scene": "鲁镇街头", "span": "人死了之后，究竟有没有灵魂的？"},
            "type": "dialogue",
            "context": {"situation": "街头偶遇问询", "interlocutor": "我 (读书人)"},
            "observation": {"speech": "人死了之后，究竟有没有灵魂的？", "content": "求证灵魂存在"},
            "confidence": 0.95,
        },
        {
            "id": "ev_002",
            "source": {"chapter": 1, "scene": "鲁镇街头", "span": "双手神经质地搓着洗得发白的粗布围裙"},
            "type": "behavior",
            "context": {"situation": "精神高度焦虑", "interlocutor": "我"},
            "observation": {"behavior": "搓粗布围裙", "content": "躯体应激防御"},
            "confidence": 0.90,
        },
    ]

    response = client.post(
        "/api/personas/compile-from-evidence",
        json={
            "character_name": "祥林嫂",
            "evidence_list": sample_evidence,
            "run_llm_critic": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["character_name"] == "祥林嫂"
    assert "extracted" in data
    assert "external_layer" in data["extracted"]
    assert "middle_layer" in data["extracted"]
    assert "internal_layer" in data["extracted"]
    assert "critique_report" in data
    assert data["critique_report"]["is_valid"] is True


def test_get_persona_detail_api():
    """Verify GET /api/personas/{id} returns config and raw YAML string."""
    response = client.get("/api/personas/evelyn")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["id"] == "evelyn"
    assert data["name"] == "Evelyn"
    assert "config" in data
    assert "raw_yaml" in data
    assert "persona:" in data["raw_yaml"]

    # Test non-existent persona returns 404
    notFoundRes = client.get("/api/personas/non_existent_persona_999")
    assert notFoundRes.status_code == 404


def test_validate_yaml_api():
    """Verify POST /api/personas/validate-yaml validates against PersonaConfig."""
    valid_yaml = """
persona:
  id: test_person
  name: Test Person
  age: 30
  role: Tester
scenario:
  title: Test Scenario
  initial_context: Testing in progress
  user_role: User
  persona_role: Tester
external_layer:
  communication_style: [direct]
  emotional_tone: [calm]
  observable_behavior: [focused]
middle_layer:
  beliefs: [testing is good]
  conditional_information: []
  resistance_patterns: []
internal_layer:
  motivations: [quality assurance]
  fears: [bugs in production]
  psychological_needs: [clarity]
  non_disclosure_rules: [never reveal directly]
dynamics:
  initial_stage: guarded
  stages:
    guarded:
      description: guarded
  transitions: []
embodied_expression:
  enabled: true
  format: "[action]"
  allowed: [gaze, posture]
constraints:
  - remain in role
evidence_index: []
"""
    res1 = client.post("/api/personas/validate-yaml", json={"yaml_content": valid_yaml})
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["valid"] is True
    assert data1["id"] == "test_person"
    assert data1["name"] == "Test Person"

    # Malformed YAML
    invalid_yaml = "persona:\n  id: invalid\n  missing_required_fields: true"
    res2 = client.post("/api/personas/validate-yaml", json={"yaml_content": invalid_yaml})
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["valid"] is False
    assert "error" in data2


def test_create_and_overwrite_persona_flow(tmp_path, monkeypatch):
    """Verify saving a new persona and overwriting with updated configuration."""
    from deep_persona.web import server

    monkeypatch.setattr(server, "PERSONAS_DIR", tmp_path)

    payload = {
        "id": "studio_doctor",
        "name": "Doctor Alex",
        "age": 28,
        "role": "Resident Physician",
        "scenario_title": "Emergency Triage Confrontation",
        "scenario_initial_context": "The senior consultant enters demanding an explanation.",
        "scenario_user_role": "Senior Consultant",
        "scenario_persona_role": "Doctor Alex",
        "communication_style": ["hesitant", "polite"],
        "emotional_tone": ["anxious"],
        "observable_behavior": ["fidgets with pen"],
        "beliefs": ["must avoid mistakes"],
        "conditional_secrets": [
            {
                "id": "secret_shift",
                "content": "Worked a 36-hour continuous shift.",
                "reveal_if": ["trust >= 0.5"],
            }
        ],
        "motivations": ["professional survival"],
        "fears": ["losing license"],
        "psychological_needs": ["safety"],
        "evidence_index": [
            {
                "id": "ev_001",
                "source": {"chapter": 1, "scene": "ER", "span": "I checked the charts twice."},
                "type": "dialogue",
                "context": {"situation": "triage", "interlocutor": "consultant"},
                "observation": {"speech": "I checked the charts twice.", "content": "chart check"},
                "confidence": 0.95,
            }
        ],
        "overwrite": True,
    }

    # First save
    res = client.post("/api/personas/create", json=payload)
    assert res.status_code == 200
    created = res.json()
    assert created["status"] == "created"
    assert created["persona_id"] == "studio_doctor"

    saved_file = tmp_path / "studio_doctor.yaml"
    assert saved_file.exists()

    with open(saved_file, "r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f)
    assert loaded["persona"]["name"] == "Doctor Alex"
    assert len(loaded["evidence_index"]) == 1
    assert loaded["evidence_index"][0]["id"] == "ev_001"

    # Overwrite with modified age
    payload["age"] = 29
    res_overwrite = client.post("/api/personas/create", json=payload)
    assert res_overwrite.status_code == 200

    with open(saved_file, "r", encoding="utf-8") as f:
        reloaded = yaml.safe_load(f)
    assert reloaded["persona"]["age"] == 29
