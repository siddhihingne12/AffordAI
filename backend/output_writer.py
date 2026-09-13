"""
AFFORDAI Output Writer

Writes the final output.csv with the exact schema required by the problem statement.
Column order and names must match exactly.
"""

from __future__ import annotations
import csv
from pathlib import Path

from backend.config import DATASET_DIR
from backend.models import AgentDecision


OUTPUT_COLUMNS = [
    "request_id",
    "amount_safe_to_pay",
    "affordability_status",
    "recommended_payment_method",
    "payment_plan",
    "earliest_date_for_full_payment",
    "spending_changes_needed",
    "decision_explanation",
]


def write_output(
    decisions: list[AgentDecision],
    output_path: Path | None = None,
) -> Path:
    """
    Write all decisions to output.csv with exact schema.
    
    Args:
        decisions: List of AgentDecision objects to write
        output_path: Override output path (default: dataset/output.csv)
        
    Returns:
        Path to the written output file
    """
    if output_path is None:
        output_path = DATASET_DIR / "output.csv"
    
    # Sort by request_id (numeric order)
    decisions.sort(key=lambda d: int(d.request_id.split("_")[1]))
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        
        for decision in decisions:
            row = decision.to_csv_row()
            writer.writerow(row)
    
    print(f"\n[OUT] Output written to {output_path} ({len(decisions)} rows)")
    return output_path
