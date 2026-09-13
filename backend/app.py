"""
AFFORDAI — FastAPI Backend

REST API for the React dashboard to consume.
Exposes endpoints for requests, user profiles, forecasts, and evaluation.
"""

from __future__ import annotations
import json
import traceback
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.data_loader import load_all_data, DataStore
from backend.evidence_extractor import extract_image_amounts, parse_all_messages
from backend.profile_builder import build_safety_twin
from backend.strategy_simulator import evaluate_all_strategies, select_best_strategy
from backend.safety_engine import validate_strategy, compute_safety_score
from backend.decision_agent import generate_decision
from backend.output_writer import write_output
from backend.models import AgentDecision
from backend.utils import format_amount

# ── App Setup ──────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AFFORDAI API",
    description="AI-Powered Financial Affordability & Safe Spending Agent",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global State ───────────────────────────────────────────────────────────────
_data: DataStore | None = None
_decisions: dict[str, dict] = {}  # request_id -> decision dict
_message_adjustments: dict = {}


def _get_data() -> DataStore:
    global _data
    if _data is None:
        _data = load_all_data()
    return _data


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "AFFORDAI"}


@app.get("/api/requests")
async def list_requests():
    """List all requests with their decisions (if available)."""
    data = _get_data()
    results = []
    
    for req_id, req in sorted(data.requests.items(), key=lambda x: int(x[0].split("_")[1])):
        profile = data.profiles.get(req.user_id, None)
        entry = {
            "request_id": req.request_id,
            "user_id": req.user_id,
            "request_date": req.request_date.isoformat() if req.request_date else "",
            "request_type": req.request_type,
            "requested_amount": req.requested_amount,
            "desired_completion_date": req.desired_completion_date.isoformat() if req.desired_completion_date else "",
            "allows_partial_payment": req.allows_partial_payment,
            "request_text": req.request_text,
            "currency": profile.home_currency if profile else "",
        }
        
        if req_id in _decisions:
            entry["decision"] = _decisions[req_id]
        
        results.append(entry)
    
    return {"requests": results, "total": len(results)}


@app.get("/api/requests/{request_id}")
async def get_request(request_id: str):
    """Get detailed info for a single request."""
    data = _get_data()
    
    req = data.requests.get(request_id)
    if not req:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")
    
    profile = data.profiles.get(req.user_id)
    messages = data.messages_by_request.get(request_id, [])
    payment_options = data.payment_options_by_request.get(request_id, [])
    
    result = {
        "request_id": req.request_id,
        "user_id": req.user_id,
        "request_date": req.request_date.isoformat() if req.request_date else "",
        "request_type": req.request_type,
        "requested_amount": req.requested_amount,
        "desired_completion_date": req.desired_completion_date.isoformat() if req.desired_completion_date else "",
        "allows_partial_payment": req.allows_partial_payment,
        "request_text": req.request_text,
        "profile": {
            "home_currency": profile.home_currency,
            "current_available_balance": profile.current_available_balance,
            "minimum_balance_to_keep": profile.minimum_balance_to_keep,
            "financial_priorities": profile.financial_priorities,
            "protected_categories": profile.expense_categories_to_protect,
            "willing_to_reduce": profile.expense_categories_user_is_willing_to_reduce,
            "willing_to_stop": profile.expense_categories_user_is_willing_to_stop,
            "accepted_methods": profile.payment_methods_user_will_consider,
        } if profile else None,
        "messages": [
            {
                "message_id": m.message_id,
                "source_type": m.source_type,
                "message_text": m.message_text,
                "sent_at": m.sent_at,
            }
            for m in messages
        ],
        "payment_options": [
            {
                "payment_option_id": o.payment_option_id,
                "payment_method": o.payment_method,
                "payment_amount": o.payment_amount,
                "number_of_payments": o.number_of_payments,
                "first_payment_date": o.first_payment_date.isoformat() if o.first_payment_date else "",
                "payment_frequency_days": o.payment_frequency_days,
                "financing_fee": o.financing_fee,
                "total_payable_amount": o.total_payable_amount,
            }
            for o in payment_options
        ],
        "decision": _decisions.get(request_id),
    }
    
    return result


