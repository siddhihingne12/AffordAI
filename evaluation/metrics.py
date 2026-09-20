"""
AFFORDAI Evaluation Metrics

Functions to compare agent decisions against ground truth sample outputs.
"""

from __future__ import annotations
from datetime import date, timedelta
from typing import Optional

from backend.models import AgentDecision


def exact_match(predicted: str, expected: str) -> bool:
    """Check exact string match."""
    return str(predicted).strip() == str(expected).strip()


def numeric_accuracy(predicted: float, expected: float, tolerance: float = 0.05) -> tuple[bool, float]:
    """
    Check numeric accuracy within a tolerance.
    
    Returns:
        (is_match, relative_error)
    """
    if expected == 0:
        return predicted == 0, abs(predicted)
    
    error = abs(predicted - expected) / abs(expected)
    return error <= tolerance, error


def date_accuracy(predicted_str: str, expected_str: str, tolerance_days: int = 3) -> tuple[bool, int]:
    """
    Check date accuracy within a tolerance.
    
    Returns:
        (is_match, days_off)
    """
    p = str(predicted_str).strip() if predicted_str is not None else ""
    e = str(expected_str).strip() if expected_str is not None else ""
    if p.lower() in ("nan", "none", "<na>"):
        p = ""
    if e.lower() in ("nan", "none", "<na>"):
        e = ""

    if not p and not e:
        return True, 0
    
    if not p or not e:
        return False, 999
    
    try:
        pred_date = date.fromisoformat(p)
        exp_date = date.fromisoformat(e)
        delta = abs((pred_date - exp_date).days)
        return delta <= tolerance_days, delta
    except (ValueError, TypeError):
        return False, 999


def payment_plan_accuracy(
    predicted_plan: str,
    expected_plan: str,
    date_tolerance: int = 3,
    amount_tolerance: float = 0.05,
) -> tuple[bool, dict]:
    """
    Compare payment plans structurally.
    
    Format: "YYYY-MM-DD:amount|YYYY-MM-DD:amount"
    
    Returns:
        (is_match, details)
    """
    if predicted_plan == expected_plan:
        return True, {"exact_match": True}
    
    if predicted_plan == "none" and expected_plan == "none":
        return True, {"both_none": True}
    
    if predicted_plan == "none" or expected_plan == "none":
        return False, {"mismatch": "one is none"}
    
    pred_entries = _parse_plan(predicted_plan)
    exp_entries = _parse_plan(expected_plan)
    
    if len(pred_entries) != len(exp_entries):
        return False, {"entry_count_mismatch": True, "pred": len(pred_entries), "exp": len(exp_entries)}
    
    total_date_diff = 0
    total_amount_error = 0
    all_match = True
    
    for (pd, pa), (ed, ea) in zip(pred_entries, exp_entries):
        date_match, date_diff = date_accuracy(pd, ed, date_tolerance)
        amount_match, amount_error = numeric_accuracy(pa, ea, amount_tolerance)
        
        total_date_diff += date_diff
        total_amount_error += amount_error
        
        if not date_match or not amount_match:
            all_match = False
    
    return all_match, {
        "avg_date_diff": total_date_diff / len(pred_entries) if pred_entries else 0,
        "avg_amount_error": total_amount_error / len(pred_entries) if pred_entries else 0,
    }


def spending_changes_accuracy(predicted: str, expected: str) -> bool:
    """Compare spending changes — exact match required."""
    # Normalize
    pred = set(predicted.strip().split("|"))
    exp = set(expected.strip().split("|"))
    return pred == exp


def _parse_plan(plan_str: str) -> list[tuple[str, float]]:
    """Parse a payment plan string into (date, amount) tuples."""
    entries = []
    for part in plan_str.split("|"):
        part = part.strip()
        if ":" in part:
            date_str, amount_str = part.rsplit(":", 1)
            try:
                entries.append((date_str.strip(), float(amount_str.strip())))
            except ValueError:
                continue
    return entries


def evaluate_single(predicted: AgentDecision, expected: dict) -> dict:
    """
    Evaluate a single decision against ground truth.
    
    Returns dict with per-field scores and details.
    """
    results = {}
    
    # 1. Affordability Status — exact match
    pred_status = predicted.affordability_status
    exp_status = str(expected.get("affordability_status", ""))
    results["status_match"] = exact_match(pred_status, exp_status)
    results["status_predicted"] = pred_status
    results["status_expected"] = exp_status
    
    # 2. Amount Safe to Pay — within 5%
    pred_amount = float(predicted.amount_safe_to_pay)
    exp_amount = float(expected.get("amount_safe_to_pay", 0))
    amount_match, amount_error = numeric_accuracy(pred_amount, exp_amount)
    results["amount_match"] = amount_match
    results["amount_error"] = amount_error
    results["amount_predicted"] = pred_amount
    results["amount_expected"] = exp_amount
    
    # 3. Recommended Payment Method — exact match
    pred_method = predicted.recommended_payment_method
    exp_method = str(expected.get("recommended_payment_method", ""))
    results["method_match"] = exact_match(pred_method, exp_method)
    results["method_predicted"] = pred_method
    results["method_expected"] = exp_method
    
    # 4. Payment Plan — structural match
    pred_plan = predicted.payment_plan
    exp_plan = str(expected.get("payment_plan", ""))
    plan_match, plan_details = payment_plan_accuracy(pred_plan, exp_plan)
    results["plan_match"] = plan_match
    results["plan_details"] = plan_details
    
    # 5. Earliest Date — within 3 days
    pred_date = predicted.earliest_date_for_full_payment
    exp_date = str(expected.get("earliest_date_for_full_payment", ""))
    date_match, date_diff = date_accuracy(pred_date, exp_date)
    results["date_match"] = date_match
    results["date_diff_days"] = date_diff
    
    # 6. Spending Changes — exact match
    pred_changes = predicted.spending_changes_needed
    exp_changes = str(expected.get("spending_changes_needed", ""))
    results["changes_match"] = spending_changes_accuracy(pred_changes, exp_changes)
    
    # Overall score (weighted)
    weights = {
        "status_match": 0.25,
        "amount_match": 0.20,
        "method_match": 0.20,
        "plan_match": 0.15,
        "date_match": 0.10,
        "changes_match": 0.10,
    }
    results["score"] = sum(
        weights[k] * (1.0 if results[k] else 0.0)
        for k in weights
    )
    
    return results
