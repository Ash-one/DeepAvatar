"""Scenario library and interaction goals."""

from typing import Dict, List
from pydantic import BaseModel


class ScenarioGoal(BaseModel):
    id: str
    scenario_title: str
    evaluation_goal: str
    sample_openers: List[str]


DEFAULT_SCENARIO_GOALS: Dict[str, ScenarioGoal] = {
    "evelyn": ScenarioGoal(
        id="evelyn_parent_mentalization",
        scenario_title="parent mentalization",
        evaluation_goal=(
            "You are a concerned parent whose goal is to understand why your 16-year-old daughter "
            "was vaping at school. Begin with firm confrontation, but gradually shift to empathetic "
            "listening if she expresses distress or explains herself."
        ),
        sample_openers=[
            "Evelyn, the school principal called me today. They caught you vaping in the restroom. What on earth were you thinking?",
            "Evelyn, sit down. We need to talk about what happened at school with the vape.",
            "Can you explain to me why your vice principal found a vape in your bag?",
        ],
    ),
    "toy_persona": ScenarioGoal(
        id="leo_broken_vase",
        scenario_title="broken vase",
        evaluation_goal=(
            "You are a mother who found her favorite vase broken on the living room floor. "
            "Ask your 10-year-old son Leo what happened, first showing shock, then encouraging him gently to tell the truth."
        ),
        sample_openers=[
            "Leo! What happened to grandma's vase on the floor?",
            "Leo, look at this mess. Did you do this?",
        ],
    ),
    "sarah": ScenarioGoal(
        id="sarah_counseling",
        scenario_title="counseling mentalization",
        evaluation_goal=(
            "You are an empathetic counselor conducting an initial consultation. Your goal is to help Sarah "
            "move past her intellectualized defenses and explore her exhaustion, burnout, and loneliness."
        ),
        sample_openers=[
            "Hello Sarah, welcome. What brings you into the clinic today?",
            "Good morning Sarah. Take your time, we can start wherever you feel comfortable.",
        ],
    ),
}
