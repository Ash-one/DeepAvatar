"""Tests for Evidence-Grounded Persona construction, compilation, critique, and schema extensions."""

import json
from typing import Any, Dict, List, Optional
import pytest

from deep_persona.llm.base import BaseLLM, LLMResponse
from deep_persona.persona.compiler import PersonaCompiler
from deep_persona.persona.critic import ConsistencyCritic, CritiqueReport
from deep_persona.persona.evidence_extractor import EvidenceExtractor
from deep_persona.persona.extractor import StoryPersonaExtractor, segment_narrative
from deep_persona.persona.schema import (
    BehaviorPattern,
    DynamicsBaseline,
    DynamicsConfig,
    EventSensitivity,
    Evidence,
    EvidenceContext,
    EvidenceObservation,
    EvidenceSource,
    ExternalLayer,
    InternalLayer,
    MiddleLayer,
    PersonaConfig,
    PersonaIdentity,
    ScenarioConfig,
    TraitHypothesis,
    VoiceProfile,
)


# --- MOCK LLMS FOR TESTING ---

MOCK_SCENE_EVIDENCE_RESPONSE = {
    "evidence": [
        {
            "type": "dialogue",
            "span": "祥林嫂又对我说：'人死了之后，究竟有没有灵魂的？'",
            "situation": "鲁镇街头偶遇问话",
            "interlocutor": "我 (旅行文人)",
            "speech": "人死了之后，究竟有没有灵魂的？",
            "behavior": "眼神空洞，步履迟缓",
            "content": "求证死后灵魂存在与否",
            "confidence": 0.95,
        },
        {
            "type": "behavior",
            "span": "她双手神经质地搓着洗得发白的粗布围裙，呆呆地立着。",
            "situation": "被问及阿毛之事",
            "interlocutor": "鲁镇茶客",
            "speech": None,
            "behavior": "双手搓着粗布围裙，发呆站立",
            "content": "应激躯体化动作",
            "confidence": 0.90,
        },
    ]
}

MOCK_COMPILED_PERSONA_RESPONSE = {
    "id": "xianglin_sao",
    "name": "祥林嫂",
    "age": 42,
    "role": "鲁镇帮工女仆",
    "scenario": {
        "title": "鲁镇冬日街头的灵魂追问",
        "initial_context": "新年前夕，祥林嫂在鲁镇街头拦住返乡的知识分子，急切想要证实灵魂之说。",
        "user_role": "同乡读书人",
        "persona_role": "祥林嫂",
    },
    "external_layer": {
        "communication_style": ["重复念叨", "语气怯懦发颤"],
        "emotional_tone": ["麻木哀绝", "神经质惶恐"],
        "observable_behavior": ["双手搓围裙", "两眼直视前方"],
        "behavior_patterns": [
            {
                "id": "bp_soul_inquiry",
                "trigger": {"event": "meet_intellectual", "relationship": "townsman"},
                "appraisal": ["fearing_hell_punishment", "desperate_for_reassurance"],
                "response_tendencies": {"question_about_soul": 0.9, "hesitant_withdrawal": 0.4},
                "evidence": ["ev_001"],
            }
        ],
        "voice_profile": {
            "lexical": {"sentence_length": "short", "style": "repetitive_archaic"},
            "discourse": {"preferred_patterns": ["rhetorical_confession"]},
            "pragmatic": {"directness": 0.75, "hedging": 0.15},
            "exemplars": [
                {"evidence_id": "ev_001", "quote": "人死了之后，究竟有没有灵魂的？"}
            ],
        },
    },
    "middle_layer": {
        "beliefs": ["人死后真的有阎罗地狱", "做了错事会被锯开分给两个男人"],
        "conditional_information": [
            {
                "id": "threshold_donation",
                "content": "我在土地庙捐了门槛，本以为替自己赎了身，但祭祀时他们还是不许我沾手祭具。",
                "reveal_if": ["trust >= 0.50"],
            }
        ],
        "resistance_patterns": [
            {"trigger": "mockery", "behavior": "freeze_and_stare"},
        ],
        "appraisal_patterns": ["interpreting_all_disapproval_as_sinful_uncleanliness"],
    },
    "internal_layer": {
        "motivations": ["寻求灵魂解脱", "消除阿毛惨死的愧疚"],
        "fears": ["在阴间被阎王锯成两半", "死后无法与阿毛相认"],
        "psychological_needs": ["心理赎罪感", "免于永恒惩罚的确定感"],
        "non_disclosure_rules": [
            "never state psychological needs directly as thesis statements",
            "indirectly channel dread into physical repetition and hesitant inquiries",
        ],
        "latent_hypotheses": [
            {
                "id": "hyp_spiritual_terror",
                "hypothesis": "Extreme existential dread of post-mortem retribution",
                "description": "Her incessant questioning stems from guilt rather than mere curiosity.",
                "confidence": 0.88,
                "evidence_for": ["ev_001", "ev_002"],
                "evidence_against": [],
            }
        ],
    },
    "dynamics": {
        "baseline": {
            "trust": 0.15,
            "defensiveness": 0.85,
            "engagement": 0.50,
        },
        "sensitivities": {
            "criticism": {"trust_delta": -0.20, "defensiveness_delta": 0.25, "engagement_delta": -0.10},
            "empathy": {"trust_delta": 0.15, "defensiveness_delta": -0.10, "engagement_delta": 0.15},
        },
        "recovery": {
            "trust_decay": 0.01,
            "defensiveness_decay": 0.02,
        },
    },
}


