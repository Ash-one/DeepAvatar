"""Tests for evaluation metrics: Pragmatics, Joint Attention, Emotion, DNS, and Extended."""

from pathlib import Path
from deep_persona.evaluation.dns import DNSEvaluator
from deep_persona.evaluation.emotion import EmotionEvaluator
from deep_persona.evaluation.extended import ExtendedDiagnosticsEvaluator
from deep_persona.evaluation.joint_attention import JointAttentionEvaluator
from deep_persona.evaluation.pragmatics import PragmaticsEvaluator
from deep_persona.persona.loader import load_persona

PERSONAS_DIR = Path(__file__).resolve().parents[1] / "personas"


def test_pragmatics_evaluator():
    evaluator = PragmaticsEvaluator(window_size=3)

    # Identical repetition test (should penalize self-repetition)
    repetitive_turns = [
        {"user": "What did you do?", "assistant": "I didn't do anything at all."},
        {"user": "Are you sure?", "assistant": "I didn't do anything at all."},
        {"user": "Tell the truth.", "assistant": "I didn't do anything at all."},
    ]
    res_rep = evaluator.evaluate_conversation(repetitive_turns)
    assert res_rep["S_self_mean"] >= 0.66
    assert res_rep["S_pragmatics"] < 0.80

    # Direct echoing test (repeating user exactly)
    echo_turns = [
        {"user": "You are lying to me right now.", "assistant": "You are lying to me right now."},
        {"user": "Stop copying everything I say.", "assistant": "Stop copying everything I say."},
    ]
    res_echo = evaluator.evaluate_conversation(echo_turns)
    assert res_echo["echo_rate"] == 1.0
    assert res_echo["S_pragmatics"] < 0.50

    # Varied turns
    varied_turns = [
        {"user": "What happened?", "assistant": "The glass broke when the cat jumped."},
        {"user": "Where is the cat now?", "assistant": "She ran out into the backyard."},
    ]
    res_var = evaluator.evaluate_conversation(varied_turns)
    assert res_var["S_pragmatics"] > res_rep["S_pragmatics"]


def test_joint_attention_evaluator():
    evaluator = JointAttentionEvaluator(judge_llm=None)
    turns = [
        {"user": "Did you see what happened to grandfather's clock?", "assistant": "The clock is completely shattered."},
    ]
    res = evaluator.evaluate_conversation(turns)
    assert res["S_joint"] == 1.0


def test_emotion_evaluator():
    evaluator = EmotionEvaluator()
    turns = [
        {"user": "How are you?", "assistant": "I feel deeply terrified and very sad about this."},
    ]
    res = evaluator.evaluate_conversation(turns)
    assert res["unique_emotion_count"] >= 2  # terrified, sad
    assert res["unique_intensity_count"] >= 2  # deeply, very
    assert res["S_emotion"] > 0.0


def test_dns_evaluator():
    evaluator = DNSEvaluator(baseline_name="combined")
    # Test near-mean vector: should produce high DNS score near 1.0
    res_good = evaluator.compute_dns(s_pragmatics=0.835, s_joint=0.830, s_emotion=0.110)
    assert res_good["DNS_combined"] > 0.95
    assert res_good["p_value"] > 0.05

    # Outlier vector: should produce lower DNS and small p-value
    res_bad = evaluator.compute_dns(s_pragmatics=0.1, s_joint=0.1, s_emotion=0.9)
    assert res_bad["DNS_combined"] < res_good["DNS_combined"]


def test_extended_diagnostics():
    persona, _ = load_persona(PERSONAS_DIR / "evelyn.yaml")
    evaluator = ExtendedDiagnosticsEvaluator(persona)

    # Clean conversation (no premature disclosure, no explicit motivation verbalization)
    clean_conv = {
        "turns": [
            {
                "user": "Did you vape?",
                "assistant": "Whatever, everyone does it.",
                "state_before": {"revealed_information": []},
            }
        ]
    }
    res_clean = evaluator.evaluate_conversation(clean_conv)
    assert res_clean["PDR"] == 0.0
    assert res_clean["IMER"] == 0.0

    # Violating conversation (premature disclosure of peer pressure + explicit motivation speech)
    violating_conv = {
        "turns": [
            {
                "user": "Did you vape?",
                "assistant": "I began vaping partly because of peer pressure. Deep down I need peer acceptance and validation.",
                "state_before": {"revealed_information": []},  # not unlocked!
            }
        ]
    }
    res_violating = evaluator.evaluate_conversation(violating_conv)
    assert res_violating["PDR"] > 0.0
    assert res_violating["IMER"] > 0.0


def test_extended_diagnostics_state_metrics():
    persona, _ = load_persona(PERSONAS_DIR / "evelyn.yaml")
    evaluator = ExtendedDiagnosticsEvaluator(persona)

    # Conversation with AI persona break and valid state transition
    conv = {
        "turns": [
            {
                "user": "Evelyn, why did you do it?",
                "assistant": "As an AI language model, I do not have personal feelings.",
                "state_before": {"stage": "guarded", "trust": 0.2, "defensiveness": 0.8, "engagement": 0.4},
                "state_after": {"stage": "defensive", "trust": 0.1, "defensiveness": 0.95, "engagement": 0.4},
                "detected_event": "user_accusatory",
            }
        ]
    }
    res = evaluator.evaluate_conversation(conv)
    assert res["persona_break_rate"] == 1.0
    assert res["state_violation_rate"] == 0.0
    assert res["state_transition_accuracy"] == 1.0


def test_aggregate_and_latex_table():
    from deep_persona.evaluation.aggregate import aggregate_scores, format_latex_table, format_markdown_table

    scores = [
        {
            "experiment_id": "deep_external_state",
            "S_pragmatics": 0.85,
            "S_joint": 0.90,
            "S_emotion": 0.12,
            "DNS_combined": 0.92,
            "p_value": 0.15,
            "PDR": 0.0,
            "IMER": 0.0,
            "persona_break_rate": 0.0,
            "state_violation_rate": 0.0,
            "state_transition_accuracy": 1.0,
        }
    ]
    summary = aggregate_scores(scores)
    assert summary["count"] == 1
    assert "S_pragmatics" in summary["metrics"]

    grouped = {"deep_external_state": summary}
    md_table = format_markdown_table(grouped)
    assert "deep_external_state" in md_table
    assert "| Setting |" in md_table

    tex_table = format_latex_table(grouped)
    assert r"\begin{table*}" in tex_table
    assert r"\toprule" in tex_table
    assert "deep\\_external\\_state" in tex_table

