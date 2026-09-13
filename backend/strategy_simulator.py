"""
AFFORDAI Strategy Simulator

Generates and evaluates 6 candidate payment strategies:
1. BUY_NOW_FULL — pay everything today
2. PARTIAL_PAYMENT — pay safe amount now, rest later  
3. INSTALLMENTS — use each installment plan from payment_options
4. WAIT — postpone until earliest safe date
5. REDUCE_SPENDING — stop/reduce flexible expenses then pay
6. DO_NOT_PROCEED — fallback when nothing works
"""

from __future__ import annotations
from datetime import date, timedelta
from typing import Optional

from backend.models import (
    FinancialSafetyTwin, FinancialRequest, PaymentOption,
    StrategyResult, PaymentPlanEntry, SpendingChange,
    CashFlowForecast, RecurringExpense,
)
from backend.forecast_engine import (
    forecast_cash_flow, compute_safe_amount, find_earliest_full_payment_date,
)
from backend.data_loader import DataStore
from backend.config import (
    METHOD_FULL_PAYMENT, METHOD_PARTIAL_PAYMENT, METHOD_INSTALLMENTS,
    METHOD_WAIT, METHOD_NOT_RECOMMENDED,
)


def evaluate_all_strategies(
    twin: FinancialSafetyTwin,
    request: FinancialRequest,
    payment_options: list[PaymentOption],
    data: DataStore,
) -> list[StrategyResult]:
    """
    Generate and evaluate all candidate strategies for a request.
    
    Returns a list of StrategyResult objects, sorted by preference
    (valid strategies first, then by safety margin and cost).
    """
    strategies = []
    
    # 1. BUY NOW (full payment)
    strategies.append(_evaluate_buy_now(twin, request, data))
    
    # 2. INSTALLMENTS (each installment option)
    for opt in payment_options:
        if opt.payment_method == "installments":
            strategies.append(_evaluate_installments(twin, request, opt, data))
    
    # 3. WAIT (pay full later)
    strategies.append(_evaluate_wait(twin, request, data))
    
    # 4. PARTIAL PAYMENT (if allowed)
    if request.allows_partial_payment:
        strategies.append(_evaluate_partial(twin, request, data))
    
    # 5. REDUCE SPENDING + pay
    spending_strategies = _evaluate_reduce_spending(twin, request, payment_options, data)
    strategies.extend(spending_strategies)
    
    # 6. DO NOT PROCEED (always available as fallback)
    strategies.append(_evaluate_do_not_proceed(twin, request, data))
    
    return strategies


def select_best_strategy(
    strategies: list[StrategyResult],
    twin: FinancialSafetyTwin,
    request: FinancialRequest,
) -> StrategyResult:
    """
    Select the best strategy from evaluated candidates.

    Priority order:
    1. Must be valid (passes safety checks)
    2. NEVER prefer DO_NOT_PROCEED over an action strategy
    3. Prefer user-accepted methods
    4. Prefer fewer spending changes
    5. Prefer method with lower priority number (full > installments > partial > wait)
    6. Prefer lower financing cost
    7. Prefer higher safety margin
    """
    METHOD_PRIORITY = {
        METHOD_FULL_PAYMENT: 0,
        METHOD_INSTALLMENTS: 1,
        METHOD_PARTIAL_PAYMENT: 2,
        METHOD_WAIT: 3,
        METHOD_NOT_RECOMMENDED: 99,
    }

    valid = [s for s in strategies if s.is_valid]

    if not valid:
        for s in strategies:
            if s.strategy_name == "DO_NOT_PROCEED":
                return s
        return strategies[-1]

    # Separate action strategies from the do-not-proceed fallback
    action_strategies = [s for s in valid if s.payment_method != METHOD_NOT_RECOMMENDED]
    fallback = [s for s in valid if s.payment_method == METHOD_NOT_RECOMMENDED]

    # Only use fallback if no action strategy exists
    candidates = action_strategies if action_strategies else fallback

    # Among candidates, prefer user-accepted methods
    accepted = twin.accepted_payment_methods
    preferred = [s for s in candidates if s.payment_method in accepted]
    final_candidates = preferred if preferred else candidates

    def score(s: StrategyResult) -> tuple:
        method_prio = METHOD_PRIORITY.get(s.payment_method, 50)
        spending_penalty = len(s.spending_changes)
        return (
            spending_penalty,     # Fewer changes is better
            method_prio,          # Lower method priority number is better
            s.total_cost,         # Lower cost is better
            -s.safety_margin,     # Higher margin is better (negated)
        )

    final_candidates.sort(key=score)
    return final_candidates[0]


