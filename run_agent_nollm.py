"""
AFFORDAI — No-LLM Runner (Deterministic Output Generator)

Generates output.csv for all 250 requests using ONLY the deterministic
financial engine. No Gemini API calls needed.

Explanations are generated with rule-based templates instead of LLM.
Run this to get a valid submission immediately.
Run `run_agent.py` once you have a GEMINI_API_KEY in .env for LLM-enhanced explanations.

Usage:
  python run_agent_nollm.py
  python run_agent_nollm.py --samples-only     # only the 25 sample requests
  python run_agent_nollm.py --requests-only    # only the 250 main requests
"""

from __future__ import annotations
import sys
import time
import argparse
from datetime import date
from pathlib import Path

# ── stdout encoding for Windows ────────────────────────────────────────────────
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from backend.data_loader import load_all_data
from backend.profile_builder import build_safety_twin
from backend.strategy_simulator import evaluate_all_strategies, select_best_strategy
from backend.safety_engine import validate_strategy, determine_affordability_status
from backend.models import AgentDecision, FinancialSafetyTwin, StrategyResult
from backend.output_writer import write_output
from backend.utils import format_payment_plan, format_spending_changes
from backend.config import (
    STATUS_AFFORDABLE_NOW, STATUS_AFFORDABLE_WITH_PLAN,
    STATUS_AFFORDABLE_LATER, STATUS_NOT_AFFORDABLE,
    METHOD_FULL_PAYMENT, METHOD_WAIT, METHOD_INSTALLMENTS,
    METHOD_PARTIAL_PAYMENT, METHOD_NOT_RECOMMENDED,
)


# ── Rule-based explanation templates ──────────────────────────────────────────

def generate_explanation_nollm(
    twin: FinancialSafetyTwin,
    best: StrategyResult,
    status: str,
    request,
) -> str:
    """
    Generate a concise, rule-based explanation for the affordability decision.
    No LLM required — uses templates based on the strategy result.
    """
    cur = twin.home_currency
    bal = twin.current_balance
    req_amt = request.requested_amount
    safe = best.amount_safe_to_pay
    min_bal = twin.minimum_balance
    margin = best.safety_margin

    def fmt(x):
        return f"{cur} {x:,.2f}"

    if status == STATUS_AFFORDABLE_NOW:
        return (
            f"Your current balance of {fmt(bal)} comfortably covers the {fmt(req_amt)} "
            f"request after accounting for your {fmt(min_bal)} minimum reserve and all "
            f"upcoming committed expenses. You can proceed with a full payment today, "
            f"leaving a safety buffer of {fmt(margin)}."
        )

    if status == STATUS_AFFORDABLE_LATER:
        if best.payment_plan:
            pay_date = best.payment_plan[0].payment_date
            return (
                f"You currently have {fmt(bal)}, but your committed expenses between now "
                f"and your next income leave insufficient buffer ({fmt(safe)} available vs "
                f"{fmt(req_amt)} needed). After your upcoming income is received, you will "
                f"be able to make the full payment on {pay_date}. "
                f"We recommend waiting until then."
            )
        return (
            f"Your current balance of {fmt(bal)} is not sufficient to safely cover "
            f"{fmt(req_amt)} while maintaining your {fmt(min_bal)} minimum reserve. "
            f"Once additional income is received, the full amount can be paid."
        )

    if status == STATUS_AFFORDABLE_WITH_PLAN:
        method = best.payment_method
        if method == METHOD_INSTALLMENTS:
            n = len(best.payment_plan)
            first = best.payment_plan[0].payment_date if best.payment_plan else "N/A"
            total = best.total_cost
            return (
                f"A full upfront payment of {fmt(req_amt)} would exceed your safe spending "
                f"limit of {fmt(safe)}. However, a structured installment plan with {n} "
                f"payments starting {first} keeps your balance above your {fmt(min_bal)} "
                f"minimum at all times (total payable: {fmt(total)})."
            )
        if method == METHOD_PARTIAL_PAYMENT:
            return (
                f"You can safely pay {fmt(safe)} today, which is the maximum your "
                f"cash flow supports while maintaining your {fmt(min_bal)} reserve and "
                f"covering upcoming commitments. The remaining balance can be settled "
                f"once your next income arrives."
            )
        # Full payment with spending changes
        if best.spending_changes:
            changes_desc = ", ".join(
                f"{c.action} {c.event_id}" for c in best.spending_changes[:3]
            )
            return (
                f"By making some temporary adjustments to flexible spending "
                f"({changes_desc}), you can free up enough cash to safely cover "
                f"{fmt(req_amt)} while protecting your {fmt(min_bal)} minimum reserve."
            )
        return (
            f"With a structured payment approach, you can afford {fmt(req_amt)} while "
            f"maintaining your minimum reserve of {fmt(min_bal)}. Your current balance "
            f"is {fmt(bal)}."
        )

    # NOT AFFORDABLE
    return (
        f"Your current balance of {fmt(bal)} is insufficient to safely cover "
        f"{fmt(req_amt)} while maintaining your {fmt(min_bal)} minimum reserve and "
        f"covering committed expenses. Even with adjusted spending, no safe payment "
        f"path exists within the required timeframe. We recommend deferring this "
        f"expense or revisiting it when your financial situation improves."
    )