@app.get("/api/users/{user_id}/profile")
async def get_user_profile(user_id: str):
    """Get a user's financial profile and event summary."""
    data = _get_data()
    
    profile = data.profiles.get(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    events = data.events_by_user.get(user_id, [])
    messages = data.messages_by_user.get(user_id, [])
    
    # Summarize events
    event_summary = {}
    for e in events:
        cat = e.category
        if cat not in event_summary:
            event_summary[cat] = {"count": 0, "total": 0, "direction": e.direction}
        event_summary[cat]["count"] += 1
        if e.amount:
            event_summary[cat]["total"] += e.amount
    
    return {
        "user_id": user_id,
        "home_currency": profile.home_currency,
        "current_available_balance": profile.current_available_balance,
        "minimum_balance_to_keep": profile.minimum_balance_to_keep,
        "financial_priorities": profile.financial_priorities,
        "event_count": len(events),
        "event_summary": event_summary,
        "message_count": len(messages),
    }


@app.get("/api/users/{user_id}/forecast")
async def get_user_forecast(user_id: str):
    """Get a user's cash flow forecast for dashboard visualization."""
    data = _get_data()
    
    profile = data.profiles.get(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    # Find the user's request to get request_date
    user_requests = [r for r in data.requests.values() if r.user_id == user_id]
    if not user_requests:
        raise HTTPException(status_code=404, detail=f"No requests found for {user_id}")
    
    req = user_requests[0]
    
    try:
        twin = build_safety_twin(user_id, req.request_date, data)
        
        from backend.forecast_engine import forecast_cash_flow
        forecast = forecast_cash_flow(twin, req.request_date, data)
        
        # Convert daily_balances to list for chart
        timeline = [
            {"date": d.isoformat(), "balance": round(b, 2)}
            for d, b in sorted(forecast.daily_balances.items())
        ]
        
        return {
            "user_id": user_id,
            "currency": profile.home_currency,
            "minimum_balance": profile.minimum_balance_to_keep,
            "timeline": timeline,
            "minimum_reached": round(forecast.minimum_balance_reached, 2),
            "minimum_date": forecast.minimum_balance_date.isoformat(),
            "is_safe": forecast.is_safe,
            "total_income": round(forecast.total_income, 2),
            "total_expenses": round(forecast.total_expenses, 2),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/process/{request_id}")
async def process_request(request_id: str):
    """Process a single request and return the decision."""
    data = _get_data()
    
    req = data.requests.get(request_id)
    if not req:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")
    
    try:
        user_adjustments = _message_adjustments.get(req.user_id, [])
        
        twin = build_safety_twin(
            user_id=req.user_id,
            request_date=req.request_date,
            data=data,
            message_adjustments=user_adjustments,
        )
        
        payment_options = data.payment_options_by_request.get(request_id, [])
        strategies = evaluate_all_strategies(twin, req, payment_options, data)
        
        for s in strategies:
            validate_strategy(s, twin, req)
        
        best = select_best_strategy(strategies, twin, req)
        decision = generate_decision(twin, req, best, data)
        safety_score = compute_safety_score(best, twin, req)
        
        decision_dict = {
            **decision.to_csv_row(),
            "safety_score": round(safety_score, 1),
        }
        _decisions[request_id] = decision_dict
        
        return decision_dict
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/run")
async def run_all():
    """Process all requests. Returns a summary."""
    from run_agent import run_agent
    
    try:
        decisions = run_agent(process_samples=False, process_requests=True)
        
        for d in decisions:
            _decisions[d.request_id] = d.to_csv_row()
        
        return {
            "processed": len(decisions),
            "status": "complete",
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/evaluation")
async def get_evaluation():
    """Get evaluation results if available."""
    report_path = Path(__file__).parent.parent / "EVALUATION_REPORT.md"
    
    if report_path.exists():
        return {"report": report_path.read_text(encoding="utf-8")}
    
    return {"report": "No evaluation report generated yet. Run with --all first."}


@app.get("/api/sample-outputs")
async def get_sample_outputs():
    """Get the ground truth sample outputs for comparison."""
    data = _get_data()
    
    samples = []
    for rid, expected in sorted(data.sample_outputs.items()):
        samples.append({
            "request_id": rid,
            "amount_safe_to_pay": float(expected.get("amount_safe_to_pay", 0)),
            "affordability_status": str(expected.get("affordability_status", "")),
            "recommended_payment_method": str(expected.get("recommended_payment_method", "")),
            "payment_plan": str(expected.get("payment_plan", "")),
            "earliest_date_for_full_payment": str(expected.get("earliest_date_for_full_payment", "")),
            "spending_changes_needed": str(expected.get("spending_changes_needed", "")),
            "decision_explanation": str(expected.get("decision_explanation", "")),
        })
    
    return {"samples": samples, "total": len(samples)}
