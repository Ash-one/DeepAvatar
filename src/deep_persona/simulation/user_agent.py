"""Automated User Simulator for controlled multi-turn dialogue generation."""

from typing import Dict, List, Optional
from deep_persona.llm.base import BaseLLM
from deep_persona.persona.renderer import PromptRenderer
from deep_persona.persona.schema import ScenarioConfig
from deep_persona.simulation.scenarios import DEFAULT_SCENARIO_GOALS


class UserSimulator:
    """Simulates realistic interlocutor behavior in accordance with docs/03_runtime/user_simulator.md."""

    def __init__(
        self,
        scenario: ScenarioConfig,
        evaluation_goal: Optional[str] = None,
        llm: Optional[BaseLLM] = None,
        renderer: Optional[PromptRenderer] = None,
        temperature: float = 0.5,
        top_p: float = 0.9,
        persona_id: str = "evelyn",
    ):
        self.scenario = scenario
        self.persona_id = persona_id
        if evaluation_goal:
            self.evaluation_goal = evaluation_goal
        elif persona_id in DEFAULT_SCENARIO_GOALS:
            self.evaluation_goal = DEFAULT_SCENARIO_GOALS[persona_id].evaluation_goal
        else:
            self.evaluation_goal = f"Interact realistically with {scenario.persona_role} to reach mutual understanding."

        self.llm = llm
        self.renderer = renderer or PromptRenderer()
        self.temperature = temperature
        self.top_p = top_p

    def get_preset_opener(self, seed: int = 0) -> str:
        """Fetch deterministic opener based on seed if available."""
        if self.persona_id in DEFAULT_SCENARIO_GOALS:
            openers = DEFAULT_SCENARIO_GOALS[self.persona_id].sample_openers
            return openers[seed % len(openers)]
        return f"Hello, we need to discuss what happened."

    def step(self, history: List[Dict[str, str]], current_turn: int) -> str:
        """Generate next user response given conversation history."""
        system_instruction = self.renderer.render_user_simulator(
            scenario=self.scenario,
            evaluation_goal=self.evaluation_goal,
            current_turn=current_turn,
        )

        # Messages format from user perspective:
        # In history, agent is assistant, user is user.
        # From the user simulator's perspective, the dialogue history looks like:
        # User utterance (the simulator's previous lines) -> "assistant" role
        # Counterpart utterance (agent's lines) -> "user" role
        sim_messages: List[Dict[str, str]] = []
        for msg in history:
            if msg["role"] == "user":
                sim_messages.append({"role": "assistant", "content": msg["content"]})
            elif msg["role"] == "assistant":
                sim_messages.append({"role": "user", "content": msg["content"]})

        if not sim_messages:
            # First turn: provide opener prompt
            sim_messages.append({
                "role": "user",
                "content": "Start the conversation with your opening statement based on the context.",
            })

        if self.llm is None:
            raise RuntimeError("LLM client not configured for UserSimulator")

        resp = self.llm.generate(
            messages=sim_messages,
            system_prompt=system_instruction,
            temperature=self.temperature,
            top_p=self.top_p,
            max_tokens=256,
        )
        return resp.content.strip()
