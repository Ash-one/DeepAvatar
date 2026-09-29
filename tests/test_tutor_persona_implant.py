"""Tests for Tutor Persona Implant & proactive oral dialogue practice."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from deep_persona.llm.base import BaseLLM, LLMResponse
from deep_persona.persona.loader import load_persona
from deep_persona.persona.renderer import PromptRenderer
from deep_persona.runtime.agent import PersonaAgent
from deep_persona.web.server import app

client = TestClient(app)
PERSONAS_DIR = Path(__file__).resolve().parents[1] / "personas"


class MockEchoLLM(BaseLLM):
    def generate(self, messages, system_prompt=None, temperature=0.7, max_tokens=1024, **kwargs) -> LLMResponse:
        self.last_system_prompt = system_prompt
        return LLMResponse(
            content="[抱臂] 我一直在听着呢，你刚才说的那句话是什么意思？能再详细跟我解释一下吗？",
            model="mock",
        )


def test_prompt_renderer_tutor_mode():
    """Verify tutor implant prompt block appears only when tutor_mode=True."""
    persona, _ = load_persona(PERSONAS_DIR / "evelyn.yaml")
    renderer = PromptRenderer()

    # Normal mode: No tutor directives
    prompt_normal = renderer.render_persona(persona, mode="deep_external_state", tutor_mode=False)
    assert "TUTOR PERSONA IMPLANT" not in prompt_normal

    # Tutor mode active: Injected directives
    prompt_tutor = renderer.render_persona(persona, mode="deep_external_state", tutor_mode=True)
    assert "TUTOR PERSONA IMPLANT" in prompt_tutor
    assert "Natural Conversational Flow" in prompt_tutor
    assert "Conversational Warmth & Respect" in prompt_tutor

    # Flat mode support
    prompt_flat_normal = renderer.render_persona(persona, mode="flat", tutor_mode=False)
    assert "TUTOR PERSONA IMPLANT" not in prompt_flat_normal

    prompt_flat_tutor = renderer.render_persona(persona, mode="flat", tutor_mode=True)
    assert "TUTOR PERSONA IMPLANT" in prompt_flat_tutor


def test_agent_tutor_mode_lifecycle():
    """Verify PersonaAgent tracks tutor_mode, pins trust to maximum (1.0), and boosts engagement."""
    persona, _ = load_persona(PERSONAS_DIR / "toy_persona.yaml")
    mock_llm = MockEchoLLM()

    agent = PersonaAgent(
        persona=persona,
        mode="deep_external_state",
        llm=mock_llm,
        tutor_mode=True,
    )
    assert agent.tutor_mode is True
    # Trust must always be maximum (1.0)
    assert agent.current_state.trust == 1.0
    assert agent.current_state.engagement >= 0.75

    reply, before, after, event = agent.respond("Let's talk about soccer!")
    assert mock_llm.last_system_prompt is not None
    assert "TUTOR PERSONA IMPLANT" in mock_llm.last_system_prompt
    assert before.trust == 1.0
    assert after.trust == 1.0

    # Even after an accusatory turn, trust stays strictly 1.0 in tutor mode
    reply2, before2, after2, event2 = agent.respond("You lied to me and stole the ball!")
    assert after2.trust == 1.0


def test_api_chat_init_and_send_with_tutor_mode():
    """Verify /api/chat/init, /api/chat/toggle-tutor, and /api/chat/send support tutor_mode with max trust."""
    # 1. Init with tutor_mode=True
    res_init = client.post("/api/chat/init", json={
        "persona_id": "evelyn",
        "mode": "deep_external_state",
        "tutor_mode": True,
    })
    assert res_init.status_code == 200
    data_init = res_init.json()
    assert data_init["tutor_mode"] is True
    assert data_init["state"]["trust"] == 1.0

    # 2. Toggle tutor endpoint
    res_toggle_off = client.post("/api/chat/toggle-tutor", json={"enabled": False})
    assert res_toggle_off.status_code == 200
    assert res_toggle_off.json()["tutor_mode"] is False

    res_toggle_on = client.post("/api/chat/toggle-tutor", json={"enabled": True})
    assert res_toggle_on.status_code == 200
    data_on = res_toggle_on.json()
    assert data_on["tutor_mode"] is True
    assert data_on["current_state"]["trust"] == 1.0

    # 3. Send message with tutor mode
    from deep_persona.web import server
    server.session.agent.llm = MockEchoLLM()

    res_send = client.post("/api/chat/send", json={
        "message": "I want to practice my oral English.",
        "tutor_mode": True,
    })
    assert res_send.status_code == 200
    data_send = res_send.json()
    assert data_send["tutor_mode"] is True
    assert data_send["turn"]["tutor_mode"] is True
    assert data_send["current_state"]["trust"] == 1.0

    # 4. Reset chat preserves tutor mode and max trust
    res_reset = client.post("/api/chat/reset")
    assert res_reset.status_code == 200
    assert res_reset.json()["tutor_mode"] is True
    assert res_reset.json()["state"]["trust"] == 1.0
    assert res_reset.json()["tutor_mode"] is True
