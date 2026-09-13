"""Run the official evaluator against the generated output.csv."""
import sys, csv
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
from backend.data_loader import load_all_data
from backend.models import AgentDecision
from evaluation.evaluate import run_evaluation

data = load_all_data()

# Read the generated output.csv
output_csv = Path('dataset/output.csv')
decisions = []

with open(output_csv, 'r', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        # Only evaluate sample requests (request_01 to request_25)
        num = int(row['request_id'].split('_')[1])
        if num > 25:
            continue
        d = AgentDecision(
            request_id=row['request_id'],
            amount_safe_to_pay=float(row['amount_safe_to_pay']),
            affordability_status=row['affordability_status'],
            recommended_payment_method=row['recommended_payment_method'],
            payment_plan=row['payment_plan'],
            earliest_date_for_full_payment=row['earliest_date_for_full_payment'],
            spending_changes_needed=row['spending_changes_needed'],
            decision_explanation=row['decision_explanation'],
        )
        decisions.append(d)

print(f"Loaded {len(decisions)} sample decisions from output.csv")
metrics = run_evaluation(decisions, data, report_path=Path('EVALUATION_REPORT.md'))
