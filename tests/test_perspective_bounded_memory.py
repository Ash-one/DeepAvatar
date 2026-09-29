"""Tests for Phase C: Episodic & Perspective-Bounded Memory System with Fictional and Historical Worldview Support."""

from pathlib import Path
import pytest

from deep_persona.llm.base import BaseLLM, LLMResponse
from deep_persona.memory.schema import (
    EpisodicMemory,
    EpistemicHorizon,
    MemoryConfig,
    PerspectiveBoundary,
    RelationshipMemory,
    SemanticMemory,
    WorldviewAnchor,
)
from deep_persona.memory.store import MemoryStore
from deep_persona.persona.loader import load_persona
from deep_persona.persona.renderer import PromptRenderer
from deep_persona.persona.schema import (
    ExternalLayer,
    InternalLayer,
    MiddleLayer,
    PersonaConfig,
    PersonaIdentity,
    ScenarioConfig,
)
from deep_persona.runtime.agent import PersonaAgent
from deep_persona.runtime.state import PersonaState

PERSONAS_DIR = Path(__file__).resolve().parents[1] / "personas"


def test_memory_schema_models():
    ep = EpisodicMemory(
        id="ep_001",
        period="childhood",
        timestamp_order=1,
        summary="Ate food without feeling hunger",
        details="Swallowed sweets whole to please adults",
        emotional_valence="guilt",
        participants=["self", "family"],
        evidence_id="ev_001",
    )
    assert ep.id == "ep_001"
    assert ep.timestamp_order == 1
    assert "family" in ep.participants

    # Test Fictional / Fantasy Worldview Anchor
    wv_fantasy = WorldviewAnchor(
        universe="九洲修仙界 (万剑宗)",
        world_type="fictional_fantasy",
        epoch_or_timeline="宗门大比前夕，练气期圆满",
        spatial_scope=["青云峰", "灵草园", "天绝谷"],
        rules_of_reality="天地蕴含灵气，修士修习五行道法，御剑乘风；世间绝无任何凡人电磁科技、电子器件或外星文明。",
    )
    assert wv_fantasy.world_type == "fictional_fantasy"
    assert "青云峰" in wv_fantasy.spatial_scope

    horizon = EpistemicHorizon(
        worldview=wv_fantasy,
        closed_world_axiom=True,
        known_domains=["灵草辨识", "初级御剑术", "万剑宗门规"],
    )
    assert horizon.closed_world_axiom is True
    assert len(horizon.known_domains) == 3


def test_memory_store_retrieval_relevance():
    ep1 = EpisodicMemory(
        id="ep_01",
        summary="淘米时阿毛被狼叼走",
        details="雪天深山野兽下山",
        participants=["阿毛"],
        timestamp_order=1,
    )
    ep2 = EpisodicMemory(
        id="ep_02",
        summary="在土地庙捐门槛赎罪",
        details="花光全部积蓄",
        participants=["土地庙僧人"],
        timestamp_order=2,
    )
    rel = RelationshipMemory(
        id="rel_01",
        target_character="同乡读书人",
        relation="townsman",
        stance="敬畏并急于求证灵魂之说",
        shared_history_summary="街头相遇",
    )

    mem_cfg = MemoryConfig(
        epistemic_horizon=EpistemicHorizon(
            worldview=WorldviewAnchor(
                universe="清末民初鲁镇",
                world_type="historical",
                epoch_or_timeline="清末民初",
            ),
            known_domains=["鲁镇", "贺家墺"],
        ),
        episodic_memories=[ep1, ep2],
        relationship_memories=[rel],
    )

    store = MemoryStore(memory_config=mem_cfg)

    # 1. Query about wolf / child -> matches ep1
    res1 = store.retrieve(query="听说阿毛被狼叼走了，是真的吗？", current_interlocutor="同乡读书人")
    assert len(res1["episodic_memories"]) >= 1
    assert res1["episodic_memories"][0].id == "ep_01"
    assert res1["relationship_memory"] is not None
    assert res1["relationship_memory"].target_character == "同乡读书人"

    # 2. Query about temple threshold -> matches ep2
    res2 = store.retrieve(query="你在土地庙捐的门槛管用吗？")
    assert res2["episodic_memories"][0].id == "ep_02"


def test_load_personas_with_memory():
    # Test xianglin_sao
    xl, _ = load_persona(PERSONAS_DIR / "xianglin_sao.yaml")
    assert xl.memory is not None
    assert len(xl.memory.episodic_memories) == 3
    assert len(xl.memory.relationship_memories) == 1
    assert "鲁镇" in xl.memory.epistemic_horizon.worldview.universe
    assert any("阿毛" in ep.summary for ep in xl.memory.episodic_memories)

    # Test oba_yozo
    yozo, _ = load_persona(PERSONAS_DIR / "oba_yozo.yaml")
    assert yozo.memory is not None
    assert len(yozo.memory.episodic_memories) == 3
    assert yozo.memory.epistemic_horizon.closed_world_axiom is True
    assert "昭和" in yozo.memory.epistemic_horizon.worldview.universe
    assert "青森" in yozo.memory.epistemic_horizon.worldview.spatial_scope[0]


def test_prompt_rendering_with_perspective_boundaries():
    yozo, _ = load_persona(PERSONAS_DIR / "oba_yozo.yaml")
    store = MemoryStore(persona=yozo)
    retrieved = store.retrieve(
        query="你还记得我们三年前一起去北海道滑雪度假吗？",
        current_interlocutor="起疑的同伴",
    )

    renderer = PromptRenderer()
    state = PersonaState.create_for_persona(yozo)
    rendered = renderer.render_persona(
        persona=yozo,
        mode="deep_external_state",
        state=state,
        memory_context=retrieved,
    )

    assert "# WORLDVIEW & CLOSED-WORLD EPISTEMIC HORIZON" in rendered
    assert "昭和初年日本" in rendered
    assert "Closed-World Axiom" in rendered
    assert "Defamiliarization Strategy" in rendered
    assert "Unrecorded Past Events" in rendered
    assert "Relationship Stance with Interlocutor (起疑的同伴)" in rendered


