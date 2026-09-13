"""
AFFORDAI Profile Builder

Builds a Financial Safety Twin for each user by:
1. Detecting recurring expense patterns from historical events
2. Identifying income streams and salary patterns
3. Incorporating message-derived adjustments (salary changes, income terminations)
4. Cataloging pending/scheduled events
"""

from __future__ import annotations
from collections import defaultdict
from datetime import date, timedelta
from statistics import median
from typing import Optional

from backend.data_loader import DataStore
from backend.models import (
    FinancialSafetyTwin, RecurringExpense, IncomeStream,
    FinancialEvent, MessageAdjustment,
)
from backend.config import (
    EVENT_SETTLED, EVENT_PENDING, EVENT_SCHEDULED,
    IGNORED_EVENT_STATUSES,
)


def build_safety_twin(
    user_id: str,
    request_date: date,
    data: DataStore,
    message_adjustments: list[MessageAdjustment] | None = None,
) -> FinancialSafetyTwin:
    """
    Build the Financial Safety Twin for a given user at a given request date.
    
    The twin represents everything we know about the user's financial state:
    - Current balance and minimum balance
    - Recurring income and expenses (detected from historical patterns)
    - Pending/scheduled one-off events
    - Message-derived adjustments (salary changes, income terminations, etc.)
    - Preferences (what they're willing to reduce/stop, accepted payment methods)
    """
    profile = data.profiles.get(user_id)
    if not profile:
        raise ValueError(f"No profile found for {user_id}")
    
    events = data.events_by_user.get(user_id, [])
    
    # Build the twin
    twin = FinancialSafetyTwin(
        user_id=user_id,
        home_currency=profile.home_currency,
        current_balance=profile.current_available_balance,
        minimum_balance=profile.minimum_balance_to_keep,
        priorities=profile.financial_priorities,
        protected_categories=profile.expense_categories_to_protect,
        willing_to_reduce=profile.expense_categories_user_is_willing_to_reduce,
        willing_to_stop=profile.expense_categories_user_is_willing_to_stop,
        accepted_payment_methods=profile.payment_methods_user_will_consider,
        max_installment_months=profile.max_installment_months,
    )
    
    # Detect recurring expenses
    twin.recurring_expenses = _detect_recurring_expenses(events, request_date, profile.home_currency, data)
    
    # Detect income streams
    twin.income_streams = _detect_income_streams(events, request_date, profile.home_currency, data)
    
    # Collect pending/scheduled events
    twin.pending_debits, twin.pending_credits = _collect_pending_events(events, request_date)
    
    # Apply message adjustments
    if message_adjustments:
        twin.income_adjustments = message_adjustments
        _apply_message_adjustments(twin, message_adjustments, request_date)
    
    return twin


def _detect_recurring_expenses(
    events: list[FinancialEvent],
    request_date: date,
    home_currency: str,
    data: DataStore,
) -> list[RecurringExpense]:
    """
    Detect recurring monthly expenses from historical settled events.
    
    Groups events by category, checks for monthly patterns, and returns
    the median amount and typical day-of-month for each recurring expense.
    """
    # Only look at settled debit events before request_date
    settled_debits = [
        e for e in events
        if e.status == EVENT_SETTLED
        and e.direction == "debit"
        and e.event_date is not None
        and e.event_date <= request_date
        and e.amount is not None
        and e.amount > 0
    ]
    
    # Group by category
    by_category: dict[str, list[FinancialEvent]] = defaultdict(list)
    for e in settled_debits:
        by_category[e.category].append(e)
    
    recurring = []
    
    for category, cat_events in by_category.items():
        if len(cat_events) < 2:
            continue
        
        # Sort by date
        cat_events.sort(key=lambda e: e.event_date)
        
        # Check if this looks like a monthly pattern
        # For subscriptions and fixed bills (rent, utilities, etc.),
        # look for consistent day-of-month patterns
        amounts = []
        days_of_month = []
        flexibilities = []
        min_amounts = []
        sample_event_id = cat_events[-1].event_id  # Most recent event
        
        for e in cat_events:
            # Convert to home currency if needed
            if e.currency == home_currency:
                amt = e.amount
            else:
                amt = data.converter.convert(e.amount, e.currency, home_currency, e.event_date)
            amounts.append(amt)
            days_of_month.append(e.event_date.day)
            flexibilities.append(e.flexibility)
            if e.minimum_allowed_amount is not None:
                min_amounts.append(e.minimum_allowed_amount)
        
        # Determine if this is recurring (monthly)
        # Check: events span multiple months and appear at least monthly
        months_covered = set()
        for e in cat_events:
            months_covered.add((e.event_date.year, e.event_date.month))
        
        if len(months_covered) < 2:
            continue
        
        # Check frequency — should average to roughly monthly
        # Some categories (groceries, transport, dining) occur weekly
        date_diffs = []
        for i in range(1, len(cat_events)):
            diff = (cat_events[i].event_date - cat_events[i-1].event_date).days
            if diff > 0:
                date_diffs.append(diff)
        
        if not date_diffs:
            continue
        
        avg_interval = sum(date_diffs) / len(date_diffs)
        
        # Determine typical day of month and monthly amount
        if avg_interval >= 20:
            # Monthly pattern — use median of individual amounts
            monthly_amount = median(amounts)
            typical_day = int(median(days_of_month))
        elif avg_interval >= 5:
            # Weekly/biweekly — sum up to monthly
            # Calculate average monthly total
            total_amount = sum(amounts)
            months_span = len(months_covered)
            monthly_amount = total_amount / months_span
            typical_day = int(median(days_of_month))
        else:
            # Too frequent (daily) — skip
            continue
        
        # Determine flexibility (use most recent)
        flex = flexibilities[-1] if flexibilities else "fixed"
        min_amount = min_amounts[-1] if min_amounts else None
        
        # If this is a weekly category (groceries, dining, transport), 
        # we'll store the monthly total
        recurring.append(RecurringExpense(
            category=category,
            median_amount=monthly_amount,
            typical_day_of_month=typical_day,
            flexibility=flex,
            minimum_allowed_amount=min_amount,
            sample_event_id=sample_event_id,
        ))
    
    return recurring