# ═══════════════════════════════════════════════════════════════════════════════
# Individual Strategy Evaluators
# ═══════════════════════════════════════════════════════════════════════════════

def _evaluate_buy_now(
    twin: FinancialSafetyTwin,
    request: FinancialRequest,
    data: DataStore,
) -> StrategyResult:
    """Strategy: Pay the full amount today."""
    payment = [PaymentPlanEntry(
        payment_date=request.request_date,
        amount=request.requested_amount,
    )]
    
    forecast = forecast_cash_flow(
        twin, request.request_date, data, additional_debits=payment
    )
    
    safe_amount = compute_safe_amount(twin, request.request_date, data)
    
    return StrategyResult(
        strategy_name="BUY_NOW_FULL",
        is_valid=forecast.is_safe,
        payment_method=METHOD_FULL_PAYMENT,
        payment_plan=payment,
        amount_safe_to_pay=safe_amount,
        earliest_full_payment_date=request.request_date if forecast.is_safe else None,
        spending_changes=[],
        safety_margin=forecast.minimum_balance_reached - twin.minimum_balance,
        total_cost=request.requested_amount,
        forecast=forecast,
    )


def _evaluate_installments(
    twin: FinancialSafetyTwin,
    request: FinancialRequest,
    option: PaymentOption,
    data: DataStore,
) -> StrategyResult:
    """Strategy: Use a specific installment plan."""
    # Build the payment schedule
    payments = []
    current_date = option.first_payment_date or request.request_date
    
    for i in range(option.number_of_payments):
        payments.append(PaymentPlanEntry(
            payment_date=current_date,
            amount=option.payment_amount,
        ))
        if option.payment_frequency_days:
            current_date = current_date + timedelta(days=option.payment_frequency_days)
    
    # Check if plan completes by desired date
    last_payment_date = payments[-1].payment_date if payments else request.request_date
    completes_on_time = last_payment_date <= request.desired_completion_date
    
    # Check max installment months
    if twin.max_installment_months:
        plan_months = (last_payment_date - request.request_date).days / 30
        if plan_months > twin.max_installment_months:
            return StrategyResult(
                strategy_name=f"INSTALLMENTS_{option.payment_option_id}",
                is_valid=False,
                payment_method=METHOD_INSTALLMENTS,
                payment_plan=payments,
                amount_safe_to_pay=compute_safe_amount(twin, request.request_date, data),
                earliest_full_payment_date=None,
                spending_changes=[],
                safety_margin=-1,
                total_cost=option.total_payable_amount,
                forecast=None,
                rejection_reason="Exceeds max installment months",
            )
    
    # Simulate the full installment plan
    forecast = forecast_cash_flow(
        twin, request.request_date, data, additional_debits=payments
    )
    
    safe_amount = compute_safe_amount(twin, request.request_date, data)
    
    return StrategyResult(
        strategy_name=f"INSTALLMENTS_{option.payment_option_id}",
        is_valid=forecast.is_safe and completes_on_time,
        payment_method=METHOD_INSTALLMENTS,
        payment_plan=payments,
        amount_safe_to_pay=safe_amount,
        earliest_full_payment_date=last_payment_date if forecast.is_safe else None,
        spending_changes=[],
        safety_margin=forecast.minimum_balance_reached - twin.minimum_balance,
        total_cost=option.total_payable_amount,
        forecast=forecast,
        rejection_reason=None if (forecast.is_safe and completes_on_time) else (
            "Plan breaches minimum balance" if not forecast.is_safe else "Does not complete on time"
        ),
    )


