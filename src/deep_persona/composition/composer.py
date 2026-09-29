"""Session composer that dynamically combines Persona, Scenario, and Relationship."""

import copy
from pathlib import Path
from typing import Dict, Optional, Union
import yaml

from deep_persona.composition.schema import RelationshipDefinition, ScenarioDefinition
from deep_persona.memory.schema import MemoryConfig, RelationshipMemory
from deep_persona.persona.schema import PersonaConfig, ScenarioConfig


class SessionComposer:
    """Dynamically composes a persona core with an interchangeable scenario and relationship."""

    def __init__(
        self,
        scenarios_dir: Union[str, Path] = "scenarios",
        relationships_dir: Union[str, Path] = "relationships",
    ):
        self.scenarios_dir = Path(scenarios_dir)
        self.relationships_dir = Path(relationships_dir)

    def load_scenario(self, scenario_id: str) -> ScenarioDefinition:
        """Load scenario definition from scenarios directory."""
        file_path = self.scenarios_dir / f"{scenario_id}.yaml"
        if not file_path.exists():
            raise FileNotFoundError(f"Scenario not found: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if not isinstance(data, dict):
                raise ValueError(f"Invalid scenario YAML at {file_path}")
            if "id" not in data:
                data["id"] = scenario_id
            return ScenarioDefinition.model_validate(data)

    def load_relationship(self, persona_id: str, relationship_id: str) -> RelationshipDefinition:
        """Load relationship definition from relationships directory."""
        file_path = self.relationships_dir / persona_id / f"{relationship_id}.yaml"
        if not file_path.exists():
            raise FileNotFoundError(f"Relationship not found: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if not isinstance(data, dict):
                raise ValueError(f"Invalid relationship YAML at {file_path}")
            if "id" not in data:
                data["id"] = relationship_id
            if "source_persona_id" not in data:
                data["source_persona_id"] = persona_id
            return RelationshipDefinition.model_validate(data)

    def compose(
        self,
        persona: PersonaConfig,
        scenario: Union[str, ScenarioDefinition],
        relationship: Optional[Union[str, RelationshipDefinition]] = None,
    ) -> PersonaConfig:
        """
        Produce a composed PersonaConfig with scenario and relationship cleanly mapped.
        """
        composed = copy.deepcopy(persona)

        # 1. Resolve Scenario
        scen_def: ScenarioDefinition
        if isinstance(scenario, str):
            scen_def = self.load_scenario(scenario)
        else:
            scen_def = scenario

        composed.scenario = ScenarioConfig(
            title=scen_def.title,
            initial_context=scen_def.initial_context,
            user_role=scen_def.user_role,
            persona_role=scen_def.persona_role,
        )

        if scen_def.constraints:
            composed.constraints = list(composed.constraints) + [
                f"[Scenario] {c}" for c in scen_def.constraints if c not in composed.constraints
            ]

        # Apply scenario baseline offset if present
        if scen_def.baseline_state_offset and composed.dynamics.baseline:
            base = composed.dynamics.baseline
            base.trust = max(0.0, min(1.0, base.trust + scen_def.baseline_state_offset.get("trust", 0.0)))
            base.defensiveness = max(
                0.0, min(1.0, base.defensiveness + scen_def.baseline_state_offset.get("defensiveness", 0.0))
            )
            base.engagement = max(
                0.0, min(1.0, base.engagement + scen_def.baseline_state_offset.get("engagement", 0.0))
            )

        # 2. Resolve Relationship
        rel_def: Optional[RelationshipDefinition] = None
        if isinstance(relationship, str):
            rel_def = self.load_relationship(composed.persona.id, relationship)
        elif isinstance(relationship, RelationshipDefinition):
            rel_def = relationship

        if rel_def:
            if composed.memory is None:
                composed.memory = MemoryConfig()

            # Insert or replace relationship memory
            rel_mem = RelationshipMemory(
                id=rel_def.id,
                target_character=rel_def.target_character,
                relation=rel_def.relation,
                stance=rel_def.stance,
                shared_history_summary=rel_def.shared_history_summary,
            )
            existing = [r for r in composed.memory.relationship_memories if r.target_character != rel_def.target_character]
            existing.insert(0, rel_mem)
            composed.memory.relationship_memories = existing

            # Apply relationship biases to baseline
            if composed.dynamics.baseline:
                base = composed.dynamics.baseline
                base.trust = max(0.0, min(1.0, base.trust + rel_def.trust_bias))
                base.defensiveness = max(0.0, min(1.0, base.defensiveness + rel_def.defensiveness_bias))

            if rel_def.interaction_rules:
                composed.constraints = list(composed.constraints) + [
                    f"[Interpersonal Rule] {r}" for r in rel_def.interaction_rules
                ]

        return composed
