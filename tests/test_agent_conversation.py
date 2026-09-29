"""End-to-end multi-turn simulation and logging validation tests."""

import json
from pathlib import Path
import tempfile
from deep_persona.llm.gemini import MockLLM
from deep_persona.persona.loader import load_persona
from deep_persona.persona.renderer import PromptRenderer
from deep_persona.runtime.agent import PersonaAgent
from deep_persona.runtime.conversation import ConversationRunner
from deep_persona.runtime.logging import ConversationLogger
from deep_persona.simulation.user_agent import UserSimulator

PERSONAS_DIR = Path(__file__).resolve().parents[1] / "personas"


def test_agent_conversation_flow():
    persona, persona_hash = load_persona(PERSONAS_DIR / "toy_persona.yaml")
    renderer = PromptRenderer()

    agent_llm = MockLLM(default_response="I kicked the ball by mistake. [Looks down.]")
    user_llm = MockLLM(default_response="Leo, tell me what happened.")

    agent = PersonaAgent(persona=persona, mode="deep_external_state", llm=agent_llm, renderer=renderer)
    user_sim = UserSimulator(scenario=persona.scenario, llm=user_llm, renderer=renderer, persona_id="toy_persona")

    with tempfile.TemporaryDirectory() as tmpdir:
        logger = ConversationLogger(
            experiment_id="deep_external_state",
            persona_id="toy_persona",
            scenario=persona.scenario.model_dump(),
            output_dir=Path(tmpdir),
        )

        runner = ConversationRunner(
            agent=agent,
            user_simulator=user_sim,
            logger=logger,
            max_turns=3,
        )

        saved_path, conv_data = runner.run(initial_opener="Leo, did you break the vase?")

        assert saved_path.exists()
        assert len(conv_data["turns"]) == 3

        # Check turn structure matches schema
        turn1 = conv_data["turns"][0]
        assert turn1["turn"] == 1
        assert "state_before" in turn1
        assert "state_after" in turn1
        assert turn1["assistant_embodied_action"] == "[Looks down.]"
        assert turn1["assistant"] == "I kicked the ball by mistake."

        # Verify saved JSON can be read back cleanly
        with open(saved_path, "r", encoding="utf-8") as f:
            persisted = json.load(f)
            assert persisted["metadata"]["experiment_id"] == "deep_external_state"
