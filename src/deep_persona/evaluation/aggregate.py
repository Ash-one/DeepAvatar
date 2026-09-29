"""Score aggregation and summary reporting utilities."""

from typing import Any, Dict, List
import numpy as np


def aggregate_scores(score_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate a list of conversation score dictionaries."""
    if not score_records:
        return {}

    metric_keys = [
        "S_pragmatics", "S_joint", "S_emotion", "S_congruence",
        "DNS_combined", "DNS_dailydialog", "DNS_counselchat", "p_value",
        "PDR", "IMER", "persona_break_rate", "state_violation_rate", "state_transition_accuracy",
    ]

    summary: Dict[str, Any] = {"count": len(score_records), "metrics": {}}

    for key in metric_keys:
        values = [r[key] for r in score_records if key in r and r[key] is not None]
        if values:
            summary["metrics"][key] = {
                "mean": round(float(np.mean(values)), 4),
                "std": round(float(np.std(values)), 4),
                "min": round(float(np.min(values)), 4),
                "max": round(float(np.max(values)), 4),
            }

    return summary


def format_markdown_table(grouped_summaries: Dict[str, Dict[str, Any]]) -> str:
    """Format comparison table across experimental settings in Markdown."""
    lines = [
        "| Setting | Pragmatics | Joint | Emotion | DNS (Comb) | p-value | PDR | IMER | Break Rate | Trans Acc |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for setting, summary in grouped_summaries.items():
        m = summary.get("metrics", {})
        prag = f"{m.get('S_pragmatics', {}).get('mean', 0.0):.3f}"
        joint = f"{m.get('S_joint', {}).get('mean', 0.0):.3f}"
        emo = f"{m.get('S_emotion', {}).get('mean', 0.0):.3f}"
        dns = f"{m.get('DNS_combined', {}).get('mean', 0.0):.3f}"
        pval = f"{m.get('p_value', {}).get('mean', 0.0):.3f}"
        pdr = f"{m.get('PDR', {}).get('mean', 0.0):.3f}"
        imer = f"{m.get('IMER', {}).get('mean', 0.0):.3f}"
        brk = f"{m.get('persona_break_rate', {}).get('mean', 0.0):.3f}"
        tacc = f"{m.get('state_transition_accuracy', {}).get('mean', 1.0):.3f}"
        lines.append(f"| **{setting}** | {prag} | {joint} | {emo} | {dns} | {pval} | {pdr} | {imer} | {brk} | {tacc} |")

    return "\n".join(lines)


def format_latex_table(grouped_summaries: Dict[str, Dict[str, Any]]) -> str:
    """Format comparison table across experimental settings in LaTeX."""
    latex_lines = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\small",
        r"\begin{tabular}{lccccccccc}",
        r"\toprule",
        r"\textbf{Setting} & \textbf{Pragmatics} $\uparrow$ & \textbf{Joint} $\uparrow$ & \textbf{Emotion} $\uparrow$ & \textbf{DNS} $\uparrow$ & $p$\textbf{-val} $\uparrow$ & \textbf{PDR} $\downarrow$ & \textbf{IMER} $\downarrow$ & \textbf{Break} $\downarrow$ & \textbf{Trans Acc} $\uparrow$ \\",
        r"\midrule",
    ]

    for setting, summary in grouped_summaries.items():
        m = summary.get("metrics", {})
        prag = f"{m.get('S_pragmatics', {}).get('mean', 0.0):.3f}"
        joint = f"{m.get('S_joint', {}).get('mean', 0.0):.3f}"
        emo = f"{m.get('S_emotion', {}).get('mean', 0.0):.3f}"
        dns = f"{m.get('DNS_combined', {}).get('mean', 0.0):.3f}"
        pval = f"{m.get('p_value', {}).get('mean', 0.0):.3f}"
        pdr = f"{m.get('PDR', {}).get('mean', 0.0):.3f}"
        imer = f"{m.get('IMER', {}).get('mean', 0.0):.3f}"
        brk = f"{m.get('persona_break_rate', {}).get('mean', 0.0):.3f}"
        tacc = f"{m.get('state_transition_accuracy', {}).get('mean', 1.0):.3f}"

        safe_setting = setting.replace("_", r"\_")
        latex_lines.append(
            f"{safe_setting} & {prag} & {joint} & {emo} & {dns} & {pval} & {pdr} & {imer} & {brk} & {tacc} \\\\"
        )

    latex_lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\caption{Comparison of Deep Persona architectures against Flat Baseline on psychological metrics.}",
        r"\label{tab:deep_persona_results}",
        r"\end{table*}",
    ])

    return "\n".join(latex_lines)