def _detect_income_streams(
    events: list[FinancialEvent],
    request_date: date,
    home_currency: str,
    data: DataStore,
) -> list[IncomeStream]:
    """
    Detect income streams from salary/income events.
    
    Looks for:
    - Regular salary payments (monthly)
    - The next scheduled/confirmed salary
    - One-off income (bonuses, arrears) — NOT counted as recurring
    """
    # Collect income events
    income_events = [
        e for e in events
        if e.direction == "credit"
        and e.event_type == "income"
        and e.amount is not None
        and e.amount > 0
    ]
    
    if not income_events:
        return []
    
    income_events.sort(key=lambda e: e.event_date)
    
    streams = []
    
    # Find the next confirmed salary (scheduled event)
    scheduled_income = [
        e for e in income_events
        if e.status == EVENT_SCHEDULED
        and e.event_date >= request_date
    ]
    
    # Find settled salary events to determine pattern
    settled_income = [
        e for e in income_events
        if e.status == EVENT_SETTLED
        and e.category == "salary"
    ]
    
    # Priority: scheduled salary > regular settled > any settled (fallback)
    if scheduled_income:
        # Best source: a confirmed scheduled future salary
        si = scheduled_income[0]
        salary_amount = si.amount
        if si.currency != home_currency:
            salary_amount = data.converter.convert(
                salary_amount, si.currency, home_currency, si.event_date
            )
        
        # Detect salary day from history or scheduled event
        salary_days = [e.event_date.day for e in settled_income[-6:]] if settled_income else []
        salary_days.append(si.event_date.day)
        typical_salary_day = int(median(salary_days))
        
        streams.append(IncomeStream(
            amount=salary_amount,
            day_of_month=typical_salary_day,
            currency=home_currency,
            source="salary",
            is_confirmed=True,
            next_date=si.event_date,
        ))
    elif settled_income:
        # No scheduled salary, use most recent settled salary
        # Filter out one-off items but keep as fallback
        regular_salaries = [
            e for e in settled_income
            if "bonus" not in e.description.lower()
            and "arrear" not in e.description.lower()
            and "one-time" not in e.description.lower()
        ]
        
        # Use regular if available, otherwise fall back to all settled
        source_salaries = regular_salaries if regular_salaries else settled_income
        
        latest = source_salaries[-1]
        
        # CRITICAL: detect income termination from event description
        # e.g. "Final employer payroll" means salary has ended
        income_ended_keywords = ["final ", "last payroll", "last salary", "termination", "severance", "farewell payroll"]
        is_income_ended = any(kw in latest.description.lower() for kw in income_ended_keywords)
        
        if is_income_ended:
            # Income terminated — stream with amount=0 / unconfirmed
            streams.append(IncomeStream(
                amount=0,
                day_of_month=latest.event_date.day,
                currency=home_currency,
                source="salary",
                is_confirmed=False,
                next_date=None,
            ))
        else:
            salary_amount = latest.amount
            if latest.currency != home_currency:
                salary_amount = data.converter.convert(
                    salary_amount, latest.currency, home_currency, latest.event_date
                )
            salary_days = [e.event_date.day for e in source_salaries[-6:]]
            typical_salary_day = int(median(salary_days)) if salary_days else 15
            streams.append(IncomeStream(
                amount=salary_amount,
                day_of_month=typical_salary_day,
                currency=home_currency,
                source="salary",
                is_confirmed=True,
                next_date=None,
            ))
    
    return streams


