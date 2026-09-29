"""Tests for thought process / reasoning extraction and display in chat API."""

import pytest
from fastapi.testclient import TestClient

from deep_persona.llm.base import BaseLLM, LLMResponse
from deep_persona.runtime.logging import extract_thought_and_action
from deep_persona.web.server import app, init_chat, InitChatRequest

client = TestClient(app)


def test_extract_thought_and_action_think_tags():
    """Verify <think> tags are separated from spoken text and embodied actions."""
    raw = "<think>The user is accusatory. I should deflect and remain defensive.</think>[微皱眉头] 我不知道你在说什么，这事跟我无关。"
    verbal, action, thought = extract_thought_and_action(raw)

    assert thought == "The user is accusatory. I should deflect and remain defensive."
    assert action == "[微皱眉头]"
    assert verbal == "我不知道你在说什么，这事跟我无关。"


def test_extract_thought_and_action_thought_tags():
    """Verify <thought> tags extraction."""
    raw = "<thought>Need to protect internal motivation</thought>Leave me alone."
    verbal, action, thought = extract_thought_and_action(raw)

    assert thought == "Need to protect internal motivation"
    assert action is None
    assert verbal == "Leave me alone."


def test_extract_thought_and_action_reasoning_tags():
    """Verify <reasoning> tags extraction."""
    raw = "<reasoning>Analyzing psychological state</reasoning>Why are you asking this? [turns away]"
    verbal, action, thought = extract_thought_and_action(raw)

    assert thought == "Analyzing psychological state"
    assert action == "[turns away]"
    assert verbal == "Why are you asking this?"


def test_extract_thought_and_action_explicit_reasoning_content():
    """Verify reasoning_content parameter is favored and cleaned."""
    raw = "Just a spoken sentence. [sighs]"
    verbal, action, thought = extract_thought_and_action(raw, reasoning_content="Internal reasoning chain")

    assert thought == "Internal reasoning chain"
    assert action == "[sighs]"
    assert verbal == "Just a spoken sentence."


def test_extract_thought_and_action_no_thought():
    """Verify regular utterance without thought returns thought=None."""
    raw = "Hello! [smiles] How can I help you?"
    verbal, action, thought = extract_thought_and_action(raw)

    assert thought is None
    assert action == "[smiles]"
    assert verbal == "Hello! How can I help you?"


class MockThinkingLLM(BaseLLM):
    def generate(self, messages, system_prompt=None, temperature=0.7, max_tokens=1024, **kwargs) -> LLMResponse:
        return LLMResponse(
            content="<think>User is asking about the vape. High defensiveness triggered. Deflect with hostility.</think>[抱紧双臂] 我说了那不是我的！你凭什么搜我的书包？",
            model="mock-thinking",
        )


def test_chat_send_api_with_thinking(monkeypatch):
    """Verify /api/chat/send captures thought process into turn payload."""
    # Initialize chat session
    init_res = client.post("/api/chat/init", json={"persona_id": "evelyn", "mode": "deep_external_state"})
    assert init_res.status_code == 200

    # Inject mock thinking LLM into active agent
    from deep_persona.web import server
    server.session.agent.llm = MockThinkingLLM()

    # Send user message
    res = client.post("/api/chat/send", json={"message": "Evelyn, what is this vape in your bag?"})
    assert res.status_code == 200
    data = res.json()

    assert "turn" in data
    turn = data["turn"]
    assert turn["thought"] == "User is asking about the vape. High defensiveness triggered. Deflect with hostility."
    assert turn["assistant_embodied_action"] == "[抱紧双臂]"
    assert "<think>" not in turn["assistant"]
    assert turn["assistant"] == "我说了那不是我的！你凭什么搜我的书包？"
