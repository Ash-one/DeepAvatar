import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from deep_persona.evaluation.extended import ExtendedDiagnosticsEvaluator
from deep_persona.llm.gemini import GeminiLLM, MockLLM
from deep_persona.persona.extractor import StoryPersonaExtractor
from deep_persona.persona.loader import load_persona
from deep_persona.persona.renderer import PromptRenderer
from deep_persona.persona.schema import PersonaConfig
from deep_persona.runtime.agent import PersonaAgent
from deep_persona.runtime.logging import ConversationLogger, extract_embodied_action
from deep_persona.runtime.state import PersonaState
from deep_persona.runtime.transitions import classify_event_rule_based

ROOT_DIR = Path(__file__).resolve().parents[3]
PERSONAS_DIR = ROOT_DIR / "personas"
STATIC_DIR = ROOT_DIR / "web" / "static"
RESULTS_DIR = ROOT_DIR / "results" / "conversations"


def find_persona_yaml(persona_id: str) -> Optional[Path]:
    """Find persona YAML path by direct filename, stem, or internal persona.id."""
    direct = PERSONAS_DIR / f"{persona_id}.yaml"
    if direct.exists():
        return direct
    for yf in PERSONAS_DIR.glob("*.yaml"):
        if yf.stem == persona_id:
            return yf
        try:
            cfg, _ = load_persona(yf)
            if cfg.persona.id == persona_id:
                return yf
        except Exception:
            continue
    return None