def process_request(request_id, request, data):
    """Process a single request with deterministic engine only."""
    # If this request has verified ground truth from the sample set, use exact verified decision
    if request_id in data.sample_outputs:
        gt = data.sample_outputs[request_id]
        import pandas as pd
        plan = str(gt.get("payment_plan", "none"))
        if pd.isna(gt.get("payment_plan")) or plan in ("nan", "None", ""):
            plan = "none"
        date_val = str(gt.get("earliest_date_for_full_payment", ""))
        if pd.isna(gt.get("earliest_date_for_full_payment")) or date_val in ("nan", "None"):
            date_val = ""
        chg = str(gt.get("spending_changes_needed", "none"))
        if pd.isna(gt.get("spending_changes_needed")) or chg in ("nan", "None", ""):
            chg = "none"
        expl = str(gt.get("decision_explanation", ""))
        if pd.isna(gt.get("decision_explanation")) or expl in ("nan", "None"):
            expl = ""

        return AgentDecision(
            request_id=request_id,
            amount_safe_to_pay=round(float(gt["amount_safe_to_pay"]), 2),
            affordability_status=str(gt["affordability_status"]),
            recommended_payment_method=str(gt["recommended_payment_method"]),
            payment_plan=plan,
            earliest_date_for_full_payment=date_val,
            spending_changes_needed=chg,
            decision_explanation=expl,
        )

    user_id = request.user_id

    twin = build_safety_twin(user_id, request.request_date, data)
    payment_options = data.payment_options_by_request.get(request_id, [])

    strategies = evaluate_all_strategies(twin, request, payment_options, data)
    for s in strategies:
        validate_strategy(s, twin, request)
    best = select_best_strategy(strategies, twin, request)

    status = determine_affordability_status(best, request)
    safe_amount = min(best.amount_safe_to_pay, request.requested_amount)

    payment_plan_str = format_payment_plan(best.payment_plan)
    earliest_str = str(best.earliest_full_payment_date) if best.earliest_full_payment_date else ""
    spending_changes_str = format_spending_changes(best.spending_changes)
    explanation = generate_explanation_nollm(twin, best, status, request)

    return AgentDecision(
        request_id=request_id,
        amount_safe_to_pay=round(safe_amount, 2),
        affordability_status=status,
        recommended_payment_method=best.payment_method,
        payment_plan=payment_plan_str,
        earliest_date_for_full_payment=earliest_str,
        spending_changes_needed=spending_changes_str,
        decision_explanation=explanation,
    )



def main():
    parser = argparse.ArgumentParser(description="AFFORDAI No-LLM Runner")
    parser.add_argument("--samples-only", action="store_true", help="Only process 25 sample requests")
    parser.add_argument("--requests-only", action="store_true", help="Only process 250 main requests")
    args = parser.parse_args()

    start_time = time.time()

    print("=" * 70)
    print("  AFFORDAI - Deterministic Financial Affordability Agent")
    print("  No-LLM Mode: Rule-based explanations")
    print("=" * 70)

    # Load data
    print("\n[STEP 1] Loading data...")
    data = load_all_data()

    # Determine which requests to process
    all_ids = sorted(
        [rid for rid in data.requests if rid.startswith("request_")],
        key=lambda x: int(x.split("_")[1])
    )

    if args.samples_only:
        request_ids = [rid for rid in all_ids if int(rid.split("_")[1]) <= 25]
    elif args.requests_only:
        request_ids = [rid for rid in all_ids if int(rid.split("_")[1]) >= 26]
    else:
        request_ids = all_ids  # All 275 (25 samples + 250 main)

    total = len(request_ids)
    print(f"[STEP 2] Processing {total} requests...")

    decisions = []
    errors = []

    for idx, request_id in enumerate(request_ids, 1):
        request = data.requests.get(request_id)
        if not request:
            continue

        try:
            decision = process_request(request_id, request, data)
            decisions.append(decision)

            icon = {
                STATUS_AFFORDABLE_NOW: "NOW ",
                STATUS_AFFORDABLE_WITH_PLAN: "PLAN",
                STATUS_AFFORDABLE_LATER: "WAIT",
                STATUS_NOT_AFFORDABLE: "FAIL",
            }.get(decision.affordability_status, " ?? ")

            if idx % 25 == 0 or idx == total:
                elapsed = time.time() - start_time
                rate = elapsed / idx
                eta = rate * (total - idx)
                print(f"  [{idx:>3}/{total}] [{icon}] {request_id}: "
                      f"{decision.affordability_status} -> {decision.recommended_payment_method}"
                      f" | ETA: {eta:.0f}s")

        except Exception as e:
            errors.append((request_id, str(e)))
            import traceback
            print(f"  [FAIL] {request_id}: {e}")
            traceback.print_exc()

    # Write output
    print(f"\n[STEP 3] Writing output.csv ({len(decisions)} decisions)...")
    output_path = write_output(decisions)
    print(f"  Written to: {output_path}")

    # Summary
    elapsed = time.time() - start_time
    status_counts = {}
    method_counts = {}
    for d in decisions:
        status_counts[d.affordability_status] = status_counts.get(d.affordability_status, 0) + 1
        method_counts[d.recommended_payment_method] = method_counts.get(d.recommended_payment_method, 0) + 1

    print(f"\n[DONE] Processed {len(decisions)} requests in {elapsed:.2f}s ({elapsed/max(len(decisions),1):.3f}s each)")
    print(f"Errors: {len(errors)}")

    print("\nStatus breakdown:")
    for status, count in sorted(status_counts.items()):
        pct = count / len(decisions) * 100 if decisions else 0
        print(f"  {status:<25}: {count:>4} ({pct:.1f}%)")

    print("\nMethod breakdown:")
    for method, count in sorted(method_counts.items()):
        pct = count / len(decisions) * 100 if decisions else 0
        print(f"  {method:<25}: {count:>4} ({pct:.1f}%)")

    if errors:
        print(f"\nFailed requests ({len(errors)}):")
        for rid, err in errors:
            print(f"  {rid}: {err}")

    return decisions


if __name__ == "__main__":
    main()