def _evaluate_wait(
    twin: FinancialSafetyTwin,
    request: FinancialRequest,
    data: DataStore,
) -> StrategyResult:
    """Strategy: Wait until the earliest safe date to pay in full.
    
    Extends forecast window to cover desired_completion_date so we can
    find payment dates beyond 90 days.
    """
    from backend.config import FORECAST_DAYS
    
    safe_amount = compute_safe_amount(twin, request.request_date, data)
    
    # Compute extended horizon: at least FORECAST_DAYS, at most to completion date + 30
    days_to_completion = (request.desired_completion_date - request.request_date).days
    extended_days = max(FORECAST_DAYS, days_to_completion + 30)
    
    # Build extended base forecast (without purchase)
    end_date = request.request_date + timedelta(days=extended_days)
    from backend.forecast_engine import _build_flow_schedule, CashFlowForecast as CF
    
    earliest = find_earliest_full_payment_date(
        twin, request.request_date, request.requested_amount, data,
        desired_completion_date=request.desired_completion_date,
        extended_days=extended_days,
    )
    
    if earliest and earliest > request.request_date:
        # Can pay later
        payment = [PaymentPlanEntry(
            payment_date=earliest,
            amount=request.requested_amount,
        )]
        
        # Use extended forecast that covers the payment date
        forecast = forecast_cash_flow(
            twin, request.request_date, data,
            additional_debits=payment,
            forecast_days=extended_days,
        )
        
        completes_on_time = earliest <= request.desired_completion_date
        
        return StrategyResult(
            strategy_name="WAIT",
            is_valid=forecast.is_safe and completes_on_time,
            payment_method=METHOD_WAIT,
            payment_plan=payment,
            amount_safe_to_pay=safe_amount,
            earliest_full_payment_date=earliest,
            spending_changes=[],
            safety_margin=forecast.minimum_balance_reached - twin.minimum_balance,
            total_cost=request.requested_amount,
            forecast=forecast,
            rejection_reason=None if completes_on_time else "Cannot complete by desired date",
        )
    
    return StrategyResult(
        strategy_name="WAIT",
        is_valid=False,
        payment_method=METHOD_WAIT,
        payment_plan=[],
        amount_safe_to_pay=safe_amount,
        earliest_full_payment_date=earliest,
        spending_changes=[],
        safety_margin=-1,
        total_cost=request.requested_amount,
        forecast=None,
        rejection_reason="Cannot afford full payment within forecast period",
    )


