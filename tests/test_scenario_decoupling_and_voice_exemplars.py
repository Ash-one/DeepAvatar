"""Tests for Phase D: Scenario Decoupling & Dynamic Voice Profile Exemplars."""

from pathlib import Path
import pytest

from deep_persona.composition.composer import SessionComposer
from deep_persona.composition.schema import RelationshipDefinition, ScenarioDefinition
from deep_persona.llm.base import BaseLLM, LLMResponse
from deep_persona.persona.loader import load_persona
from deep_persona.persona.renderer import PromptRenderer
from deep_persona.persona.voice_retriever import VoiceExemplarRetriever
from deep_persona.runtime.agent import PersonaAgent
from deep_persona.runtime.state import PersonaState

PERSONAS_DIR = Path(__file__).resolve().parents[1] / "personas"
SCENARIOS_DIR = Path(__file__).resolve().parents[1] / "scenarios"
RELATIONSHIPS_DIR = Path(__file__).resolve().parents[1] / "relationships"


def test_scenario_definition_and_loading():
    composer = SessionComposer(scenarios_dir=SCENARIOS_DIR, relationships_dir=RELATIONSHIPS_DIR)
    scen = composer.load_scenario("yozo_with_takeichi")
    assert scen.id == "yozo_with_takeichi"
    assert "竹一" in scen.user_role
    assert scen.baseline_state_offset.get("defensiveness") == 0.08

    jobs_keynote = composer.load_scenario("jobs_keynote")
    assert jobs_keynote.id == "jobs_keynote"
    assert "Moscone Center" in jobs_keynote.location


def test_relationship_definition_and_loading():
    composer = SessionComposer(scenarios_dir=SCENARIOS_DIR, relationships_dir=RELATIONSHIPS_DIR)
    rel = composer.load_relationship("oba_yozo", "takeichi")
    assert rel.id == "rel_takeichi"
    assert rel.target_character == "竹一"
    assert rel.trust_bias == 0.15
    assert len(rel.interaction_rules) >= 1


def test_session_composer_composition():
    composer = SessionComposer(scenarios_dir=SCENARIOS_DIR, relationships_dir=RELATIONSHIPS_DIR)
    yozo, _ = load_persona(PERSONAS_DIR / "oba_yozo.yaml")

    # Initial baseline
    orig_trust = yozo.dynamics.baseline.trust  # 0.10
    orig_def = yozo.dynamics.baseline.defensiveness  # 0.90

    composed = composer.compose(
        persona=yozo,
        scenario="yozo_with_takeichi",
        relationship="takeichi",
    )

    # 1. Scenario updated
    assert composed.scenario.title == "单杠下的识破"
    assert "竹一" in composed.scenario.user_role

    # 2. Baseline state altered
    # scen offset: trust -0.05, def +0.08
    # rel bias:    trust +0.15, def +0.10
    # Expected trust: 0.10 - 0.05 + 0.15 = 0.20
    # Expected def:   0.90 + 0.08 + 0.10 = 1.0 (clamped)
    assert round(composed.dynamics.baseline.trust, 2) == 0.20
    assert round(composed.dynamics.baseline.defensiveness, 2) == 1.00

    # 3. Relationship memory injected into memory store
    assert composed.memory is not None
    assert composed.memory.relationship_memories[0].target_character == "竹一"

    # 4. Constraints augmented with scenario & relationship rules
    scenario_constraints = [c for c in composed.constraints if "[Scenario]" in c]
    rel_constraints = [c for c in composed.constraints if "[Interpersonal Rule]" in c]
    assert len(scenario_constraints) >= 1
    assert len(rel_constraints) >= 1


def test_dynamic_voice_exemplar_retriever_interlocutor_and_topic_match():
    yozo, _ = load_persona(PERSONAS_DIR / "oba_yozo.yaml")
    retriever = VoiceExemplarRetriever(yozo)
    assert len(retriever.exemplars) >= 4

    # 1. Test Interlocutor Match: Talking with Takeichi
    takeichi_exemplars = retriever.retrieve(
        query="要不要一起走？外面下雨了。",
        current_interlocutor="竹一",
        top_k=2,
    )
    assert any("伞" in ex.quote for ex in takeichi_exemplars)

    # 2. Test Topic Match: Asking about monster painting
    painting_exemplars = retriever.retrieve(
        query="你这画画的是什么妖怪啊？",
        top_k=2,
    )
    assert any("妖怪" in ex.quote for ex in painting_exemplars)


def test_prompt_rendering_with_composed_session_and_dynamic_exemplars():
    composer = SessionComposer(scenarios_dir=SCENARIOS_DIR, relationships_dir=RELATIONSHIPS_DIR)
    yozo, _ = load_persona(PERSONAS_DIR / "oba_yozo.yaml")
    composed = composer.compose(
        persona=yozo,
        scenario="yozo_with_takeichi",
        relationship="takeichi",
    )

    renderer = PromptRenderer()
    state = PersonaState.create_for_persona(composed)
    retriever = VoiceExemplarRetriever(composed)
    voice_ex = retriever.retrieve("下雨了，我没带伞。", state=state, current_interlocutor="竹一")

    rendered = renderer.render_persona(
        persona=composed,
        mode="deep_external_state",
        state=state,
        voice_exemplars=voice_ex,
    )

    assert "单杠下的识破" in rendered
    assert "竹一 (看穿叶藏伪装的同窗)" in rendered
    assert "[Scenario]" in rendered
    assert "[Interpersonal Rule]" in rendered
    assert "Authentic Voice Exemplars (Contextually Resonant):" in rendered
    assert any(ex.quote in rendered for ex in voice_ex)


class MockContextualLLM(BaseLLM):
    def generate(self, messages, system_prompt=None, **kwargs) -> LLMResponse:
        assert "单杠下的识破" in system_prompt
        assert "竹一" in system_prompt
        assert "Authentic Voice Exemplars (Contextually Resonant):" in system_prompt
        return LLMResponse(
            content="[瞳孔剧烈收缩，整个人僵死在原地] （你……你说什么？你刚才看到了？！）……竹一，你、你胡说什么呐……",
            model="mock",
        )


def test_persona_agent_with_composed_session():
    composer = SessionComposer(scenarios_dir=SCENARIOS_DIR, relationships_dir=RELATIONSHIPS_DIR)
    yozo, _ = load_persona(PERSONAS_DIR / "oba_yozo.yaml")
    composed = composer.compose(
        persona=yozo,
        scenario="yozo_with_takeichi",
        relationship="takeichi",
    )

    agent = PersonaAgent(
        persona=composed,
        mode="deep_external_state",
        llm=MockContextualLLM(),
    )

    reply, before, after, event = agent.respond("叶藏，你是故意的吧？刚才在单杠上故意掉下来的。")
    assert "瞳孔剧烈收缩" in reply
    assert "竹一" in reply
