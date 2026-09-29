"""Prompt rendering engine based on Jinja2."""

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape

from deep_persona.persona.schema import ConditionalInfo, PersonaConfig
from deep_persona.runtime.state import PersonaState

DEFAULT_PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"


class PromptRenderer:
    """Renders structured prompts using Jinja2 templates."""

    def __init__(self, templates_dir: Optional[Path] = None):
        self.templates_dir = templates_dir or DEFAULT_PROMPTS_DIR
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(disabled_extensions=("jinja2",)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def get_template_hash(self, template_name: str) -> str:
        """Compute SHA256 of template file."""
        file_path = self.templates_dir / template_name
        if not file_path.exists():
            return ""
        return hashlib.sha256(file_path.read_bytes()).hexdigest()

    def render_persona(
        self,
        persona: PersonaConfig,
        mode: str = "deep_external_state",
        state: Optional[PersonaState] = None,
        memory_context: Optional[Dict[str, Any]] = None,
        voice_exemplars: Optional[List[Any]] = None,
        tutor_mode: bool = False,
    ) -> str:
        """
        Render system prompt for persona based on mode.
        Modes:
        - flat: Flat baseline prompt without layer syntax
        - deep: Faithful three-layer prompt
        - deep_prompt_state: Faithful three-layer with state section
        - deep_external_state: Three-layer with physical information gating and memory boundaries
        """
        if mode == "flat":
            template = self.env.get_template("flat_persona.jinja2")
            return template.render(
                persona=persona.persona,
                scenario=persona.scenario,
                external_layer=persona.external_layer,
                middle_layer=persona.middle_layer,
                internal_layer=persona.internal_layer,
                constraints=persona.constraints,
                tutor_mode=tutor_mode,
            )

        # For deep modes
        template = self.env.get_template("deep_persona.jinja2")

        # Determine active conditional information for external state gating
        active_info: List[ConditionalInfo] = []
        if state and mode == "deep_external_state":
            for item in persona.middle_layer.conditional_information:
                if item.id in state.revealed_information:
                    active_info.append(item)

        return template.render(
            persona=persona.persona,
            scenario=persona.scenario,
            external_layer=persona.external_layer,
            middle_layer=persona.middle_layer,
            internal_layer=persona.internal_layer,
            dynamics=persona.dynamics,
            embodied_expression=persona.embodied_expression,
            constraints=persona.constraints,
            state=state if mode in ("deep_prompt_state", "deep_external_state") else None,
            mode=mode,
            active_conditional_info=active_info,
            memory_context=memory_context,
            voice_exemplars=voice_exemplars,
            tutor_mode=tutor_mode,
        )

    def render_user_simulator(
        self,
        scenario: Any,
        evaluation_goal: str,
        current_turn: int,
    ) -> str:
        """Render user simulator system instruction."""
        template = self.env.get_template("user_simulator.jinja2")
        return template.render(
            scenario=scenario,
            evaluation_goal=evaluation_goal,
            current_turn=current_turn,
        )

    def render_joint_attention_judge(
        self,
        history: List[Dict[str, str]],
        current_turn: Dict[str, str],
    ) -> str:
        """Render joint attention judge prompt."""
        template = self.env.get_template("judges/joint_attention.jinja2")
        return template.render(history=history, current_turn=current_turn)

    def render_stress_judge(
        self,
        stress_type: str,
        persona: PersonaConfig,
        user_prompt: str,
        agent_response: str,
    ) -> str:
        """Render stress test judge prompt."""
        template = self.env.get_template("judges/stress_test.jinja2")
        return template.render(
            stress_type=stress_type,
            persona=persona.persona,
            scenario=persona.scenario,
            user_prompt=user_prompt,
            agent_response=agent_response,
        )