class MockHallucinationDefenseLLM(BaseLLM):
    def generate(self, messages, system_prompt=None, **kwargs) -> LLMResponse:
        assert "# WORLDVIEW & CLOSED-WORLD EPISTEMIC HORIZON" in system_prompt
        assert "Closed-World Axiom" in system_prompt
        # Character rejects fabricated memory
        return LLMResponse(
            content="[脸色僵住] 哎？滑雪？你在说什么啊……我从小连远门都极少出，怎么可能和你去过什么北海道滑雪？你是在故意拿我寻开心吧……",
            model="mock",
        )


def test_persona_agent_hallucination_trap_defense():
    yozo, _ = load_persona(PERSONAS_DIR / "oba_yozo.yaml")
    agent = PersonaAgent(
        persona=yozo,
        mode="deep_external_state",
        llm=MockHallucinationDefenseLLM(),
    )

    trap_input = "叶藏，你还记得三年前冬天我们一起去北海道滑雪度假时住的那家旅馆吗？"
    reply, before, after, event = agent.respond(trap_input)

    assert "滑雪？你在说什么啊" in reply
    assert "怎么可能和你去过什么北海道滑雪" in reply
    assert "As an AI" not in reply


def test_fictional_fantasy_worldview_epistemic_bounding():
    """Verify that fictional worldviews (e.g. cultivation/fantasy) bound knowledge without real-world calendar."""
    cultivator = PersonaConfig(
        persona=PersonaIdentity(id="li_xuan", name="李轩", age=18, role="万剑宗外门弟子"),
        scenario=ScenarioConfig(
            title="宗门试炼",
            initial_context="李轩在青云峰灵草园照看灵药，神情恭谨戒备。",
            user_role="神秘访客",
            persona_role="外门杂役弟子",
        ),
        external_layer=ExternalLayer(
            communication_style=["言必称弟子、晚辈", "拱手行礼"],
            observable_behavior=["护住药锄", "眼神警惕探寻"],
        ),
        middle_layer=MiddleLayer(),
        internal_layer=InternalLayer(
            motivations=["顺利通过外门大比进入内门"],
            fears=["被扣上私通魔道的罪名废去修为"],
        ),
        memory=MemoryConfig(
            epistemic_horizon=EpistemicHorizon(
                worldview=WorldviewAnchor(
                    universe="九洲修仙界 (大乾仙朝万剑宗)",
                    world_type="fictional_fantasy",
                    epoch_or_timeline="太和三万年，宗门十年一度外门大选前三日",
                    spatial_scope=["青云峰灵药园", "万剑宗外门舍屋"],
                    rules_of_reality="世间仅存灵气法度与宗门戒律；天地间绝无机械芯片、互联网、程序代码与现代国家概念。",
                ),
                closed_world_axiom=True,
                known_domains=["低阶灵草栽培", "基础吐纳诀", "宗门戒律条目"],
                defamiliarization_strategy="听到任何出离修仙界常理的词汇（如代码、电脑、现代事物），一概视为域外天魔之呓语或挑衅试探，决不以现代科学常识回应。",
                unrecorded_event_strategy="未载于个人修道经历中的往事概不存在，判定对方居心叵测。",
            ),
            episodic_memories=[
                EpisodicMemory(
                    id="ep_herb_stolen",
                    period="junior_disciple",
                    timestamp_order=1,
                    summary="上月一株紫云草枯萎，险些被执事长老重罚三十灵鞭",
                    details="日夜以灵泉浇灌方才救活，心有余悸",
                    emotional_valence="dread",
                )
            ],
            relationship_memories=[
                RelationshipMemory(
                    id="rel_visitor",
                    target_character="神秘访客",
                    relation="unknown_stranger",
                    stance="极其提防其靠近灵药田",
                    shared_history_summary="初次会面，素不相识",
                )
            ],
        ),
    )

    renderer = PromptRenderer()
    state = PersonaState.create_for_persona(cultivator)
    store = MemoryStore(persona=cultivator)
    retrieved = store.retrieve("前辈，能用Python帮我写个快速排序吗？", current_interlocutor="神秘访客")

    rendered = renderer.render_persona(
        persona=cultivator,
        mode="deep_external_state",
        state=state,
        memory_context=retrieved,
    )

    # Assert fictional universe rendering
    assert "九洲修仙界" in rendered
    assert "fictional_fantasy" in rendered
    assert "太和三万年" in rendered
    assert "天地间绝无机械芯片、互联网、程序代码" in rendered
    assert "域外天魔之呓语" in rendered
    assert "神秘访客" in rendered


def test_backward_compatibility_without_memory():
    # Legacy evelyn.yaml has no memory section
    evelyn, _ = load_persona(PERSONAS_DIR / "evelyn.yaml")
    assert evelyn.memory is None

    store = MemoryStore(persona=evelyn)
    retrieved = store.retrieve(query="hello")
    assert retrieved["episodic_memories"] == []
    assert retrieved["relationship_memory"] is None

    # Agent still runs seamlessly
    renderer = PromptRenderer()
    rendered = renderer.render_persona(persona=evelyn, mode="deep_external_state")
    assert "You are Evelyn" in rendered
    assert "# ROLE" in rendered