def _collect_pending_events(
    events: list[FinancialEvent],
    request_date: date,
) -> tuple[list[FinancialEvent], list[FinancialEvent]]:
    """
    Collect pending and scheduled events that haven't settled yet.
    
    These are one-off future events that affect the cash flow forecast.
    """
    pending_debits = []
    pending_credits = []
    
    for e in events:
        if e.status not in (EVENT_PENDING, EVENT_SCHEDULED):
            continue
        if e.amount is None or e.amount <= 0:
            continue
        
        # Use settlement_date if available, otherwise event_date
        effective_date = e.settlement_date or e.event_date
        if effective_date is None:
            continue
        
        if e.direction == "debit":
            pending_debits.append(e)
        elif e.direction == "credit":
            pending_credits.append(e)
    
    return pending_debits, pending_credits


def _apply_message_adjustments(
    twin: FinancialSafetyTwin,
    adjustments: list[MessageAdjustment],
    request_date: date,
) -> None:
    """
    Apply message-derived adjustments to the Financial Safety Twin.
    
    This modifies income streams and recurring expenses based on
    information extracted from messages (salary changes, income
    terminations, rent increases, etc.)
    """
    for adj in adjustments:
        if adj.adjustment_type == "salary_change" and adj.amount is not None:
            # Update salary amount
            for stream in twin.income_streams:
                if stream.source == "salary":
                    # Only apply if effective date is relevant
                    if adj.effective_date is None or adj.effective_date <= request_date + timedelta(days=90):
                        stream.amount = adj.amount
                        if adj.effective_date:
                            stream.next_date = adj.effective_date
                    break
        
        elif adj.adjustment_type == "new_income" and adj.amount is not None:
            # New income source (e.g., first salary from new employer)
            day = adj.effective_date.day if adj.effective_date else 15
            twin.income_streams.append(IncomeStream(
                amount=adj.amount,
                day_of_month=day,
                currency=twin.home_currency,
                source="salary",
                is_confirmed=True,
                next_date=adj.effective_date,
            ))
        
        elif adj.adjustment_type == "income_end":
            # Employment ended — remove or zero out salary
            for stream in twin.income_streams:
                if stream.source == "salary":
                    stream.is_confirmed = False
                    stream.amount = 0
                    break
        
        elif adj.adjustment_type == "salary_confirmed" and adj.amount is not None:
            # Confirm salary amount and/or date
            found = False
            for stream in twin.income_streams:
                if stream.source == "salary":
                    stream.amount = adj.amount
                    stream.is_confirmed = True
                    if adj.effective_date:
                        stream.next_date = adj.effective_date
                    found = True
                    break
            if not found:
                twin.income_streams.append(IncomeStream(
                    amount=adj.amount,
                    day_of_month=adj.effective_date.day if adj.effective_date else 15,
                    currency=twin.home_currency,
                    source="salary",
                    is_confirmed=True,
                    next_date=adj.effective_date,
                ))
        
        elif adj.adjustment_type == "payment_delay" and adj.effective_date:
            # Update salary date
            for stream in twin.income_streams:
                if stream.source == "salary":
                    stream.next_date = adj.effective_date
                    stream.day_of_month = adj.effective_date.day
                    break
        
        elif adj.adjustment_type == "rent_increase" and adj.amount is not None:
            # Find and update rent expense
            for exp in twin.recurring_expenses:
                if exp.category == "rent":
                    # adj.amount might be a percentage or absolute
                    if adj.amount < 1:  # Percentage (e.g., 0.12 for 12%)
                        exp.median_amount *= (1 + adj.amount)
                    elif adj.amount < 100:  # Percentage like 12
                        exp.median_amount *= (1 + adj.amount / 100)
                    else:
                        exp.median_amount = adj.amount
                    break