def _evaluate_partial(
    twin: FinancialSafetyTwin,
    request: FinancialRequest,
    data: DataStore,
) -> StrategyResult:
    """Strategy: Pay what's safe now, pay the rest on the earliest safe date."""
    safe_amount = compute_safe_amount(twin, request.request_date, data)
    
    if safe_amount <= 0:
        return StrategyResult(
            strategy_name="PARTIAL",
            is_valid=False,
            payment_method=METHOD_PARTIAL_PAYMENT,
            payment_plan=[],
            amount_safe_to_pay=0,
            earliest_full_payment_date=None,
            spending_changes=[],
            safety_margin=-1,
            total_cost=request.requested_amount,
            forecast=None,
            rejection_reason="No safe amount to pay today",
        )
    
    remaining = request.requested_amount - safe_amount
    
    # Pay safe amount today
    payments = [PaymentPlanEntry(
        payment_date=request.request_date,
        amount=safe_amount,
    )]
    
    # Find when we can pay the rest
    if remaining > 0:
        # After first payment, find earliest date for the remainder
        # We need to simulate the first payment, then find when remainder is safe
        earliest_remainder = find_earliest_full_payment_date(
            twin, request.request_date, request.requested_amount, data,
            desired_completion_date=request.desired_completion_date,
        )
        
        if earliest_remainder and earliest_remainder > request.request_date:
            # Pay remainder on that date
            payments.append(PaymentPlanEntry(
                payment_date=earliest_remainder,
                amount=remaining,
            ))
        else:
            # Can't find a safe date for remainder
            return StrategyResult(
                strategy_name="PARTIAL",
                is_valid=False,
                payment_method=METHOD_PARTIAL_PAYMENT,
                payment_plan=payments,
                amount_safe_to_pay=safe_amount,
                earliest_full_payment_date=None,
                spending_changes=[],
                safety_margin=-1,
                total_cost=request.requested_amount,
                forecast=None,
                rejection_reason="Cannot pay remainder within forecast period",
            )
    
    # Simulate the full partial plan
    forecast = forecast_cash_flow(
        twin, request.request_date, data, additional_debits=payments
    )
    
    last_payment_date = payments[-1].payment_date
    completes_on_time = last_payment_date <= request.desired_completion_date
    
    return StrategyResult(
        strategy_name="PARTIAL",
        is_valid=forecast.is_safe and completes_on_time,
        payment_method=METHOD_PARTIAL_PAYMENT,
        payment_plan=payments,
        amount_safe_to_pay=safe_amount,
        earliest_full_payment_date=last_payment_date if forecast.is_safe else None,
        spending_changes=[],
        safety_margin=forecast.minimum_balance_reached - twin.minimum_balance,
        total_cost=request.requested_amount,
        forecast=forecast,
        rejection_reason=None if (forecast.is_safe and completes_on_time) else "Plan is not safe",
    )


def _evaluate_reduce_spending(
    twin: FinancialSafetyTwin,
    request: FinancialRequest,
    payment_options: list[PaymentOption],
    data: DataStore,
) -> list[StrategyResult]:
    """
    Strategy: Reduce or stop flexible expenses, then try to pay.
    
    Tries combinations of stopping/reducing expenses the user is willing to adjust.
    """
    results = []
    
    # Find stoppable and reducible expenses
    stoppable = []
    reducible = []
    
    for exp in twin.recurring_expenses:
        if exp.category in twin.willing_to_stop:
            if exp.flexibility in ("stoppable", "reducible_or_stoppable"):
                stoppable.append(exp)
        if exp.category in twin.willing_to_reduce:
            if exp.flexibility in ("reducible", "reducible_or_stoppable"):
                reducible.append(exp)
    
    # Generate spending change combinations
    change_sets = _generate_change_combinations(stoppable, reducible)
    
    for changes in change_sets:
        if not changes:
            continue
        
        # Calculate savings from changes
        # Try buy-now with spending changes
        safe_amount = compute_safe_amount(
            twin, request.request_date, data, spending_changes=changes
        )
        
        payment = [PaymentPlanEntry(
            payment_date=request.request_date,
            amount=request.requested_amount,
        )]
        
        forecast = forecast_cash_flow(
            twin, request.request_date, data,
            additional_debits=payment,
            spending_changes=changes,
        )
        
        if forecast.is_safe:
            results.append(StrategyResult(
                strategy_name=f"REDUCE_BUY_NOW",
                is_valid=True,
                payment_method=METHOD_FULL_PAYMENT,
                payment_plan=payment,
                amount_safe_to_pay=safe_amount,
                earliest_full_payment_date=request.request_date,
                spending_changes=changes,
                safety_margin=forecast.minimum_balance_reached - twin.minimum_balance,
                total_cost=request.requested_amount,
                forecast=forecast,
            ))
        
        # Also try installments with spending changes
        for opt in payment_options:
            if opt.payment_method != "installments":
                continue
            
            inst_payments = []
            current_date = opt.first_payment_date or request.request_date
            for i in range(opt.number_of_payments):
                inst_payments.append(PaymentPlanEntry(
                    payment_date=current_date,
                    amount=opt.payment_amount,
                ))
                if opt.payment_frequency_days:
                    current_date += timedelta(days=opt.payment_frequency_days)
            
            forecast_inst = forecast_cash_flow(
                twin, request.request_date, data,
                additional_debits=inst_payments,
                spending_changes=changes,
            )
            
            last_date = inst_payments[-1].payment_date if inst_payments else request.request_date
            completes = last_date <= request.desired_completion_date
            
            if forecast_inst.is_safe and completes:
                results.append(StrategyResult(
                    strategy_name=f"REDUCE_INSTALLMENTS_{opt.payment_option_id}",
                    is_valid=True,
                    payment_method=METHOD_INSTALLMENTS,
                    payment_plan=inst_payments,
                    amount_safe_to_pay=safe_amount,
                    earliest_full_payment_date=last_date,
                    spending_changes=changes,
                    safety_margin=forecast_inst.minimum_balance_reached - twin.minimum_balance,
                    total_cost=opt.total_payable_amount,
                    forecast=forecast_inst,
                ))
    
    return results


