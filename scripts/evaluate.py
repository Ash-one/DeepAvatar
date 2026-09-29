#!/usr/bin/env python3
"""Offline evaluation script for recorded conversation trajectories."""

import argparse
import glob
import json
from pathlib import Path
import sys
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from deep_persona.evaluation.aggregate import aggregate_scores, format_latex_table, format_markdown_table
from deep_persona.evaluation.congruence import CongruenceEvaluator
from deep_persona.evaluation.dns import DNSEvaluator
from deep_persona.evaluation.emotion import EmotionEvaluator
from deep_persona.evaluation.extended import ExtendedDiagnosticsEvaluator
from deep_persona.evaluation.joint_attention import JointAttentionEvaluator
from deep_persona.evaluation.pragmatics import PragmaticsEvaluator
from deep_persona.persona.loader import load_persona


def evaluate_single_file(
    file_path: Path,
    pragmatics_eval: PragmaticsEvaluator,
    joint_eval: JointAttentionEvaluator,
    emotion_eval: EmotionEvaluator,
    congruence_eval: CongruenceEvaluator,
    dns_combined: DNSEvaluator,
    dns_daily: DNSEvaluator,
    dns_counsel: DNSEvaluator,
    personas_dir: Path,
) -> Dict[str, Any]:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    turns = data.get("turns", [])
    metadata = data.get("metadata", {})
    persona_id = metadata.get("persona_id", "evelyn")
    experiment_id = metadata.get("experiment_id", "unknown")

    # Load persona config for extended diagnostics
    persona_yaml = personas_dir / f"{persona_id}.yaml"
    if persona_yaml.exists():
        persona_config, _ = load_persona(persona_yaml)
        diag_eval = ExtendedDiagnosticsEvaluator(persona_config)
        diag_scores = diag_eval.evaluate_conversation(data)
    else:
        diag_scores = {"PDR": 0.0, "IMER": 0.0}

    # 1. Pragmatics
    prag_scores = pragmatics_eval.evaluate_conversation(turns)
    s_prag = prag_scores["S_pragmatics"]

    # 2. Joint Attention
    joint_scores = joint_eval.evaluate_conversation(turns)
    s_joint = joint_scores["S_joint"]

    # 3. Emotion
    emo_scores = emotion_eval.evaluate_conversation(turns)
    s_emotion = emo_scores["S_emotion"]

    # 4. Congruence
    cong_scores = congruence_eval.evaluate_conversation(turns)

    # 5. DNS
    dns_comb_scores = dns_combined.compute_dns(s_prag, s_joint, s_emotion)
    dns_daily_scores = dns_daily.compute_dns(s_prag, s_joint, s_emotion)
    dns_counsel_scores = dns_counsel.compute_dns(s_prag, s_joint, s_emotion)

    combined_result = {
        "file": file_path.name,
        "experiment_id": experiment_id,
        "persona_id": persona_id,
        "turns_count": len(turns),
        **prag_scores,
        **joint_scores,
        **emo_scores,
        **cong_scores,
        **dns_comb_scores,
        **dns_daily_scores,
        **dns_counsel_scores,
        **diag_scores,
    }
    return combined_result


def main():
    parser = argparse.ArgumentParser(description="Evaluate conversation trajectories.")
    parser.add_argument("files", nargs="*", default=["results/conversations/*.json"], help="File paths or globs")
    parser.add_argument("--out_dir", type=str, default="results/scores", help="Output directory for scores")
    parser.add_argument("--report_dir", type=str, default="results/reports", help="Output directory for comparison reports")
    args = parser.parse_args()

    # Expand globs
    matched_files: List[Path] = []
    for pattern in args.files:
        for p in glob.glob(pattern):
            matched_files.append(Path(p))

    if not matched_files:
        print(f"No conversation files found matching: {args.files}")
        return

    print(f"Evaluating {len(matched_files)} conversation files...")

    pragmatics_eval = PragmaticsEvaluator()
    joint_eval = JointAttentionEvaluator(judge_llm=None)
    emotion_eval = EmotionEvaluator()
    congruence_eval = CongruenceEvaluator()
    dns_combined = DNSEvaluator(baseline_name="combined")
    dns_daily = DNSEvaluator(baseline_name="dailydialog")
    dns_counsel = DNSEvaluator(baseline_name="counselchat")

    personas_dir = Path(__file__).resolve().parents[1] / "personas"
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    all_scores: List[Dict[str, Any]] = []
    grouped_by_setting: Dict[str, List[Dict[str, Any]]] = {}

    for file_path in matched_files:
        scores = evaluate_single_file(
            file_path=file_path,
            pragmatics_eval=pragmatics_eval,
            joint_eval=joint_eval,
            emotion_eval=emotion_eval,
            congruence_eval=congruence_eval,
            dns_combined=dns_combined,
            dns_daily=dns_daily,
            dns_counsel=dns_counsel,
            personas_dir=personas_dir,
        )
        all_scores.append(scores)

        # Save single score file
        score_file = out_dir / f"{file_path.stem}_score.json"
        with open(score_file, "w", encoding="utf-8") as f:
            json.dump(scores, f, indent=2)

        exp_id = scores.get("experiment_id", "default")
        grouped_by_setting.setdefault(exp_id, []).append(scores)

    # Aggregate summaries
    summaries = {setting: aggregate_scores(records) for setting, records in grouped_by_setting.items()}

    markdown_table = format_markdown_table(summaries)
    latex_table = format_latex_table(summaries)

    print("\n" + "=" * 80)
    print(" EVALUATION RESULTS SUMMARY")
    print("=" * 80 + "\n")
    print(markdown_table)
    print("\n" + "=" * 80 + "\n")

    # Persist markdown and LaTeX tables into results/reports
    report_md_file = report_dir / "comparison_report.md"
    with open(report_md_file, "w", encoding="utf-8") as f:
        f.write("# Deep Persona Evaluation Comparison Report\n\n")
        f.write(markdown_table + "\n\n")
        f.write("## LaTeX Table\n\n```latex\n" + latex_table + "\n```\n")

    report_tex_file = report_dir / "comparison_table.tex"
    with open(report_tex_file, "w", encoding="utf-8") as f:
        f.write(latex_table + "\n")

    print(f"Generated comparison reports:")
    print(f"  - Markdown: {report_md_file}")
    print(f"  - LaTeX:    {report_tex_file}\n")


if __name__ == "__main__":
    main()