class MockMultiStageLLM(BaseLLM):
    def generate(self, messages, system_prompt=None, temperature=0.7, max_tokens=1024, **kwargs) -> LLMResponse:
        sys = system_prompt or ""
        if "evidence annotator" in sys.lower():
            return LLMResponse(content=f"```json\n{json.dumps(MOCK_SCENE_EVIDENCE_RESPONSE)}\n```", model="mock")
        elif "persona compiler" in sys.lower():
            return LLMResponse(content=f"```json\n{json.dumps(MOCK_COMPILED_PERSONA_RESPONSE)}\n```", model="mock")
        elif "consistency auditor" in sys.lower():
            critic_data = {
                "contradictions": [],
                "unsupported_claims": [],
                "suggested_counter_evidence": [],
                "suggestions": ["Groundedness is solid."],
            }
            return LLMResponse(content=f"```json\n{json.dumps(critic_data)}\n```", model="mock")
        return LLMResponse(content=f"```json\n{json.dumps(MOCK_COMPILED_PERSONA_RESPONSE)}\n```", model="mock")


# --- TESTS ---

def test_evidence_extractor_unit():
    mock_llm = MockMultiStageLLM()
    extractor = EvidenceExtractor(llm=mock_llm)
    evs = extractor.extract_from_scene(
        scene_text="旧历的年底毕竟最像年底。祥林嫂迎上来问我...",
        character_name="祥林嫂",
        chapter=1,
        scene_title="街头相遇",
    )
    assert len(evs) == 2
    assert evs[0].id == "ev_001"
    assert evs[0].type == "dialogue"
    assert evs[0].observation.speech == "人死了之后，究竟有没有灵魂的？"
    assert evs[0].source.chapter == 1
    assert evs[1].id == "ev_002"
    assert evs[1].type == "behavior"


def test_persona_compiler_unit():
    mock_llm = MockMultiStageLLM()
    compiler = PersonaCompiler(llm=mock_llm)
    sample_ev = [
        Evidence(
            id="ev_001",
            source=EvidenceSource(chapter=1, span="quote"),
            type="dialogue",
            context=EvidenceContext(situation="sit", interlocutor="int"),
            observation=EvidenceObservation(speech="quote"),
            confidence=0.9,
        )
    ]
    compiled = compiler.compile(
        character_name="祥林嫂",
        evidence_list=sample_ev,
    )
    assert compiled["id"] == "xianglin_sao"
    assert len(compiled["evidence_index"]) == 1
    assert "latent_hypotheses" in compiled["internal_layer"]
    assert len(compiled["internal_layer"]["latent_hypotheses"]) == 1
    assert compiled["internal_layer"]["latent_hypotheses"][0]["evidence_for"] == ["ev_001", "ev_002"]


