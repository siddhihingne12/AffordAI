"""
AFFORDAI Decision Agent

Uses Gemini LLM to generate personalized decision explanations.
All financial calculations are done BEFORE this step — the LLM only
writes the human-friendly explanation based on computed results.
"""

from __future__ import annotations
import json
from typing import Optional

from backend.config import get_gemini_client, GEMINI_MODEL
from backend.models import (
    FinancialSafetyTwin, FinancialRequest, StrategyResult,
    AgentDecision, PaymentPlanEntry, SpendingChange,
)
from backend.safety_engine import determine_affordability_status, compute_safety_score
from backend.utils import format_amount, format_payment_plan, format_spending_changes
from backend.data_loader import DataStore


def generate_decision(
    twin: FinancialSafetyTwin,
    request: FinancialRequest,
    best_strategy: StrategyResult,
    data: DataStore,
) -> AgentDecision:
    """
    Generate the final decision for a request.
    
    Combines the deterministic strategy result with an LLM-generated
    explanation to produce the complete output row.
    """
    # Determine affordability status
    status = determine_affordability_status(best_strategy, request)
    
    # Format payment plan
    plan_str = format_payment_plan(best_strategy.payment_plan)
    
    # Format spending changes
    changes_str = format_spending_changes(best_strategy.spending_changes)
    
    # Format earliest date
    earliest_str = ""
    if best_strategy.earliest_full_payment_date:
        earliest_str = best_strategy.earliest_full_payment_date.isoformat()
    
    # Determine payment method for output
    method = best_strategy.payment_method
    
    # Amount safe to pay — capped at requested amount
    # (safe amount = how much of THIS request can be paid, not total disposable)
    safe_amount = min(best_strategy.amount_safe_to_pay, request.requested_amount)
    
    # Generate explanation
    explanation = _generate_explanation(
        twin, request, best_strategy, status, method, data
    )
    
    return AgentDecision(
        request_id=request.request_id,
        amount_safe_to_pay=round(safe_amount, 2),
        affordability_status=status,
        recommended_payment_method=method,
        payment_plan=plan_str,
        earliest_date_for_full_payment=earliest_str,
        spending_changes_needed=changes_str,
        decision_explanation=explanation,
    )


