"""Quick integration test — process request_01 without LLM to validate financial engine."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from backend.data_loader import load_all_data
from backend.profile_builder import build_safety_twin
from backend.forecast_engine import forecast_cash_flow, compute_safe_amount, find_earliest_full_payment_date
from backend.strategy_simulator import evaluate_all_strategies, select_best_strategy
from backend.safety_engine import validate_strategy, determine_affordability_status, compute_safety_score
from backend.utils import format_amount, format_payment_plan, format_spending_changes

# Load data
data = load_all_data()

# Test with request_01 (ground truth: affordable_now, full_payment, safe=25256)
req = data.requests["request_01"]
print(f"\n=== Testing {req.request_id} ===")
print(f"User: {req.user_id}")
print(f"Amount: {req.requested_amount}")
print(f"Date: {req.request_date}")
print(f"Text: {req.request_text[:80]}...")

# Build twin
twin = build_safety_twin(req.user_id, req.request_date, data)
print(f"\nFinancial Safety Twin:")
print(f"  Balance: {twin.home_currency} {twin.current_balance:,.2f}")
print(f"  Minimum: {twin.home_currency} {twin.minimum_balance:,.2f}")
print(f"  Income streams: {len(twin.income_streams)}")
for inc in twin.income_streams:
    print(f"    - {inc.source}: {twin.home_currency} {inc.amount:,.2f} on day {inc.day_of_month}")
print(f"  Recurring expenses: {len(twin.recurring_expenses)}")
for exp in twin.recurring_expenses:
    print(f"    - {exp.category}: {twin.home_currency} {exp.median_amount:,.2f} ({exp.flexibility})")
print(f"  Pending debits: {len(twin.pending_debits)}")
print(f"  Pending credits: {len(twin.pending_credits)}")
print(f"  Accepted methods: {twin.accepted_payment_methods}")

# Forecast
forecast = forecast_cash_flow(twin, req.request_date, data)
print(f"\n90-day Forecast (no purchase):")
print(f"  Safe: {forecast.is_safe}")
print(f"  Min balance reached: {twin.home_currency} {forecast.minimum_balance_reached:,.2f}")
print(f"  Min balance date: {forecast.minimum_balance_date}")

# Compute safe amount
safe = compute_safe_amount(twin, req.request_date, data)
print(f"\nAmount safe to pay: {twin.home_currency} {safe:,.2f}")
print(f"  Expected: 25,256.00")

# Earliest full payment
earliest = find_earliest_full_payment_date(twin, req.request_date, req.requested_amount, data)
print(f"\nEarliest full payment: {earliest}")
print(f"  Expected: 2024-03-03")

# Strategies
payment_options = data.payment_options_by_request.get(req.request_id, [])
strategies = evaluate_all_strategies(twin, req, payment_options, data)
for s in strategies:
    validate_strategy(s, twin, req)
    valid = "VALID" if s.is_valid else f"INVALID ({s.rejection_reason})"
    print(f"\n  Strategy: {s.strategy_name}")
    print(f"    Valid: {valid}")
    print(f"    Method: {s.payment_method}")
    print(f"    Safe margin: {s.safety_margin:,.2f}")
    if s.payment_plan:
        print(f"    Plan: {format_payment_plan(s.payment_plan)}")

best = select_best_strategy(strategies, twin, req)
status = determine_affordability_status(best, req)
print(f"\n=== RESULT ===")
print(f"  Status: {status} (expected: affordable_now)")
print(f"  Method: {best.payment_method} (expected: full_payment)")
print(f"  Safe: {safe:,.2f} (expected: 25,256)")
print(f"  Plan: {format_payment_plan(best.payment_plan)} (expected: 2024-03-03:25256)")

# Test request_05 (not_affordable)
print("\n\n=== Testing request_05 (expected: not_affordable) ===")
req5 = data.requests["request_05"]
print(f"User: {req5.user_id}, Amount: {req5.requested_amount}")
twin5 = build_safety_twin(req5.user_id, req5.request_date, data)
safe5 = compute_safe_amount(twin5, req5.request_date, data)
print(f"  Balance: {twin5.home_currency} {twin5.current_balance:,.2f}")
print(f"  Minimum: {twin5.home_currency} {twin5.minimum_balance:,.2f}")
print(f"  Safe to pay: {safe5:,.2f} (expected: 737)")

payment_options5 = data.payment_options_by_request.get(req5.request_id, [])
strategies5 = evaluate_all_strategies(twin5, req5, payment_options5, data)
for s in strategies5:
    validate_strategy(s, twin5, req5)
best5 = select_best_strategy(strategies5, twin5, req5)
status5 = determine_affordability_status(best5, req5)
print(f"  Status: {status5} (expected: not_affordable)")
print(f"  Method: {best5.payment_method} (expected: not_recommended)")
