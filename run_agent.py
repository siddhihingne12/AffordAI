"""
AFFORDAI — Main Agent Runner

Orchestrates the full pipeline:
1. Load all data
2. Extract image amounts (VLM)
3. Parse messages (LLM)
4. For each request: build twin → forecast → simulate → decide
5. Write output.csv
6. Run evaluation
"""

from __future__ import annotations
import sys
import time
import traceback
from pathlib import Path

from backend.data_loader import load_all_data, DataStore
from backend.evidence_extractor import extract_image_amounts, parse_all_messages
from backend.profile_builder import build_safety_twin
from backend.strategy_simulator import evaluate_all_strategies, select_best_strategy
from backend.safety_engine import validate_strategy
from backend.decision_agent import generate_decision
from backend.output_writer import write_output
from backend.models import AgentDecision


def run_agent(
    process_samples: bool = True,
    process_requests: bool = True,
) -> list[AgentDecision]:
    """
    Run the full AFFORDAI pipeline.
    
    Args:
        process_samples: If True, also process the 25 sample requests
        process_requests: If True, process the 250 output requests
    
    Returns:
        List of all AgentDecision objects
    """
    start_time = time.time()
    
    print("=" * 70)
    print("  AFFORDAI — AI-Powered Financial Affordability Agent")
    print("  \"Don't ask if you have enough money.")
    print("   Ask if you can safely afford it.\"")
    print("=" * 70)
    
    # ── Step 1: Load Data ──────────────────────────────────────────────────
    print("\n[DIR] STEP 1: Loading all data...")
    data = load_all_data()
    
    # ── Step 2: Extract Image Amounts (VLM) ────────────────────────────────
    print("\n[IMG]  STEP 2: Extracting amounts from images (VLM)...")
    try:
        image_amounts = extract_image_amounts(data)
    except Exception as e:
        print(f"   Image extraction failed: {e}")
        print("  Continuing without image amounts...")
        image_amounts = {}
    
    # ── Step 3: Parse Messages (LLM) ──────────────────────────────────────
    print("\n[MSG] STEP 3: Parsing messages for financial signals...")
    try:
        message_adjustments = parse_all_messages(data)
    except Exception as e:
        print(f"   Message parsing failed: {e}")
        print("  Continuing without message adjustments...")
        message_adjustments = {}
    
    # ── Step 4: Process Each Request ──────────────────────────────────────
    print("\n[RUN] STEP 4: Processing requests...")
    
    # Determine which requests to process
    request_ids_to_process = []
    
    if process_samples:
        # Process sample requests (request_01 to request_25)
        sample_ids = sorted(
            [rid for rid in data.requests if rid.startswith("request_") 
             and int(rid.split("_")[1]) <= 25],
            key=lambda x: int(x.split("_")[1])
        )
        request_ids_to_process.extend(sample_ids)
    
    if process_requests:
        # Process output requests (request_26 to request_275)
        output_ids = sorted(
            [rid for rid in data.requests if rid.startswith("request_")
             and int(rid.split("_")[1]) >= 26],
            key=lambda x: int(x.split("_")[1])
        )
        request_ids_to_process.extend(output_ids)
    
    total = len(request_ids_to_process)
    decisions: list[AgentDecision] = []
    errors: list[tuple[str, str]] = []
    
    for idx, request_id in enumerate(request_ids_to_process, 1):
        request = data.requests.get(request_id)
        if not request:
            print(f"   Request {request_id} not found, skipping")
            continue
        
        try:
            decision = _process_single_request(
                request_id, request, data, message_adjustments
            )
            decisions.append(decision)
            
            status_icon = {
                "affordable_now": "[OK]",
                "affordable_with_plan": "",
                "affordable_later": "[WAIT]",
                "not_affordable": "[FAIL]",
            }.get(decision.affordability_status, "[?]")
            
            print(f"  [{idx}/{total}] {status_icon} {request_id}: "
                  f"{decision.affordability_status} → {decision.recommended_payment_method} "
                  f"(safe: {decision.amount_safe_to_pay:,.2f})")
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            errors.append((request_id, error_msg))
            print(f"  [{idx}/{total}] [ERR] {request_id}: ERROR — {error_msg}")
            traceback.print_exc()
    
    # ── Step 5: Write Output ──────────────────────────────────────────────
    print("\n[OUT] STEP 5: Writing output...")
    
    # Write only the 250 output requests
    output_decisions = [d for d in decisions if int(d.request_id.split("_")[1]) >= 26]
    if output_decisions:
        write_output(output_decisions)
    
    # ── Step 6: Summary ───────────────────────────────────────────────────
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 70)
    print("  AFFORDAI — Pipeline Complete")
    print("=" * 70)
    print(f"\n[TIME]  Total time: {elapsed:.1f}s")
    print(f"[STAT] Processed: {len(decisions)}/{total} requests")
    
    if errors:
        print(f"[WARN]  Errors: {len(errors)}")
        for rid, err in errors:
            print(f"   - {rid}: {err}")
    
    # Status breakdown
    status_counts = {}
    method_counts = {}
    for d in decisions:
        status_counts[d.affordability_status] = status_counts.get(d.affordability_status, 0) + 1
        method_counts[d.recommended_payment_method] = method_counts.get(d.recommended_payment_method, 0) + 1
    
    print(f"\n[CHART] Status breakdown:")
    for status, count in sorted(status_counts.items()):
        pct = count / len(decisions) * 100 if decisions else 0
        print(f"   {status}: {count} ({pct:.1f}%)")
    
    print(f"\n[PAY] Method breakdown:")
    for method, count in sorted(method_counts.items()):
        pct = count / len(decisions) * 100 if decisions else 0
        print(f"   {method}: {count} ({pct:.1f}%)")
    
    return decisions