def test_consistency_critic_citation_and_calibration():
    critic = ConsistencyCritic(llm=MockMultiStageLLM())
    evidence_list = [
        Evidence(
            id="ev_001",
            source=EvidenceSource(chapter=1),
            type="dialogue",
            observation=EvidenceObservation(speech="test"),
        )
    ]
    # Provide persona citing both valid ev_001 and non-existent ev_999
    persona = {
        "internal_layer": {
            "latent_hypotheses": [
                {
                    "id": "hyp_1",
                    "hypothesis": "Test hyp 1",
                    "confidence": 0.85,
                    "evidence_for": ["ev_001", "ev_999"],
                    "evidence_against": ["ev_888"],
                },
                {
                    "id": "hyp_unsupported",
                    "hypothesis": "Unbacked hyp",
                    "confidence": 0.90,
                    "evidence_for": ["ev_777"],
                    "evidence_against": [],
                },
            ]
        },
        "external_layer": {
            "behavior_patterns": [
                {"id": "bp_1", "evidence": ["ev_001", "ev_555"]}
            ]
        },
    }

    refined_persona, report = critic.audit(
        compiled_persona=persona,
        evidence_list=evidence_list,
        run_llm_critic=False,
    )

    # ev_999, ev_888, ev_777, ev_555 should be flagged as invalid citations
    assert "ev_999" in report.invalid_evidence_ids
    assert "ev_777" in report.invalid_evidence_ids
    assert "ev_555" in report.invalid_evidence_ids

    # Check refined hypotheses
    hyp1 = refined_persona["internal_layer"]["latent_hypotheses"][0]
    assert hyp1["evidence_for"] == ["ev_001"]
    assert hyp1["evidence_against"] == []

    hyp_unsupported = refined_persona["internal_layer"]["latent_hypotheses"][1]
    assert hyp_unsupported["evidence_for"] == []
    # Confidence should be heavily capped due to zero valid evidence
    assert hyp_unsupported["confidence"] <= 0.40


def test_story_segmentation():
    # Long text with paragraphs
    paras = [f"Paragraph {i}: This is detailed narrative about the town." for i in range(20)]
    story = "\n\n".join(paras)
    chunks = segment_narrative(story, max_chunk_size=300)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk["text"]) <= 500  # roughly within chunk boundaries


def test_story_persona_extractor_multi_stage_pipeline():
    mock_llm = MockMultiStageLLM()
    extractor = StoryPersonaExtractor(llm=mock_llm)
    story_text = "鲁镇的新年将到。祥林嫂走向前向我问话：'人死了之后，究竟有没有灵魂的？'"

    # 1. extract_from_story returns unified schema
    extracted = extractor.extract_from_story(story_text, character_name="祥林嫂")
    assert extracted["id"] == "xianglin_sao"
    assert "evidence_index" in extracted
    assert len(extracted["evidence_index"]) == 2
    assert "communication_style" in extracted
    assert "latent_hypotheses" in extracted["internal_layer"]

    # 2. extract_with_evidence returns artifacts
    persona, evs, report = extractor.extract_with_evidence(story_text, character_name="祥林嫂", run_llm_critic=False)
    assert len(evs) == 2
    assert isinstance(report, CritiqueReport)
    assert report.total_hypotheses >= 1


def test_v2_persona_config_schema_validation():
    # Verify that PersonaConfig can parse the complete v2 schema with Evidence, Hypotheses, BehaviorPatterns, Dynamics
    pydantic_cfg = PersonaConfig.model_validate(MOCK_COMPILED_PERSONA_RESPONSE)
    assert pydantic_cfg.persona.id == "xianglin_sao"
    assert pydantic_cfg.scenario is not None
    assert pydantic_cfg.scenario.user_role == "同乡读书人"
    assert len(pydantic_cfg.external_layer.behavior_patterns) == 1
    assert pydantic_cfg.external_layer.voice_profile is not None
    assert len(pydantic_cfg.internal_layer.latent_hypotheses) == 1
    assert pydantic_cfg.internal_layer.latent_hypotheses[0].confidence == 0.88
    assert pydantic_cfg.dynamics.baseline is not None
    assert pydantic_cfg.dynamics.baseline.trust == 0.15
    assert "criticism" in pydantic_cfg.dynamics.sensitivities
    assert pydantic_cfg.dynamics.sensitivities["criticism"].trust_delta == -0.20
