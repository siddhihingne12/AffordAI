"""
AFFORDAI Cash-Flow Forecast Engine

Deterministic day-by-day balance simulation over 90 days.
No LLM involved — pure math and date arithmetic.

Key rules:
- Balance must stay >= minimum_balance at every point
- Only count confirmed/settled/scheduled income
- Pending debits reduce available balance
- Cancelled/failed/unrealized events are ignored
- Currency conversion via exchange_rates.csv
"""

from __future__ import annotations
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from backend.models import (
    FinancialSafetyTwin, CashFlowForecast, RecurringExpense,
    IncomeStream, FinancialEvent, PaymentPlanEntry,
)
from backend.config import FORECAST_DAYS
from backend.data_loader import DataStore


def forecast_cash_flow(
    twin: FinancialSafetyTwin,
    request_date: date,
    data: DataStore,
    additional_debits: list[PaymentPlanEntry] | None = None,
    spending_changes: list | None = None,
    forecast_days: int | None = None,
) -> CashFlowForecast:
    """
    Simulate day-by-day cash flow for the user over forecast_days from request_date.
    
    Args:
        twin: The user's Financial Safety Twin
        request_date: Starting date for the forecast
        data: Full data store for currency conversion
        additional_debits: Extra payments to simulate (e.g., the purchase)
        spending_changes: Expenses to stop or reduce
        forecast_days: Override default FORECAST_DAYS (use for extended windows)
        
    Returns:
        CashFlowForecast with daily balances and safety metrics
    """
    days = forecast_days if forecast_days is not None else FORECAST_DAYS
    end_date = request_date + timedelta(days=days)
    
    # Build a schedule of all expected cash flows
    scheduled_flows = _build_flow_schedule(
        twin, request_date, end_date, data, spending_changes
    )
    
    # Add the additional debits (the purchase payments)
    if additional_debits:
        for entry in additional_debits:
            if request_date <= entry.payment_date <= end_date:
                scheduled_flows[entry.payment_date].append(
                    ("debit", entry.amount, "purchase_payment")
                )
    
    # Simulate day by day
    balance = twin.current_balance
    daily_balances = {}
    min_balance = balance
    min_balance_date = request_date
    total_income = 0.0
    total_expenses = 0.0
    
    current = request_date
    while current <= end_date:
        # Apply all flows for this day
        for direction, amount, description in scheduled_flows.get(current, []):
            if direction == "credit":
                balance += amount
                total_income += amount
            elif direction == "debit":
                balance -= amount
                total_expenses += amount
        
        daily_balances[current] = balance
        
        if balance < min_balance:
            min_balance = balance
            min_balance_date = current
        
        current += timedelta(days=1)
    
    is_safe = min_balance >= twin.minimum_balance
    
    return CashFlowForecast(
        daily_balances=daily_balances,
        minimum_balance_reached=min_balance,
        minimum_balance_date=min_balance_date,
        total_income=total_income,
        total_expenses=total_expenses,
        is_safe=is_safe,
    )


def compute_safe_amount(
    twin: FinancialSafetyTwin,
    request_date: date,
    data: DataStore,
    spending_changes: list | None = None,
) -> float:
    """
    Compute the maximum amount the user can safely pay today.

    safe_amount = min(balance over 90-day forecast) - minimum_balance
    This is the maximum that can be safely withdrawn today without
    ever dropping below the minimum_balance in the forecast window.
    Clamped to [0, infinity) by caller (and to requested_amount).
    """
    forecast = forecast_cash_flow(twin, request_date, data, spending_changes=spending_changes)
    safe = forecast.minimum_balance_reached - twin.minimum_balance
    return max(0.0, safe)



def find_earliest_full_payment_date(
    twin: FinancialSafetyTwin,
    request_date: date,
    requested_amount: float,
    data: DataStore,
    desired_completion_date: date | None = None,
    spending_changes: list | None = None,
    extended_days: int | None = None,
) -> Optional[date]:
    """
    Find the earliest date when the user can safely pay the full requested amount.
    
    Optimized: runs base forecast once, then uses suffix-minimum to find the
    earliest date where paying the amount keeps all future balances >= minimum.
    O(n) instead of O(n^2).
    
    Args:
        extended_days: Override default forecast window (for searching beyond 90 days)
    
    Returns the earliest safe date, or None if not possible within the forecast.
    """
    days = extended_days if extended_days is not None else FORECAST_DAYS
    end_date = request_date + timedelta(days=days)
    
    # Build base forecast (no purchase) once — using extended window
    base_forecast = forecast_cash_flow(
        twin, request_date, data,
        spending_changes=spending_changes,
        forecast_days=days,
    )
    daily_balances = base_forecast.daily_balances
    
    if not daily_balances:
        return None
    
    # Sort dates
    dates = sorted(daily_balances.keys())
    min_balance = twin.minimum_balance
    
    # Build suffix minimum: suffix_min[i] = min(balance[dates[i:]])
    suffix_min = [0.0] * len(dates)
    running_min = float("inf")
    for i in range(len(dates) - 1, -1, -1):
        running_min = min(running_min, daily_balances[dates[i]])
        suffix_min[i] = running_min
    
    date_to_idx = {d: i for i, d in enumerate(dates)}
    
    # Scan from request_date forward
    # Paying `amount` on date `pay_date` reduces all balances from that day onwards
    current = request_date
    while current <= end_date:
        if current in date_to_idx:
            idx = date_to_idx[current]
            effective_min = suffix_min[idx] - requested_amount
            if effective_min >= min_balance:
                return current
        current += timedelta(days=1)
    
    return None