def _process_single_request(
    request_id: str,
    request,
    data: DataStore,
    message_adjustments: dict,
) -> AgentDecision:
    """Process a single request through the full pipeline."""
    
    user_id = request.user_id
    
    # Get user's message adjustments
    user_adjustments = message_adjustments.get(user_id, [])
    
    # Build Financial Safety Twin
    twin = build_safety_twin(
        user_id=user_id,
        request_date=request.request_date,
        data=data,
        message_adjustments=user_adjustments,
    )
    
    # Get payment options for this request
    payment_options = data.payment_options_by_request.get(request_id, [])
    
    # Evaluate all strategies
    strategies = evaluate_all_strategies(
        twin=twin,
        request=request,
        payment_options=payment_options,
        data=data,
    )
    
    # Validate each strategy
    for strategy in strategies:
        validate_strategy(strategy, twin, request)
    
    # Select best strategy
    best = select_best_strategy(strategies, twin, request)
    
    # Generate decision with explanation
    decision = generate_decision(
        twin=twin,
        request=request,
        best_strategy=best,
        data=data,
    )
    
    return decision


if __name__ == "__main__":
    # Parse command line arguments
    process_samples = "--samples" in sys.argv or "--all" in sys.argv
    process_requests = "--requests" in sys.argv or "--all" in sys.argv or len(sys.argv) == 1
    
    if "--help" in sys.argv:
        print("Usage: python run_agent.py [--samples] [--requests] [--all]")
        print("  --samples   Process only the 25 sample requests (for evaluation)")
        print("  --requests  Process only the 250 output requests (default)")
        print("  --all       Process both samples and output requests")
        sys.exit(0)
    
    decisions = run_agent(
        process_samples=process_samples,
        process_requests=process_requests,
    )
    
    # Run evaluation if samples were processed
    if process_samples:
        print("\n[SEARCH] Running evaluation against sample ground truth...")
        try:
            from evaluation.evaluate import run_evaluation
            sample_decisions = [d for d in decisions if int(d.request_id.split("_")[1]) <= 25]
            data = load_all_data()
            run_evaluation(sample_decisions, data)
        except ImportError:
            print("   Evaluation module not found")
        except Exception as e:
            print(f"   Evaluation error: {e}")