def _evaluate_do_not_proceed(
    twin: FinancialSafetyTwin,
    request: FinancialRequest,
    data: DataStore,
) -> StrategyResult:
    """Fallback strategy: do not proceed with the purchase."""
    safe_amount = compute_safe_amount(twin, request.request_date, data)
    
    return StrategyResult(
        strategy_name="DO_NOT_PROCEED",
        is_valid=True,  # Always "valid" as a fallback
        payment_method=METHOD_NOT_RECOMMENDED,
        payment_plan=[],
        amount_safe_to_pay=safe_amount,
        earliest_full_payment_date=None,
        spending_changes=[],
        safety_margin=0,
        total_cost=0,
        forecast=None,
    )


def _generate_change_combinations(
    stoppable: list[RecurringExpense],
    reducible: list[RecurringExpense],
) -> list[list[SpendingChange]]:
    """
    Generate combinations of spending changes to try.
    Keep it manageable — try individual changes and small combos.
    """
    combos = []
    
    # Individual stops
    for exp in stoppable:
        combos.append([SpendingChange(
            action="stop",
            event_id=exp.sample_event_id,
        )])
    
    # Individual reductions
    for exp in reducible:
        if exp.minimum_allowed_amount is not None:
            combos.append([SpendingChange(
                action="reduce_to",
                event_id=exp.sample_event_id,
                reduce_to_amount=exp.minimum_allowed_amount,
            )])
    
    # Combinations: all stops + all reductions
    if stoppable or reducible:
        full_combo = []
        for exp in stoppable:
            full_combo.append(SpendingChange(action="stop", event_id=exp.sample_event_id))
        for exp in reducible:
            if exp.minimum_allowed_amount is not None:
                full_combo.append(SpendingChange(
                    action="reduce_to",
                    event_id=exp.sample_event_id,
                    reduce_to_amount=exp.minimum_allowed_amount,
                ))
        if full_combo:
            combos.append(full_combo)
    
    # Pairwise combinations of stops
    for i in range(len(stoppable)):
        for j in range(i + 1, len(stoppable)):
            combos.append([
                SpendingChange(action="stop", event_id=stoppable[i].sample_event_id),
                SpendingChange(action="stop", event_id=stoppable[j].sample_event_id),
            ])
    
    # Stop + reduce combos
    for s in stoppable:
        for r in reducible:
            if r.minimum_allowed_amount is not None:
                combos.append([
                    SpendingChange(action="stop", event_id=s.sample_event_id),
                    SpendingChange(
                        action="reduce_to",
                        event_id=r.sample_event_id,
                        reduce_to_amount=r.minimum_allowed_amount,
                    ),
                ])
    
    return combos