def _generate_explanation(
    twin: FinancialSafetyTwin,
    request: FinancialRequest,
    strategy: StrategyResult,
    status: str,
    method: str,
    data: DataStore,
) -> str:
    """
    Generate a concise, personalized explanation using Gemini.
    
    The explanation should be 1-2 sentences, evidence-based, and mention
    specific amounts and dates.
    """
    client = get_gemini_client()
    
    currency = twin.home_currency
    min_bal = format_amount(twin.minimum_balance)
    req_amount = format_amount(request.requested_amount)
    safe_amount = format_amount(strategy.amount_safe_to_pay)
    
    # Build context for the LLM
    context_parts = [
        f"Currency: {currency}",
        f"Requested amount: {currency} {req_amount}",
        f"Request type: {request.request_type}",
        f"Minimum balance to keep: {currency} {min_bal}",
        f"Affordability status: {status}",
        f"Recommended method: {method}",
        f"Amount safe to pay today: {currency} {safe_amount}",
        f"Desired completion date: {request.desired_completion_date.isoformat()}",
    ]
    
    if strategy.payment_plan:
        plan_parts = []
        for p in strategy.payment_plan:
            plan_parts.append(f"{p.payment_date.isoformat()}: {currency} {format_amount(p.amount)}")
        context_parts.append(f"Payment plan: {' | '.join(plan_parts)}")
    
    if strategy.earliest_full_payment_date:
        context_parts.append(f"Earliest full payment date: {strategy.earliest_full_payment_date.isoformat()}")
    
    if strategy.spending_changes:
        change_descs = []
        for change in strategy.spending_changes:
            evt = data.events_by_id.get(change.event_id)
            desc = evt.description if evt else change.event_id
            if change.action == "stop":
                change_descs.append(f"Stop: {desc}")
            else:
                change_descs.append(f"Reduce {desc} to {currency} {format_amount(change.reduce_to_amount)}")
        context_parts.append(f"Spending changes: {'; '.join(change_descs)}")
    
    context = "\n".join(context_parts)
    
    prompt = f"""Generate a SHORT decision explanation (1-2 sentences) for this financial recommendation.

{context}

RULES:
- Be concise: maximum 2 sentences.
- Include specific amounts with currency code.
- For amounts, use comma-separated thousands (e.g., "ZAR 25,256" or "IDR 15,952,906.67").
- Mention the minimum balance that will be maintained.
- Match these styles exactly:

Example styles by status:
- affordable_now: "Pay {{currency}} {{amount}} today. This leaves at least {{currency}} {{min_balance}} available over the next 90 days."
- affordable_with_plan (installments): "Use {{n}} installments of {{currency}} {{amount}}, starting {{date}}. This leaves at least {{currency}} {{min_balance}} available."
- affordable_with_plan (spending changes): "Stop/Reduce the {{expense_name}}, then pay {{currency}} {{amount}} today. This leaves at least {{currency}} {{min_balance}} available."
- affordable_later (wait): "Wait until {{date}}, then pay {{currency}} {{amount}} in full. Paying earlier would put the {{currency}} {{min_balance}} minimum at risk."
- affordable_later (wait): "Pay {{currency}} {{amount}} in full on {{date}}. Paying earlier would take the balance below the {{currency}} {{min_balance}} minimum."
- not_affordable: "Do not make this payment by {{deadline}}. None of the available options keeps the {{currency}} {{min_balance}} minimum protected."
- not_affordable (partial possible): "Do not proceed with the {{currency}} {{amount}} request. Although {{currency}} {{safe_amount}} is available today, the full amount cannot be completed safely within 90 days."

Return ONLY the explanation text, no quotes or prefixes.
"""
    
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        explanation = response.text.strip()
        # Clean up any surrounding quotes
        if explanation.startswith('"') and explanation.endswith('"'):
            explanation = explanation[1:-1]
        if explanation.startswith("'") and explanation.endswith("'"):
            explanation = explanation[1:-1]
        return explanation
    except Exception as e:
        # Fallback: generate a template-based explanation
        return _fallback_explanation(twin, request, strategy, status, method)


def _fallback_explanation(
    twin: FinancialSafetyTwin,
    request: FinancialRequest,
    strategy: StrategyResult,
    status: str,
    method: str,
) -> str:
    """Generate a template-based explanation without LLM (fallback)."""
    currency = twin.home_currency
    min_bal = format_amount(twin.minimum_balance)
    req_amount = format_amount(request.requested_amount)
    safe_amount = format_amount(strategy.amount_safe_to_pay)
    
    if status == "affordable_now":
        return (f"Pay {currency} {req_amount} today. "
                f"This leaves at least {currency} {min_bal} available over the next 90 days.")
    
    elif status == "affordable_with_plan" and method == "installments":
        n = len(strategy.payment_plan)
        inst_amount = format_amount(strategy.payment_plan[0].amount) if strategy.payment_plan else "0"
        start_date = strategy.payment_plan[0].payment_date.strftime("%-d %B %Y") if strategy.payment_plan else ""
        return (f"Use {n} installments of {currency} {inst_amount}, starting {start_date}. "
                f"This leaves at least {currency} {min_bal} available.")
    
    elif status == "affordable_later":
        if strategy.earliest_full_payment_date:
            pay_date = strategy.earliest_full_payment_date.strftime("%-d %B %Y")
            return (f"Wait until {pay_date}, then pay {currency} {req_amount} in full. "
                    f"Paying earlier would put the {currency} {min_bal} minimum at risk.")
        return f"Wait for more income before proceeding with this {currency} {req_amount} request."
    
    elif status == "not_affordable":
        deadline = request.desired_completion_date.strftime("%-d %B %Y")
        if strategy.amount_safe_to_pay > 0:
            return (f"Do not proceed with the {currency} {req_amount} request. "
                    f"Although {currency} {safe_amount} is available today, the full amount "
                    f"cannot be completed safely within 90 days.")
        return (f"Do not make this payment by {deadline}. "
                f"None of the available options keeps the {currency} {min_bal} minimum protected.")
    
    return f"Recommendation for {currency} {req_amount}: {method}."