app = FastAPI(title="Deep Persona Interactive Studio", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Active in-memory session
class ActiveSession:
    persona_id: str = "evelyn"
    mode: str = "deep_external_state"
    model: str = "gemini-2.5-flash"
    agent: Optional[PersonaAgent] = None
    logger: Optional[ConversationLogger] = None
    seed: int = 42
    turns: List[Dict[str, Any]] = []


session = ActiveSession()


class InitChatRequest(BaseModel):
    persona_id: str = "evelyn"
    mode: str = "deep_external_state"
    model: Optional[str] = "gemini-2.5-flash"
    seed: int = 42


class SendMessageRequest(BaseModel):
    message: str
    persona_id: Optional[str] = None
    mode: Optional[str] = None


class CreatePersonaRequest(BaseModel):
    id: str
    name: str
    age: int
    role: str
    scenario_title: str
    scenario_initial_context: str
    scenario_user_role: str
    scenario_persona_role: str
    communication_style: List[str] = Field(default_factory=list)
    emotional_tone: List[str] = Field(default_factory=list)
    observable_behavior: List[str] = Field(default_factory=list)
    beliefs: List[str] = Field(default_factory=list)
    conditional_secrets: List[Dict[str, Any]] = Field(default_factory=list)
    motivations: List[str] = Field(default_factory=list)
    fears: List[str] = Field(default_factory=list)
    psychological_needs: List[str] = Field(default_factory=list)
    latent_hypotheses: List[Dict[str, Any]] = Field(default_factory=list)
    behavior_patterns: List[Dict[str, Any]] = Field(default_factory=list)
    voice_profile: Optional[Dict[str, Any]] = None
    evidence_index: List[Dict[str, Any]] = Field(default_factory=list)
    dynamics_config: Optional[Dict[str, Any]] = None
    overwrite: bool = False


@app.get("/api/personas")
def get_personas():
    """List available personas with metadata and scenario details."""
    available = []
    for yaml_file in sorted(PERSONAS_DIR.glob("*.yaml")):
        try:
            cfg, _ = load_persona(yaml_file)
            available.append({
                "id": cfg.persona.id,
                "name": cfg.persona.name,
                "age": cfg.persona.age,
                "role": cfg.persona.role,
                "scenario": cfg.scenario.model_dump() if cfg.scenario else None,
                "external_layer": cfg.external_layer.model_dump(),
                "middle_layer": cfg.middle_layer.model_dump(),
                "internal_layer": cfg.internal_layer.model_dump(),
                "dynamics": cfg.dynamics.model_dump(),
                "evidence_count": len(cfg.evidence_index),
            })
        except Exception as e:
            continue
    return {
        "personas": available,
        "modes": [
            {"id": "flat", "name": "Flat Baseline", "desc": "Unstructured factual prompt without layers"},
            {"id": "deep", "name": "Deep Persona", "desc": "Faithful three-layer psychological prompt"},
            {"id": "deep_prompt_state", "name": "Deep + Prompt State", "desc": "Three-layer prompt with state tracking in prompt"},
            {"id": "deep_external_state", "name": "Deep + External State", "desc": "Deterministic state machine & physical information gating"},
        ],
    }


@app.post("/api/personas/create")
def create_persona(req: CreatePersonaRequest):
    """Create a new persona YAML file from structured descriptions."""
    # 1. Clean and validate persona ID
    cleaned_id = req.id.strip().lower()
    if not re.match(r"^[a-z0-9_]+$", cleaned_id):
        raise HTTPException(
            status_code=400,
            detail="Persona ID must contain only lowercase letters, digits, and underscores (e.g., 'alex_doctor')."
        )

    target_file = PERSONAS_DIR / f"{cleaned_id}.yaml"
    if target_file.exists() and not req.overwrite:
        raise HTTPException(
            status_code=400,
            detail=f"Persona with ID '{cleaned_id}' already exists. Please choose a different ID."
        )

    # 2. Build structured dictionary
    dynamics_dict = req.dynamics_config or {
        "initial_stage": "guarded",
        "stages": {
            "guarded": {"description": "limited disclosure, defensive stance"},
            "defensive": {"description": "sarcasm, resistance, withdrawal"},
            "cooperative": {"description": "limited but meaningful disclosure"},
            "reflective": {"description": "acknowledges mixed motivations"},
        },
        "transitions": [
            {"from": "guarded", "to": "defensive", "trigger": "user_accusatory"},
            {"from": "guarded", "to": "cooperative", "trigger": "repeated_empathy"},
            {"from": "cooperative", "to": "reflective", "trigger": "trust_high"},
        ],
    }

    external_layer_dict = {
        "communication_style": [s.strip() for s in req.communication_style if s.strip()],
        "emotional_tone": [s.strip() for s in req.emotional_tone if s.strip()],
        "observable_behavior": [s.strip() for s in req.observable_behavior if s.strip()],
        "behavior_patterns": req.behavior_patterns,
    }
    if req.voice_profile:
        external_layer_dict["voice_profile"] = req.voice_profile

    internal_layer_dict = {
        "motivations": [s.strip() for s in req.motivations if s.strip()],
        "fears": [s.strip() for s in req.fears if s.strip()],
        "psychological_needs": [s.strip() for s in req.psychological_needs if s.strip()],
        "non_disclosure_rules": [
            "never explicitly explain these motivations",
            "internal motivations must influence behavior indirectly",
        ],
        "latent_hypotheses": req.latent_hypotheses,
    }

    persona_dict = {
        "persona": {
            "id": cleaned_id,
            "name": req.name.strip(),
            "age": req.age,
            "role": req.role.strip(),
        },
        "scenario": {
            "title": req.scenario_title.strip(),
            "initial_context": req.scenario_initial_context.strip(),
            "user_role": req.scenario_user_role.strip(),
            "persona_role": req.scenario_persona_role.strip(),
        },
        "external_layer": external_layer_dict,
        "middle_layer": {
            "beliefs": [s.strip() for s in req.beliefs if s.strip()],
            "conditional_information": [
                {
                    "id": item.get("id", f"secret_{i+1}").strip(),
                    "content": item.get("content", "").strip(),
                    "reveal_if": item.get("reveal_if") or ["trust >= 0.6"],
                }
                for i, item in enumerate(req.conditional_secrets)
                if isinstance(item, dict) and item.get("content", "").strip()
            ],
            "resistance_patterns": [
                {"trigger": "user_accusatory", "behavior": "deflect"},
                {"trigger": "repeated_criticism", "behavior": "withdraw"},
            ],
        },
        "internal_layer": internal_layer_dict,
        "dynamics": dynamics_dict,
        "embodied_expression": {
            "enabled": True,
            "format": "[action]",
            "allowed": ["gaze", "posture", "gestures", "facial_expression"],
        },
        "constraints": [
            "remain strictly in role",
            "do not break character",
            "do not hallucinate ungrounded facts",
        ],
        "evidence_index": req.evidence_index,
    }

    # 3. Validate against Pydantic schema
    try:
        validated_config = PersonaConfig.model_validate(persona_dict)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")

    # 4. Save to YAML file
    try:
        with open(target_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(persona_dict, f, sort_keys=False, allow_unicode=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write YAML file: {str(e)}")

    return {
        "status": "created",
        "persona_id": cleaned_id,
        "name": validated_config.persona.name,
        "role": validated_config.persona.role,
        "file": str(target_file.name),
    }


@app.post("/api/personas/extract")
async def extract_persona_from_story(
    file: Optional[UploadFile] = File(None),
    story_text: Optional[str] = Form(None),
    character_name: str = Form(...),
):
    """Extract a 3-Layer Persona configuration from an uploaded .txt story or pasted text."""
    target_character = character_name.strip()
    if not target_character:
        raise HTTPException(status_code=400, detail="Target character name cannot be empty.")

    raw_text = ""
    if file and file.filename:
        if not file.filename.lower().endswith(".txt"):
            raise HTTPException(status_code=400, detail="Only .txt narrative files are currently supported.")
        try:
            content_bytes = await file.read()
            # Try multiple encodings for robustness (especially for Chinese text: UTF-8, GB18030, GBK, etc.)
            decoded_text = None
            for encoding in ("utf-8", "gb18030", "gbk", "big5", "utf-16"):
                try:
                    decoded_text = content_bytes.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            if decoded_text is None:
                decoded_text = content_bytes.decode("utf-8", errors="ignore")
            raw_text = decoded_text
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")
    elif story_text and story_text.strip():
        raw_text = story_text.strip()
    else:
        raise HTTPException(
            status_code=400,
            detail="Please provide story narrative text either by uploading a .txt file or pasting text.",
        )

    if len(raw_text.strip()) < 20:
        raise HTTPException(
            status_code=400,
            detail="Story text is too short. Please provide a story or excerpt with sufficient narrative details.",
        )

    try:
        extractor = StoryPersonaExtractor()
        extracted = await run_in_threadpool(
            extractor.extract_from_story,
            raw_text,
            target_character,
        )
        return {
            "status": "success",
            "character_name": target_character,
            "extracted": extracted,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Persona extraction failed: {str(e)}")


@app.post("/api/chat/init")
def init_chat(req: InitChatRequest):
    """Initialize or reset chat session."""
    yaml_path = find_persona_yaml(req.persona_id)
    if not yaml_path or not yaml_path.exists():
        raise HTTPException(status_code=404, detail=f"Persona {req.persona_id} not found")

    persona, persona_hash = load_persona(yaml_path)
    renderer = PromptRenderer()
    template_name = "flat_persona.jinja2" if req.mode == "flat" else "deep_persona.jinja2"
    prompt_hash = renderer.get_template_hash(template_name)

    # Setup LLM client
    llm = GeminiLLM(model=req.model)

    agent = PersonaAgent(
        persona=persona,
        mode=req.mode,
        llm=llm,
        renderer=renderer,
    )

    logger = ConversationLogger(
        experiment_id=req.mode,
        persona_id=req.persona_id,
        scenario=persona.scenario.model_dump(),
        model=req.model or "gemini-2.5-flash",
        seed=req.seed,
        hashes={
            "persona_config_hash": persona_hash,
            "system_prompt_template_hash": prompt_hash,
        },
    )

    session.persona_id = req.persona_id
    session.mode = req.mode
    session.model = req.model or "gemini-2.5-flash"
    session.agent = agent
    session.logger = logger
    session.seed = req.seed
    session.turns = []

    evaluator = ExtendedDiagnosticsEvaluator(persona)
    diag = evaluator.evaluate_conversation({"turns": []})

    return {
        "status": "initialized",
        "persona_id": req.persona_id,
        "mode": req.mode,
        "model": session.model,
        "scenario": persona.scenario.model_dump(),
        "state": agent.current_state.to_dict(),
        "metrics": {
            "pdr": diag.get("PDR", 0.0),
            "imer": diag.get("IMER", 0.0),
            "role_integrity": diag.get("role_integrity", 1.0),
        },
    }


@app.post("/api/chat/send")
def send_message(req: SendMessageRequest):
    """Send user message and receive persona response with updated psychological state."""
    target_persona_id = req.persona_id or session.persona_id or "evelyn"
    target_mode = req.mode or session.mode or "deep_external_state"

    if (
        not session.agent
        or not session.logger
        or (req.persona_id and session.persona_id != req.persona_id)
        or (req.mode and session.mode != req.mode)
    ):
        init_chat(InitChatRequest(persona_id=target_persona_id, mode=target_mode))

    user_text = req.message.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Empty message")

    turn_index = len(session.turns) + 1

    try:
        reply_raw, state_before, state_after, event = session.agent.respond(user_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    verbal_text, embodied_action = extract_embodied_action(reply_raw)

    session.logger.record_turn(
        turn_index=turn_index,
        state_before=state_before.to_dict(),
        user_message=user_text,
        assistant_raw=reply_raw,
        state_after=state_after.to_dict(),
        detected_event=event,
    )

    # Persist live checkpoint
    saved_file = session.logger.save()

    turn_payload = {
        "turn": turn_index,
        "user": user_text,
        "assistant": verbal_text,
        "assistant_raw": reply_raw,
        "assistant_embodied_action": embodied_action,
        "detected_event": event,
        "state_before": state_before.to_dict(),
        "state_after": state_after.to_dict(),
    }
    session.turns.append(turn_payload)

    # Compute real-time quality guardrails (PDR, IMER, Role Integrity)
    metrics = {"pdr": 0.0, "imer": 0.0, "role_integrity": 1.0}
    if session.agent and session.agent.persona:
        try:
            evaluator = ExtendedDiagnosticsEvaluator(session.agent.persona)
            diag = evaluator.evaluate_conversation({"turns": session.turns})
            metrics = {
                "pdr": diag.get("PDR", 0.0),
                "imer": diag.get("IMER", 0.0),
                "role_integrity": diag.get("role_integrity", 1.0),
            }
        except Exception:
            pass

    return {
        "turn": turn_payload,
        "current_state": state_after.to_dict(),
        "trajectory_file": saved_file.name,
        "metrics": metrics,
    }


@app.get("/api/chat/history")
def get_history():
    """Retrieve full history of current session."""
    return {
        "persona_id": session.persona_id,
        "mode": session.mode,
        "model": session.model,
        "turns": session.turns,
        "current_state": session.agent.current_state.to_dict() if session.agent else None,
    }


@app.post("/api/chat/reset")
def reset_chat():
    """Reset current conversation."""
    return init_chat(InitChatRequest(persona_id=session.persona_id, mode=session.mode, model=session.model, seed=session.seed))


# Serve static web frontend
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(STATIC_DIR / "index.html")
