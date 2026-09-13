"""
AFFORDAI Pydantic Models

Strict schemas for all input/output data structures.
Enforces the exact output schema required by the problem statement.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════════

class AffordabilityStatus(str, Enum):
    AFFORDABLE_NOW = "affordable_now"
    AFFORDABLE_WITH_PLAN = "affordable_with_plan"
    AFFORDABLE_LATER = "affordable_later"
    NOT_AFFORDABLE = "not_affordable"


class PaymentMethod(str, Enum):
    FULL_PAYMENT = "full_payment"
    PARTIAL_PAYMENT = "partial_payment"
    INSTALLMENTS = "installments"
    WAIT = "wait"
    NOT_RECOMMENDED = "not_recommended"


class EventStatus(str, Enum):
    SETTLED = "settled"
    PENDING = "pending"
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    FAILED = "failed"
    UNREALIZED = "unrealized"


class Flexibility(str, Enum):
    FIXED = "fixed"
    STOPPABLE = "stoppable"
    REDUCIBLE = "reducible"
    REDUCIBLE_OR_STOPPABLE = "reducible_or_stoppable"


# ═══════════════════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FinancialRequest:
    """A single request from requests.csv."""
    request_id: str
    user_id: str
    request_date: date
    request_type: str
    requested_amount: float
    desired_completion_date: date
    allows_partial_payment: bool
    request_text: str


@dataclass
class UserProfile:
    """User financial profile from financial_profiles.csv."""
    user_id: str
    home_currency: str
    current_available_balance: float
    minimum_balance_to_keep: float
    financial_priorities: list[str]
    expense_categories_to_protect: list[str]
    expense_categories_user_is_willing_to_reduce: list[str]
    expense_categories_user_is_willing_to_stop: list[str]
    payment_methods_user_will_consider: list[str]
    max_installment_months: Optional[int]


@dataclass
class FinancialEvent:
    """A single financial event from financial_events.csv."""
    event_id: str
    user_id: str
    event_type: str
    description: str
    category: str
    direction: str  # 'debit' or 'credit'
    amount: Optional[float]
    currency: str
    event_date: date
    settlement_date: Optional[date]
    status: str
    linked_event_id: Optional[str]
    flexibility: str
    minimum_allowed_amount: Optional[float]


@dataclass
class PaymentOption:
    """A payment option from request_payment_options.csv."""
    payment_option_id: str
    request_id: str
    payment_method: str  # 'full_payment' or 'installments'
    payment_amount: float
    number_of_payments: int
    first_payment_date: Optional[date]
    payment_frequency_days: Optional[int]
    financing_fee: float
    total_payable_amount: float


@dataclass
class Message:
    """A message from messages.csv."""
    message_id: str
    user_id: str
    request_id: Optional[str]
    related_event_id: Optional[str]
    sent_at: str
    source_type: str
    message_text: str


@dataclass
class ImageMapping:
    """An image mapping from images.csv."""
    image_id: str
    user_id: str
    request_id: Optional[str]
    related_event_id: str


@dataclass
class ExchangeRate:
    """An exchange rate from exchange_rates.csv."""
    rate_date: date
    from_currency: str
    to_currency: str
    rate: float


# ═══════════════════════════════════════════════════════════════════════════════
# Financial Safety Twin
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RecurringExpense:
    """A detected recurring expense pattern."""
    category: str
    median_amount: float
    typical_day_of_month: int
    flexibility: str
    minimum_allowed_amount: Optional[float]
    sample_event_id: str  # Reference event for stop/reduce format


@dataclass
class IncomeStream:
    """A confirmed income stream."""
    amount: float
    day_of_month: int
    currency: str
    source: str  # 'salary', 'freelance', etc.
    is_confirmed: bool
    next_date: Optional[date]


@dataclass
class MessageAdjustment:
    """A financial adjustment extracted from a message."""
    adjustment_type: str  # 'salary_change', 'income_end', 'refund_pending', etc.
    amount: Optional[float]
    effective_date: Optional[date]
    description: str
    confidence: float


@dataclass
class FinancialSafetyTwin:
    """Complete financial profile for a user — the 'Safety Twin'."""
    user_id: str
    home_currency: str
    current_balance: float
    minimum_balance: float
    
    # Income
    income_streams: list[IncomeStream] = field(default_factory=list)
    income_adjustments: list[MessageAdjustment] = field(default_factory=list)
    
    # Recurring expenses
    recurring_expenses: list[RecurringExpense] = field(default_factory=list)
    
    # One-off pending/scheduled
    pending_debits: list[FinancialEvent] = field(default_factory=list)
    pending_credits: list[FinancialEvent] = field(default_factory=list)
    
    # Preferences
    priorities: list[str] = field(default_factory=list)
    protected_categories: list[str] = field(default_factory=list)
    willing_to_reduce: list[str] = field(default_factory=list)
    willing_to_stop: list[str] = field(default_factory=list)
    accepted_payment_methods: list[str] = field(default_factory=list)
    max_installment_months: Optional[int] = None


# ═══════════════════════════════════════════════════════════════════════════════
# Strategy & Decision Models
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PaymentPlanEntry:
    """A single payment in a payment plan."""
    payment_date: date
    amount: float


@dataclass
class SpendingChange:
    """A recommended spending change."""
    action: str  # 'stop' or 'reduce_to'
    event_id: str
    reduce_to_amount: Optional[float] = None

    def to_string(self) -> str:
        if self.action == "stop":
            return f"stop:{self.event_id}"
        else:
            # Format amount: remove trailing zeros after decimal
            amt = self.reduce_to_amount
            if amt is not None:
                if amt == int(amt):
                    amt_str = str(int(amt))
                else:
                    amt_str = f"{amt:.2f}".rstrip('0').rstrip('.')
                return f"reduce_to:{self.event_id}:{amt_str}"
            return f"reduce_to:{self.event_id}"


@dataclass
class CashFlowForecast:
    """Result of a cash-flow simulation."""
    daily_balances: dict  # date -> balance
    minimum_balance_reached: float
    minimum_balance_date: date
    total_income: float
    total_expenses: float
    is_safe: bool  # True if min balance never breached


@dataclass
class StrategyResult:
    """Result of evaluating a single payment strategy."""
    strategy_name: str
    is_valid: bool
    payment_method: str
    payment_plan: list[PaymentPlanEntry]
    amount_safe_to_pay: float
    earliest_full_payment_date: Optional[date]
    spending_changes: list[SpendingChange]
    safety_margin: float  # min balance above minimum
    total_cost: float
    forecast: Optional[CashFlowForecast]
    rejection_reason: Optional[str] = None


@dataclass
class AgentDecision:
    """Final output for a single request — matches exact output.csv schema."""
    request_id: str
    amount_safe_to_pay: float
    affordability_status: str
    recommended_payment_method: str
    payment_plan: str  # "YYYY-MM-DD:amount|YYYY-MM-DD:amount" or "none"
    earliest_date_for_full_payment: str  # "YYYY-MM-DD" or ""
    spending_changes_needed: str  # "none", "stop:event_XXX", etc.
    decision_explanation: str

    def to_csv_row(self) -> dict:
        """Convert to dict matching output.csv column names."""
        return {
            "request_id": self.request_id,
            "amount_safe_to_pay": self.amount_safe_to_pay,
            "affordability_status": self.affordability_status,
            "recommended_payment_method": self.recommended_payment_method,
            "payment_plan": self.payment_plan,
            "earliest_date_for_full_payment": self.earliest_date_for_full_payment,
            "spending_changes_needed": self.spending_changes_needed,
            "decision_explanation": self.decision_explanation,
        }