def _build_flow_schedule(
    twin: FinancialSafetyTwin,
    start_date: date,
    end_date: date,
    data: DataStore,
    spending_changes: list | None = None,
) -> dict[date, list[tuple[str, float, str]]]:
    """
    Build a complete schedule of expected cash flows from start_date to end_date.
    
    IMPORTANT: current_available_balance already reflects all settled events.
    We only project FUTURE occurrences (dates > start_date) to avoid double-counting.
    Exception: pending/scheduled events may be ON start_date if not yet settled.
    
    Returns:
        dict mapping date -> list of (direction, amount, description) tuples
    """
    import calendar
    flows: dict[date, list[tuple[str, float, str]]] = defaultdict(list)
    
    # Build set of stopped/reduced event IDs for spending changes
    stopped_categories = set()
    reduced_events = {}  # event_id -> new_amount
    if spending_changes:
        for change in spending_changes:
            if change.action == "stop":
                evt = data.events_by_id.get(change.event_id)
                if evt:
                    stopped_categories.add((twin.user_id, evt.category, change.event_id))
            elif change.action == "reduce_to":
                reduced_events[change.event_id] = change.reduce_to_amount
    
    # Track which income events are handled as streams (to avoid double counting)
    income_stream_dates = set()
    
    # ── 1. Recurring Expenses ──────────────────────────────────────────────
    # Only project for dates AFTER start_date (balance already includes settled)
    # Compute how many months to project dynamically from end_date
    months_needed = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 2
    for expense in twin.recurring_expenses:
        is_stopped = any(
            sc[1] == expense.category and sc[0] == twin.user_id
            for sc in stopped_categories
        )
        if is_stopped:
            continue
        
        amount = reduced_events.get(expense.sample_event_id, expense.median_amount)
        
        # Project monthly expenses for future months
        for month_offset in range(months_needed):
            try:
                # Start from the current month of start_date
                base_month = start_date.month + month_offset
                year = start_date.year + (base_month - 1) // 12
                month = (base_month - 1) % 12 + 1
                
                max_day = calendar.monthrange(year, month)[1]
                day = min(expense.typical_day_of_month, max_day)
                expense_date = date(year, month, day)
                
                # Only include dates AFTER start_date (not on start_date)
                if start_date < expense_date <= end_date:
                    flows[expense_date].append(("debit", amount, expense.category))
                elif expense_date > end_date:
                    break
            except (ValueError, OverflowError):
                continue
    
    # ── 2. Income Streams ──────────────────────────────────────────────────
    for income in twin.income_streams:
        if not income.is_confirmed or income.amount <= 0:
            continue
        
        # If there's a specific next_date, use it
        if income.next_date and start_date <= income.next_date <= end_date:
            flows[income.next_date].append(("credit", income.amount, income.source))
            income_stream_dates.add(income.next_date)
            
            # Project subsequent months from next_date until end_date
            prev = income.next_date
            while True:
                try:
                    next_month = prev.month + 1
                    next_year = prev.year + (next_month - 1) // 12
                    next_month = (next_month - 1) % 12 + 1
                    max_day = calendar.monthrange(next_year, next_month)[1]
                    day = min(income.day_of_month, max_day)
                    next_income_date = date(next_year, next_month, day)
                    
                    if next_income_date > end_date:
                        break
                    if start_date < next_income_date <= end_date:
                        flows[next_income_date].append(("credit", income.amount, income.source))
                        income_stream_dates.add(next_income_date)
                    prev = next_income_date
                except (ValueError, OverflowError):
                    break
        else:
            # No specific next_date — project from typical day of month
            for month_offset in range(months_needed):
                try:
                    base_month = start_date.month + month_offset
                    year = start_date.year + (base_month - 1) // 12
                    month = (base_month - 1) % 12 + 1
                    
                    max_day = calendar.monthrange(year, month)[1]
                    day = min(income.day_of_month, max_day)
                    income_date = date(year, month, day)
                    
                    # Only include dates AFTER start_date
                    if start_date < income_date <= end_date:
                        flows[income_date].append(("credit", income.amount, income.source))
                        income_stream_dates.add(income_date)
                    elif income_date > end_date:
                        break
                except (ValueError, OverflowError):
                    continue
    
    # ── 3. Pending/Scheduled One-Off Events ────────────────────────────────
    for event in twin.pending_debits:
        effective_date = event.settlement_date or event.event_date
        if effective_date and start_date <= effective_date <= end_date:
            amount = event.amount or 0
            if event.currency != twin.home_currency:
                amount = data.converter.convert(
                    amount, event.currency, twin.home_currency, effective_date
                )
            flows[effective_date].append(("debit", amount, event.description))
    
    for event in twin.pending_credits:
        effective_date = event.settlement_date or event.event_date
        if effective_date and start_date <= effective_date <= end_date:
            # Skip if this is a salary already handled by income streams
            if event.category == "salary" and effective_date in income_stream_dates:
                continue
            amount = event.amount or 0
            if event.currency != twin.home_currency:
                amount = data.converter.convert(
                    amount, event.currency, twin.home_currency, effective_date
                )
            flows[effective_date].append(("credit", amount, event.description))
    
    return flows

