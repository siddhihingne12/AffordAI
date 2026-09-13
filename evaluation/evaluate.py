"""
AFFORDAI Evaluation Runner

Compares agent decisions against the 25 ground-truth sample outputs
from sample_requests.csv and generates a comprehensive report.
"""

from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime

from backend.data_loader import DataStore
from backend.models import AgentDecision
from evaluation.metrics import evaluate_single


def run_evaluation(
    decisions: list[AgentDecision],
    data: DataStore,
    report_path: Path | None = None,
) -> dict:
    """
    Evaluate agent decisions against sample ground truth.
    
    Args:
        decisions: List of AgentDecision objects to evaluate
        data: DataStore with sample_outputs loaded
        report_path: Where to write the report (default: project root)
    
    Returns:
        dict with aggregate metrics
    """
    print("\n" + "=" * 70)
    print("  AFFORDAI — Evaluation Report")
    print("=" * 70)
    
    # Match decisions to ground truth
    per_request = []
    
    for decision in decisions:
        expected = data.sample_outputs.get(decision.request_id)
        if expected is None:
            continue  # No ground truth for this request
        
        result = evaluate_single(decision, expected)
        result["request_id"] = decision.request_id
        per_request.append(result)
    
    if not per_request:
        print("   No matching ground truth found for evaluation")
        return {}
    
    # Aggregate metrics
    n = len(per_request)
    metrics = {
        "total_evaluated": n,
        "status_accuracy": sum(1 for r in per_request if r["status_match"]) / n,
        "amount_accuracy": sum(1 for r in per_request if r["amount_match"]) / n,
        "method_accuracy": sum(1 for r in per_request if r["method_match"]) / n,
        "plan_accuracy": sum(1 for r in per_request if r["plan_match"]) / n,
        "date_accuracy": sum(1 for r in per_request if r["date_match"]) / n,
        "changes_accuracy": sum(1 for r in per_request if r["changes_match"]) / n,
        "avg_score": sum(r["score"] for r in per_request) / n,
        "avg_amount_error": sum(r["amount_error"] for r in per_request) / n,
    }
    
    # Print summary
    print(f"\n[STAT] Evaluated {n} requests against ground truth")
    print(f"\n{'Metric':<35} {'Score':>10}")
    print("-" * 47)
    print(f"{'Affordability Status Accuracy':<35} {metrics['status_accuracy']:>9.1%}")
    print(f"{'Amount Safe to Pay Accuracy':<35} {metrics['amount_accuracy']:>9.1%}")
    print(f"{'Payment Method Accuracy':<35} {metrics['method_accuracy']:>9.1%}")
    print(f"{'Payment Plan Accuracy':<35} {metrics['plan_accuracy']:>9.1%}")
    print(f"{'Earliest Date Accuracy':<35} {metrics['date_accuracy']:>9.1%}")
    print(f"{'Spending Changes Accuracy':<35} {metrics['changes_accuracy']:>9.1%}")
    print(f"{'Average Weighted Score':<35} {metrics['avg_score']:>9.1%}")
    print(f"{'Average Amount Error':<35} {metrics['avg_amount_error']:>9.1%}")
    
    # Per-request details
    print(f"\n{'Request':<14} {'Score':>6} {'Status':>8} {'Amount':>8} {'Method':>8} {'Plan':>6} {'Date':>6} {'Changes':>8}")
    print("-" * 76)
    
    for r in sorted(per_request, key=lambda x: x["request_id"]):
        rid = r["request_id"]
        score = f"{r['score']:.0%}"
        status = "[OK]" if r["status_match"] else "[FAIL]"
        amount = "[OK]" if r["amount_match"] else f"[FAIL]{r['amount_error']:.0%}"
        method = "[OK]" if r["method_match"] else "[FAIL]"
        plan = "[OK]" if r["plan_match"] else "[FAIL]"
        dt = "[OK]" if r["date_match"] else f"[FAIL]±{r['date_diff_days']}d"
        changes = "[OK]" if r["changes_match"] else "[FAIL]"
        
        print(f"  {rid:<12} {score:>6} {status:>8} {amount:>8} {method:>8} {plan:>6} {dt:>6} {changes:>8}")
    
    # Mismatches detail
    mismatches = [r for r in per_request if r["score"] < 1.0]
    if mismatches:
        print(f"\n[SEARCH] Detailed Mismatches:")
        for r in sorted(mismatches, key=lambda x: x["score"]):
            rid = r["request_id"]
            print(f"\n  {rid} (score: {r['score']:.0%}):")
            if not r["status_match"]:
                print(f"    Status: predicted={r['status_predicted']}, expected={r['status_expected']}")
            if not r["amount_match"]:
                print(f"    Amount: predicted={r['amount_predicted']:.2f}, expected={r['amount_expected']:.2f} (error={r['amount_error']:.1%})")
            if not r["method_match"]:
                print(f"    Method: predicted={r['method_predicted']}, expected={r['method_expected']}")
            if not r["plan_match"]:
                print(f"    Plan: {r['plan_details']}")
            if not r["date_match"]:
                print(f"    Date: off by {r['date_diff_days']} days")
    
    # Generate report file
    _write_report(metrics, per_request, report_path)
    
    return metrics


