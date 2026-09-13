"""
AFFORDAI Safety Engine

Hard constraint validation for payment strategies.
A strategy FAILS if any of these are violated:
- Balance drops below minimum_balance_to_keep at any point
- Essential expense categories become uncoverable
- Installment payments can't be made on scheduled dates
- Plan doesn't complete by desired_completion_date
- User hasn't accepted the required payment method
"""

from __future__ import annotations
from datetime import date

from backend.models import (
    StrategyResult, FinancialSafetyTwin, FinancialRequest,
)
from backend.config import (
    STATUS_AFFORDABLE_NOW, STATUS_AFFORDABLE_WITH_PLAN,
    STATUS_AFFORDABLE_LATER, STATUS_NOT_AFFORDABLE,
    METHOD_FULL_PAYMENT, METHOD_INSTALLMENTS, METHOD_WAIT,
    METHOD_PARTIAL_PAYMENT, METHOD_NOT_RECOMMENDED,
)


def determine_affordability_status(
    best_strategy: StrategyResult,
    request: FinancialRequest,
) -> str:
    """
    Determine the affordability status based on the best strategy.
    
    Returns one of:
    - affordable_now: Can pay FULL amount TODAY, no spending changes needed
    - affordable_with_plan: Can afford using installments, partial pay, or spending changes
    - affordable_later: Can only afford by waiting for future income (WAIT strategy)
    - not_affordable: No safe strategy exists within the forecast period
    """
    if best_strategy.payment_method == METHOD_NOT_RECOMMENDED:
        return STATUS_NOT_AFFORDABLE
    
    if not best_strategy.is_valid:
        return STATUS_NOT_AFFORDABLE
    
    # WAIT strategy = affordable_later (can pay full but only after future income)
    if best_strategy.payment_method == METHOD_WAIT:
        return STATUS_AFFORDABLE_LATER
    
    # Check if payment is today
    pays_today = (
        best_strategy.payment_plan
        and best_strategy.payment_plan[0].payment_date == request.request_date
    )
    
    # Check if amount_safe_to_pay covers the full requested amount without changes
    safe_covers_full = best_strategy.amount_safe_to_pay >= request.requested_amount
    
    # Affordable NOW: pays today, covers full amount, no spending changes needed
    if (best_strategy.payment_method == METHOD_FULL_PAYMENT
            and pays_today
            and safe_covers_full
            and not best_strategy.spending_changes):
        return STATUS_AFFORDABLE_NOW
    
    # Full payment on a future date with no spending changes = affordable_later
    if (best_strategy.payment_method == METHOD_FULL_PAYMENT
            and not best_strategy.spending_changes
            and best_strategy.payment_plan
            and best_strategy.payment_plan[0].payment_date > request.request_date):
        return STATUS_AFFORDABLE_LATER
    
    # Everything else: installments, partial, spending changes, or today-but-tight
    return STATUS_AFFORDABLE_WITH_PLAN


def validate_strategy(
    strategy: StrategyResult,
    twin: FinancialSafetyTwin,
    request: FinancialRequest,
) -> StrategyResult:
    """
    Apply hard safety checks to a strategy and update its validity.
    
    Checks:
    1. Balance never drops below minimum
    2. Plan completes by desired_completion_date
    3. User accepts the payment method
    4. Installment count within limits
    """
    reasons = []
    
    # Skip DO_NOT_PROCEED — it's always "valid"
    if strategy.payment_method == METHOD_NOT_RECOMMENDED:
        return strategy
    
    # Check 1: Balance safety
    if strategy.forecast and not strategy.forecast.is_safe:
        reasons.append("Balance drops below minimum")
    
    # Check 2: Completion date
    if strategy.payment_plan:
        last_payment = max(p.payment_date for p in strategy.payment_plan)
        if last_payment > request.desired_completion_date:
            reasons.append("Does not complete by desired date")
    
    # Check 3: Payment method accepted
    if strategy.payment_method not in (METHOD_NOT_RECOMMENDED, METHOD_WAIT):
        if strategy.payment_method not in twin.accepted_payment_methods:
            # Wait is always implicitly acceptable
            if strategy.payment_method != METHOD_FULL_PAYMENT:
                reasons.append(f"User does not accept {strategy.payment_method}")
    
    # Check 4: Installment limits
    if strategy.payment_method == METHOD_INSTALLMENTS and twin.max_installment_months:
        if strategy.payment_plan:
            first_date = strategy.payment_plan[0].payment_date
            last_date = strategy.payment_plan[-1].payment_date
            months = (last_date - first_date).days / 30.0
            if months > twin.max_installment_months:
                reasons.append("Exceeds max installment months")
    
    if reasons:
        strategy.is_valid = False
        strategy.rejection_reason = "; ".join(reasons)
    
    return strategy


def compute_safety_score(
    strategy: StrategyResult,
    twin: FinancialSafetyTwin,
    request: FinancialRequest,
) -> float:
    """
    Compute a 0-100 safety score for a strategy.
    
    Dimensions:
    - Cash-flow safety (40%): How much above minimum does balance stay?
    - Emergency buffer (20%): How much buffer above minimum?  
    - Commitment coverage (20%): Are all essential expenses covered?
    - Income certainty (10%): Is income confirmed?
    - Spending flexibility (10%): Can user reduce spending if needed?
    """
    if not strategy.is_valid or strategy.payment_method == METHOD_NOT_RECOMMENDED:
        return 0.0
    
    score = 0.0
    
    # Cash-flow safety (40 points)
    if strategy.safety_margin > 0:
        margin_ratio = strategy.safety_margin / twin.minimum_balance if twin.minimum_balance > 0 else 1
        cash_score = min(40, margin_ratio * 40)
        score += cash_score
    
    # Emergency buffer (20 points)
    buffer = strategy.safety_margin
    if buffer > twin.minimum_balance * 0.5:
        score += 20
    elif buffer > twin.minimum_balance * 0.2:
        score += 12
    elif buffer > 0:
        score += 5
    
    # Commitment coverage (20 points)
    if strategy.forecast and strategy.forecast.is_safe:
        score += 20
    
    # Income certainty (10 points)
    confirmed_income = [s for s in twin.income_streams if s.is_confirmed and s.amount > 0]
    if confirmed_income:
        score += 10
    
    # Spending flexibility (10 points)
    if not strategy.spending_changes:
        score += 10  # No changes needed = more flexible
    elif len(strategy.spending_changes) <= 1:
        score += 5
    
    return min(100, max(0, score))