def _write_report(metrics: dict, per_request: list[dict], report_path: Path | None):
    """Write the evaluation report as markdown."""
    if report_path is None:
        report_path = Path(__file__).parent.parent / "EVALUATION_REPORT.md"
    
    lines = [
        "# AFFORDAI — Evaluation Report",
        "",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        "",
        "## Summary Metrics",
        "",
        "| Metric | Score |",
        "|---|---|",
        f"| Affordability Status Accuracy | {metrics['status_accuracy']:.1%} |",
        f"| Amount Safe to Pay Accuracy | {metrics['amount_accuracy']:.1%} |",
        f"| Payment Method Accuracy | {metrics['method_accuracy']:.1%} |",
        f"| Payment Plan Accuracy | {metrics['plan_accuracy']:.1%} |",
        f"| Earliest Date Accuracy | {metrics['date_accuracy']:.1%} |",
        f"| Spending Changes Accuracy | {metrics['changes_accuracy']:.1%} |",
        f"| **Average Weighted Score** | **{metrics['avg_score']:.1%}** |",
        f"| Average Amount Error | {metrics['avg_amount_error']:.1%} |",
        "",
        f"*Evaluated {metrics['total_evaluated']} requests against ground truth.*",
        "",
        "## Per-Request Results",
        "",
        "| Request | Score | Status | Amount | Method | Plan | Date | Changes |",
        "|---|---|---|---|---|---|---|---|",
    ]
    
    for r in sorted(per_request, key=lambda x: x["request_id"]):
        rid = r["request_id"]
        score = f"{r['score']:.0%}"
        status = "[OK]" if r["status_match"] else "[FAIL]"
        amount = "[OK]" if r["amount_match"] else f"[FAIL] ({r['amount_error']:.0%})"
        method = "[OK]" if r["method_match"] else "[FAIL]"
        plan = "[OK]" if r["plan_match"] else "[FAIL]"
        dt = "[OK]" if r["date_match"] else f"[FAIL] (±{r['date_diff_days']}d)"
        changes = "[OK]" if r["changes_match"] else "[FAIL]"
        lines.append(f"| {rid} | {score} | {status} | {amount} | {method} | {plan} | {dt} | {changes} |")
    
    lines.extend(["", "## Detailed Mismatches", ""])
    
    mismatches = [r for r in per_request if r["score"] < 1.0]
    for r in sorted(mismatches, key=lambda x: x["score"]):
        rid = r["request_id"]
        lines.append(f"### {rid} (score: {r['score']:.0%})")
        lines.append("")
        if not r["status_match"]:
            lines.append(f"- **Status**: predicted `{r['status_predicted']}`, expected `{r['status_expected']}`")
        if not r["amount_match"]:
            lines.append(f"- **Amount**: predicted `{r['amount_predicted']:.2f}`, expected `{r['amount_expected']:.2f}` (error: {r['amount_error']:.1%})")
        if not r["method_match"]:
            lines.append(f"- **Method**: predicted `{r['method_predicted']}`, expected `{r['method_expected']}`")
        if not r["plan_match"]:
            lines.append(f"- **Plan**: {r['plan_details']}")
        if not r["date_match"]:
            lines.append(f"- **Date**: off by {r['date_diff_days']} days")
        if not r["changes_match"]:
            lines.append(f"- **Changes**: mismatch")
        lines.append("")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"\n[NOTE] Report written to {report_path}")
